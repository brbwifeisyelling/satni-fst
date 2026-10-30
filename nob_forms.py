"""Norjankielisten käännösten taivutusmuodot Norsk ordbankista: taulu nob_forms tietokantaan satni.db.

LÄHDE (ks. CREDITS.md): Norsk ordbank – bokmål 2005, Språkbanken / Nasjonalbiblioteket, lisenssi CC BY.
https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-5/  (hakee: ./hae_sanakirjat.sh -> ordbank-nob/)

Taivutetaan saamen substantiivien, verbien ja adjektiivien yksisanaiset norjankieliset käännökset
(nob_translation ja norjankieliset merkitykset). Yhdyssana, jota ordbankissa ei ole (arealgrense), taivutetaan
pisimmän ordbankista löytyvän loppuosan mukaan (grense). Erisnimiä (isolla alkukirjaimella) ei taivuteta.

Taulu: nob_forms(word, pos, forms), pos = saamen sanaluokka N/V/A ja forms esim.
"Sg+Indef=hus;Sg+Def=huset;Pl+Indef=hus;Pl+Def=husene/husa". Vaihtoehtoiset muodot erotetaan /-merkillä,
konservatiivisempi ensin (boken/boka, pratet/prata).

Aja yksinään olemassa olevaan tietokantaan: python3 nob_forms.py (import_full_dict.py ajaa tämän myös).
"""
import collections
import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORDBANK_DIR = os.path.join(SCRIPT_DIR, "ordbank-nob")
DB_FILE = os.path.join(SCRIPT_DIR, "satni.db")

# Tallennettavat muodot sanaluokittain, samassa järjestyksessä kuin forms-sarakkeessa
CELLS = {
    "N": ["Sg+Indef", "Sg+Def", "Pl+Indef", "Pl+Def"],
    "V": ["Inf", "Prs", "Prt", "PrfPrc", "Imp"],
    "A": ["Pos", "Neu", "Pl", "Comp", "Superl"],
}
ORDBANK_POS = {"N": "subst", "V": "verb", "A": "adj"}
WORD_RE = re.compile(r"[a-zæøåéèêóòôüäö][a-zæøåéèêóòôüäö\-]*")


def ordbank_cell(pos, tags):
    """Ordbankin tagit (esim. "subst nøyt appell ent be normert") -> CELLS-solu tai None."""
    t = tags.split()
    if t[0] != ORDBANK_POS[pos] or any(x.startswith("<") for x in t if pos != "V"):
        return None
    if pos == "N":
        if "prop" in t:
            return None
        number = "Sg" if "ent" in t else "Pl" if "fl" in t else None
        definite = "Indef" if "ub" in t else "Def" if "be" in t else None
        return number and definite and f"{number}+{definite}"
    if pos == "V":
        if "pass" in t:
            return None
        for key, cell in (("inf", "Inf"), ("pres", "Prs"), ("pret", "Prt"), ("perf-part", "PrfPrc"), ("imp", "Imp")):
            if key in t:
                return cell
        return None
    if "komp" in t:
        return "Comp"
    if "sup" in t:
        return "Superl" if "ub" in t else None
    if "pos" in t:
        return "Neu" if "nøyt" in t else "Pos" if "m/f" in t else "Pl" if "fl" in t else None
    return None


def preferred_first(forms, cell, word):
    """Ordbank ei kerro, mikä vaihtoehdoista on tavallisin, joten järjestetään säännöillä: tavallisempi
    (konservatiivisempi) muoto ensin. Jälkimmäiseksi joutuvat
      - a-pääte (boka, prata, husa), kun muu vaihtoehto on (boken, pratet, husene)
      - diftongi (skreiv, skøyv, veit), kun vaihtoehdossa sitä ei ole (skrev, skjøv, vet)
      - o, kun vaihtoehdossa on samassa kohdassa ø (boker -> bøker)
      - monikko ilman päätettä (prosjekt), kun päätteellinen on (prosjekter)
      - -ete (kremfargete), kun -ede on (kremfargede)
      - imperatiivi ilman -e:tä (plystr), kun -e:llinen on (plystre)"""
    diphthong = re.compile("ei|øy|au")

    def penalty(f):
        others = [g for g in forms if g != f]
        return sum((
            f.endswith("a") and any(not g.endswith("a") for g in others),
            bool(diphthong.search(f)) and any(not diphthong.search(g) for g in others),
            any(f[:i] + "ø" + f[i + 1:] in others for i, ch in enumerate(f) if ch == "o"),
            cell == "Pl+Indef" and f == word and bool(others),
            f.endswith("ete") and f[:-3] + "ede" in others,
            cell == "Imp" and f + "e" in others,
        ))
    return sorted(forms, key=penalty)


