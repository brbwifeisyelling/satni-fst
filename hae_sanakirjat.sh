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
for repo in dict-sme-nob dict-sme-eng dict-sme-smn dict-sme-smj dict-sme-sma dict-fin-sme dict-nob-sme; do
    if [ -d "$repo/.git" ]; then
        echo "Päivitetään $repo..."
        git -C "$repo" pull --ff-only --quiet || echo "  $repo: päivitys epäonnistui"
    else
        echo "Haetaan $repo..."
        git clone --quiet "https://github.com/giellalt/$repo.git" || echo "  $repo: haku epäonnistui"
    fi
done
echo
echo "Versiot:"
for repo in dict-sme-nob dict-sme-eng dict-sme-smn dict-sme-smj dict-sme-sma dict-fin-sme dict-nob-sme; do
    [ -d "$repo/.git" ] && echo "  $repo $(git -C "$repo" log -1 --format='%h %cs')"
done
echo "Aja sitten: python3 import_full_dict.py"
