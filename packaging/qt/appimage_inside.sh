#!/bin/sh
# Ajetaan build_qt_appimage.sh:n käynnistämän Docker-kontin sisällä. Älä aja suoraan.
# Kääntää Qt-työpöytäsovelluksen ja kokoaa AppDir-kansion; paketointi tehdään isäntäkoneella.
set -e

# /work = ~/.cache/satni-fst-build/qt-appimage isäntäkoneella (ei projektikansiossa)
WORK=/work
mkdir -p "$HOME" "$WORK"

pyinstaller --clean --noconfirm --windowed --onedir -n satni-fst \
    --workpath "$WORK/build" --distpath "$WORK/dist" --specpath "$WORK" \
    --add-data "/src/web:web" \
    --collect-data certifi \
    /src/satni_desktop.py

APPDIR="$WORK/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a "$WORK/dist/satni-fst" "$APPDIR/usr/bin/"
INTERNAL="$APPDIR/usr/bin/satni-fst/_internal"

# Grafiikka-, ääni-, fontti- ja ikkunointikirjastot otetaan käyttäjän järjestelmästä
# (AppImagen excludelist-käytäntö): niiden on vastattava koneen omia ajureita ja asetuksia.
for pattern in 'libGL.so*' 'libGLX*' 'libGLdispatch*' 'libEGL.so*' 'libOpenGL*' 'libgbm*' 'libdrm*' \
               'libasound*' 'libfontconfig*' 'libfreetype*' 'libexpat*' 'libX11.so*' 'libX11-xcb*' \
               'libxcb.so*' 'libXau*' 'libXdmcp*' 'libwayland-*' \
               'libstdc++.so*' 'libgcc_s.so*'; do
    # libstdc++/libgcc_s: järjestelmän grafiikka-ajurit (Mesa) tarvitsevat uudemman version kuin
    # Debian 11:n; vanha mukana oleva kaatoi ohjelman ("EGL not available")
    find "$INTERNAL" -maxdepth 1 -name "$pattern" -delete
done

# Chromiumin apuohjelma (QtWebEngineProcess) tarvitsee libatomicin, jota PyInstaller ei tunnista
# (apuohjelma ei ole Python-moduuli) ja jota kaikissa jakeluissa ei ole valmiina
cp -L /usr/lib/x86_64-linux-gnu/libatomic.so.1 "$INTERNAL/"

# Lisenssit: mukana olevien järjestelmäkirjastojen Debian-paketin copyright-tiedostot ja Pythonin lisenssi
# (web/licenses/desktop/, näkyvät Tietoa-ikkunan Lisenssit-kohdassa; luettelo files.txt)
LIC="$INTERNAL/web/licenses/desktop"
mkdir -p "$LIC/debian"
cp /usr/local/lib/python3.12/LICENSE.txt "$LIC/python-LICENSE.txt"
for lib in "$INTERNAL"/*.so*; do
    pkg=$(dpkg -S "*/$(basename "$lib")" 2>/dev/null | head -1 | cut -d: -f1)
    [ -n "$pkg" ] && [ -f "/usr/share/doc/$pkg/copyright" ] && cp "/usr/share/doc/$pkg/copyright" "$LIC/debian/$pkg.txt"
done
(cd "$LIC" && ls python-LICENSE.txt debian/*.txt) > "$LIC/files.txt"
echo "Lisenssit: $(ls "$LIC/debian" | wc -l) Debian-pakettia"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/satni-fst/satni-fst" "$@"
EOF
chmod +x "$APPDIR/AppRun"

VERSION=$(python3 -c "import sys; sys.path.insert(0, '/src'); from version import VERSION; print(VERSION)")
cat > "$APPDIR/satni-fst.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Sátni FST
Comment=Pohjoissaamen sanakirja ja taivutusgeneraattori
Exec=satni-fst
Icon=satni-fst
Categories=Education;Languages;
Terminal=false
StartupWMClass=satni-fst
X-AppImage-Version=$VERSION
EOF

cp /src/web/icons/icon-512.png "$APPDIR/satni-fst.png"
ln -sf satni-fst.png "$APPDIR/.DirIcon"
echo "AppDir valmis: $APPDIR ($(du -sh "$APPDIR" | cut -f1))"
