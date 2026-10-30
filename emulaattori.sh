#!/bin/sh
# Android-emulaattorit sovelluksen testaamiseen Dockerissa (Android Studiota ei tarvita, vain /dev/kvm).
# Kaksi erillistä virtuaalilaitetta, jotta eri avaimilla allekirjoitetut versiot eivät sotke toisiaan
# (Android ei asenna toisella avaimella allekirjoitettua versiota vanhan päälle):
#   dev   kehitysversiot debug-avaimella: ./build_apk.sh --debug -> dist/satni-fst-debug.apk
#   main  julkaisuversiot julkaisuavaimella: dist/satni-fst.apk (käyttäjien versio) ja päivitystesti
#         ./build_apk.sh --testi -> ~/.cache/satni-fst-build/android/satni-fst-testi.apk (ei dist-kansioon)
#
# Käyttö:
#   ./emulaattori.sh kaynnista dev|main       käynnistää laitteen (luo sen ensimmäisellä kerralla) ja odottaa
#   ./emulaattori.sh asenna dev|main [APK]    asentaa APK:n; oletus dev: debug-APK, main: dist/satni-fst.apk,
#                                             main testi: julkaisuavaimella tehty testiversio
#   ./emulaattori.sh jaa dev|main TEKSTI      jakaa tekstin sovellukselle kuten Androidin jakovalikko
#   ./emulaattori.sh kuva dev|main [PNG]      kuvakaappaus (oletus: ~/.cache/satni-fst-build/android/kuvat/)
#   ./emulaattori.sh adb dev|main ARGS...     muu adb-komento, esim. shell input tap 400 600
#   ./emulaattori.sh pysayta [dev|main]       pysäyttää laitteen (ilman nimeä molemmat)
#   ./emulaattori.sh tila                     käynnissä olevat laitteet
#
# Emulaattori, Android 15 -järjestelmäkuva (~5 Gt) ja laitteet ovat kansiossa ~/.cache/satni-fst-build/android/emu.
cd "$(dirname "$0")" || exit 1

WORK="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/android"
SYSTEM_IMAGE="system-images;android-35;google_apis;x86_64"
PACKAGE=fi.somby.satnifst
ADB=/work/emu/sdk/platform-tools/adb

usage() { sed -n '/^# Käyttö:/,/^#$/p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

device() {  # dev|main -> säiliön nimi
    case "$1" in
        dev|main) echo "satni-emu-$1" ;;
        *) echo "Laite on dev tai main" >&2; exit 1 ;;
    esac
}

running() { [ -n "$(docker ps -q -f "name=^$(device "$1")\$")" ]; }

adb() {  # adb dev|main ARGS...
    name=$1; shift
    running "$name" || { echo "Laite $name ei ole käynnissä (./emulaattori.sh kaynnista $name)" >&2; exit 1; }
    docker exec "$(device "$name")" "$ADB" "$@"
}

images() {
    docker build -q -t satni-fst-android-build packaging/android >/dev/null &&
        docker build -q -t satni-fst-android-emu packaging/android/emulator >/dev/null
}

# Ajaa komennon emulaattorikuvassa välimuistikansio /work-kansiona, omana käyttäjänä
in_image() {
    docker run --rm --user "$(id -u):$(id -g)" --entrypoint "" -e HOME=/work/home \
        -e ANDROID_HOME=/work/emu/sdk -e ANDROID_SDK_ROOT=/work/emu/sdk -e ANDROID_AVD_HOME=/work/emu/avd \
        -v "$WORK":/work satni-fst-android-emu "$@"
}

setup() {  # emulaattori, järjestelmäkuva ja laite tarvittaessa
    mkdir -p "$WORK/emu/avd" "$WORK/home" || exit 1
    if [ ! -x "$WORK/emu/sdk/emulator/emulator" ] || [ ! -d "$WORK/emu/sdk/system-images/android-35" ]; then
        echo "Asennetaan emulaattori ja järjestelmäkuva (kerran, ~5 Gt)..."
        in_image sh -c "yes | /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/work/emu/sdk --licenses >/dev/null &&
            /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/work/emu/sdk \
                emulator platform-tools 'cmdline-tools;latest' '$SYSTEM_IMAGE' >/dev/null" || exit 1
    fi
    if [ ! -f "$WORK/emu/avd/satni-$1.ini" ]; then
        echo "Luodaan virtuaalilaite satni-$1 (Pixel 6, Android 15)..."
        in_image sh -c "echo no | /work/emu/sdk/cmdline-tools/latest/bin/avdmanager -s create avd \
            -n satni-$1 -k '$SYSTEM_IMAGE' -d pixel_6 >/dev/null" || exit 1
    fi
}

