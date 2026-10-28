"""Astevaihtelun (dássemolsašupmi) tunnistus generoiduista taivutusmuodoista.

FST ei merkitse astetta, joten se päätellään muodoista: etsitään sanan konsonanttikeskus,
joka vaihtelee muodosta toiseen (dahkat ~ dagan: hk ~ g), ja ratkaistaan vahva/heikko
oahpa.no:n astevaihtelutaulukon avulla (https://oahpa.no/sme/gramm/tabell_stadieveksling.html).
Taulukko on välttämätön, koska kirjainten määrä ei kerro astetta: juolgi (lg) on vahva
ja juolggit (lgg) heikko.

GD = gievrras dássi (vahva aste), HD = headju dássi (heikko aste).
"""
import re
from collections import Counter

VOWELS = "aáeiouyäöâ"
_PARTS = re.compile(f"[{VOWELS}]+|[^{VOWELS}]+")

# oahpa.no-taulukko ryhmittäin: ryhmän nimi -> rivit (CIII, CII, CI). Tyhjä = astetta ei ole.
GRADATION_TABLE = [
    ("Duppalkonsonánttat 1", [
        ("đđ", "đđ", "đ"), ("ff", "ff", "f"), ("ll", "ll", "l"), ("hll", "hll", "hl"), ("llj", "lj", ""),
        ("mm", "mm", "m"), ("nn", "nn", "n"), ("nnj", "nnj", "nj"), ("ŋŋ", "ŋŋ", "ŋ"), ("rr", "rr", "r"),
        ("hrr", "hrr", "hr"), ("ss", "ss", "s"), ("šš", "šš", "š"), ("ŧŧ", "ŧŧ", "ŧ"), ("vv", "vv", "v"),
    ]),
    ("Duppalkonsonánttat 2", [
        ("bb", "pp", ""), ("dd", "tt", ""), ("ddj", "dj", "j"), ("gg", "kk", ""), ("zz", "cc", ""),
        ("žž", "čč", ""),
    ]),
    ("Joavku 3: h-čoahkit", [
        ("hcc", "hc", "z"), ("hčč", "hč", "ž"), ("hkk", "hk", "g"), ("hpp", "hp", "b"), ("htt", "ht", "đ"),
    ]),
    ("Joavku 4: klusiila + nasála", [
        ("bm", "pm", "m"), ("dn", "tn", "n"), ("dnj", "tnj", "nj"), ("gŋ", "kŋ", "ŋ"),
    ]),
    ("Joavku 5", [
        ("rbm", "rpm", ""), ("rdn", "rtn", ""), ("rdnj", "rtnj", ""), ("rgŋ", "rkŋ", ""),
    ]),
    ("Joavku 6: đ-, i-, l-, nasála-, r-, s/š/t- ja v-čoahkit", [
        ("đb", "đbb", ""), ("đg", "đgg", ""), ("đj", "đjj", ""), ("đv", "đvv", ""), ("ib", "ibb", ""),
        ("ic", "icc", ""), ("id", "idd", ""), ("if", "iff", ""), ("ig", "igg", ""), ("ik", "ikk", ""),
        ("il", "ill", ""), ("ihl", "ihll", ""), ("ihm", "ihmm", ""), ("ihn", "ihnn", ""), ("ip", "ipp", ""),
        ("ir", "irr", ""), ("is", "iss", ""), ("it", "itt", ""), ("iv", "ivv", ""), ("iz", "izz", ""),
        ("lb", "lbb", ""), ("lc", "lcc", ""), ("ld", "ldd", ""), ("lf", "lff", ""), ("lg", "lgg", ""),
        ("lk", "lkk", ""), ("lj", "ljj", ""), ("lp", "lpp", ""), ("ls", "lss", ""), ("lš", "lšš", ""),
        ("lt", "ltt", ""), ("lv", "lvv", ""), ("lž", "lžž", ""), ("mb", "mbb", ""), ("mp", "mpp", ""),
        ("ms", "mss", ""), ("mš", "mšš", ""), ("nc", "ncc", ""), ("nč", "nčč", ""), ("nd", "ndd", ""),
        ("ns", "nss", ""), ("nt", "ntt", ""), ("nz", "nzz", ""), ("nž", "nžž", ""), ("ŋg", "ŋgg", ""),
        ("ŋk", "ŋkk", ""), ("rb", "rbb", ""), ("rc", "rcc", ""), ("rč", "rčč", ""), ("rd", "rdd", ""),
        ("rf", "rff", ""), ("rg", "rgg", ""), ("rj", "rjj", ""), ("rk", "rkk", ""), ("rp", "rpp", ""),
        ("rs", "rss", ""), ("rš", "ršš", ""), ("rt", "rtt", ""), ("rv", "rvv", ""), ("rz", "rzz", ""),
        ("rž", "ržž", ""), ("sk", "skk", ""), ("sm", "smm", ""), ("sp", "spp", ""), ("st", "stt", ""),
        ("šk", "škk", ""), ("šm", "šmm", ""), ("št", "štt", ""), ("šv", "švv", ""), ("tk", "tkk", ""),
        ("tm", "tmm", ""), ("vd", "vdd", ""), ("vg", "vgg", ""), ("vj", "vjj", ""), ("vk", "vkk", ""),
        ("vl", "vll", ""), ("vhl", "vhll", ""), ("vp", "vpp", ""), ("vr", "vrr", ""), ("vt", "vtt", ""),
        ("vz", "vzz", ""), ("vž", "vžž", ""),
    ]),
    ("Joavku 7", [
        ("đbm", "đmm", ""), ("đgŋ", "đŋŋ", ""), ("ibm", "imm", ""), ("idn", "inn", ""), ("igŋ", "iŋŋ", ""),
        ("lbm", "lmm", ""), ("ldn", "lnn", ""), ("lgŋ", "lŋŋ", ""), ("vdn", "vnn", ""), ("vdnj", "vnnj", ""),
    ]),
    ("Joavku 8", [
        ("isk", "iskk", ""), ("ist", "istt", ""), ("mšk", "mškk", ""), ("nsk", "nskk", ""), ("nst", "nstt", ""),
        ("rsk", "rskk", ""), ("rst", "rstt", ""), ("vsk", "vskk", ""),
    ]),
    ("Joavku 9: k-čoahkit", [
        ("kc", "vcc", ""), ("kč", "včč", ""), ("ks", "vss", ""), ("kst", "vstt", ""), ("kš", "všš", ""),
        ("kt", "vtt", ""),
    ]),
]

