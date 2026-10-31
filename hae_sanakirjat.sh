#!/bin/sh
# Hakee tai päivittää GiellaLT:n sanakirjat, joista import_full_dict.py lukee muiden kielten käännökset
# (dict-sme-*) ja suomen- ja norjankielisen haun (dict-fin-sme, dict-nob-sme).
# Puuttuva repo kloonataan, olemassa oleva päivitetään (git pull). Lopuksi tulostetaan käytetyt versiot.
#
# LÄHDE: GiellaLT / Divvun / Giellatekno, UiT Norjan arktinen yliopisto (https://github.com/giellalt).
# Sanakirjat ovat heidän työtään (lisenssi CC BY 4.0), eivätkä ne kuulu tähän repoon: skripti hakee ne
# suoraan GiellaLT:ltä, jolloin tekijä- ja lisenssitiedot tulevat mukana. Ks. CREDITS.md.
# dict-sme-fin on tallennettu tähän repoon tiedostoina, eikä sitä päivitetä täällä.
cd "$(dirname "$0")" || exit 1
for repo in dict-sme-nob dict-sme-eng dict-sme-smn dict-sme-smj dict-sme-sma dict-fin-sme dict-nob-sme \
            dict-sms-mul dict-fin-sms dict-nob-sms; do
    if [ -d "$repo/.git" ]; then
        echo "Päivitetään $repo..."
        git -C "$repo" pull --ff-only --quiet || echo "  $repo: päivitys epäonnistui"
    else
        echo "Haetaan $repo..."
        git clone --quiet "https://github.com/giellalt/$repo.git" || echo "  $repo: haku epäonnistui"
    fi
done
# Norsk ordbank (Språkbanken / Nasjonalbiblioteket, CC BY): norjankielisten käännösten taivutus (nob_forms.py)
ORDBANK_URL="https://www.nb.no/sbfil/leksikalske_databaser/ordbank/20220201_norsk_ordbank_nob_2005.tar.gz"
if [ ! -f ordbank-nob/fullformsliste.txt ]; then
    echo "Haetaan Norsk ordbank..."
    mkdir -p ordbank-nob && curl -sSfL "$ORDBANK_URL" | tar -xz -C ordbank-nob --no-same-owner \
        || echo "  Norsk ordbank: haku epäonnistui"
fi
# GiellaLT lang-fin (GPL-3.0+): suomenkielisten käännösten taivutus (fin_forms.py). Valmiit mallit GiellaLT:n
# nightly-paketista; .deb-paketista otetaan vain analysaattori ja generaattori (paketissa on ~1.7 Gt muuta).
GIELLA_NIGHTLY="https://apertium.projectjj.com/apt/nightly/pool/main/g/giella-fin"
if [ ! -f giella-fin/analyser-gt-desc.hfstol ] || [ "$1" = "--paivita-fin" ]; then
    echo "Haetaan GiellaLT lang-fin (nightly)..."
    DEB=$(curl -sSf "$GIELLA_NIGHTLY/" | grep -oE 'giella-fin_[^"]+_all\.deb' | head -1)
    TMP=$(mktemp -d)
    if [ -n "$DEB" ] && curl -sSfL -o "$TMP/fin.deb" "$GIELLA_NIGHTLY/$DEB" && (cd "$TMP" && ar x fin.deb data.tar.xz) \
        && mkdir -p giella-fin && tar -xJf "$TMP/data.tar.xz" -C giella-fin --strip-components=5 \
            ./usr/share/giella/fin/analyser-gt-desc.hfstol ./usr/share/giella/fin/generator-gt-norm.hfstol; then
        echo "$DEB" > giella-fin/VERSION
    else
        echo "  lang-fin: haku epäonnistui"
    fi
    rm -rf "$TMP"
fi
echo
echo "Versiot:"
for repo in dict-sme-nob dict-sme-eng dict-sme-smn dict-sme-smj dict-sme-sma dict-fin-sme dict-nob-sme \
            dict-sms-mul dict-fin-sms dict-nob-sms; do
    [ -d "$repo/.git" ] && echo "  $repo $(git -C "$repo" log -1 --format='%h %cs')"
done
[ -f giella-fin/VERSION ] && echo "  lang-fin $(cat giella-fin/VERSION)"
[ -f ordbank-nob/fullformsliste.txt ] && echo "  Norsk ordbank $(basename "$ORDBANK_URL" .tar.gz | cut -c1-8)"
echo "Aja sitten: python3 import_full_dict.py"
