"""Koltansaame (kokeellinen): suomen ja norjan sanoille koltansaamen vastineet GiellaLT:n sanakirjoista.

Lähteet (haetaan: ./hae_sanakirjat.sh, eivät kuulu tähän repoon):
  dict-sms-mul  koltansaame -> suomi, norja ym. (CC BY 4.0), luetaan toisin päin
  dict-fin-sms  suomi -> koltansaame (CC BY 3.0)
  dict-nob-sms  norja -> koltansaame (CC BY 4.0)

Pohjoissaamen ja koltansaamen välillä ei ole sanakirjaa. Sovellus näyttää koltan sanat suomen- tai norjankielisen
hakusanan vastineina, tai pohjoissaamen sanalle sen suomennosten kautta ("suomen kautta", web/app.js: skoltFor).

Monimerkityksinen suomen sana tuo ehdokkaita myös väärästä merkityksestä (sisar -> täti-sanat), joten ehdokkaat
pisteytetään ja vain vahvat (enintään 3) otetaan mukaan:
  +2  suomen/norjan sana on koltan sanan ensimmäinen merkitys (dict-sms-mul)
  +2  molemmat lähteet antavat saman sanan (dict-*-sms ja dict-sms-mul)
  +1  suorassa sanakirjassa (dict-*-sms)
  +1  koltan sanalla on enintään 3 merkitystä (ei yleissana, jonka merkitys voi olla toinen)
Tasapisteissä ensin sana, jolla on enemmän merkityksiä: yleiset perussanat (vesi -> čääʹcc) ennen
erikoissanoja (mueʹles). Tarkistukset (2026-10-31): kaksi suomen lähdettä samaa mieltä 91 %:ssa sanoista.
"""
import collections
import glob
import os
import re
import xml.etree.ElementTree as ET

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
# Sanaluokat samoiksi kuin satni.db:n pos-sarakkeessa (N, V, A, Adv, ...)
POS = {"N": "N", "V": "V", "A": "A", "ADV": "Adv", "PRON": "Pron", "NUM": "Num", "PCLE": "Pcle", "CC": "CC",
       "CS": "CS", "INTERJ": "Interj", "PO": "Adp", "PR": "Adp", "ADP": "Adp"}
MIN_SCORE = 3
MAX_WORDS = 3


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _pos(p):
    return POS.get((p or "").strip().upper(), (p or "").strip().capitalize())


def _entries(path):
    return ET.parse(path).getroot().iter("e")


def load(root):
    """Lukee sanakirjat. Palauttaa (info, rev): info[koltta] = {fin: [...], nob: [...], pos}, rev[kieli][sana][koltta] = merkit."""
    info = collections.defaultdict(lambda: {"fin": [], "nob": [], "pos": ""})
    rev = {"fin": collections.defaultdict(lambda: collections.defaultdict(set)),
           "nob": collections.defaultdict(lambda: collections.defaultdict(set))}
    for path in sorted(glob.glob(os.path.join(root, "dict-sms-mul", "src", "*_sms2x.xml"))):
        for e in _entries(path):
            l = e.find("lg/l")
            if l is None or not (l.text or "").strip():
                continue
            sms = l.text.strip()
            info[sms]["pos"] = _pos(l.get("pos"))
            for mg_i, mg in enumerate(e.iter("mg")):
                for tg in mg.iter("tg"):
                    lang = tg.get(XML_LANG)
                    if lang not in rev:
                        continue
                    for t_i, t in enumerate(tg.iter("t")):
                        word = _norm(t.text)
                        if word:
                            info[sms][lang].append(word)
                            rev[lang][word][sms].add("first" if mg_i == 0 and t_i == 0 else "mul")
    for lang in rev:
        for path in sorted(glob.glob(os.path.join(root, f"dict-{lang}-sms", "src", "*.xml"))):
            for e in _entries(path):
                l = e.find("lg/l")
                if l is None or not (l.text or "").strip():
                    continue
                word = _norm(l.text)
                for tg in e.iter("tg"):
                    if tg.get(XML_LANG) != "sms":
                        continue
                    for t in tg.iter("t"):
                        sms = (t.text or "").strip()
                        if sms:
                            rev[lang][word][sms].add("dir")
                            if not info[sms]["pos"]:
                                info[sms]["pos"] = _pos(t.get("pos") or l.get("pos"))
    return info, rev


def _score(marks, info_sms, lang):
    return (2 * ("first" in marks) + 2 * ("dir" in marks and ("mul" in marks or "first" in marks))
            + ("dir" in marks) + (len(info_sms[lang]) <= 3))


def rows(root):
    """(kieli, sana, sanaluokka, "koltta1, koltta2") jokaiselle suomen ja norjan sanalle, jolla on vahvoja vastineita."""
    if not os.path.isdir(os.path.join(root, "dict-sms-mul")):
        return []
    info, rev = load(root)
    out = []
    for lang, words in rev.items():
        for word, cands in words.items():
            by_pos = collections.defaultdict(list)
            for sms, marks in cands.items():
                score = _score(marks, info[sms], lang)
                if score >= MIN_SCORE:
                    n_meanings = len(info[sms]["fin"]) + len(info[sms]["nob"])
                    by_pos[info[sms]["pos"]].append((-score, -n_meanings, sms))
            for pos, cs in by_pos.items():
                cs.sort()
                out.append((lang, word, pos, ", ".join(s for _, _, s in cs[:MAX_WORDS])))
    return out


if __name__ == "__main__":
    import sys
    r = rows(os.path.dirname(os.path.abspath(__file__)))
    print(len(r), "riviä")
    for lang, word, pos, sms in r:
        if word in sys.argv[1:]:
            print(lang, word, pos, "->", sms)
