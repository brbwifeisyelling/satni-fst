#!/bin/sh
# Rakentaa Android-sovelluksen (android/) APK:n Docker-kontissa (packaging/android/Dockerfile).
# Tulos: dist/satni-fst.apk. Versio otetaan version.py:stä samana kuin työpöytäversioissa
# (aja ensin build.sh tai bump_version.py), versionCode: 0.2.20261029.7 -> 2026102907.
# APK allekirjoitetaan debug-avaimella, joka säilyy välimuistikansiossa: saman avaimen päivitykset
# asentuvat vanhan päälle. Avaimen vaihtuessa sovellus pitää poistaa ennen uuden asentamista.
cd "$(dirname "$0")" || exit 1

[ -f web/data/satni-web.db.gz ] || python3 export_web_data.py || exit 1
VERSION=$(python3 -c "import version; print(version.VERSION)") || exit 1
VERSION_CODE=$(python3 -c "v = '$VERSION'.split('.'); print(int(v[2]) * 100 + int(v[3]))") || exit 1

# Väliaikaiset tiedostot (Gradle, käännös, debug-avain) välimuistikansioon, ei projektikansioon
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/android"
mkdir -p "$CACHE_DIR/home" "$CACHE_DIR/build" || exit 1

docker build -q -t satni-fst-android-build packaging/android >/dev/null || exit 1
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/work/home \
    -e GRADLE_USER_HOME=/work/home/gradle \
    -e SATNI_BUILD_DIR=/work/build \
    -v "$PWD":/src:ro \
    -v "$CACHE_DIR":/work \
    -w /src/android \
    satni-fst-android-build \
    gradle --quiet --no-daemon --project-cache-dir /work/project-cache \
        -PsatniVersionName="$VERSION" -PsatniVersionCode="$VERSION_CODE" assembleDebug || exit 1

mkdir -p dist
cp "$CACHE_DIR/build/app/outputs/apk/debug/app-debug.apk" dist/satni-fst.apk || exit 1
echo "dist/satni-fst.apk: versio $VERSION ($VERSION_CODE)"
ls -la dist/satni-fst.apk
