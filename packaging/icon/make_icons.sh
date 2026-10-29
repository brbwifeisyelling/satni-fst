#!/bin/sh
# Tekee kaikki sovelluksen kuvakkeet logosta satni-icon.svg (saamen lippu pisaran muodossa).
# Vaatii rsvg-convertin (librsvg) ja ImageMagickin (magick). Tulokset:
#   web/icons/icon-192.png, icon-512.png   PWA, välilehti, yläpalkki, työpöytäikkuna ja AppImage
#   web/icons/maskable-512.png             PWA:n "maskable"-kuvake: pisara valkoisella, 80 %:n turva-alueella
#   android/.../ic_launcher*.png           Androidin kuvake (adaptiivinen: pisara 108 dp:n alueen keskellä)
#   sami_icon.ico                          Windows-version exe-kuvake
cd "$(dirname "$0")/../.." || exit 1
SVG=packaging/icon/satni-icon.svg
RES=android/app/src/main/res
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

render() {  # render <koko> <tiedosto>: pisara läpinäkyvällä taustalla
    rsvg-convert -w "$1" -h "$1" "$SVG" -o "$2" || exit 1
}
# padded <koko> <pisaran osuus %> <tausta> <tiedosto>
padded() {
    inner=$(( $1 * $2 / 100 ))
    render "$inner" "$TMP/inner.png"
    magick -size "$1x$1" "xc:$3" "$TMP/inner.png" -gravity center -composite -depth 8 "$4" || exit 1
}

render 192 web/icons/icon-192.png
render 512 web/icons/icon-512.png
padded 512 72 white web/icons/maskable-512.png

# Android: adaptiivisen kuvakkeen etuala 108 dp, josta näkyy keskimmäiset 72 dp (pyöreä maski ~66 dp)
padded 432 60 none "$RES/drawable-nodpi/ic_launcher_foreground.png"
# Vanhemmille Androideille (alle 8.0) pisara sellaisenaan
render 192 "$RES/mipmap-xxxhdpi/ic_launcher.png"

for s in 16 24 32 48 64 128 256; do render "$s" "$TMP/ico-$s.png"; done
magick "$TMP"/ico-16.png "$TMP"/ico-24.png "$TMP"/ico-32.png "$TMP"/ico-48.png \
       "$TMP"/ico-64.png "$TMP"/ico-128.png "$TMP"/ico-256.png sami_icon.ico || exit 1
echo "Kuvakkeet tehty logosta $SVG"
