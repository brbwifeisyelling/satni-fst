"""Rakentaa sovelluksen tietokannan satni.db GiellaLT:n sanakirjoista ja FST-malleista.

LÄHTEET (ks. CREDITS.md):
  - Sanakirjat: GiellaLT / Divvun / Giellatekno, UiT Norjan arktinen yliopisto, lisenssi CC BY 4.0:
    dict-sme-fin, dict-sme-nob, dict-sme-eng, dict-sme-smn, dict-sme-smj, dict-sme-sma (käännökset)
    sekä dict-fin-sme ja dict-nob-sme (haku suomeksi ja norjaksi). https://github.com/giellalt
  - Taivutus: GiellaLT lang-sme -analysaattori ja -generaattori (src/fst/), lisenssi GPL-3.0.
CC BY 4.0 edellyttää muutosten mainitsemista: sanakirjat yhdistetään, niihin lisätään FST:llä
generoidut taivutusmuodot ja astevaihtelu, korjaukset.tsv:n korjaukset sovelletaan ja suomennosten
norjalaiset kirjaimet korjataan (ks. CREDITS.md: "Changes made to the dictionary data").
"""
import sqlite3
import subprocess
import os
import glob
import sys
import threading
import xml.etree.ElementTree as ET

import gradation

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(SCRIPT_DIR, "src", "fst", "generator-gt-norm.hfst")
ANALYSER = os.path.join(SCRIPT_DIR, "src", "fst", "analyser-gt-norm.hfst")
DB_FILE = os.path.join(SCRIPT_DIR, "satni.db")
# Käännöskielet ja niiden GiellaLT-sanakirjat. Suomi luetaan ensin: muiden kielten sanat liitetään
# suomenkielisen sanakirjan sanoihin, ja vain saamen FST:n tuntemat uudet sanat otetaan mukaan.
LANGUAGES = ["fin", "nob", "eng", "smn", "smj", "sma"]
XML_DIRS = {lang: os.path.join(SCRIPT_DIR, f"dict-sme-{lang}", "src") for lang in LANGUAGES}
# Käänteiset sanakirjat (suomi/norja -> saame): parantavat hakua suomen- ja norjankielisillä sanoilla
REVERSE_DIRS = {lang: os.path.join(SCRIPT_DIR, f"dict-{lang}-sme", "src") for lang in ("fin", "nob")}
TRANSLATION_COLUMNS = {lang: "finnish_translation" if lang == "fin" else f"{lang}_translation" for lang in LANGUAGES}
CORRECTIONS_FILE = os.path.join(SCRIPT_DIR, "korjaukset.tsv")

# Montako hfst-lookup-prosessia ajetaan rinnakkain
WORKERS = max(1, min(8, os.cpu_count() or 1))
# Aikaraja sekunteina yhdelle syötteelle: muutama muiden kielten sanakirjojen sana jumittaa analysaattorin
# loputtomiin (tavallinen sana vie ~30 ms)
LOOKUP_TIME_CUTOFF = "2"

# XML:n pos-attribuutti -> FST:n sanaluokkatagi
POS_MAP = {
    "N": "N", "V": "V", "A": "A", "ADV": "Adv", "NUM": "Num", "PRON": "Pron",
    "PCLE": "Pcle", "CC": "CC", "CS": "CS", "INTERJ": "Interj", "PO": "Po",
    "PR": "Pr", "CMP": "Cmp", "MWE": "MWE",
}
FST_POS_TAGS = set(POS_MAP.values())
NOMINALS = {"N", "A", "Num", "Pron"}

# Tiedostonimen perusteella arvattu sanaluokka, jos <l>-elementiltä puuttuu pos
FILE_POS = [
    ("n_prop", "N"), ("pronpers", "Pron"), ("prondem", "Pron"), ("pronindef", "Pron"),
    ("proninterr", "Pron"), ("pronrefl", "Pron"), ("pronrel", "Pron"),
    ("adv_", "Adv"), ("num_", "Num"), ("pcle_", "Pcle"), ("interj_", "Interj"),
    ("cc_", "CC"), ("cs_", "CS"), ("po_", "Po"), ("pr_", "Pr"), ("cmp_", "Cmp"),
    ("mwe_", "MWE"), ("v_", "V"), ("a_", "A"), ("n_", "N"),
]

PERSONS = ["Sg1", "Sg2", "Sg3", "Du1", "Du2", "Du3", "Pl1", "Pl2", "Pl3"]
CASES = ["Nom", "Gen", "Acc", "Ill", "Loc", "Com"]

