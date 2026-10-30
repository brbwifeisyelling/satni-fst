"""Suomenkielisten käännösten taivutusmuodot GiellaLT:n lang-fin-FST:llä: taulu fin_forms tietokantaan satni.db.

LÄHDE (ks. CREDITS.md): GiellaLT lang-fin -analysaattori ja -generaattori (UiT, Giellatekno), lisenssi GPL-3.0+.
Valmiiksi käännetyt mallit haetaan GiellaLT:n nightly-paketista giella-fin (./hae_sanakirjat.sh -> giella-fin/).

Taivutetaan saamen substantiivien, verbien ja adjektiivien yksisanaiset suomenkieliset käännökset
(finnish_translation ja suomenkieliset merkitykset). Käännös analysoidaan ensin, jotta saadaan oikea
sanaluokka ja yhdyssanan rajat (maan#käyttö#raja), ja muodot generoidaan analyysin perusteella.

Taulu: fin_forms(word, pos, forms), pos = saamen sanaluokka N/V/A ja forms esim.
"Sg+Nom=talo;Sg+Gen=talon;...;Pl+Ine=taloissa". Vaihtoehtoiset muodot erotetaan /-merkillä, tavallisempi
ensin; vanhahtavat rinnakkaismuodot pudotetaan (ks. clean_variants).

Aja yksinään olemassa olevaan tietokantaan: python3 fin_forms.py (import_full_dict.py ajaa tämän myös).
"""
import collections
import os
import re
import sqlite3
import subprocess

from nob_forms import translation_words

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FST_DIR = os.path.join(SCRIPT_DIR, "giella-fin")
# desc-analysaattori säilyttää piilotagit (maa+N+CmpNP/None), joita generaattori tarvitsee
ANALYSER = os.path.join(FST_DIR, "analyser-gt-desc.hfstol")
GENERATOR = os.path.join(FST_DIR, "generator-gt-norm.hfstol")
DB_FILE = os.path.join(SCRIPT_DIR, "satni.db")

PERSONS = ["Sg1", "Sg2", "Sg3", "Pl1", "Pl2", "Pl3"]
# Vain sovelluksessa käytetyt sijat (web/app.js: finPhrase); adessiivi ja ablatiivi jätetään pois tilan säästämiseksi
CASES = ["Nom", "Gen", "Par", "Ine", "Ela", "Ill", "All", "Ess"]
NOMINAL_CELLS = {f"{n}+{c}": f"{n}+{c}" for n in ("Sg", "Pl") for c in CASES}
# Solu -> generaattorin tagit perusmuodon ja sanaluokan jälkeen
CELLS = {
    "N": NOMINAL_CELLS,
    "A": {**NOMINAL_CELLS, "Comp": "Comp+Sg+Nom", "Superl": "Superl+Sg+Nom"},
    "V": {
        "Inf": "Act+InfA+Sg+Lat",
        **{f"Prs+{p}": f"Act+Ind+Prs+{p}" for p in PERSONS},
        **{f"Prt+{p}": f"Act+Ind+Prt+{p}" for p in PERSONS},
        **{f"Cond+{p}": f"Act+Cond+{p}" for p in PERSONS},
        **{f"Pot+{p}": f"Act+Pot+{p}" for p in PERSONS},
        **{f"Imprt+{p}": f"Act+Imprt+{p}" for p in PERSONS if p != "Sg1"},
        "PrfPrc": "Act+PrfPrc+Sg+Nom",
        "Prs+ConNeg": "Act+Ind+Prs+ConNeg",
        "Cond+ConNeg": "Act+Cond+ConNeg",
        "Pot+ConNeg": "Act+Pot+ConNeg",
    },
}
FIN_POS = {"N": "N", "V": "V", "A": "A"}


def lookup(fst, queries, generate=False):
    """hfst-optimized-lookup: {kysely: [tulos, ...]}; tuntemattomat (+?) jätetään pois."""
    proc = subprocess.run(["hfst-optimized-lookup", "-q", fst], input="\n".join(queries) + "\n",
                          capture_output=True, text=True, encoding="utf-8")
    results = collections.defaultdict(list)
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or "+?" in parts or (generate and "+" in parts[1]):
            continue
        if parts[1] not in results[parts[0]]:
            results[parts[0]].append(parts[1])
    return results


# Perusmuodon analyysin loppu sanaluokittain: sitä edeltävä osa (talo+N, maa+N+CmpNP/None, tehdä+V) on generoinnin alku
CITATION_TAGS = {"N": "+Sg+Nom", "A": "+Sg+Nom", "V": "+Act+InfA+Sg+Lat"}


def stems(word, pos, analyses):
    """Käännöksen perusmuotoanalyyseista generoinnin alut, joiden (viimeisen osan) sanaluokka on oikea:
    talo+N, maa+N+CmpNP/None, laki+Hom1+N, kirkko+N+Cmp/SgNom+Cmp#laki+Hom1+N. Kokonaisena sanana tunnettu
    analyysi ensin, yhdyssana-analyyseista vain osiltaan vähiten jaettu. Väärät alut karsii add_fin_forms
    (generoitu perusmuoto ei ole sama kuin käännös)."""
    found = []
    for a in analyses:
        last = a.split("#")[-1]
        m = re.match(r"[^+]+(\+Hom\d+)?\+(N|V|A)\+", last)
        if m and m.group(2) == FIN_POS[pos] and a.endswith(CITATION_TAGS[pos]) and a[:-len(CITATION_TAGS[pos])] not in found:
            found.append(a[:-len(CITATION_TAGS[pos])])
    simple = [s for s in found if "#" not in s]
    return simple or sorted(found, key=lambda s: s.count("#"))[:1]


