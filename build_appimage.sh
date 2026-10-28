#!/bin/sh
# Rakentaa AppImagen. Ohjelma käännetään Debian 11 -kontissa (glibc 2.31), jotta se toimii myös
# vanhemmissa Linux-jakeluissa (Ubuntu 20.04+, Debian 11+ jne.). Vaatii Dockerin.
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
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/appimage"
mkdir -p "$CACHE_DIR" || exit 1

# build.sh on jo kasvattanut versiota, jotta .exe ja AppImage saavat saman numeron
[ -n "$SKIP_VERSION_BUMP" ] || python3 bump_version.py || exit 1
VERSION=$(python3 -c "from version import VERSION; print(VERSION)")

# 1. Ohjelma ja AppDir Debian 11 -kontissa
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp/home \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD":/src \
    -v "$CACHE_DIR":/work \
    -w /src \
    python:3.12-bullseye \
    sh /src/packaging/appimage_inside.sh || exit 1

# 2. AppImage-paketointi isäntäkoneella
mkdir -p dist
# Kiinteä nimi: päivitys korvaa vanhan tiedoston ja työpöytäpikakuvake pysyy toimivana.
# Versio näkyy ohjelman Tietoa-ikkunassa ja AppImagen sisäisessä .desktop-tiedostossa.
OUT="dist/Satni_FST-x86_64.AppImage"
ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$CACHE_DIR/AppDir" "$OUT" || exit 1

ls -la "$OUT"