# Taivutusmuodot: (tallennettava tagi, FST-pääte joka lisätään sanan FST-etuliitteeseen)
VERB_FORMS = (
    [(f"Ind+Prs+{p}", f"+Ind+Prs+{p}") for p in PERSONS] + [("Ind+Prs+ConNeg", "+Ind+Prs+ConNeg")] +
    [(f"Ind+Prt+{p}", f"+Ind+Prt+{p}") for p in PERSONS] + [("Ind+Prt+ConNeg", "+Ind+Prt+ConNeg")] +
    [(f"Cond+Prs+{p}", f"+Cond+Prs+{p}") for p in PERSONS] + [("Cond+Prs+ConNeg", "+Cond+Prs+ConNeg")] +
    [(f"Pot+Prs+{p}", f"+Pot+Prs+{p}") for p in PERSONS] + [("Pot+Prs+ConNeg", "+Pot+Prs+ConNeg")] +
    [(f"Imprt+{p}", f"+Imprt+{p}") for p in PERSONS] + [("Imprt+ConNeg", "+Imprt+ConNeg")] +
    [(t, f"+{t}") for t in ["Inf", "PrfPrc", "PrsPrc", "Ger", "VGen", "VAbess", "Sup",
                            "Actio+Nom", "Actio+Loc", "Actio+Com", "Actio+Ess"]]
)

NOMINAL_FORMS = (
    [(f"Sg+{c}", f"+Sg+{c}") for c in CASES] +
    [(f"Pl+{c}", f"+Pl+{c}") for c in CASES] +
    [("Ess", "+Ess")]
)

# Numeraaleilla ja pronomineilla voi olla erillinen attribuuttimuoto (esim. juohke)
NUM_PRON_FORMS = [("Attr", "+Attr")] + NOMINAL_FORMS

ADJECTIVE_FORMS = (
    [("Attr", "+Attr")] + NOMINAL_FORMS +
    [("Comp+Attr", "+Der/Comp+A+Attr"), ("Comp+Sg+Nom", "+Der/Comp+A+Sg+Nom"),
     ("Superl+Attr", "+Der/Superl+A+Attr"), ("Superl+Sg+Nom", "+Der/Superl+A+Sg+Nom")]
)

# Persoonapronominit ja refleksiivit: luku/persoona on jo etuliitteessä (mun+Pron+Pers+Sg1)
PERSONAL_PRONOUN_FORMS = [(c, f"+{c}") for c in CASES + ["Ess"]]

# Taivutustagit, joista FST-analyysin taivutusosa alkaa (kaikki ennen tätä on etuliitettä)
INFLECTION_START = {"Sg", "Pl", "Nom", "Attr", "Inf", "Ess"}


# Suomennoksissa on paikoin norjalaiset kirjaimet suomalaisten tilalla (esim. "viisikymmentæ")
FINNISH_LETTER_FIXES = str.maketrans({"æ": "ä", "Æ": "Ä", "ø": "ö", "Ø": "Ö"})


def fix_finnish_text(text):
    return text.translate(FINNISH_LETTER_FIXES)


# Sanaluokka puuttuu (dict-sme-eng: pos="Xxx"): päätellään toisesta sanakirjasta tai FST:stä
UNKNOWN_POS = "?"


def detect_pos(raw_pos, filename):
    if raw_pos:
        if raw_pos.strip().upper() == "XXX":
            return UNKNOWN_POS
        return POS_MAP.get(raw_pos.strip().upper(), raw_pos.strip())
    file_lower = filename.lower()
    for prefix, pos in FILE_POS:
        if file_lower.startswith(prefix):
            return pos
    return "N"


XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def _clean(text):
    return " ".join(text.split()) if text else ""


def _placeholder(text):
    """Täyttämätön käännöspaikka, esim. "_FIN_" tai "_NOB_"."""
    return len(text) > 2 and text.startswith("_") and text.endswith("_") and text[1:-1].isupper()


