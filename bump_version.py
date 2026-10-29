#!/usr/bin/env python3
# Kasvattaa build-numeroa ja kirjoittaa version.py-tiedoston (sovellukset ja build-skriptit lukevat sen).
# Versio on muotoa X.Y.Z.VVVVKKPP.N: X.Y.Z on julkaisun numero tiedostosta RELEASE_VERSION (sama kuin
# GitHub-julkaisun tagi vX.Y.Z), VVVVKKPP päivämäärä ja N päivän juokseva build-numero (1, 2, 3...).
# Uusi julkaisu kasvattaa yleensä viimeistä numeroa: 0.7.1 -> 0.7.2.
import os
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASE_FILE = os.path.join(SCRIPT_DIR, "RELEASE_VERSION")
COUNTER_FILE = os.path.join(SCRIPT_DIR, "build_number.txt")
VERSION_FILE = os.path.join(SCRIPT_DIR, "version.py")


def main():
    today = datetime.date.today().strftime("%Y%m%d")
    with open(RELEASE_FILE, encoding="utf-8") as f:
        release = f.read().strip()

    last_date, last_number = "", 0
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, encoding="utf-8") as f:
                last_date, last_number = f.read().split()
                last_number = int(last_number)
        except ValueError:
            last_date, last_number = "", 0

    number = last_number + 1 if last_date == today else 1
    version = f"{release}.{today}.{number}"

    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(f"{today} {number}\n")
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write("# Tämän tiedoston luo bump_version.py jokaisella buildilla. Älä muokkaa käsin.\n")
        f.write(f'VERSION = "{version}"\n')

    print(f"Versio: {version}")


if __name__ == "__main__":
    main()