def clean_variants(forms, cell, pos, word):
    """Generaattori (norm) antaa myös vanhahtavia ja murteellisia rinnakkaismuotoja. Ne pudotetaan, kun
    yleiskielinen vaihtoehto on olemassa, ja tavallisin muoto laitetaan ensin:
      - heittomerkilliset (kivijal’oilla, sii’asta) ja väliviivalliset yhdyssanat (kirkko-laissa)
      - h:lliset vanhat muodot (vaattehissa -> vaatteissa, asiakkahilta -> asiakkailta, -hisin)
      - monikon genetiivin -in ja -tten (taloin, kirjain, omenoitten), kun -en/-den on
      - essiivin lyhyt muoto (suurna, taloudellisna), kun -ena on
      - muoto, jossa on enemmän h-kirjaimia kuin vaihtoehdossa (vaattehien -> vaatteiden)
      - yhdyssana, jonka alkuosakin taipuu (hienoissasokereissa), kun alkuosan säilyttävä on (hienosokereissa)
      - verbin lyhyt puhekielinen muoto (meen, mee), kun pidempi on (menen, mene)"""
    if len(forms) < 2:
        return forms
    keep = [f for f in forms if "’" not in f and "'" not in f and ("-" not in f or "-" in word)] or forms

    def archaic(f, others):
        return (any(f[:i] + f[i + 1:] in others for i, ch in enumerate(f) if ch == "h")
                or f.endswith("hisin") or f.endswith("hisiin")
                or (cell == "Pl+Gen" and f.endswith("in") and any(g.endswith("en") for g in others))
                or ("tten" in f and f.replace("tten", "den") in others)
                or (cell == "Sg+Ess" and not f.endswith(("ena", "enä")) and any(g.endswith(("ena", "enä")) for g in others)))
    keep = [f for f in keep if not archaic(f, [g for g in keep if g != f])] or keep
    fewest_h = min(f.count("h") for f in keep)
    keep = [f for f in keep if f.count("h") == fewest_h]
    # Alkuosaltaan taipunut yhdyssana on pidempi ja eroaa perusmuodosta aiemmin kuin vaihtoehtonsa
    # (hienoissasokereissa / hienosokereissa); lasten / lapsien säilyy, koska lasten on lyhyempi.
    prefix = {f: len(os.path.commonprefix([f, word])) for f in keep}
    best = max(keep, key=lambda f: prefix[f])
    keep = [f for f in keep if not (prefix[f] <= prefix[best] - 3 and len(f) > len(best))]
    vowels = "aeiouyäö"
    if pos == "V":
        keep = sorted(keep, key=len, reverse=True)
    elif cell == "Comp" and word[-1] in "aä":
        keep = sorted(keep, key=lambda f: not f.endswith(word[-1] + "mpi"))  # ankarampi, väkevämpi
    elif cell == "Sg+Par" and word[-1] in vowels:
        # kampelaa (ei kampelata), mutta variaatiota (ei variaatioa)
        two_vowels = len(word) > 1 and word[-2] in vowels
        keep = sorted(keep, key=lambda f: f.endswith(("ta", "tä")) != two_vowels)
    return keep


def add_fin_forms(cursor):
    print("Taivutetaan suomenkieliset käännökset (GiellaLT lang-fin)...")
    cursor.execute("DROP TABLE IF EXISTS fin_forms")
    cursor.execute("CREATE TABLE fin_forms (word TEXT, pos TEXT, forms TEXT)")
    if not (os.path.exists(ANALYSER) and os.path.exists(GENERATOR)):
        print(f"  lang-fin-malleja ei löydy kansiosta {FST_DIR} (aja ./hae_sanakirjat.sh): fin_forms jää tyhjäksi")
        return
    words = sorted(translation_words(cursor, "fin", "finnish_translation"))
    analyses = lookup(ANALYSER, sorted({w for w, _ in words}))
    requests = {}
    for word, pos in words:
        for stem in stems(word, pos, analyses.get(word, [])):
            for cell, tags in CELLS[pos].items():
                requests.setdefault((word, pos), []).append((cell, f"{stem}+{tags}"))
            # Perusmuodon generointi tarkistusta varten (alku kelpaa vain, jos se tuottaa käännöksen itsensä)
            requests[(word, pos)].append(("citation", stem + CITATION_TAGS[pos]))
    generated = lookup(GENERATOR, sorted({q for reqs in requests.values() for _, q in reqs}), generate=True)

    rows = []
    for (word, pos), reqs in requests.items():
        cells = {}
        valid_stems = {q[:-len(CITATION_TAGS[pos])] for c, q in reqs if c == "citation" and word in generated.get(q, [])}
        for cell, query in reqs:
            if cell == "citation" or not any(query.startswith(st + "+") for st in valid_stems):
                continue
            for form in generated.get(query, []):
                cells.setdefault(cell, [])
                if form not in cells[cell]:
                    cells[cell].append(form)
        if cells:
            forms = ";".join(f"{c}={'/'.join(clean_variants(cells[c], c, pos, word))}" for c in CELLS[pos] if c in cells)
            rows.append((word, pos, forms))
    cursor.executemany("INSERT INTO fin_forms VALUES (?, ?, ?)", rows)
    cursor.execute("CREATE INDEX idx_fin_forms_word ON fin_forms(word)")
    print(f"  {len(rows)}/{len(words)} suomenkieliselle sanalle löytyi taivutus")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    add_fin_forms(conn.cursor())
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
