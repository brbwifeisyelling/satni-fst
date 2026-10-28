#!/bin/sh
# Ajetaan build_appimage.sh:n käynnistämän Docker-kontin sisällä. Älä aja suoraan.
# Rakentaa ohjelman ja AppDir-kansion; build_appimage.sh pakkaa sen AppImageksi isäntäkoneella.
set -e

# /work = ~/.cache/satni-fst-build/appimage isäntäkoneella (ei Seafile-kansiossa)
WORK=/work
VERSION=$(python3 -c "import sys; sys.path.insert(0, '/src'); from version import VERSION; print(VERSION)")

mkdir -p "$HOME" "$WORK"
# Python-ympäristö säilyy välimuistissa buildien välillä
[ -x "$WORK/venv/bin/python3" ] || python3 -m venv "$WORK/venv"
. "$WORK/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet "pyinstaller==6.11.1" "pillow==11.0.0"

# Ohjelma kansiomuodossa (--onedir käynnistyy nopeammin kuin --onefile AppImagen sisällä)
pyinstaller --clean --noconfirm --windowed --onedir -n satni-fst \
    --workpath "$WORK/build" --distpath "$WORK/dist" --specpath "$WORK" \
    --hidden-import="PIL._tkinter_finder" \
    --add-data "/src/Sami_flag.svg.webp:." \
    --add-data "/src/satni.db:." \
    /src/gui.py

APPDIR="$WORK/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a "$WORK/dist/satni-fst" "$APPDIR/usr/bin/"

# Fontit ja X11-peruskirjastot otetaan käyttäjän järjestelmästä (AppImage-käytäntö, ks. excludelist):
# vanha Debian 11:n fontconfig ei osaa lukea uusien jakeluiden fonttiasetuksia.
for lib in libfontconfig.so.1 libfreetype.so.6 libexpat.so.1 libpng16.so.16 \
           libbrotlicommon.so.1 libbrotlidec.so.1 \
           libX11.so.6 libXau.so.6 libXdmcp.so.6 libXext.so.6 libXrender.so.1; do
    rm -f "$APPDIR/usr/bin/satni-fst/_internal/$lib"
done

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/satni-fst/satni-fst" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/satni-fst.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Sátni FST
Comment=Pohjoissaamen sanakirja ja taivutusgeneraattori
Exec=satni-fst
Icon=satni-fst
Categories=Education;Languages;
Terminal=false
X-AppImage-Version=$VERSION
EOF

# Kuvake: saamen lippu neliöksi 256x256-kokoon
python3 - "$APPDIR/satni-fst.png" <<'EOF'
import sys
from PIL import Image
flag = Image.open("/src/Sami_flag.svg.webp").convert("RGBA")
flag.thumbnail((256, 256), Image.Resampling.LANCZOS)
icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
icon.paste(flag, ((256 - flag.width) // 2, (256 - flag.height) // 2), flag)
icon.save(sys.argv[1])
EOF
ln -sf satni-fst.png "$APPDIR/.DirIcon"

echo "AppDir valmis: $APPDIR"