QUANTITY_NAMES = {3: "III", 2: "II", 1: "I"}

# oahpa.no jakaa joukon 6 alaryhmiin konsonanttiryhmän alkukirjaimen mukaan
GROUP_6_NAMES = {
    "đ": "đ-čoahkit", "i": "i-čoahkit", "l": "l-čoahkit", "m": "nasála čoahkit", "n": "nasála čoahkit",
    "ŋ": "nasála čoahkit", "r": "r-čoahkit", "s": "s-/š-/t-čoahkit", "š": "s-/š-/t-čoahkit",
    "t": "s-/š-/t-čoahkit", "v": "v-čoahkit",
}


def _clusters(word):
    """{vokaaliryhmän numero: (sitä seuraava konsonanttiryhmä, vokaaliryhmä)}"""
    result = {}
    vowel_index = 0
    prev_vowels = ""
    for part in _PARTS.findall(word.lower()):
        if part[0] in VOWELS:
            vowel_index += 1
            prev_vowels = part
        elif vowel_index > 0:
            result[vowel_index] = (part, prev_vowels)
    return result


def _keys(cluster, prev_vowels):
    """Taulukkoavain sellaisenaan sekä i-čoahkit-muodossa (ig ~ igg), jossa i kuuluu edeltävään
    vokaaliryhmään. Kumpaa käytetään, ratkeaa sanakohtaisesti taulukon perusteella."""
    return cluster, ("i" + cluster if prev_vowels.endswith("i") else None)