def parse_meaning(mg, lang="fin"):
    """Yksi merkitysryhmä <mg> kielellä lang: käännökset, selitykset, käyttörajoitus (<re>), tunnisteet (<gramm>),
    alue (<geo>: N = Norja, S = Suomi, R = Ruotsi) ja esimerkkilauseet (<xg>)."""
    fix = fix_finnish_text if lang == "fin" else (lambda text: text)
    meaning = new_meaning(lang)
    for tg in mg.findall('tg'):
        tg_lang = tg.get(XML_LANG)
        if tg_lang and tg_lang != lang:
            continue
        for t_elem in tg.findall('t'):
            text = fix(_clean(t_elem.text))
            if not text:
                continue
            # t_type="expl" on selitys (esim. "naisen nimi"), ei varsinainen käännös
            target = meaning["explanations"] if t_elem.get('t_type') == "expl" else meaning["translations"]
            if t_elem.get('dial'):
                text += f" ({t_elem.get('dial')})"
            if text not in target:
                target.append(text)
        for re_elem in tg.findall('re'):
            text = fix(_clean(re_elem.text))
            if text and text not in meaning["restrictions"]:
                meaning["restrictions"].append(text)
        for gramm in tg.findall('gramm'):
            text = _clean(gramm.text)
            # gramm-kentässä toistuu usein aluekoodi (N/S/R) tai pelkkä "-"
            if text and text not in ("-", "N", "S", "R") and text not in meaning["labels"]:
                meaning["labels"].append(text)
        for geo in tg.findall('geo'):
            text = _clean(geo.text)
            if text and text not in meaning["geo"]:
                meaning["geo"].append(text)
        for xg in tg.findall('xg'):
            sme = _clean(xg.findtext('x'))
            trans = fix(_clean(xg.findtext('xt')))
            if _placeholder(trans):
                trans = ""
            src = _clean((xg.find('x').get('src') if xg.find('x') is not None else "") or "")
            if sme:
                meaning["examples"].append((sme, trans, src))
    return meaning


def new_meaning(lang, translations=()):
    return {"lang": lang, "translations": list(translations), "explanations": [], "restrictions": [],
            "labels": [], "geo": [], "examples": []}


def find_entry(entries, by_lemma, lemma, pos, subtype):
    """Toisen kielen sanakirjan sana liitetään olemassa olevaan, jos lemma ja sanaluokka täsmäävät
    (alaluokka voi puuttua tai erota, esim. NomAg vain toisessa). Palauttaa avaimen tai None."""
    if (lemma, pos, subtype) in entries:
        return (lemma, pos, subtype)
    keys = by_lemma.get(lemma, [])
    same_pos = [k for k in keys if k[1] == pos]
    if len(same_pos) == 1:
        return same_pos[0]
    if pos == UNKNOWN_POS and len(keys) == 1:
        return keys[0]
    return None


def existing_lemma_entry(by_lemma, lemma, pos):
    """Käänteisen sanakirjan saamennos, jonka lemma on jo olemassa toisella sanaluokalla: liitetään
    olemassa olevaan sanaan eikä lisätä uutta. Käänteisissä sanakirjoissa sanaluokka on usein väärin
    (esim. dict-fin-sme: isä (A) -> áhčči (A)), mikä tuotti satoja kaksoissanoja. None, jos lemma on uusi."""
    keys = by_lemma.get(lemma, [])
    same_pos = [k for k in keys if k[1] == pos]
    return (same_pos or keys or [None])[0]


