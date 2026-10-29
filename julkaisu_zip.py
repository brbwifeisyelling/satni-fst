"""Pakkaa build.sh:n tuottamat AppImagen ja Windows-version julkaisuzipiksi:
~/Seafile/Files/Git/dist/satni-fst.zip (satni-fst/: AppImage, Windows/satni-fst/, LUEMINUT.txt).

Edellinen zip siirretään ensin kansioon dist/_archive nimellä archive_<versio>.zip, ja arkistoon
jätetään vain viisi uusinta versiota. Väliaikaiset tiedostot: ~/.cache/satni-fst-build/release.
"""
import os
import re
import shutil
import sys
import zipfile

from version import VERSION

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPIMAGE = os.path.join(SCRIPT_DIR, "dist", "Satni_FST-x86_64.AppImage")
WINDOWS_ZIP = os.path.join(SCRIPT_DIR, "dist", "satni-fst-windows.zip")
README = os.path.join(SCRIPT_DIR, "packaging", "LUEMINUT.txt")
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "dist")
OUT_ZIP = os.path.join(OUT_DIR, "satni-fst.zip")
ARCHIVE_DIR = os.path.join(OUT_DIR, "_archive")
KEEP_ARCHIVES = 5
WORK_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
                        "satni-fst-build", "release")


def zip_version(path):
    """Versionumero zipin LUEMINUT.txt:n ensimmäiseltä riviltä ("Sátni FST 0.2.20261029.7 – ...")."""
    try:
        with zipfile.ZipFile(path) as z:
            first = z.read("satni-fst/LUEMINUT.txt").decode("utf-8").splitlines()[0]
    except (KeyError, IndexError, zipfile.BadZipFile):
        return None
    m = re.search(r"\d+\.\d+\.\d+\.\d+", first)
    return m.group(0) if m else None


def version_key(name):
    m = re.match(r"archive_(\d+)\.(\d+)\.(\d+)\.(\d+)\.zip$", name)
    return tuple(int(p) for p in m.groups()) if m else None


def archive_previous():
    if not os.path.exists(OUT_ZIP):
        return
    old = zip_version(OUT_ZIP)
    if old == VERSION:
        sys.exit(f"dist/satni-fst.zip on jo versio {VERSION}. Aja ensin ./build.sh (uusi versionumero).")
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    name = f"archive_{old}.zip" if old else "archive_tuntematon.zip"
    shutil.move(OUT_ZIP, os.path.join(ARCHIVE_DIR, name))
    print(f"Edellinen versio arkistoon: _archive/{name}")

    archives = sorted((n for n in os.listdir(ARCHIVE_DIR) if version_key(n)), key=version_key, reverse=True)
    for name in archives[KEEP_ARCHIVES:]:
        os.remove(os.path.join(ARCHIVE_DIR, name))
        print(f"Poistettiin vanha arkisto: _archive/{name}")


def build_tree():
    root = os.path.join(WORK_DIR, "satni-fst")
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    os.makedirs(os.path.join(root, "Windows"))
    shutil.copy2(APPIMAGE, root)
    with zipfile.ZipFile(WINDOWS_ZIP) as z:
        for info in z.infolist():
            # Windowsin Compress-Archive käyttää polkuerottimena kenoviivaa
            target = os.path.join(root, "Windows", *info.filename.replace("\\", "/").split("/"))
            if info.filename.endswith(("/", "\\")):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    with open(README, encoding="utf-8") as f:
        text = f.read().replace("{VERSION}", VERSION)
    with open(os.path.join(root, "LUEMINUT.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)
    return root


def write_zip(root):
    count = 0
    tmp = OUT_ZIP + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dirpath, _, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(dirpath, name)
                z.write(path, os.path.relpath(path, WORK_DIR))
                count += 1
    with zipfile.ZipFile(tmp) as z:
        if z.testzip() is not None:
            sys.exit("Zip-tiedoston tarkistus epäonnistui")
    os.replace(tmp, OUT_ZIP)
    return count


def main():
    for path in (APPIMAGE, WINDOWS_ZIP, README):
        if not os.path.exists(path):
            sys.exit(f"Tiedostoa ei löydy: {path} (aja ensin ./build.sh)")
    os.makedirs(OUT_DIR, exist_ok=True)
    archive_previous()
    root = build_tree()
    count = write_zip(root)
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    print(f"{OUT_ZIP}: versio {VERSION}, {count} tiedostoa, {os.path.getsize(OUT_ZIP) / 1e6:.0f} Mt")


if __name__ == "__main__":
    main()
