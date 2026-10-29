# Sátni FST

**An offline North Sámi dictionary with full inflection** — for Linux, Windows, Android and the web.

> **Suomeksi:** Pohjoissaamen sanakirja ja taivutin, joka toimii ilman verkkoyhteyttä. Käännökset suomeksi
> ja norjaksi, käyttöliittymä suomeksi tai norjaksi.
>
> **På norsk:** Nordsamisk ordbok og bøyingsverktøy som virker uten nett. Oversettelser til norsk og finsk,
> brukergrensesnitt på norsk eller finsk.

Sátni FST combines the open dictionaries and morphology of [GiellaLT](https://giellalt.github.io/),
[Divvun](https://divvun.no/) and [Giellatekno](https://giellatekno.uit.no/) into one app.
**All language data comes from them — see [CREDITS.md](CREDITS.md).**

## Features

- About 80 000 North Sámi words, about 74 000 of them with full inflection tables
  (all moods for verbs, cases in singular and plural for nominals)
- Consonant gradation shown in colour (strong grade GD / weak grade HD)
- Translations in Finnish and Norwegian, and for some words English, Inari, Lule and Southern Sámi
- Search with a North Sámi word, an inflected form (*dagan* → *dahkat*) or a Finnish/Norwegian word
- Pronunciation with Divvun's speech synthesis (voices Biret, Máhtte, Sunná; needs a network connection)
- User interface in Finnish or Norwegian, light and dark theme, history and favourites

## Building

The finished apps are built from these steps. Most build steps run in Docker, so little needs to be installed.

| Step | Command | Needs |
|---|---|---|
| 1. Download the GiellaLT dictionaries | `./hae_sanakirjat.sh` | git |
| 2. Build the database (`satni.db`, ~10 min) | `python3 import_full_dict.py` | Python 3, [HFST](https://hfst.github.io/) (`hfst-lookup`) |
| 3. Desktop apps (AppImage + Windows) | `./build.sh` | Docker; a Windows VM for the Windows build (see `build_qt_exe.sh`) |
| 4. Android app (APK) | `./build_apk.sh` | Docker |
| 5. Release zip | `python3 julkaisu_zip.py` | Python 3 |

The web version (`web/`) needs only `python3 export_web_data.py` and any static web server.

The compiled FST models are included in [`src/fst/`](src/fst/SOURCE.md), so building
[lang-sme](https://github.com/giellalt/lang-sme) yourself is not necessary.

Code comments and commit messages are in Finnish.

## Licence

Sátni FST is free software under the [GNU General Public License v3.0](LICENSE).
The dictionaries are © GiellaLT and licensed under CC BY 4.0, the morphology (lang-sme) under GPL-3.0 —
see [CREDITS.md](CREDITS.md) for all sources, licences and the changes made to the data.

Feedback: Juha Somby, <juha@somby.fi>
