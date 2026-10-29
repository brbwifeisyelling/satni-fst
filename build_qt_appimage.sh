#!/bin/sh
# Rakentaa Qt-työpöytäsovelluksen (satni_desktop.py) AppImagen. Ohjelma käännetään Debian 11
# -kontissa (packaging/qt/Dockerfile), jotta se toimii myös vanhemmissa Linux-jakeluissa. Vaatii Dockerin.
cd "$(dirname "$0")" || exit 1

APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-x86_64.AppImage"
APPIMAGETOOL=$(command -v appimagetool || echo "$HOME/.local/bin/appimagetool")
if [ ! -x "$APPIMAGETOOL" ]; then
    echo "Asennetaan appimagetool: $APPIMAGETOOL"
    mkdir -p "$(dirname "$APPIMAGETOOL")"
    curl -sSL -o "$APPIMAGETOOL" "$APPIMAGETOOL_URL" || exit 1
    chmod +x "$APPIMAGETOOL"
fi

# Väliaikaiset tiedostot välimuistikansioon, ei Seafile-synkronoituun projektikansioon
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/qt-appimage"
mkdir -p "$CACHE_DIR" || exit 1

# build.sh on jo kasvattanut versiota, jotta .exe ja AppImage saavat saman numeron
[ -n "$SKIP_VERSION_BUMP" ] || python3 bump_version.py || exit 1

# Web-käyttöliittymän sanakirja (~40 Mt) satni.db:stä
python3 export_web_data.py || exit 1

docker build -q -t satni-fst-qt-build packaging/qt >/dev/null || exit 1
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp/home \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD":/src:ro \
    -v "$CACHE_DIR":/work \
    -w /work \
    satni-fst-qt-build \
    sh /src/packaging/qt/appimage_inside.sh || exit 1

mkdir -p dist
OUT="dist/Satni_FST-x86_64.AppImage"
ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$CACHE_DIR/AppDir" "$OUT" || exit 1
ls -la "$OUT"