def parse_xml_dictionaries():
    """Palauttaa (sanat, lisätiedot). Sama lemma + sanaluokka + alaluokka yhdistetään yhdeksi riviksi,
    käännökset kerätään kielittäin: sana = (lemma, pos, alaluokka, sem_type, {kieli: "käännös, ..."}).
    Lisätiedot: {(lemma, pos, alaluokka): {"meanings": [...], "freq": n, "notes": [...], "new_from": kieli}}.
    new_from on muu kuin "fin", jos sana löytyi vain muun kielen sanakirjasta (tarkistetaan FST:llä)."""
    entries = {}
    by_lemma = {}

    for lang in LANGUAGES:
        xml_files = sorted(glob.glob(os.path.join(XML_DIRS[lang], "*.xml")))
        if not xml_files:
            print(f"Sanakirjaa dict-sme-{lang} ei löydy, ohitetaan (hae: ./hae_sanakirjat.sh).")
        merged = added = 0
        for filepath in xml_files:
            filename = os.path.basename(filepath)
            if filename == "meta.xml":
                continue
            print(f"Luetaan tiedostoa: dict-sme-{lang}/{filename}...")
            try:
                root = ET.parse(filepath).getroot()
            except ET.ParseError as e:
                print(f"Virhe XML-tiedoston {filename} käsittelyssä: {e}")
                continue

            for entry in root.iter('e'):
                lemma_elem = entry.find('lg/l')
                if lemma_elem is None or not lemma_elem.text or not lemma_elem.text.strip():
                    continue
                lemma = " ".join(lemma_elem.text.split())
                pos = detect_pos(lemma_elem.get('pos'), filename)
                subtype = lemma_elem.get('type') or ""
                if pos == "Prop":  # dict-sme-smj/smn/sma: pos="Prop"
                    pos, subtype = "N", "Prop"
                sem_type = lemma_elem.get('sem_type') or ""

                key = (lemma, pos, subtype)
                if lang != "fin":
                    key = find_entry(entries, by_lemma, lemma, pos, subtype) or key
                if key not in entries:
                    entries[key] = {"sem_type": sem_type, "translations": {}, "meanings": [], "freq": None,
                                    "notes": [], "new_from": lang}
                    by_lemma.setdefault(lemma, []).append(key)
                    added += lang != "fin"
                else:
                    merged += lang != "fin"
                data = entries[key]
                if not data["sem_type"]:
                    data["sem_type"] = sem_type

                for mg in entry.findall('mg'):
                    meaning = parse_meaning(mg, lang)
                    if any(meaning[k] for k in ("translations", "explanations", "examples")):
                        data["meanings"].append(meaning)
                    trans = data["translations"].setdefault(lang, [])
                    for text in meaning["translations"] + meaning["explanations"]:
                        if text not in trans:
                            trans.append(text)

                # Sanatason tiedot: yleisyys, murre, johdos, monikkosana
                freq = entry.find('lg').get('freq')
                if freq and freq.isdigit():
                    data["freq"] = max(int(freq), data["freq"] or 0)
                notes = []
                if lemma_elem.get('dial'):
                    notes.append(f"murre: {lemma_elem.get('dial')}")
                if lemma_elem.get('ader'):
                    notes.append(f"johdettu sanasta {lemma_elem.get('ader')}")
                if lemma_elem.get('nr') == "Pl":
                    notes.append("monikkosana")
                for note in notes:
                    if note not in data["notes"]:
                        data["notes"].append(note)
        if lang != "fin" and xml_files:
            print(f"  dict-sme-{lang}: {merged} käännöstä olemassa oleviin sanoihin, {added} uutta sanaehdokasta")

    parse_reverse_dictionaries(entries, by_lemma)

    words = [
        (lemma, pos, subtype, data["sem_type"], {l: ", ".join(t) for l, t in data["translations"].items() if t})
        for (lemma, pos, subtype), data in entries.items()
    ]
    details = {key: {k: data.get(k, []) if k == "reverse" else data[k]
                     for k in ("meanings", "freq", "notes", "new_from", "reverse")} for key, data in entries.items()}
    return words, details


def parse_reverse_dictionaries(entries, by_lemma):
    """dict-fin-sme ja dict-nob-sme: hakusana (suomi/norja) -> saamen sanat. Parit tallennetaan sanalle
    kenttään "reverse" [(kieli, hakusana, järjestys)], 0 = sanakirjan ensimmäinen saamennos. Saamen sana,
    jota muissa sanakirjoissa ei ole, lisätään uutena (tarkistetaan FST:llä kuten muutkin uudet sanat)."""
    for lang, xml_dir in REVERSE_DIRS.items():
        xml_files = sorted(glob.glob(os.path.join(xml_dir, "*.xml")))
        if not xml_files:
            print(f"Sanakirjaa dict-{lang}-sme ei löydy, ohitetaan (hae: ./hae_sanakirjat.sh).")
            continue
        fix = fix_finnish_text if lang == "fin" else (lambda text: text)
        pairs = added = 0
        for filepath in xml_files:
            filename = os.path.basename(filepath)
            if filename == "meta.xml":
                continue
            try:
                root = ET.parse(filepath).getroot()
            except ET.ParseError as e:
                print(f"Virhe XML-tiedoston {filename} käsittelyssä: {e}")
                continue
            for entry in root.iter('e'):
                head_elem = entry.find('lg/l')
                headword = fix(_clean(head_elem.text)) if head_elem is not None else ""
                if not headword:
                    continue
                order = 0
                for tg in entry.iter('tg'):
                    if tg.get(XML_LANG) not in (None, "sme"):
                        continue
                    for t_elem in tg.findall('t'):
                        lemma = _clean(t_elem.text)
                        if not lemma or _placeholder(lemma):
                            continue
                        pos = detect_pos(t_elem.get('pos') or head_elem.get('pos'), filename)
                        subtype = ""
                        if pos == "Prop":
                            pos, subtype = "N", "Prop"
                        key = find_entry(entries, by_lemma, lemma, pos, subtype) or existing_lemma_entry(
                            by_lemma, lemma, pos) or (lemma, pos, subtype)
                        if key not in entries:
                            entries[key] = {"sem_type": "", "translations": {}, "meanings": [],
                                            "freq": None, "notes": [], "new_from": f"{lang}-sme"}
                            by_lemma.setdefault(lemma, []).append(key)
                            added += 1
                        data = entries[key]
                        data.setdefault("reverse", []).append((lang, headword, order))
                        # Hakusanat tulevat käännöksiksi, jos sanalla ei ole tämän kielen käännöstä muista
                        # sanakirjoista (esim. vain dict-sme-nob:ssa ollut sana saa suomennoksen dict-fin-sme:stä)
                        filled = data.setdefault("reverse_langs", set())
                        if not data["translations"].get(lang):
                            filled.add(lang)
                        if lang in filled:
                            trans = data["translations"].setdefault(lang, [])
                            if headword not in trans:
                                trans.append(headword)
                                meaning = next((m for m in data["meanings"] if m["lang"] == lang), None)
                                if meaning is None:
                                    meaning = new_meaning(lang)
                                    data["meanings"].append(meaning)
                                meaning["translations"].append(headword)
                        order += 1
                        pairs += 1
        print(f"  dict-{lang}-sme: {pairs} hakusana-saamennos-paria, {added} uutta sanaehdokasta")