def _find_row(keys):
    """Taulukon rivi, jolla kaikki avaimet esiintyvät eri asteina.
    Palauttaa ({avain: aste 3/2/1}, ryhmän nimi, rivi) tai (None, None, None)."""
    for group, rows in GRADATION_TABLE:
        for row in rows:
            ranks = {}
            for quantity, value in zip((3, 2, 1), row):
                if value and value in keys and value not in ranks:
                    ranks[value] = quantity
            if len(ranks) == len(keys) and len(set(ranks.values())) == len(keys):
                if group.startswith("Joavku 6"):
                    group = f"Joavku 6: {GROUP_6_NAMES.get(row[0][0], '')}".rstrip(": ")
                return ranks, group, row
    return None, None, None


def analyse(lemma, forms):
    """forms: [(tagi, pintamuoto), ...]

    Palauttaa (tiedot, {(tagi, pintamuoto): (aste, konsonanttikeskus)}) tai (None, {}).
    tiedot = {"summary": "hk (GD) ~ g (HD), myös hkk (GD, aste III)", "strong": "hk", "weak": "g",
              "group": "Joavku 3: h-čoahkit", "row": "hkk · hk · g"}
    """
    if not forms or not lemma or " " in lemma:
        return None, {}

    vowel_groups = sum(1 for p in _PARTS.findall(lemma.lower()) if p[0] in VOWELS)
    form_clusters = [(tag, surface, _clusters(surface)) for tag, surface in forms]

    # Astevaihtelukohta: lemman viimeisestä keskuksesta alkaen (yhdyssanoissa vaihtelu on viimeisessä osassa)
    for position in range(vowel_groups - 1, 0, -1):
        ranks = None
        # i-čoahkit ensin: muuten esim. biila (il ~ ill) tulkittaisiin riviltä ll ~ l väärin päin
        for use_i in (True, False):
            counts = Counter()
            for _, _, clusters in form_clusters:
                if position in clusters:
                    raw, with_i = _keys(*clusters[position])
                    key = (with_i or raw) if use_i else raw
                    counts[key] += 1
            candidates = [key for key, n in counts.most_common() if n >= 2]
            if len(candidates) < 2:
                continue
            # Kaksi yleisintä muodostavat pääparin; sen pitää löytyä taulukon samalta riviltä
            main_pair = candidates[:2]
            ranks, group, row = _find_row(main_pair)
            if ranks:
                break
        if not ranks:
            continue

        strong, weak = sorted(main_pair, key=lambda k: -ranks[k])
        # Muut saman rivin asteet (esim. hkk dahkat-verbin preesensin partisiipissa)
        extra_ranks = _find_row(candidates[:3])[0] if len(candidates) > 2 else None
        if extra_ranks:
            ranks = extra_ranks

        grades = {}
        for tag, surface, clusters in form_clusters:
            if position not in clusters:
                continue
            raw, with_i = _keys(*clusters[position])
            key = with_i if with_i in ranks else raw
            if key not in ranks:
                continue
            grade = "GD" if ranks[key] >= ranks[strong] else "HD"
            grades[(tag, surface)] = (grade, key)

        summary = f"{strong} (GD) ~ {weak} (HD)"
        extras = [k for k in ranks if k not in (strong, weak)]
        for k in extras:
            summary += f", myös {k} ({'GD' if ranks[k] > ranks[strong] else 'HD'}, aste {QUANTITY_NAMES[ranks[k]]})"
        info = {
            "summary": summary,
            "strong": strong,
            "weak": weak,
            "group": group,
            "row": " · ".join(f"{v} ({QUANTITY_NAMES[q]})" for q, v in zip((3, 2, 1), row) if v),
        }
        return info, grades

    return None, {}
