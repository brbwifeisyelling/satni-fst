#!/bin/sh
# Julkaisee kotisivun GitHub Pagesiin (https://brbwifeisyelling.github.io/satni-fst/):
#   /      kotisivu (site/, kuvat docs/screenshots/)
#   /app/  selainversio (web/ ja sen sanakirja web/data/satni-web.db.gz, luo: export_web_data.py)
# Sivu kootaan kansioon ~/.cache/satni-fst-build/pages ja työnnetään haaraan gh-pages yhtenä committina
# (vanha korvataan), jottei 40 Mt:n sanakirja kerry versiohistoriaan. GitHubissa kerran:
# Settings -> Pages -> Deploy from a branch: gh-pages / (root).
# --vain-kokoa: kootaan sivu testattavaksi, ei julkaista (esim. python3 -m http.server -d <kansio>).
cd "$(dirname "$0")" || exit 1

OUT="$HOME/.cache/satni-fst-build/pages"
[ -f web/data/satni-web.db.gz ] || { echo "web/data/satni-web.db.gz puuttuu (aja export_web_data.py)"; exit 1; }

rm -rf "$OUT" && mkdir -p "$OUT/screenshots" || exit 1
cp site/index.html site/site.css site/site.js packaging/icon/satni-icon.svg "$OUT/" || exit 1
cp docs/screenshots/*.png "$OUT/screenshots/" || exit 1
cp -r web "$OUT/app" || exit 1
# Selainversion Tietoa-ikkunaan julkaisun numero (RELEASE_VERSION)
WEB_VERSION=$(cat RELEASE_VERSION)
sed -i "s|<title>|<script>window.SATNI_WEB_VERSION = \"$WEB_VERSION\";</script>\n  <title>|" "$OUT/app/index.html"
grep -q "SATNI_WEB_VERSION = \"$WEB_VERSION\"" "$OUT/app/index.html" || { echo "Selainversion numeron lisäys epäonnistui"; exit 1; }
touch "$OUT/.nojekyll"  # ei Jekyll-käsittelyä

# Selainten välimuistit nimetään sisällön mukaan (web/sw.js): uusi sanakirja tai sovellus korvaa vanhan
# välimuistin. Muuten kerran ladattu sanakirja jäisi selaimeen pysyvästi.
DATA_HASH=$(sha256sum web/data/satni-web.db.gz | cut -c1-12)
APP_HASH=$(cd web && cat index.html styles.css i18n.js app.js sw.js manifest.webmanifest | sha256sum | cut -c1-12)
sed -i -e "s/^const VERSION = \"\(satni-v[0-9]*\)\";/const VERSION = \"\1-$APP_HASH\";/" \
       -e "s/^const DATA_CACHE = \"\(satni-data-v[0-9]*\)\";/const DATA_CACHE = \"\1-$DATA_HASH\";/" "$OUT/app/sw.js"
grep -q "satni-data-v[0-9]*-$DATA_HASH" "$OUT/app/sw.js" || { echo "sw.js:n välimuistien nimeäminen epäonnistui"; exit 1; }

# Kotisivun tyyli ja skripti versioidaan sisällön mukaan (site.js?v=...): GitHub Pages antaa selainten pitää
# tiedostoja välimuistissa 10 min, jolloin uusi sivu saattoi saada vanhan site.js:n (uusien osioiden tekstit tyhjinä).
for f in site.css site.js; do
    HASH=$(sha256sum "site/$f" | cut -c1-10)
    sed -i "s|\"$f\"|\"$f?v=$HASH\"|" "$OUT/index.html"
    grep -q "$f?v=$HASH" "$OUT/index.html" || { echo "$f:n versiointi epäonnistui"; exit 1; }
done

if [ "$1" = "--vain-kokoa" ]; then
    echo "Sivu koottu: $OUT"; exit 0
fi

# Oma väliaikainen git-repo, jottei sanakirja tallennu projektikansion .git-kansioon
URL=$(git config --get remote.github.url) && SSH=$(git config --get core.sshCommand) || exit 1
cd "$OUT" && git init -q -b gh-pages && git add -A || exit 1
GIT_AUTHOR_NAME="Juha Somby" GIT_AUTHOR_EMAIL=satni@somby.fi GIT_COMMITTER_NAME="Juha Somby" GIT_COMMITTER_EMAIL=satni@somby.fi \
    git commit -q -m "Sátni FST -kotisivu" || exit 1
GIT_SSH_COMMAND="$SSH" git push -q --force "$URL" gh-pages:gh-pages || exit 1
rm -rf "$OUT/.git"
echo "Julkaistu: https://brbwifeisyelling.github.io/satni-fst/"
