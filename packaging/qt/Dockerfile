# Qt-työpöytäsovelluksen käännösympäristö: Debian 11 (glibc 2.31), jotta AppImage toimii myös
# vanhemmissa jakeluissa. Qt WebEngine (Chromium) tarvitsee käännöksessä nämä järjestelmäkirjastot,
# jotta PyInstaller osaa niputtaa ne mukaan.
FROM python:3.12-bullseye

# Debian 11:n tuki on päättynyt ja paketit ovat siirtyneet archive.debian.org-palvelimelle
RUN printf '%s\n' \
        'deb http://archive.debian.org/debian bullseye main' \
        'deb http://archive.debian.org/debian-security bullseye-security main' \
        > /etc/apt/sources.list \
    && echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99archive

RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libxkbcommon0 libxkbcommon-x11-0 libxcomposite1 libxdamage1 libxrandr2 \
        libxtst6 libxshmfence1 libxkbfile1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxcb-util1 \
        libgbm1 libasound2 libegl1 libgl1 libopengl0 libfontconfig1 libdbus-1-3 \
        libwayland-client0 libwayland-cursor0 libwayland-egl1 libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# PySide6 6.10+ vaatii uudemman glibc:n kuin Debian 11:ssä on; 6.9.3 on viimeisin yhteensopiva
RUN pip install --no-cache-dir "pyinstaller==6.22.3" "PySide6==6.9.3" "certifi==2024.8.30"
