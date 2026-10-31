#!/bin/sh
# Rakentaa Qt-työpöytäsovelluksen Windows-version Windows-virtuaalikoneessa (libvirt) SSH:n kautta.
# Tulos: dist/satni-fst-windows.zip (kansio: satni-fst.exe + _internal). Qt WebEngine on niin suuri,
# ettei yksittäistä .exe-tiedostoa kannata tehdä: se purkaisi ~500 Mt joka käynnistyksellä.
cd "$(dirname "$0")" || exit 1

# ANONYMISOITU: virtuaalikoneen nimi, käyttäjätunnus ja SSH-avain eivät ole tässä tiedostossa.
# Omat arvot annetaan ympäristömuuttujina tai tiedostossa build_qt_exe.local (ei versionhallinnassa,
# ks. .gitignore), esim.:
#   SATNI_WIN_VM=oma-windows-vm
#   SATNI_WIN_USER=oma-tunnus
#   SATNI_WIN_KEY=$HOME/.ssh/oma_avain
# Virtuaalikone: Windows 10/11, Python 3.12 (C:\Program Files\Python312), OpenSSH-palvelin ja
# avainkirjautuminen. Käännöskansio C:\satni-build luodaan automaattisesti.
[ -f ./build_qt_exe.local ] && . ./build_qt_exe.local
VM="${SATNI_WIN_VM:-windows-build}"
WIN_USER="${SATNI_WIN_USER:-builder}"
SSH_KEY="${SATNI_WIN_KEY:-$HOME/.ssh/id_ed25519}"
VM_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/winvm"
# Oma salasanaton avain vain tälle virtuaalikoneelle (näkyy vain tältä koneelta NAT-verkossa)
SSH_OPTS="-i $SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o LogLevel=ERROR -o UserKnownHostsFile=$VM_DIR/known_hosts -o StrictHostKeyChecking=accept-new"

# Virtuaalikone käyntiin tarvittaessa ja sen osoite
if [ "$(virsh -c qemu:///system domstate $VM 2>/dev/null)" != "running" ]; then
    virsh -c qemu:///system start $VM >/dev/null || exit 1
fi
for i in $(seq 1 60); do
    IP=$(virsh -c qemu:///system domifaddr $VM --source lease 2>/dev/null | awk '/ipv4/ {split($4,a,"/"); print a[1]; exit}')
    [ -n "$IP" ] && ssh $SSH_OPTS "$WIN_USER@$IP" "exit" 2>/dev/null && break
    IP=""
    sleep 5
done
[ -n "$IP" ] || { echo "Virtuaalikoneeseen ei saatu SSH-yhteyttä"; exit 1; }
echo "Virtuaalikone: $IP"

# build.sh on jo kasvattanut versiota, jotta .exe ja AppImage saavat saman numeron
[ -n "$SKIP_VERSION_BUMP" ] || python3 bump_version.py || exit 1
[ -f web/data/satni-web.db.gz ] || python3 export_web_data.py || exit 1

# Lähdekoodi virtuaalikoneelle (vain sovelluksen tarvitsemat tiedostot)
SRC_TAR="${XDG_CACHE_HOME:-$HOME/.cache}/satni-fst-build/satni-src.tar"
tar -cf "$SRC_TAR" satni_desktop.py tts.py version.py sami_icon.ico web || exit 1
ssh $SSH_OPTS "$WIN_USER@$IP" "Remove-Item -Recurse -Force C:\satni-build\src -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force C:\satni-build\src | Out-Null" || exit 1
scp -q $SSH_OPTS "$SRC_TAR" "$WIN_USER@$IP":C:/satni-build/satni-src.tar || exit 1

# Käännös: oma Python-ympäristö, PySide6 6.9.3 (sama kuin Linux-versiossa) ja PyInstaller
# Windows PowerShell pitää ohjelmien stderr-tulostetta virheenä, joten pip ja PyInstaller ajetaan
# cmd:n kautta lokitiedostoon ja onnistuminen tarkistetaan paluukoodista.
ssh $SSH_OPTS "$WIN_USER@$IP" '
Set-Location C:\satni-build
tar -xf satni-src.tar -C src
if (-not (Test-Path venv\Scripts\python.exe)) { & "C:\Program Files\Python312\python.exe" -m venv venv }
cmd /c "venv\Scripts\python.exe -m pip install --quiet --upgrade pip > pip.log 2>&1"
cmd /c "venv\Scripts\python.exe -m pip install --quiet pyinstaller==6.22.3 PySide6==6.9.3 certifi==2024.8.30 >> pip.log 2>&1"
if ($LASTEXITCODE -ne 0) { Get-Content pip.log -Tail 20; exit 1 }
Set-Location src
cmd /c "..\venv\Scripts\pyinstaller.exe --clean --noconfirm --windowed --onedir -n satni-fst --icon C:\satni-build\src\sami_icon.ico --add-data C:\satni-build\src\web;web --collect-data certifi --workpath C:\satni-build\work --distpath C:\satni-build\dist --specpath C:\satni-build\work satni_desktop.py > C:\satni-build\pyinstaller.log 2>&1"
if ($LASTEXITCODE -ne 0) { Get-Content C:\satni-build\pyinstaller.log -Tail 30; exit 1 }
Select-String -Path C:\satni-build\pyinstaller.log -Pattern "completed successfully" | Select-Object -Last 1
# Lisenssit: Pythonin lisenssi (sis. mukana tulevat OpenSSL, libffi, zlib ym.) Tietoa-ikkunan Lisenssit-kohtaan
$lic = "C:\satni-build\dist\satni-fst\_internal\web\licenses\desktop"
New-Item -ItemType Directory -Force $lic | Out-Null
Copy-Item "C:\Program Files\Python312\LICENSE.txt" "$lic\python-LICENSE.txt"
Set-Content -Path "$lic\files.txt" -Value "python-LICENSE.txt" -Encoding ascii
Remove-Item -Force C:\satni-build\satni-fst-windows.zip -ErrorAction SilentlyContinue
Compress-Archive -Path C:\satni-build\dist\satni-fst -DestinationPath C:\satni-build\satni-fst-windows.zip
if (-not (Test-Path C:\satni-build\satni-fst-windows.zip)) { exit 1 }
' || exit 1

mkdir -p dist
scp -q $SSH_OPTS "$WIN_USER@$IP":C:/satni-build/satni-fst-windows.zip dist/satni-fst-windows.zip || exit 1
ls -la dist/satni-fst-windows.zip
