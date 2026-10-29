"""Tekee satni.db:stä kevennetyn ja pakatun tietokannan web-versiota (PWA) varten: web/data/satni-web.db.gz

Selaimessa tietokanta luetaan sql.js:llä (SQLite WebAssemblynä). Perusmuodoille ja käännöksille
(trans_search, yksi rivi sanaa ja kieltä kohden) lasketaan valmiiksi pienaakkosiin muutetut sarakkeet (Pythonin lower(), joka toimii myös Á, Č, Š
-kirjaimille), koska selaimen SQLite ei osaa muuttaa niitä. Taivutusmuodot haetaan sellaisenaan
(muodot ovat pienaakkosia, erisnimet isolla alkukirjaimella).
"""
import gzip
import os
import shutil
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB = os.path.join(SCRIPT_DIR, "satni.db")
OUT_DIR = os.path.join(SCRIPT_DIR, "web", "data")
OUT_DB = os.path.join(OUT_DIR, "satni-web.db")

# Sama haun normalisointi kuin gui.py:ssä: ä = æ, ö = ø
SEARCH_FOLD = str.maketrans({"æ": "ä", "ø": "ö"})


# Käännöskielet ja niiden sarakkeet satni.db:ssä (ks. import_full_dict.py)
TRANSLATION_COLUMNS = {"fin": "finnish_translation", "nob": "nob_translation", "eng": "eng_translation",
                       "smn": "smn_translation", "smj": "smj_translation", "sma": "sma_translation"}


def fold(text):
    return text.lower().translate(SEARCH_FOLD) if isinstance(text, str) else text


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)

    src = sqlite3.connect(SOURCE_DB)
    dst = sqlite3.connect(OUT_DB)
    dst.execute("PRAGMA page_size = 4096")
    dst.executescript("""
        CREATE TABLE dictionary (
            id INTEGER PRIMARY KEY, sme_lemma TEXT, pos TEXT, subtype TEXT, finnish_translation TEXT,
            nob_translation TEXT, eng_translation TEXT, smn_translation TEXT, smj_translation TEXT,
            sma_translation TEXT, notes TEXT, gradation TEXT, gd_cluster TEXT, hd_cluster TEXT,
            gradation_group TEXT, gradation_row TEXT, lemma_fold TEXT
        );
        CREATE TABLE trans_search (word_id INTEGER, lang TEXT, fold TEXT);
        -- Taivutustagit (Ind+Prs+Sg1 ...) numeroina: sama merkkijono toistuisi muuten lähes miljoona kertaa
        CREATE TABLE tags (id INTEGER PRIMARY KEY, tag TEXT);
        CREATE TABLE paradigms (word_id INTEGER, tag_id INTEGER, surface TEXT, grade TEXT);
        CREATE TABLE meanings (word_id INTEGER, lang TEXT, nr INTEGER, translations TEXT, explanations TEXT,
                               restrictions TEXT, labels TEXT, geo TEXT);
        CREATE TABLE examples (word_id INTEGER, lang TEXT, meaning_nr INTEGER, sme TEXT, translation TEXT,
                               source TEXT);
    """)

    trans_cols = ", ".join(TRANSLATION_COLUMNS.values())
    rows = src.execute(
        f"SELECT id, sme_lemma, pos, subtype, {trans_cols}, notes, gradation, gd_cluster, hd_cluster, "
        "gradation_group, gradation_row FROM dictionary"
    ).fetchall()
    dst.executemany(f"INSERT INTO dictionary VALUES ({', '.join('?' * (len(rows[0]) + 1))})",
                    [r + (fold(r[1]),) for r in rows])
    dst.executemany("INSERT INTO trans_search VALUES (?, ?, ?)", [
        (r[0], lang, fold(r[4 + i])) for r in rows for i, lang in enumerate(TRANSLATION_COLUMNS) if r[4 + i]
    ])

    tag_ids = {}
    for (tag,) in src.execute("SELECT DISTINCT tag FROM paradigms ORDER BY tag"):
        tag_ids[tag] = len(tag_ids) + 1
    dst.executemany("INSERT INTO tags VALUES (?, ?)", [(i, t) for t, i in tag_ids.items()])
    dst.executemany(
        "INSERT INTO paradigms VALUES (?,?,?,?)",
        ((w, tag_ids[t], s, g) for w, t, s, g in
         src.execute("SELECT word_id, tag, surface, grade FROM paradigms ORDER BY word_id, rowid"))
    )
    dst.executemany("INSERT INTO meanings VALUES (?,?,?,?,?,?,?,?)", src.execute(
        "SELECT word_id, lang, nr, translations, explanations, restrictions, labels, geo FROM meanings "
        "ORDER BY word_id, rowid"))
    dst.executemany("INSERT INTO examples VALUES (?,?,?,?,?,?)", src.execute(
        "SELECT word_id, lang, meaning_nr, sme, translation, source FROM examples ORDER BY word_id, rowid"))

    dst.executescript("""
        CREATE INDEX idx_lemma_fold ON dictionary(lemma_fold);
        CREATE INDEX idx_paradigms_word ON paradigms(word_id);
        CREATE INDEX idx_paradigms_surface ON paradigms(surface);
        CREATE INDEX idx_meanings_word ON meanings(word_id);
        CREATE INDEX idx_examples_word ON examples(word_id);
    """)
    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    src.close()

    with open(OUT_DB, "rb") as f_in, gzip.open(OUT_DB + ".gz", "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)
    raw, packed = os.path.getsize(OUT_DB), os.path.getsize(OUT_DB + ".gz")
    os.remove(OUT_DB)
    print(f"web/data/satni-web.db.gz: {packed / 1e6:.1f} Mt (purettuna {raw / 1e6:.1f} Mt)")


if __name__ == "__main__":
    main()