def read_ordbank():
    """{(perusmuoto, pos): {solu: [muodot]}} ordbankin lemma- ja fullformslistasta."""
    lemmas = {}
    with open(os.path.join(ORDBANK_DIR, "lemma.txt"), encoding="latin-1") as f:
        for line in f:
            cols = line.rstrip("\r\n").split("\t")
            if len(cols) > 2:
                lemmas[cols[1]] = cols[2]
    table = collections.defaultdict(lambda: collections.defaultdict(list))
    with open(os.path.join(ORDBANK_DIR, "fullformsliste.txt"), encoding="latin-1") as f:
        next(f)
        for line in f:
            cols = line.rstrip("\r\n").split("\t")
            lemma = lemmas.get(cols[1])
            if not lemma:
                continue
            for pos in CELLS:
                cell = ordbank_cell(pos, cols[3])
                if cell and cols[2] not in table[(lemma, pos)][cell]:
                    table[(lemma, pos)][cell].append(cols[2])
    return table


def translation_words(cursor, lang="nob", column="nob_translation"):
    """Saamen N/V/A-sanojen yksisanaiset käännökset kielellä lang: {(sana, pos)}. Käyttää myös fin_forms.py."""
    words = set()

    def add(text, pos):
        for w in re.split(r"[,;]", re.sub(r"\(.*?\)", "", text or "")):
            w = w.strip()
            if WORD_RE.fullmatch(w):
                words.add((w, pos))
    for pos, text in cursor.execute(f"SELECT pos, {column} FROM dictionary WHERE pos IN ('N', 'V', 'A')").fetchall():
        add(text, pos)
    for pos, text in cursor.execute("SELECT d.pos, m.translations FROM meanings m JOIN dictionary d ON d.id = m.word_id "
                                    "WHERE m.lang = ? AND d.pos IN ('N', 'V', 'A')", (lang,)).fetchall():
        add(text, pos)
    return words


def inflect(word, pos, table):
    """Sanan muodot ordbankista; yhdyssanalle pisimmän tunnetun loppuosan muodot (vain N ja A)."""
    if (word, pos) in table:
        return table[(word, pos)]
    if pos == "V":
        return None
    for i in range(1, len(word) - 2):
        tail = table.get((word[i:], pos))
        if tail and "-" not in word[i:]:
            return {cell: [word[:i] + f for f in forms] for cell, forms in tail.items()}
    return None


def add_nob_forms(cursor):
    print("Taivutetaan norjankieliset käännökset (Norsk ordbank)...")
    cursor.execute("DROP TABLE IF EXISTS nob_forms")
    cursor.execute("CREATE TABLE nob_forms (word TEXT, pos TEXT, forms TEXT)")
    if not os.path.exists(os.path.join(ORDBANK_DIR, "fullformsliste.txt")):
        print(f"  Norsk ordbankia ei löydy kansiosta {ORDBANK_DIR} (aja ./hae_sanakirjat.sh): nob_forms jää tyhjäksi")
        return
    table = read_ordbank()
    words = translation_words(cursor)
    rows = []
    for word, pos in sorted(words):
        cells = inflect(word, pos, table)
        if cells:
            forms = ";".join(f"{c}={'/'.join(preferred_first(cells[c], c, word))}" for c in CELLS[pos] if c in cells)
            rows.append((word, pos, forms))
    cursor.executemany("INSERT INTO nob_forms VALUES (?, ?, ?)", rows)
    cursor.execute("CREATE INDEX idx_nob_forms_word ON nob_forms(word)")
    print(f"  {len(rows)}/{len(words)} norjankieliselle sanalle löytyi taivutus")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    add_nob_forms(conn.cursor())
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
