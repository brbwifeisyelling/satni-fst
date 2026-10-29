#!/bin/sh
# Luo Android-sovelluksen julkaisuavaimen (kerran). Avain ja sen salasana EIVÄT kuulu versionhallintaan.
#   Avain:     $SATNI_SIGNING_DIR/satni-fst-release.jks   (oletus ~/.config/satni-fst-signing)
#   Salasana:  $SATNI_SIGNING_DIR/keystore.properties     (vain omistajan luettavissa, build_apk.sh lukee)
# Skripti kysyy salasanan itse; sitä ei näytetä eikä kirjoiteta muualle. Säilytä avaintiedosto ja
# salasana varmuuskopioituna (esim. salasananhallinnassa): ilman niitä sovellukseen ei voi tehdä
# päivityksiä, jotka asentuvat vanhan version päälle.
cd "$(dirname "$0")/../.." || exit 1
DIR="${SATNI_SIGNING_DIR:-$HOME/.config/satni-fst-signing}"
KEY="$DIR/satni-fst-release.jks"
ALIAS=satni-fst
if [ -e "$KEY" ]; then
    echo "Avain on jo olemassa: $KEY (ei korvata)"; exit 1
fi
mkdir -p "$DIR" && chmod 700 "$DIR" || exit 1

printf "Avaimen salasana (vähintään 6 merkkiä, ei näy): "
stty -echo; read -r PASS; stty echo; echo
printf "Sama salasana uudelleen: "
stty -echo; read -r PASS2; stty echo; echo
[ "$PASS" = "$PASS2" ] || { echo "Salasanat eivät täsmää"; exit 1; }
[ ${#PASS} -ge 6 ] || { echo "Salasana on liian lyhyt"; exit 1; }

docker build -q -t satni-fst-android-build packaging/android >/dev/null || exit 1
# Salasana kontille ympäristömuuttujana (ei komentoriville, jottei näy prosessilistassa)
SATNI_KEY_PASS="$PASS" docker run --rm -e SATNI_KEY_PASS --user "$(id -u):$(id -g)" -v "$DIR":/k \
    satni-fst-android-build keytool -genkeypair -keystore /k/satni-fst-release.jks -storetype PKCS12 \
    -alias "$ALIAS" -keyalg RSA -keysize 4096 -validity 10000 \
    -storepass:env SATNI_KEY_PASS -keypass:env SATNI_KEY_PASS \
    -dname "CN=Juha Somby, O=Satni FST, C=FI" || exit 1

umask 077
printf 'storePassword=%s\nkeyPassword=%s\nkeyAlias=%s\n' "$PASS" "$PASS" "$ALIAS" > "$DIR/keystore.properties"
chmod 600 "$KEY" "$DIR/keystore.properties"
echo
echo "Avain luotu: $KEY (alias $ALIAS)"
SATNI_KEY_PASS="$PASS" docker run --rm -e SATNI_KEY_PASS --user "$(id -u):$(id -g)" -v "$DIR":/k satni-fst-android-build \
    keytool -list -v -keystore /k/satni-fst-release.jks -storepass:env SATNI_KEY_PASS | grep -E "Alias name|Valid from|SHA256:"
