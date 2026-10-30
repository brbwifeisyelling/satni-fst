# Android-emulaattorin ajoympäristö (emulaattori.sh): käännösympäristö (packaging/android/Dockerfile) ja
# emulaattorin tarvitsemat kirjastot. Emulaattori, järjestelmäkuva ja virtuaalilaitteet (AVD) ovat
# välimuistikansiossa ~/.cache/satni-fst-build/android/emu, eivät kuvassa.
FROM satni-fst-android-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 libx11-xcb1 libxext6 libxrender1 libxtst6 libxi6 libxcomposite1 libxcursor1 libxdamage1 \
    libxfixes3 libxrandr2 libnss3 libnspr4 libpulse0 libgl1 libegl1 libdbus-1-3 libfontconfig1 \
    libxkbfile1 libxcb-cursor0 libasound2 libdrm2 libgbm1 libxshmfence1 libxkbcommon0 libxkbcommon-x11-0 \
    libxcb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
    libxcb-xinerama0 libxcb-xkb1 libxcb-util1 libbsd0 \
    && rm -rf /var/lib/apt/lists/*
