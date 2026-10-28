import sqlite3
import subprocess
import os
import glob
import threading
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(SCRIPT_DIR, "src", "fst", "generator-gt-norm.hfst")
ANALYSER = os.path.join(SCRIPT_DIR, "src", "fst", "analyser-gt-norm.hfst")
DB_FILE = os.path.join(SCRIPT_DIR, "satni.db")
XML_DIR = os.path.join(SCRIPT_DIR, "dict-sme-fin", "src")
CORRECTIONS_FILE = os.path.join(SCRIPT_DIR, "korjaukset.tsv")

# Montako hfst-lookup-prosessia ajetaan rinnakkain
WORKERS = max(1, min(8, os.cpu_count() or 1))

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


def detect_pos(raw_pos, filename):
    if raw_pos:
        return POS_MAP.get(raw_pos.strip().upper(), raw_pos.strip())
    file_lower = filename.lower()
    for prefix, pos in FILE_POS:
        if file_lower.startswith(prefix):
            return pos
    return "N"


def parse_xml_dictionaries():
    # Sama lemma + sanaluokka + alaluokka yhdistetään yhdeksi riviksi, käännökset kerätään yhteen
    entries = {}
    xml_files = sorted(glob.glob(os.path.join(XML_DIR, "*.xml")))

    for filepath in xml_files:
        filename = os.path.basename(filepath)
        if filename == "meta.xml":
            continue
        print(f"Luetaan tiedostoa: {filename}...")
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
            sem_type = lemma_elem.get('sem_type') or ""

            key = (lemma, pos, subtype)
            if key not in entries:
                entries[key] = {"sem_type": sem_type, "translations": []}
            translations = entries[key]["translations"]

            for tg in entry.findall('mg/tg'):
                lang = tg.get('{http://www.w3.org/XML/1998/namespace}lang')
                if lang and lang != "fin":
                    continue
                for t_elem in tg.findall('t'):
                    if t_elem.text:
                        t_text = fix_finnish_text(" ".join(t_elem.text.split()))
                        if t_text and t_text not in translations:
                            translations.append(t_text)

    return [
        (lemma, pos, subtype, data["sem_type"], ", ".join(data["translations"]))
        for (lemma, pos, subtype), data in entries.items()
    ]


def apply_corrections(words):
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
            trans = corrections[key]
        result.append((lemma, pos, subtype, sem_type, trans))

    # Korjaustiedoston sanat, joita XML:ssä ei ollut, lisätään uusina
    for (lemma, pos), trans in corrections.items():
        if (lemma, pos) not in applied and trans != "-":
            result.append((lemma, pos, "", "", trans))
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
                ["hfst-lookup", "-q", fst_path],
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


def find_fst_prefixes(words):
    """Etsii analysaattorilla jokaiselle sanalle sen FST-etuliitteen, esim.
    mannat -> mannat+V+IV, Ánte -> Ánte+N+Prop+Sem/Mal, mun -> mun+Pron+Pers+Sg1."""
    analyses = run_hfst_lookup(ANALYSER, [w[0] for w in words])
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


def main():
    for path in (GENERATOR, ANALYSER):
        if not os.path.exists(path):
            print(f"FST-tiedostoa ei löydy: {path}")
            return

    words_list = apply_corrections(parse_xml_dictionaries())
    print(f"Löytyi yhteensä {len(words_list)} uniikkia sanaa XML-tiedostoista.")
    if not words_list:
        return

    print("Analysoidaan perusmuodot FST-analysaattorilla...")
    prefixes = find_fst_prefixes(words_list)

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
            finnish_translation TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE paradigms (
            word_id INTEGER,
            tag TEXT,
            surface TEXT,
            FOREIGN KEY(word_id) REFERENCES dictionary(id)
        )
    ''')

    print("Tallennetaan sanat ja taivutusmuodot tietokantaan...")
    stats = {}
    for lemma, pos, subtype, _, trans in sorted(words_list):
        word_prefixes = prefixes.get((lemma, pos, subtype), [])
        cursor.execute(
            "INSERT INTO dictionary (sme_lemma, pos, subtype, fst_tags, finnish_translation) VALUES (?, ?, ?, ?, ?)",
            (lemma, pos, subtype, " | ".join(word_prefixes), trans)
        )
        w_id = cursor.lastrowid

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

    print("Luodaan tietokantaan indeksit...")
    cursor.execute("CREATE INDEX idx_lemma ON dictionary(sme_lemma COLLATE NOCASE);")
    cursor.execute("CREATE INDEX idx_trans ON dictionary(finnish_translation);")
    cursor.execute("CREATE INDEX idx_paradigms_word_id ON paradigms(word_id);")
    cursor.execute("CREATE INDEX idx_paradigms_surface ON paradigms(surface COLLATE NOCASE);")

    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

    print("\nSanaluokka      sanoja   joilla taivutusmuotoja")
    for pos, (total, with_forms) in sorted(stats.items(), key=lambda x: -x[1][0]):
        print(f"  {pos:12} {total:8} {with_forms:10}")
    print("Valmista! Tietokanta luotu onnistuneesti.")


if __name__ == "__main__":
    main()
