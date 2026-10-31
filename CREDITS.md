# Credits and licences

Sátni FST is built almost entirely on the open work of others. **The dictionaries, the morphology
and the pronunciation all come from the Sámi language technology community** — above all
[GiellaLT](https://giellalt.github.io/), [Divvun](https://divvun.no/) and
[Giellatekno](https://giellatekno.uit.no/) at UiT The Arctic University of Norway. Sátni FST only
combines their work into one offline app.

## Dictionaries — GiellaLT, CC BY 4.0

| Dictionary | Used for | Source |
|---|---|---|
| North Sámi → Finnish | Finnish translations, meanings and examples | [giellalt/dict-sme-fin](https://github.com/giellalt/dict-sme-fin) |
| North Sámi → Norwegian | Norwegian translations, meanings and examples | [giellalt/dict-sme-nob](https://github.com/giellalt/dict-sme-nob) |
| North Sámi → English | English translations | [giellalt/dict-sme-eng](https://github.com/giellalt/dict-sme-eng) |
| North Sámi → Inari Sámi | Inari Sámi translations | [giellalt/dict-sme-smn](https://github.com/giellalt/dict-sme-smn) |
| North Sámi → Lule Sámi | Lule Sámi translations | [giellalt/dict-sme-smj](https://github.com/giellalt/dict-sme-smj) |
| North Sámi → Southern Sámi | Southern Sámi translations | [giellalt/dict-sme-sma](https://github.com/giellalt/dict-sme-sma) |
| Finnish → North Sámi | Searching with Finnish words | [giellalt/dict-fin-sme](https://github.com/giellalt/dict-fin-sme) |
| Norwegian → North Sámi | Searching with Norwegian words | [giellalt/dict-nob-sme](https://github.com/giellalt/dict-nob-sme) |

All are © GiellaLT / Divvun / Giellatekno and their contributors, licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
`dict-sme-fin` is included in this repository as an unmodified copy ([dict-sme-fin/SOURCE.md](dict-sme-fin/SOURCE.md));
the others are downloaded from GiellaLT by [`hae_sanakirjat.sh`](hae_sanakirjat.sh) and are not part
of this repository.

### Changes made to the dictionary data

CC BY 4.0 requires saying what was changed. When building the app's database,
[`import_full_dict.py`](import_full_dict.py):

- merges all the dictionaries above into one database, joining translations of the same word;
- adds words that appear only in the other-language dictionaries, if the North Sámi FST recognises them;
- adds inflection tables and consonant gradation generated with the lang-sme FST (below);
- applies hand-made corrections from [`korjaukset.tsv`](korjaukset.tsv);
- replaces Norwegian letters in Finnish translations (æ → ä, ø → ö) and drops empty placeholders such as `_FIN_`.

## Morphology — GiellaLT lang-sme, GPL-3.0

The inflection tables are generated with the North Sámi analyser and generator from
[giellalt/lang-sme](https://github.com/giellalt/lang-sme), licensed under the
[GNU General Public License v3.0](LICENSE). Authors: Linda Wiechetek, Katri Hiovain-Asikainen,
Inga Lill Sigga Mikkelsen, Sjur N. Moshagen, Flammie A Pirinen, Trond Trosterud, Børre Gaup and the
lang-sme contributors. The compiled models are in [`src/fst/`](src/fst/SOURCE.md).

## Finnish inflection — GiellaLT lang-fin, GPL-3.0

The inflected forms of the Finnish translations (*talo – talossa – taloon*, *tehdä – teen – tekisin*)
are generated with the Finnish analyser and generator from [giellalt/lang-fin](https://github.com/giellalt/lang-fin)
(GiellaLT / Giellatekno, UiT The Arctic University of Norway; based on the Omorfi lexicon), licensed under the
[GNU General Public License v3.0](LICENSE). The compiled models come from GiellaLT's nightly
package `giella-fin` and are downloaded by [`hae_sanakirjat.sh`](hae_sanakirjat.sh); they are not part of
this repository. [`fin_forms.py`](fin_forms.py) keeps only the forms of words used as translations and drops
archaic and dialectal variants (*vaattehien*, *taloin*, *kirkko-laissa*).

## Norwegian inflection — Norsk ordbank, CC BY

The inflected forms of the Norwegian translations (*hus – huset – husene*, *gjøre – gjorde – gjort*)
come from [Norsk ordbank – bokmål 2005](https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-5/)
(dump of 2022-02-01), © Språkbanken / Nasjonalbiblioteket, licensed under
[CC BY](https://creativecommons.org/licenses/by/4.0/). It is downloaded by
[`hae_sanakirjat.sh`](hae_sanakirjat.sh) and is not part of this repository.
Changes: [`nob_forms.py`](nob_forms.py) keeps only the forms of words used as translations, and
inflects compounds missing from the word bank by their last part (*arealgrense* like *grense*).

## Consonant gradation table — Oahpa

The gradation groups and series shown in the app (`gradation.py`) follow the
[consonant gradation table of Oahpa](https://oahpa.no/sme/gramm/tabell_stadieveksling.html)
(Giellatekno, UiT).

## Pronunciation — Divvun speech synthesis

Pronunciation uses the speech synthesis of Divvun and Giellatekno (UiT The Arctic University of
Norway), voices **Biret, Máhtte and Sunná**, through the service `api-giellalt.uit.no`, in the same
way as [sátni.org](https://satni.org). The synthesis runs as a network service; the voices themselves are not included in the app.
Divvun has confirmed (2026-10-29) that the app may use the API this way.
The voice menu's sample sentence (*Bures boahtin Sápmái*, one per voice) is included in the app as small
audio files ([`web/voices/`](web/voices/), made with [`hae_aaninaytteet.sh`](hae_aaninaytteet.sh) from the
same service) so that it plays without a network connection. Divvun (UiT The Arctic University of Norway)
has given permission (2026-10-30) to keep generated samples in the app.

## Other links

The "Giellatekno" button opens the word's full paradigm in Giellatekno's
[online paradigm generator](https://gtweb.uit.no/) (link only).

## Software

| Component | Where | Licence |
|---|---|---|
| [sql.js](https://github.com/sql-js/sql.js) 1.10.3 (SQLite compiled to WebAssembly) | `web/vendor/` | MIT ([LICENSE-sql.js.txt](web/vendor/LICENSE-sql.js.txt)); SQLite itself is public domain |
| [Qt for Python / PySide6](https://doc.qt.io/qtforpython/) 6.9.3 (incl. Qt WebEngine) | desktop builds only, not in this repository | LGPL-3.0 |
| [PyInstaller](https://pyinstaller.org/) | builds the desktop apps | GPL-2.0 with bootloader exception |
| [HFST](https://hfst.github.io/) (`hfst-lookup`) | used when building the database, not distributed | see HFST |
| [Google ML Kit Text Recognition v2](https://developers.google.com/ml-kit/vision/text-recognition/v2) 16.0.1 (bundled model) | Android app only (experimental photo search), downloaded by Gradle, not in this repository | [ML Kit Terms of Service](https://developers.google.com/ml-kit/terms); closed source, free to use. Runs on the phone: photos are not sent anywhere. According to Google, ML Kit sends anonymous usage and performance statistics to Google and may download model updates (only when the photo search is used) |
| [AndroidX Core](https://developer.android.com/jetpack/androidx/releases/core) 1.13.1 (FileProvider) | Android app only, downloaded by Gradle | Apache-2.0 |
| Libraries that ML Kit depends on (AndroidX, Kotlin standard library, Google Play services base libraries) | Android app only, downloaded by Gradle | AndroidX and Kotlin: Apache-2.0; Google Play services libraries: [Android Software Development Kit License](https://developer.android.com/studio/terms) |

## Logo

The logo is the [Sámi flag](https://en.wikipedia.org/wiki/Sámi_flag) (designed by Astrid Båhl, 1986)
drawn as a drop ([`packaging/icon/satni-icon.svg`](packaging/icon/satni-icon.svg)).

## Sátni FST

© 2026 Juha Somby. Licensed under the [GNU General Public License v3.0](LICENSE), with the additional
permission below.

### Additional permission under GNU GPL version 3 section 7

If you modify this Program, or any covered work, by linking or combining it with Google ML Kit
(including ML Kit Text Recognition and the libraries it depends on, or a modified version of them),
containing parts covered by the terms of the ML Kit Terms of Service, the licensor of this Program
grants you additional permission to convey the resulting work. Corresponding Source for a non-source
form of such a combination shall not include the source code for the parts of Google ML Kit used, as
well as that of the covered work.

This permission is given by Juha Somby for the parts of Sátni FST he holds the copyright to. It does
not change the licences of the third-party parts listed above. The Android app uses ML Kit only for
the experimental photo search; the desktop apps and the web version do not contain it.
