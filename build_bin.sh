python3 bump_version.py || exit 1
# PyInstallerin väliaikaiset tiedostot välimuistikansioon, ei projektikansioon (se voi olla synkronoitu)
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build"
mkdir -p "$CACHE_DIR" || exit 1
pyinstaller --clean --workpath "$CACHE_DIR/linux" --noconsole --onefile -n satni-fst --icon="sami_icon.ico" --hidden-import="PIL._tkinter_finder" --add-data "Sami_flag.svg.webp:." --add-data "satni.db:." gui.py