start() {
    if running "$1"; then echo "Laite $1 on jo käynnissä"; return; fi
    images || exit 1
    setup "$1"
    docker rm -f "$(device "$1")" >/dev/null 2>&1
    # Kaatuneen ajon lukot estäisivät käynnistyksen ("Running multiple emulators with the same AVD")
    rm -f "$WORK/emu/avd/satni-$1.avd/"*.lock
    mkdir -p "$WORK/emu/home-$1"
    docker run -d --name "$(device "$1")" --device /dev/kvm --user "$(id -u):$(id -g)" --entrypoint "" \
        -e HOME="/work/emu/home-$1" -e ANDROID_HOME=/work/emu/sdk -e ANDROID_SDK_ROOT=/work/emu/sdk \
        -e ANDROID_AVD_HOME=/work/emu/avd \
        -v "$WORK":/work satni-fst-android-emu \
        /work/emu/sdk/emulator/emulator -avd "satni-$1" -no-window -no-audio -no-boot-anim -no-metrics \
            -gpu swiftshader_indirect -memory 3072 >/dev/null || exit 1
    printf "Käynnistetään %s" "$1"
    i=0
    # Emulaattorikuvan ANDROID_HOME (/opt/android-sdk) ohitetaan yllä: emulaattori käyttää sitä ennen ANDROID_SDK_ROOTia
    until [ "$(docker exec "$(device "$1")" "$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
        if ! running "$1"; then
            echo; echo "Emulaattori pysähtyi:"; docker logs "$(device "$1")" 2>&1 | grep -E "FATAL|ERROR" | tail -5; exit 1
        fi
        i=$((i + 1)); [ $i -gt 120 ] && { echo; echo "Käynnistys ei valmistunut 10 minuutissa"; exit 1; }
        printf "."; sleep 5
    done
    echo " valmis"
}

install_apk() {
    name=$1; apk=$2
    if [ -z "$apk" ]; then
        [ "$name" = dev ] && apk=dist/satni-fst-debug.apk || apk=dist/satni-fst.apk
    elif [ "$apk" = testi ]; then
        apk="$WORK/satni-fst-testi.apk"
    fi
    [ -f "$apk" ] || { echo "APK:ta ei löydy: $apk"; exit 1; }
    docker cp "$apk" "$(device "$name"):/tmp/satni.apk" >/dev/null || exit 1
    out=$(adb "$name" install -r /tmp/satni.apk 2>&1)
    echo "$out" | tail -1
    if echo "$out" | grep -q UPDATE_INCOMPATIBLE; then
        echo "Allekirjoitusavain ei ole sama kuin laitteen versiossa: dev on debug-avaimelle, main julkaisuavaimelle."
        echo "Poista vanha versio tarvittaessa: ./emulaattori.sh adb $name uninstall $PACKAGE"
        exit 1
    fi
    echo "$out" | grep -q Success || exit 1
    adb "$name" shell dumpsys package "$PACKAGE" | grep -m1 versionName | sed 's/^ */  /'
}

[ $# -ge 1 ] || usage
cmd=$1; shift
case "$cmd" in
    kaynnista) [ $# -eq 1 ] || usage; start "$1" ;;
    asenna) [ $# -ge 1 ] || usage; install_apk "$1" "$2" ;;
    jaa)
        [ $# -ge 2 ] || usage
        adb "$1" shell am start -a android.intent.action.SEND -t text/plain \
            --es android.intent.extra.TEXT "'$2'" -n "$PACKAGE/.MainActivity" >/dev/null 2>&1 ;;
    kuva)
        [ $# -ge 1 ] || usage
        out=${2:-$WORK/kuvat/$1-$(date +%Y%m%d-%H%M%S).png}
        mkdir -p "$(dirname "$out")"
        adb "$1" exec-out screencap -p > "$out" && echo "$out" ;;
    adb) [ $# -ge 2 ] || usage; name=$1; shift; adb "$name" "$@" ;;
    pysayta)
        for name in ${1:-dev main}; do
            if running "$name"; then
                # Siisti sammutus tallentaa pikakäynnistyksen tilan (seuraava käynnistys on nopea)
                docker exec "$(device "$name")" "$ADB" emu kill >/dev/null 2>&1
                sleep 3
                docker rm -f "$(device "$name")" >/dev/null && echo "$name pysäytetty"
            fi
        done ;;
    tila)
        for name in dev main; do
            if running "$name"; then
                v=$(docker exec "$(device "$name")" "$ADB" shell dumpsys package "$PACKAGE" 2>/dev/null | grep -m1 versionName | tr -d ' ')
                echo "$name: käynnissä ${v:-(sovellusta ei asennettu)}"
            else
                echo "$name: pysäytetty"
            fi
        done ;;
    *) usage ;;
esac
