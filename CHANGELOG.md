# Changelog

All releases of Sátni FST. Downloads: [GitHub releases](https://github.com/sombyduodji/satni-fst/releases).

## 0.8.1 — 2026-10-31

- **Loading ring in the photo search** (Android, experimental): a spinning ring over the photo while the text is
  recognised and while dictionary words are looked up, also when switching the direction (Sámi ⇄ Finnish or
  Norwegian) with a photo open. Looking up words in the other direction can take a few seconds on a phone, and the
  app no longer looks frozen meanwhile.
- **Buy me a coffee** link at the end of the About window, for those who want to support Sátni FST.
- The photo appears right away while its words are looked up, and the direction button changes as soon as it is
  tapped.

## 0.8 — 2026-10-31

- **Listen and copy any form:** tap a form in the inflection table or the *All forms* tab to open a small bubble
  with 🔈 and a copy button. Copying works on Android, Windows, Linux and the web version.
- **New listen button:** a round 🔈 button next to the word replaces the *Listen* button; a spinning ring shows
  while the sound is fetched.
- **Tidier word card:** consonant gradation is shown in labelled cells (strong → weak form, consonants, grades,
  Oahpa group) that no longer break in the middle of a line; on phones they form a 2 × 2 grid.
- **Links to other sites as pills:** Giellatekno and sátni.org are now round buttons under *Word elsewhere*, in their
  own box to the right of the word on wide screens and at the bottom of the card on phones. The ChatGPT button was
  removed.
- **Photo word marks in the Sámi flag colours:** red, yellow, blue or green. Yellow marks get a darker edge so they
  stand out on light paper.
- **Licences in the app:** the About window has a *Licences* button that shows all copyright and licence notices
  and the full licence texts, including those of the libraries bundled in the desktop apps. The About window now
  also credits Oahpa and links to the source code.

## 0.7.6.1 — 2026-10-30

- **Experimental, Android: look up words from a photo.** Take a photo of text or pick one, and the words found in
  the dictionary are marked in the photo. Tap a word to see a bubble with its translation and a 🔈 button, and tap the
  bubble to open the word in the dictionary; Back returns to the photo.
  - Works from North Sámi to Finnish or Norwegian (the user interface language) and back, also with inflected words
    (*dagan* → *dahkat*, *talossa* → *viessu*). Missing Sámi diacritics are fixed with the dictionary (*cahci* → *čáhci*).
  - Choose how words are marked: a light frame or an underline, in one of six colours.
  - Zoom with two fingers or a double tap.
  - Text is recognised on the phone with Google ML Kit; the photo never leaves the device. ML Kit may send anonymous
    usage statistics to Google when the feature is used.
  - Off by default: switch it on under *Experimental features* at the bottom of the ☰ menu.
- **Loading animation** on the 🔈 Listen button while the sound is fetched.
- **Licence:** an additional permission under GPL-3.0 section 7 allows the Android app to include Google ML Kit
  (see [CREDITS.md](CREDITS.md)).
- The Android app is larger (about 57 MB) because of the text recognition model. The desktop apps and the web version
  are unchanged apart from the version number.

## 0.7.5 — 2026-10-30

- Search with inflected Finnish and Norwegian words: *juon* finds *juhkat*, *taloon* finds *viessu*, *husene* finds
  *dállu*. For Finnish words the card also shows the Sámi word in the same form.
- First stable release; contact for problems and feedback in the About window and README.

## 0.7.4 — 2026-10-30

- The translation follows the searched form (*viesus* ≈ *talossa / talosta*, *dagan* ≈ *teen*).
- Better search for inflected words: common words first, search limited to North Sámi and the user interface language.
- Cleaner dictionary: duplicate entries merged, grammar notes no longer shown as words.
- New ☰ menu on all platforms; translations follow the user interface language; other languages can be switched on.
- Voice samples (Biret, Máhtte, Sunná) included in the app; the first start asks for the language.

## 0.7.3 — 2026-10-30

- Android: share a word from any app straight to Sátni FST.
- Search the word on sátni.org or ask ChatGPT from the word card.
- About 1 300 more Finnish translations from the Finnish–Sámi dictionary.

## 0.7.2 — 2026-10-29

- Fixes.

## 0.7.1 — 2026-10-29

- Phone layout and scrolling fixes.

## 0.7 — 2026-10-29

- Phone layout fixes.

## 0.6 — 2026-10-29

- Clearer search results; translations only in the selected language.

## 0.5 — 2026-10-29

- Contact address satni@somby.fi; Android release signing key (updates install over 0.5 and newer).

## 0.4 — 2026-10-29

- Android app, new logo, GPL-3.0 licence and credits.

## 0.3 — 2026-10-29

- User interface in Finnish and Norwegian, translations in six languages, reverse dictionaries for searching,
  80 417 words.

## 0.2 — 2026-10-28

- Consonant gradation, Sámi case table, meanings and examples, Giellatekno button.

## 0.1 — 2026-10-28

- First version.
