#!/bin/sh
# Rakentaa julkaisuversion: Qt-työpöytäsovellus Linuxille (AppImage) ja Windowsille (kansio zipattuna),
# molemmat samalla versionumerolla.
#   Linux:   build_qt_appimage.sh  (Debian 11 -kontti, vaatii Dockerin)
#   Windows: build_qt_exe.sh       (Windows-virtuaalikone SSH:n kautta, asetukset build_qt_exe.local)
# Vanha Tk-versio: build_appimage.sh ja build_exe.sh (Wine), vain erikseen pyydettäessä.
cd "$(dirname "$0")" || exit 1
python3 bump_version.py || exit 1
SKIP_VERSION_BUMP=1 ./build_qt_appimage.sh || exit 1
SKIP_VERSION_BUMP=1 ./build_qt_exe.sh || exit 1
