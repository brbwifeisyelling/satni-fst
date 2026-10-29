# Compiled FST models (GiellaLT lang-sme)

`analyser-gt-norm.hfst` and `generator-gt-norm.hfst` are the North Sámi morphological analyser and
generator, **compiled from [giellalt/lang-sme](https://github.com/giellalt/lang-sme)**
(GiellaLT / Divvun / Giellatekno, UiT The Arctic University of Norway).

- Licence: **GPL-3.0** (see [LICENSE](../../LICENSE)). The corresponding source code is the lang-sme
  repository; these files were built from its main branch around 2026-10-28.
- Authors (lang-sme CITATION.cff): Linda Wiechetek, Katri Hiovain-Asikainen, Inga Lill Sigga Mikkelsen,
  Sjur N. Moshagen, Flammie A Pirinen, Trond Trosterud, Børre Gaup, and the contributors listed in
  the lang-sme repository.
- Used by `import_full_dict.py` to analyse base forms and generate the inflection tables. The
  generated forms in the app's database come from these models.