def apply_corrections(words, details):
    """Soveltaa korjaukset.tsv-tiedoston käsin tehdyt korjaukset XML:stä luettuihin sanoihin."""
    if not os.path.exists(CORRECTIONS_FILE):
        return words

    corrections = {}
    with open(CORRECTIONS_FILE, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) != 3 or not parts[0] or not parts[1]:
                print(f"  korjaukset.tsv rivi {line_no}: odotettiin 3 sarkaimella erotettua saraketta, ohitetaan")
                continue
            lemma, pos, trans = parts
            trans = fix_finnish_text(trans)
            corrections[(lemma, POS_MAP.get(pos.upper(), pos))] = trans

    result = []
    applied = set()
    for lemma, pos, subtype, sem_type, trans in words:
        key = (lemma, pos)
        if key in corrections:
            applied.add(key)
            if corrections[key] == "-":
                continue
            trans = {**trans, "fin": corrections[key]}
            # Korjattu suomennos korvaa XML:n suomenkieliset merkitykset (muut kielet säilyvät)
            info = details.setdefault((lemma, pos, subtype), {"freq": None, "notes": [], "meanings": [], "reverse": []})
            info["meanings"] = [new_meaning("fin", [corrections[key]])] + [
                m for m in info["meanings"] if m["lang"] != "fin"]
            info["new_from"] = "fin"
        result.append((lemma, pos, subtype, sem_type, trans))

    # Korjaustiedoston sanat, joita XML:ssä ei ollut, lisätään uusina
    for (lemma, pos), trans in corrections.items():
        if (lemma, pos) not in applied and trans != "-":
            result.append((lemma, pos, "", "", {"fin": trans}))
            details[(lemma, pos, "")] = {"freq": None, "notes": [], "new_from": "fin", "reverse": [],
                                         "meanings": [new_meaning("fin", [trans])]}
    print(f"Sovellettiin {len(corrections)} korjausta tiedostosta korjaukset.tsv.")
    return result


