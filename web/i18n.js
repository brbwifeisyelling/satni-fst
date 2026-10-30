"use strict";
/* Käyttöliittymän tekstit: suomi (oletus) ja norja (bokmål). Avaimet ovat samat molemmissa kielissä.
   Funktiona annettu teksti saa parametrit, esim. t("noHits", "dahkat"). index.html:ssä elementit
   merkitään data-i18n-attribuuteilla (ks. applyStaticTexts app.js:ssä). */

const UI_LANGUAGES = {
  fi: { name: "Suomi", translationLang: "fin" },
  nb: { name: "Norsk", translationLang: "nob" },
};

const UI_TEXTS = {
  fi: {
    title: "Sátni FST – pohjoissaamen sanakirja ja taivutin",
    brandSub: "Pohjoissaamen avoin sanakirja ja taivutusgeneraattori",
    uiLanguage: "Käyttöliittymän kieli",
    sidebar: "Historia ja suosikit",
    theme: "Teema", themeAuto: "Automaattinen", themeLight: "Vaalea", themeDark: "Tumma",
    about: "Tietoa",
    searchPlaceholder: "Hae saameksi, käännöksellä tai taivutusmuodolla",
    search: "Hae",
    showGrade: "Näytä aste (GD/HD)",
    translations: "Käännökset", mainLanguages: "Pääkielet", otherLanguages: "Muut kielet",
    voice: "Ääni",
    favourites: "★ Suosikit", history: "Historia", clearHistory: "Tyhjennä historia",
    noFavourites: "Ei vielä suosikkeja", noHistory: "Ei hakuja",
    addFavourite: "Lisää suosikkeihin", removeFavourite: "Poista suosikeista",
    loadingTitle: "Ladataan sanakirjaa…",
    loadingText: "Ensimmäisellä kerralla ladataan noin 40 Mt. Sen jälkeen sanakirja toimii myös ilman verkkoyhteyttä.",
    unpacking: "Puretaan…",
    loadFailed: (status) => `Sanakirjan lataus epäonnistui (${status})`,
    loadFailedLong: (msg) => `Sanakirjan lataus epäonnistui: ${msg}`,
    welcomeTitle: "Bures boahtin! – Tervetuloa",
    welcomeLead: "Pohjoissaamen sanakirja, jossa on sanojen koko taivutus. Käännökset suomeksi ja norjaksi " +
      "sekä osalle sanoista englanniksi, inarin-, luulajan- ja eteläsaameksi.",
    welcomeTips: `<dt>Hae</dt><dd>saamen sanalla (dahkat), suomen sanalla (tehdä) tai taivutetulla muodolla (dagan).</dd>
      <dt>Taivutus</dt><dd>verbeillä kaikki tapaluokat, nomineilla sijamuodot (ol. ja ml.).</dd>
      <dt>Astevaihtelu</dt><dd>vahva aste <b class="gd">GD</b> vihreänä, heikko aste <b class="hd">HD</b> oranssina.</dd>
      <dt>Ääntäminen</dt><dd>Kuuntele-nappi tai napautus taulukon muodossa.</dd>
      <dt>Suosikit</dt><dd>★ tallentaa sanan omalle listalle.</dd>`,
    tryThese: "Kokeile:", randomWord: "Satunnainen sana",
    listen: "Kuuntele", fetching: "Haetaan…", listenTo: (text) => `Kuuntele: ${text}`,
    tabTable: "Taivutus", tabRaw: "Kaikki muodot",
    tabMeanings: (n, examples) => `Merkitykset (${n})` + (examples ? ` ja esimerkit (${examples})` : ""),
    noHits: (q) => `Ei osumia haulle ”${q}”`,
    noHitsHint: "Kokeile toista kirjoitusasua, perusmuotoa tai käännöstä.",
    noTranslation: "(ei käännöstä)",
    noTranslationIn: { fin: "(ei suomennosta)", nob: "(ei norjankielistä käännöstä)", eng: "(ei englanninkielistä käännöstä)",
                       smn: "(ei inarinsaamenkielistä käännöstä)", smj: "(ei luulajansaamenkielistä käännöstä)",
                       sma: "(ei eteläsaamenkielistä käännöstä)" },
    morePrefix: (n, q) => `+${n} muuta sanaa, jotka alkavat ”${q}”`, fewerPrefix: "Näytä vähemmän",
    moreMeanings: (n) => `+${n} merkitystä`, otherLangs: "muut kielet",
    searchedForm: (q, tags) => `Haettu muoto ${q}: ${tags}`,
    gradation: "Astevaihtelu", noGradation: "ei näkyvää astevaihtelua",
    gradeLegend: `Aste: <b class="gd">vihreä = GD</b> vahva aste &nbsp;&nbsp; <b class="hd">oranssi = HD</b> heikko aste`,
    noForms: "FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.",
    tapHint: "Napauta muotoa kuullaksesi sen ääntämisen.",
    noMeanings: "Ei merkitystietoja.", noExampleTranslation: "(ei käännöstä lähteessä)",
    usedIn: (place, code) => `käytössä ${place} (${code})`,
    geo: { N: "Norjassa", S: "Suomessa", R: "Ruotsissa" },
    ttsFailed: (msg) => `Ääntämistä ei saatu: ${msg}.`,
    ttsOffline: "puhepalveluun ei saatu yhteyttä. Ensimmäinen kuuntelu vaatii verkkoyhteyden",
    ttsStatus: (status) => `puhepalvelu vastasi ${status}`,
    // Taivutustaulukko
    indicative: "Indikatiivi", present: "preesens", preterite: "preteriti", conditional: "Konditionaali",
    potential: "Potentiaali", imperative: "Imperatiivi", nonFinite: "Nominaalimuodot",
    affirmative: "Myönteinen", negative: "Kielteinen", baseForm: "Perusmuoto", uninflected: "Taipumaton",
    caseCol: "Sijamuoto", formCol: "Muoto", singular: "ol. (yksikkö)", plural: "ml. (monikko)",
    comparison: "Vertailumuodot", predicative: "predikatiivi", attributive: "attribuutti",
    comparative: "Komparatiivi", superlative: "Superlatiivi",
    nonFiniteRows: ["Infinitiivi", "Perfektipartisiippi", "Preesenspartisiippi", "Gerundi", "Verbigenetiivi",
                    "Verbiabessiivi", "Supiini", "Aktio (Nom)", "Aktio (Loc)", "Aktio (Com)", "Aktio (Ess)"],
    pos: {
      V: "Verbi", N: "Substantiivi", A: "Adjektiivi", ADV: "Adverbi", PRON: "Pronomini", NUM: "Numeraali",
      CC: "Rinnastuskonjunktio", CS: "Alistuskonjunktio", PCLE: "Partikkeli", INTERJ: "Interjektio",
      PO: "Postpositio", PR: "Prepositio", CMP: "Yhdyssanan alkuosa", MWE: "Monisanainen ilmaus",
      PHRASE: "Fraasi", ABBR: "Lyhenne",
    },
    subtype: {
      Prop: "Erisnimi", NomAg: "Tekijännimi", Pers: "Persoonapronomini", Dem: "Demonstratiivipronomini",
      Indef: "Indefiniittipronomini", Interr: "Interrogatiivipronomini", Refl: "Refleksiivipronomini",
      Rel: "Relatiivipronomini", Ord: "Järjestysluku", Coll: "Kollektiivi",
    },
    askAiTitle: "Kysy ChatGPT:ltä (avautuu selaimessa; tekoälyn vastaukset voivat olla virheellisiä)",
    askAi: (word, pos, known) => `Pohjoissaamen sana "${word}" (${[pos, ...known].join("; ")}): merkitys ja käännös suomeksi.`,
    langName: { fin: "suomi", nob: "norja", eng: "englanti", smn: "inarinsaame", smj: "luulajansaame", sma: "eteläsaame" },
    langIn: { fin: "Suomeksi", nob: "Norjaksi", eng: "Englanniksi", smn: "Inarinsaameksi", smj: "Luulajansaameksi", sma: "Eteläsaameksi" },
    // Tietoa-ikkuna. Ääntämisen kuvaus on sovittu Divvunin kanssa (2026-10-29), älä muuta sisältöä.
    aboutWeb: "Web-versio (testi)", aboutDesktop: (v) => `Versio ${v} (työpöytä)`,
    aboutAndroid: (v) => `Versio ${v} (Android)`,
    aboutBody: `<p>Pohjoissaamen taivutin ja sanakirja, joka perustuu avoimeen lähdekoodiin.</p>
      <p>Sanakirjadata ja kieliteknologiapohja ovat peräisin Giellateknolta ja Divvunilta. Kielidata ja
         taivutussäännöt on laskettu Giellateknon / Divvunin avoimilla FST-malleilla ja XML-sanakirjoilla.</p>
      <p>Ääntäminen: Divvunin ja Giellateknon puhesynteesi (UiT Norjan arktinen yliopisto), äänet Biret,
         Máhtte ja Sunná. Äänet haetaan palvelusta api-giellalt.uit.no samaan tapaan kuin sátni.org-sivustolla.</p>
      <p>Lisenssit: sanakirjat © GiellaLT (CC BY 4.0, yhdistetty ja täydennetty taivutusmuodoilla),
         taivutus GiellaLT lang-sme (GPL-3.0), sql.js (MIT). Sátni FST on vapaa ohjelma (GPL-3.0).
         Lähteet ja tehdyt muutokset: CREDITS.md lähdekoodin mukana.</p>
      <p>Ohjelma on tuore ja voi sisältää huomattavia virheitä, eikä sille ole virallista tukea.</p>
      <p>Tekijä: Juha Somby · Palaute: <a href="mailto:satni@somby.fi">satni@somby.fi</a></p>`,
    close: "Sulje",
  },

  nb: {
    title: "Sátni FST – nordsamisk ordbok og bøyingsverktøy",
    brandSub: "Åpen nordsamisk ordbok og bøyingsgenerator",
    uiLanguage: "Språk i brukergrensesnittet",
    sidebar: "Historikk og favoritter",
    theme: "Tema", themeAuto: "Automatisk", themeLight: "Lyst", themeDark: "Mørkt",
    about: "Om",
    searchPlaceholder: "Søk på samisk, med oversettelse eller bøyd form",
    search: "Søk",
    showGrade: "Vis stadium (GD/HD)",
    translations: "Oversettelser", mainLanguages: "Hovedspråk", otherLanguages: "Andre språk",
    voice: "Stemme",
    favourites: "★ Favoritter", history: "Historikk", clearHistory: "Tøm historikken",
    noFavourites: "Ingen favoritter ennå", noHistory: "Ingen søk",
    addFavourite: "Legg til i favoritter", removeFavourite: "Fjern fra favoritter",
    loadingTitle: "Laster ordboken…",
    loadingText: "Første gang lastes ca. 40 MB ned. Deretter fungerer ordboken også uten nettilkobling.",
    unpacking: "Pakker ut…",
    loadFailed: (status) => `Kunne ikke laste ordboken (${status})`,
    loadFailedLong: (msg) => `Kunne ikke laste ordboken: ${msg}`,
    welcomeTitle: "Bures boahtin! – Velkommen",
    welcomeLead: "Nordsamisk ordbok med full bøying av ordene. Oversettelser til norsk og finsk, " +
      "og for en del av ordene til engelsk, enaresamisk, lulesamisk og sørsamisk.",
    welcomeTips: `<dt>Søk</dt><dd>med et samisk ord (dahkat), et norsk ord (gjøre) eller en bøyd form (dagan).</dd>
      <dt>Bøying</dt><dd>alle modi for verb, kasus for nomen (ol. og ml.).</dd>
      <dt>Stadieveksling</dt><dd>sterkt stadium <b class="gd">GD</b> i grønt, svakt stadium <b class="hd">HD</b> i oransje.</dd>
      <dt>Uttale</dt><dd>Lytt-knappen, eller trykk på en form i tabellen.</dd>
      <dt>Favoritter</dt><dd>★ lagrer ordet i din egen liste.</dd>`,
    tryThese: "Prøv:", randomWord: "Tilfeldig ord",
    listen: "Lytt", fetching: "Henter…", listenTo: (text) => `Lytt: ${text}`,
    tabTable: "Bøying", tabRaw: "Alle former",
    tabMeanings: (n, examples) => `Betydninger (${n})` + (examples ? ` og eksempler (${examples})` : ""),
    noHits: (q) => `Ingen treff for «${q}»`,
    noHitsHint: "Prøv en annen skrivemåte, grunnformen eller en oversettelse.",
    noTranslation: "(ingen oversettelse)",
    noTranslationIn: { fin: "(ingen finsk oversettelse)", nob: "(ingen norsk oversettelse)", eng: "(ingen engelsk oversettelse)",
                       smn: "(ingen enaresamisk oversettelse)", smj: "(ingen lulesamisk oversettelse)",
                       sma: "(ingen sørsamisk oversettelse)" },
    morePrefix: (n, q) => `+${n} andre ord som begynner med «${q}»`, fewerPrefix: "Vis færre",
    moreMeanings: (n) => `+${n} betydninger`, otherLangs: "andre språk",
    searchedForm: (q, tags) => `Søkt form ${q}: ${tags}`,
    gradation: "Stadieveksling", noGradation: "ingen synlig stadieveksling",
    gradeLegend: `Stadium: <b class="gd">grønn = GD</b> sterkt stadium &nbsp;&nbsp; <b class="hd">oransje = HD</b> svakt stadium`,
    noForms: "FST-generatoren ga ingen bøyingsformer for dette ordet.",
    tapHint: "Trykk på en form for å høre uttalen.",
    noMeanings: "Ingen opplysninger om betydning.", noExampleTranslation: "(ingen oversettelse i kilden)",
    usedIn: (place, code) => `brukt ${place} (${code})`,
    geo: { N: "i Norge", S: "i Finland", R: "i Sverige" },
    ttsFailed: (msg) => `Kunne ikke hente uttalen: ${msg}.`,
    ttsOffline: "fikk ikke kontakt med taletjenesten. Første avspilling krever nettilkobling",
    ttsStatus: (status) => `taletjenesten svarte ${status}`,
    indicative: "Indikativ", present: "presens", preterite: "preteritum", conditional: "Kondisjonalis",
    potential: "Potensialis", imperative: "Imperativ", nonFinite: "Infinitte former",
    affirmative: "Bekreftende", negative: "Nektende", baseForm: "Grunnform", uninflected: "Ubøyelig",
    caseCol: "Kasus", formCol: "Form", singular: "ol. (entall)", plural: "ml. (flertall)",
    comparison: "Gradbøying", predicative: "predikativ", attributive: "attributiv",
    comparative: "Komparativ", superlative: "Superlativ",
    nonFiniteRows: ["Infinitiv", "Perfektum partisipp", "Presens partisipp", "Gerundium", "Verbgenitiv",
                    "Verbabessiv", "Supinum", "Aktio (Nom)", "Aktio (Loc)", "Aktio (Com)", "Aktio (Ess)"],
    pos: {
      V: "Verb", N: "Substantiv", A: "Adjektiv", ADV: "Adverb", PRON: "Pronomen", NUM: "Tallord",
      CC: "Sideordningskonjunksjon", CS: "Subjunksjon", PCLE: "Partikkel", INTERJ: "Interjeksjon",
      PO: "Postposisjon", PR: "Preposisjon", CMP: "Forledd i sammensetning", MWE: "Flerordsuttrykk",
      PHRASE: "Frase", ABBR: "Forkortelse",
    },
    subtype: {
      Prop: "Egennavn", NomAg: "Agentiv", Pers: "Personlig pronomen", Dem: "Demonstrativt pronomen",
      Indef: "Ubestemt pronomen", Interr: "Spørrepronomen", Refl: "Refleksivt pronomen",
      Rel: "Relativt pronomen", Ord: "Ordenstall", Coll: "Kollektiv",
    },
    askAiTitle: "Spør ChatGPT (åpnes i nettleseren; svar fra KI kan inneholde feil)",
    askAi: (word, pos, known) => `Nordsamisk ord "${word}" (${[pos, ...known].join("; ")}): betydning og oversettelse til norsk.`,
    langName: { fin: "finsk", nob: "norsk", eng: "engelsk", smn: "enaresamisk", smj: "lulesamisk", sma: "sørsamisk" },
    langIn: { fin: "På finsk", nob: "På norsk", eng: "På engelsk", smn: "På enaresamisk", smj: "På lulesamisk", sma: "På sørsamisk" },
    // Oversettelse av den finske teksten som er avtalt med Divvun (2026-10-29)
    aboutWeb: "Nettversjon (test)", aboutDesktop: (v) => `Versjon ${v} (skrivebord)`,
    aboutAndroid: (v) => `Versjon ${v} (Android)`,
    aboutBody: `<p>Nordsamisk bøyingsverktøy og ordbok basert på åpen kildekode.</p>
      <p>Ordbokdataene og språkteknologien kommer fra Giellatekno og Divvun. Språkdataene og
         bøyingsreglene er beregnet med Giellateknos og Divvuns åpne FST-modeller og XML-ordbøker.</p>
      <p>Uttale: talesyntese fra Divvun og Giellatekno (UiT Norges arktiske universitet), stemmene Biret,
         Máhtte og Sunná. Lyden hentes fra tjenesten api-giellalt.uit.no på samme måte som på nettstedet sátni.org.</p>
      <p>Lisenser: ordbøkene © GiellaLT (CC BY 4.0, slått sammen og utvidet med bøyingsformer),
         bøying GiellaLT lang-sme (GPL-3.0), sql.js (MIT). Sátni FST er fri programvare (GPL-3.0).
         Kilder og endringer: CREDITS.md i kildekoden.</p>
      <p>Programmet er nytt og kan inneholde betydelige feil, og det har ingen offisiell støtte.</p>
      <p>Laget av: Juha Somby · Tilbakemelding: <a href="mailto:satni@somby.fi">satni@somby.fi</a></p>`,
    close: "Lukk",
  },
};

// Liput SVG:nä (emoji-liput eivät näy Windowsissa)
const FLAGS = {
  fi: `<svg viewBox="0 0 18 11" aria-hidden="true"><rect width="18" height="11" fill="#fff"/>` +
      `<rect x="5" width="3" height="11" fill="#002f6c"/><rect y="4" width="18" height="3" fill="#002f6c"/></svg>`,
  nb: `<svg viewBox="0 0 22 16" aria-hidden="true"><rect width="22" height="16" fill="#ba0c2f"/>` +
      `<rect x="6" width="4" height="16" fill="#fff"/><rect y="6" width="22" height="4" fill="#fff"/>` +
      `<rect x="7" width="2" height="16" fill="#00205b"/><rect y="7" width="22" height="2" fill="#00205b"/></svg>`,
};
