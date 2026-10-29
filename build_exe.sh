python3 bump_version.py || exit 1
# PyInstallerin väliaikaiset tiedostot välimuistikansioon, ei projektikansioon (se voi olla synkronoitu)
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build"
mkdir -p "$CACHE_DIR" || exit 1
wine python -m PyInstaller --clean --workpath "$(winepath -w "$CACHE_DIR/windows")" --noconsole --onefile -n satni-fst --icon="sami_icon.ico" --hidden-import="PIL._tkinter_finder" --add-data "satni.db;." --add-data "Sami_flag.svg.webp;." gui.py
