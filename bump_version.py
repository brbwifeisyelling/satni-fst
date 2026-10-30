#!/usr/bin/env python3
# Kirjoittaa version.py-tiedoston (sovellukset ja build-skriptit lukevat sen) gitin tiedoista.
# Versio on muotoa X.Y.Z.VVVVKKPP.N: X.Y.Z on julkaisun numero tiedostosta RELEASE_VERSION (sama kuin
# GitHub-julkaisun tagi vX.Y.Z), VVVVKKPP viimeisimmän commitin päivämäärä ja N monesko sen päivän commit
# se on. Sama commit saa siis saman version jokaisella koneella (tämä kone, kannettava, Forgejo-runner).
# Committaamattomat muutokset: loppuun "+muokattu" (Androidin versionCode on sama kuin commitilla).
# Androidin versionCode: päivämäärä * 100 + N (0.7.3.20261030.6 -> 2026103006), siksi N enintään 99.
# Uusi julkaisu kasvattaa yleensä viimeistä numeroa tiedostossa RELEASE_VERSION: 0.7.1 -> 0.7.2.
import os
import datetime
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASE_FILE = os.path.join(SCRIPT_DIR, "RELEASE_VERSION")
VERSION_FILE = os.path.join(SCRIPT_DIR, "version.py")


def git(*args):
    return subprocess.run(["git", "-C", SCRIPT_DIR, *args], capture_output=True, text=True,
                          check=True).stdout


def commit_date_and_number():
    """Viimeisimmän commitin päivä (commitin omalla aikavyöhykkeellä) ja monesko sen päivän commit se on.
    Lasketaan kaikki HEAD:sta saavutettavat saman päivän commitit, joten sama commit antaa aina saman
    numeron. Vaatii koko historian (CI:ssä fetch-depth: 0)."""
    dates = git("log", "--format=%cd", "--date=format:%Y%m%d", "HEAD").split()
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        raise RuntimeError("git-historia on vajaa (shallow clone): numero ei olisi oikea")
    return dates[0], dates.count(dates[0])


def main():
    with open(RELEASE_FILE, encoding="utf-8") as f:
        release = f.read().strip()

    try:
        date, number = commit_date_and_number()
        modified = git("status", "--porcelain") != ""
    except (OSError, subprocess.CalledProcessError, RuntimeError, IndexError) as e:
        # Ei gittiä tai repoa (esim. lähdekoodi zip-pakettina): tunnistettava varaversio
        print(f"Varoitus: versiota ei saatu gitistä ({e}), käytetään numeroa 0", file=sys.stderr)
        date, number, modified = datetime.date.today().strftime("%Y%m%d"), 0, True
    if number > 99:
        sys.exit(f"Päivällä {date} on yli 99 committia, versionCode ei riitä")

    version = f"{release}.{date}.{number}" + ("+muokattu" if modified else "")
    version_code = int(date) * 100 + number

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write("# Tämän tiedoston luo bump_version.py jokaisella buildilla. Älä muokkaa käsin.\n")
        f.write(f'VERSION = "{version}"\n')
        f.write(f"VERSION_CODE = {version_code}\n")

    print(f"Versio: {version} ({version_code})")


if __name__ == "__main__":
    main()