def run_hfst_lookup(fst_path, queries):
    """Ajaa kyselyt hfst-lookupilla rinnakkaisissa prosesseissa.
    Palauttaa {kysely: [tulos, ...]} vain onnistuneille kyselyille."""
    queries = list(dict.fromkeys(q for q in queries if "\t" not in q and "\n" not in q))
    if not queries:
        return {}

    chunk_size = (len(queries) + WORKERS - 1) // WORKERS
    chunks = [queries[i:i + chunk_size] for i in range(0, len(queries), chunk_size)]
    outputs = [None] * len(chunks)
    errors = []

    def worker(idx, chunk):
        try:
            proc = subprocess.run(
                ["hfst-lookup", "-q", "-t", LOOKUP_TIME_CUTOFF, fst_path],
                input="\n".join(chunk) + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if proc.returncode != 0:
                errors.append(proc.stderr.strip())
            outputs[idx] = proc.stdout
        except OSError as e:
            errors.append(str(e))
            outputs[idx] = ""

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(chunks)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        print(f"hfst-lookup virhe: {errors[0]}")

    results = {}
    for out in outputs:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            inp, surf = parts[0], parts[1].strip()
            if not surf or surf.endswith("+?") or (len(parts) > 2 and parts[2].strip() == "inf"):
                continue
            lst = results.setdefault(inp, [])
            if surf not in lst:
                lst.append(surf)
    return results


def split_analysis(analysis):
    """'buorránit+V+IV+Der/NomAct+N+Sg+Nom' -> ('buorránit+V+IV+Der/NomAct+N', '+Sg+Nom').
    Persoonapronominien luku (Sg1 jne.) jää etuliitteeseen."""
    parts = analysis.split("+")
    for i in range(1, len(parts)):
        if parts[i] in INFLECTION_START:
            return "+".join(parts[:i]), "+" + "+".join(parts[i:])
    return analysis, ""


def last_pos_tag(prefix):
    for tag in reversed(prefix.split("+")[1:]):
        if tag in FST_POS_TAGS:
            return tag
    return None


def base_form_pos(analyses):
    """Analyysien perusmuodon sanaluokka (esim. 'viessu+N+Sg+Nom' -> 'N'), tai None."""
    for analysis in analyses:
        prefix, tail = split_analysis(analysis)
        fst_pos = last_pos_tag(prefix)
        if fst_pos and "#" not in prefix and tail in ("", "+Inf", "+Sg+Nom", "+Pl+Nom", "+Nom", "+Attr"):
            return fst_pos
    return None


def filter_new_words(words, details, analyses):
    """Muiden kielten sanakirjoista tulleet uudet sanat otetaan mukaan vain, jos saamen analysaattori
    tuntee ne (karsii esim. dict-sme-smj:n luulajansaamenkieliset lemmat). Puuttuva sanaluokka
    päätellään analyysistä. Monisanaiset ilmaukset hyväksytään sellaisenaan."""
    result = {}
    dropped = {}
    for lemma, pos, subtype, sem_type, trans in words:
        info = details[(lemma, pos, subtype)]
        if info["new_from"] != "fin":
            if " " in lemma:
                pos = "MWE" if pos == UNKNOWN_POS else pos
            elif not analyses.get(lemma):
                dropped[info["new_from"]] = dropped.get(info["new_from"], 0) + 1
                continue
            elif pos == UNKNOWN_POS:
                # Vain taivutetun muodon analyysi (esim. diimmážii: diimmáš+A+Sg+Ill) = taipumaton sana
                pos = base_form_pos(analyses[lemma]) or "Adv"
        key = (lemma, pos, subtype)
        if key in result:  # sanaluokan päättely toi saman sanan kahdesti: yhdistetään
            old = result[key]
            for lang, text in trans.items():
                old[4][lang] = ", ".join(filter(None, [old[4].get(lang), text]))
            details[key]["meanings"] += info["meanings"]
            details[key]["reverse"] += info["reverse"]
            continue
        result[key] = (lemma, pos, subtype, sem_type, dict(trans))
        details[key] = info
    for lang, n in dropped.items():
        source = f"dict-{lang}" if lang.endswith("-sme") else f"dict-sme-{lang}"
        print(f"  {source}: {n} sanaa ohitettiin, koska saamen FST ei tunne niitä")
    return list(result.values())


def find_fst_prefixes(words, analyses):
    """Etsii analysaattorilla jokaiselle sanalle sen FST-etuliitteen, esim.
    mannat -> mannat+V+IV, Ánte -> Ánte+N+Prop+Sem/Mal, mun -> mun+Pron+Pers+Sg1."""
    prefixes = {}

    for lemma, pos, subtype, sem_type, _ in words:
        if pos == "MWE":
            continue
        candidates = []
        for analysis in analyses.get(lemma, []):
            prefix, tail = split_analysis(analysis)
            fst_pos = last_pos_tag(prefix)
            # Nominien välillä sallitaan sanaluokkaero (esim. galle: XML Num, FST Pron), mutta heikompana
            if fst_pos != pos and not (pos in NOMINALS and fst_pos in NOMINALS):
                continue
            # Hyväksytään vain perusmuodon analyysit (ei esim. omistusliitteellisiä)
            if pos == "V":
                ok = tail == "+Inf"
            elif pos in NOMINALS:
                ok = tail in ("+Sg+Nom", "+Pl+Nom", "+Nom", "+Attr")
            else:
                ok = tail == ""
            if not ok:
                continue
            tags = prefix.split("+")
            score = (
                0 if fst_pos == pos else 1,
                0 if not subtype or subtype in tags else 1,
                0 if not sem_type or f"Sem/{sem_type}" in tags else 1,
                prefix.count("#"),
                prefix.count("Der/"),
                0 if tail != "+Pl+Nom" else 1,
            )
            candidates.append((score, prefix))

        if candidates:
            best = min(c[0] for c in candidates)
            prefixes[(lemma, pos, subtype)] = list(dict.fromkeys(p for s, p in candidates if s == best))
        elif pos in NOMINALS or pos == "V":
            # Analysaattori ei tunne sanaa: kokeillaan silti suoraa muotoa
            extra = f"+{subtype}" if subtype and pos != "V" else ""
            prefixes[(lemma, pos, subtype)] = [f"{lemma}+{pos}{extra}"]
    return prefixes


def forms_for(pos, prefix):
    if pos == "V":
        return VERB_FORMS
    if pos == "A":
        return ADJECTIVE_FORMS
    if pos == "Pron" and any(p in prefix.split("+") for p in PERSONS):
        return PERSONAL_PRONOUN_FORMS
    if pos in ("Num", "Pron"):
        return NUM_PRON_FORMS
    if pos == "N":
        return NOMINAL_FORMS
    return []


def add_gradation(cursor):
    """Päättelee astevaihtelun (GD/HD) jokaiselle sanalle ja muodolle, ks. gradation.py."""
    print("Päätellään astevaihtelu (GD/HD)...")
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(dictionary)")]
    for col in ("gradation", "gd_cluster", "hd_cluster", "gradation_group", "gradation_row"):
        if col not in cols:
            cursor.execute(f"ALTER TABLE dictionary ADD COLUMN {col} TEXT")
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(paradigms)")]
    if "grade" not in cols:
        cursor.execute("ALTER TABLE paradigms ADD COLUMN grade TEXT")

    forms = {}
    for rowid, word_id, tag, surface in cursor.execute("SELECT rowid, word_id, tag, surface FROM paradigms"):
        forms.setdefault(word_id, []).append((rowid, tag, surface))

    word_updates, form_updates = [], []
    for word_id, lemma in cursor.execute("SELECT id, sme_lemma FROM dictionary").fetchall():
        rows = forms.get(word_id)
        if not rows:
            continue
        info, grades = gradation.analyse(lemma, [(tag, surf) for _, tag, surf in rows])
        info = info or {}
        word_updates.append((info.get("summary"), info.get("strong"), info.get("weak"),
                             info.get("group"), info.get("row"), word_id))
        for rowid, tag, surf in rows:
            grade = grades.get((tag, surf))
            form_updates.append((grade[0] if grade else None, rowid))

    cursor.executemany(
        "UPDATE dictionary SET gradation = ?, gd_cluster = ?, hd_cluster = ?, gradation_group = ?, gradation_row = ? WHERE id = ?",
        word_updates
    )
    cursor.executemany("UPDATE paradigms SET grade = ? WHERE rowid = ?", form_updates)
    print(f"  astevaihtelu tunnistettiin {sum(1 for u in word_updates if u[0])} sanalle")


def main():
    for path in (GENERATOR, ANALYSER):
        if not os.path.exists(path):
            print(f"FST-tiedostoa ei löydy: {path}")
            return

    words_list, details = parse_xml_dictionaries()
    words_list = apply_corrections(words_list, details)
    print(f"Löytyi yhteensä {len(words_list)} uniikkia sanaa XML-tiedostoista.")
    if not words_list:
        return

    print("Analysoidaan perusmuodot FST-analysaattorilla...")
    analyses = run_hfst_lookup(ANALYSER, [w[0] for w in words_list])
    words_list = filter_new_words(words_list, details, analyses)
    print(f"Mukaan otetaan {len(words_list)} sanaa.")
    prefixes = find_fst_prefixes(words_list, analyses)

    print("Ajetaan FST-generointi...")
    queries = []
    for lemma, pos, subtype, _, _ in words_list:
        for prefix in prefixes.get((lemma, pos, subtype), []):
            for _, suffix in forms_for(pos, prefix):
                queries.append(prefix + suffix)
    print(f"  {len(queries)} generointikyselyä, {WORKERS} rinnakkaista prosessia")
    generated = run_hfst_lookup(GENERATOR, queries)

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sme_lemma TEXT,
            pos TEXT,
            subtype TEXT,
            fst_tags TEXT,
            finnish_translation TEXT,
            nob_translation TEXT,
            eng_translation TEXT,
            smn_translation TEXT,
            smj_translation TEXT,
            sma_translation TEXT,
            freq INTEGER,
            notes TEXT
        )
    ''')
    # Merkitysryhmät (<mg>) ja niiden esimerkkilauseet (<xg>) kielittäin; nr juoksee kielen sisällä
    cursor.execute('''
        CREATE TABLE meanings (
            word_id INTEGER,
            lang TEXT,
            nr INTEGER,
            translations TEXT,
            explanations TEXT,
            restrictions TEXT,
            labels TEXT,
            geo TEXT,
            FOREIGN KEY(word_id) REFERENCES dictionary(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE examples (
            word_id INTEGER,
            lang TEXT,
            meaning_nr INTEGER,
            sme TEXT,
            translation TEXT,
            source TEXT,
            FOREIGN KEY(word_id) REFERENCES dictionary(id)
        )
    ''')
    # Käänteisten sanakirjojen hakusanat: nr 0 = sanakirjan ensisijainen saamennos hakusanalle
    cursor.execute('''
        CREATE TABLE reverse_index (
            word_id INTEGER,
            lang TEXT,
            headword TEXT,
            nr INTEGER,
            FOREIGN KEY(word_id) REFERENCES dictionary(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE paradigms (
            word_id INTEGER,
            tag TEXT,
            surface TEXT,
            grade TEXT,
            FOREIGN KEY(word_id) REFERENCES dictionary(id)
        )
    ''')

    print("Tallennetaan sanat ja taivutusmuodot tietokantaan...")
    stats = {}
    for lemma, pos, subtype, _, trans in sorted(words_list):
        word_prefixes = prefixes.get((lemma, pos, subtype), [])
        info = details.get((lemma, pos, subtype), {})
        cursor.execute(
            "INSERT INTO dictionary (sme_lemma, pos, subtype, fst_tags, " +
            ", ".join(TRANSLATION_COLUMNS.values()) + ", freq, notes) VALUES (?, ?, ?, ?, " +
            "?, " * len(TRANSLATION_COLUMNS) + "?, ?)",
            (lemma, pos, subtype, " | ".join(word_prefixes), *(trans.get(l, "") for l in TRANSLATION_COLUMNS),
             info.get("freq"), "; ".join(info.get("notes", [])))
        )
        w_id = cursor.lastrowid

        numbers = {}
        for meaning in info.get("meanings", []):
            lang = meaning["lang"]
            nr = numbers[lang] = numbers.get(lang, 0) + 1
            cursor.execute(
                "INSERT INTO meanings (word_id, lang, nr, translations, explanations, restrictions, labels, geo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (w_id, lang, nr, ", ".join(meaning["translations"]), ", ".join(meaning["explanations"]),
                 "; ".join(meaning["restrictions"]), ", ".join(meaning["labels"]), ",".join(meaning["geo"]))
            )
            cursor.executemany(
                "INSERT INTO examples (word_id, lang, meaning_nr, sme, translation, source) VALUES (?, ?, ?, ?, ?, ?)",
                [(w_id, lang, nr, sme, t, src) for sme, t, src in meaning["examples"]]
            )

        cursor.executemany(
            "INSERT INTO reverse_index (word_id, lang, headword, nr) VALUES (?, ?, ?, ?)",
            [(w_id, lang, head, nr) for lang, head, nr in dict.fromkeys(info.get("reverse", []))]
        )

        rows = []
        for prefix in word_prefixes:
            for tag, suffix in forms_for(pos, prefix):
                for surf in generated.get(prefix + suffix, []):
                    if (tag, surf) not in rows:
                        rows.append((tag, surf))
        cursor.executemany(
            "INSERT INTO paradigms (word_id, tag, surface) VALUES (?, ?, ?)",
            [(w_id, tag, surf) for tag, surf in rows]
        )

        s = stats.setdefault(pos, [0, 0])
        s[0] += 1
        if rows:
            s[1] += 1

    add_gradation(cursor)

    print("Luodaan tietokantaan indeksit...")
    cursor.execute("CREATE INDEX idx_lemma ON dictionary(sme_lemma COLLATE NOCASE);")
    cursor.execute("CREATE INDEX idx_trans ON dictionary(finnish_translation);")
    cursor.execute("CREATE INDEX idx_paradigms_word_id ON paradigms(word_id);")
    cursor.execute("CREATE INDEX idx_meanings_word_id ON meanings(word_id);")
    cursor.execute("CREATE INDEX idx_examples_word_id ON examples(word_id);")
    cursor.execute("CREATE INDEX idx_reverse_headword ON reverse_index(headword COLLATE NOCASE);")
    cursor.execute("CREATE INDEX idx_paradigms_surface ON paradigms(surface COLLATE NOCASE);")

    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

    print("\nSanaluokka      sanoja   joilla taivutusmuotoja")
    for pos, (total, with_forms) in sorted(stats.items(), key=lambda x: -x[1][0]):
        print(f"  {pos:12} {total:8} {with_forms:10}")
    print("Valmista! Tietokanta luotu onnistuneesti.")


if __name__ == "__main__":
    if "--vain-astevaihtelu" in sys.argv:
        # Päivittää vain astevaihtelutiedot olemassa olevaan tietokantaan (nopea, ei FST-ajoa)
        conn = sqlite3.connect(DB_FILE)
        add_gradation(conn.cursor())
        conn.commit()
        conn.close()
    else:
        main()
