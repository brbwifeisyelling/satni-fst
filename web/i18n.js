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
    uiLanguage: "Käyttöliittymän kieli", language: "Kieli",
    sidebar: "Historia ja suosikit",
    theme: "Teema", themeAuto: "Automaattinen", themeLight: "Vaalea", themeDark: "Tumma",
    about: "Tietoa",
    searchPlaceholder: "Hae saameksi, käännöksellä tai taivutusmuodolla",
    search: "Hae",
    ocrTitle: "Hae sanaa valokuvasta", ocrCamera: "📷 Ota kuva", ocrGallery: "🖼️ Valitse kuva",
    ocrIntro: "Ota kuva saamen- tai suomenkielisestä tekstistä tai valitse kuva, ja valitse suunta yltä. Teksti tunnistetaan puhelimessa, eikä kuva lähde laitteelta.",
    ocrWorking: "Tunnistetaan tekstiä…", ocrFinding: "Haetaan sanoja…",
    ocrFound: (n) => `Sanakirjan sanoja ${n} · napauta sanaa · zoomaa sormilla`,
    ocrSami: "Saame", ocrUiLang: "Suomi", ocrDirTitle: "Vaihda suuntaa",
    ocrStyle: "Merkintätapa ja väri", ocrFrame: "Kehys", ocrUnderline: "Alleviivaus",
    ocrNoText: "Kuvasta ei löytynyt tekstiä. Kokeile ottaa kuva lähempää ja suoraan edestä.",
    ocrNoWords: "Tekstiä löytyi, mutta ei sanakirjan sanoja.",
    experimental: "Kokeelliset ominaisuudet", experimentalOn: "Käytössä", experimentalOff: "Pois käytöstä",
    experimentalHint: "Kokeiluversioita: voivat vielä muuttua tai poistua.",
    expOcr: "Hae sanaa valokuvasta", expOcrDesc: "📷 hakukentän vieressä: sanakirjan sanat merkitään kuvaan.",
    expOcrInfo: `<p>Hakukentän viereen tulee 📷-painike. Ota kuva tekstistä tai valitse kuva, ja sanakirjan sanat merkitään
      kuvaan. Napauta sanaa, niin näet käännöksen.</p>
      <p>Teksti tunnistetaan puhelimessa Googlen ML Kitillä, eikä kuva lähde laitteelta. ML Kit voi lähettää Googlelle
      nimettömiä käyttötilastoja, kun toimintoa käytetään.</p>`,
    expSms: "Koltansaame", expSmsDesc: "Koltansaamen sanat sanakortissa.",
    expSmsInfo: `<p>Sanakortissa näytetään koltansaamen sanoja GiellaLT:n koltansaamen sanakirjoista.</p>
      <p>Kun haet suomeksi (esim. talo), koltan sanat ovat hakusanan vastineita suoraan sanakirjasta. Pohjoissaamen ja
      koltansaamen välillä ei ole sanakirjaa, joten saamen sanalle ne haetaan sen suomennosten kautta ja merkitään
      ”suomen kautta”. Ne voivat silloin kuulua sanan toiseen merkitykseen.</p>
      <p>Koltansaamen osaaja ei ole vielä tarkistanut aineistoa.</p>`,
    expEnable: "Ota käyttöön", cancel: "Peruuta", smsVia: "suomen kautta",
    ocrError: "Kuvan käsittely ei onnistunut.", ocrNoApp: "Kamerasovellusta ei löytynyt.",
    showGrade: "Näytä aste (GD/HD)",
    settings: "Asetukset", otherLanguages: "Muut kielet",
    extraLangsHint: "Valittujen kielten käännökset näkyvät sanakortissa suomennoksen lisäksi.",
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
      <dt>Ääntäminen</dt><dd>🔈 sanan vieressä, tai napauta taulukon muotoa: kuuntele tai kopioi.</dd>
      <dt>Suosikit</dt><dd>★ tallentaa sanan omalle listalle.</dd>`,
    tryThese: "Kokeile:", randomWord: "Satunnainen sana",
    listen: "Kuuntele", fetching: "Haetaan…", listenTo: (text) => `Kuuntele: ${text}`,
    copy: "Kopioi", copied: (text) => `Kopioitu: ${text}`,
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
    formIn: (q, forms, lang) => `<b>${q}</b> ≈ ${forms} <span class="muted small">(${lang === "fin" ? "suomeksi" : "norjaksi"}, likimäärin)</span>`,
    viaForm: (q, base, sme, tag) => `<b>${q}</b> = ${base}` + (sme ? ` ≈ <b>${sme}</b> <span class="muted small">(${tag}, likimäärin)</span>` : ` <span class="muted small">(perusmuoto)</span>`),
    gradation: "Astevaihtelu", noGradation: "ei näkyvää astevaihtelua",
    gradForms: "Vahva → heikko aste", gradClusters: "Konsonantit", gradGrades: "Asteet", gradGroup: "Oahpa-ryhmä",
    gradeLegend: `Aste: <b class="gd">vihreä = GD</b> vahva aste &nbsp;&nbsp; <b class="hd">oranssi = HD</b> heikko aste`,
    noForms: "FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.",
    tapHint: "Napauta muotoa: kuuntele tai kopioi.",
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
    elsewhere: "Sanasta muualla",
    gtTitle: "Taivutus Giellateknon generaattorissa", satniTitle: "Sana sátni.org-sanakirjoissa",
    langName: { fin: "suomi", nob: "norja", eng: "englanti", smn: "inarinsaame", smj: "luulajansaame", sma: "eteläsaame" },
    langIn: { fin: "Suomeksi", nob: "Norjaksi", eng: "Englanniksi", smn: "Inarinsaameksi", sms: "Koltansaameksi", smj: "Luulajansaameksi", sma: "Eteläsaameksi" },
    // Tietoa-ikkuna. Ääntämisen kuvaus on sovittu Divvunin kanssa (2026-10-29), älä muuta sisältöä.
    aboutWeb: (v) => (v ? `Versio ${v} (web)` : "Web-versio"), aboutDesktop: (v) => `Versio ${v} (työpöytä)`,
    aboutAndroid: (v) => `Versio ${v} (Android)`,
    aboutBody: `<p>Pohjoissaamen taivutin ja sanakirja, joka perustuu avoimeen lähdekoodiin.</p>
      <p>Sanakirjadata ja kieliteknologiapohja ovat peräisin Giellateknolta ja Divvunilta. Kielidata ja
         taivutussäännöt on laskettu Giellateknon / Divvunin avoimilla FST-malleilla ja XML-sanakirjoilla.</p>
      <p>Ääntäminen: Divvunin ja Giellateknon puhesynteesi (UiT Norjan arktinen yliopisto), äänet Biret,
         Máhtte ja Sunná. Äänet haetaan palvelusta api-giellalt.uit.no samaan tapaan kuin sátni.org-sivustolla.</p>
      <p>Lisenssit: sanakirjat © GiellaLT (CC BY 4.0, yhdistetty ja täydennetty taivutusmuodoilla),
         taivutus GiellaLT lang-sme (GPL-3.0), käännösten taivutus GiellaLT lang-fin (GPL-3.0) ja Norsk ordbank
         (Språkbanken / Nasjonalbiblioteket, CC BY 4.0), koltansaame (kokeellinen) GiellaLT dict-sms-mul, dict-fin-sms ja
         dict-nob-sms (CC BY 4.0 / 3.0), sql.js (MIT). Android-sovelluksen kokeellinen
         tekstintunnistus: Google ML Kit (Googlen käyttöehdot). Kuva käsitellään puhelimessa eikä lähde laitteelta;
         ML Kit voi lähettää Googlelle nimettömiä käyttötilastoja, kun tekstintunnistusta käytetään. Sátni FST on vapaa ohjelma (GPL-3.0).
         Astevaihtelun ryhmät: Oahpa (Giellatekno). Kaikki lähteet, lisenssit ja tehdyt muutokset: Lisenssit-painike alla.
         Lähdekoodi: <a href="https://github.com/sombyduodji/satni-fst" target="_blank" rel="noopener">github.com/sombyduodji/satni-fst</a>.</p>
      <p>Jos huomaat ongelman, ota yhteyttä sähköpostitse <a href="mailto:satni@somby.fi">satni@somby.fi</a>
         tai tee ilmoitus GitHubissa: <a href="https://github.com/sombyduodji/satni-fst/issues" target="_blank" rel="noopener">github.com/sombyduodji/satni-fst/issues</a>.
         Palaute ja ehdotukset ovat tervetulleita sähköpostitse.</p>
      <p>Tekijä: Juha Somby</p>
      <p class="about-coffee">Sátni FST on ilmainen. Jos siitä on sinulle hyötyä, voit tarjota tekijälle kahvit:
         <a class="coffee-btn" href="https://buymeacoffee.com/sombyduodji" target="_blank" rel="noopener"><img src="icons/coffee.svg" alt="">Buy me a coffee</a></p>`,
    close: "Sulje", licenses: "Lisenssit", licensesTitle: "Lisenssit ja tekijänoikeudet",
  },

  nb: {
    title: "Sátni FST – nordsamisk ordbok og bøyingsverktøy",
    brandSub: "Åpen nordsamisk ordbok og bøyingsgenerator",
    uiLanguage: "Språk i brukergrensesnittet", language: "Språk",
    sidebar: "Historikk og favoritter",
    theme: "Tema", themeAuto: "Automatisk", themeLight: "Lyst", themeDark: "Mørkt",
    about: "Om",
    searchPlaceholder: "Søk på samisk, med oversettelse eller bøyd form",
    search: "Søk",
    ocrTitle: "Søk etter ord i et bilde", ocrCamera: "📷 Ta bilde", ocrGallery: "🖼️ Velg bilde",
    ocrIntro: "Ta et bilde av samisk eller norsk tekst eller velg et bilde, og velg retning ovenfor. Teksten gjenkjennes på telefonen, og bildet forlater ikke enheten.",
    ocrWorking: "Gjenkjenner tekst…", ocrFinding: "Søker etter ord…",
    ocrFound: (n) => `Ord fra ordboka: ${n} · trykk på et ord · zoom med fingrene`,
    ocrSami: "Samisk", ocrUiLang: "Norsk", ocrDirTitle: "Bytt retning",
    ocrStyle: "Merking og farge", ocrFrame: "Ramme", ocrUnderline: "Understreking",
    ocrNoText: "Fant ingen tekst i bildet. Prøv å ta bildet nærmere og rett forfra.",
    ocrNoWords: "Fant tekst, men ingen ord fra ordboka.",
    experimental: "Eksperimentelle funksjoner", experimentalOn: "På", experimentalOff: "Av",
    experimentalHint: "Prøveversjoner: kan fortsatt endres eller fjernes.",
    expOcr: "Søk etter ord i et bilde", expOcrDesc: "📷 ved søkefeltet: ordene fra ordboka merkes i bildet.",
    expOcrInfo: `<p>En 📷-knapp vises ved søkefeltet. Ta et bilde av tekst eller velg et bilde, så blir ordene fra ordboka
      merket i bildet. Trykk på et ord for å se oversettelsen.</p>
      <p>Teksten gjenkjennes på telefonen med Googles ML Kit, og bildet forlater ikke enheten. ML Kit kan sende anonym
      bruksstatistikk til Google når funksjonen brukes.</p>`,
    expSms: "Skoltesamisk", expSmsDesc: "Skoltesamiske ord på ordkortet.",
    expSmsInfo: `<p>Ordkortet viser skoltesamiske ord fra GiellaLTs skoltesamiske ordbøker.</p>
      <p>Når du søker på norsk (f.eks. hus), er de skoltesamiske ordene oversettelser av søkeordet rett fra ordboka. Det
      finnes ingen ordbok mellom nordsamisk og skoltesamisk, så for et samisk ord hentes de via de finske oversettelsene
      og merkes «via finsk». Da kan de høre til en annen betydning av ordet.</p>
      <p>Materialet er ennå ikke kontrollert av noen som kan skoltesamisk.</p>`,
    expEnable: "Slå på", cancel: "Avbryt", smsVia: "via finsk",
    ocrError: "Kunne ikke behandle bildet.", ocrNoApp: "Fant ingen kameraapp.",
    showGrade: "Vis stadium (GD/HD)",
    settings: "Innstillinger", otherLanguages: "Andre språk",
    extraLangsHint: "Oversettelser på valgte språk vises på ordkortet i tillegg til den norske.",
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
      <dt>Uttale</dt><dd>🔈 ved ordet, eller trykk på en form i tabellen: lytt eller kopier.</dd>
      <dt>Favoritter</dt><dd>★ lagrer ordet i din egen liste.</dd>`,
    tryThese: "Prøv:", randomWord: "Tilfeldig ord",
    listen: "Lytt", fetching: "Henter…", listenTo: (text) => `Lytt: ${text}`,
    copy: "Kopier", copied: (text) => `Kopiert: ${text}`,
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
    formIn: (q, forms, lang) => `<b>${q}</b> ≈ ${forms} <span class="muted small">(${lang === "fin" ? "på finsk" : "på norsk"}, omtrent)</span>`,
    viaForm: (q, base, sme, tag) => `<b>${q}</b> = ${base}` + (sme ? ` ≈ <b>${sme}</b> <span class="muted small">(${tag}, omtrent)</span>` : ` <span class="muted small">(grunnform)</span>`),
    gradation: "Stadieveksling", noGradation: "ingen synlig stadieveksling",
    gradForms: "Sterkt → svakt stadium", gradClusters: "Konsonanter", gradGrades: "Stadier", gradGroup: "Oahpa-gruppe",
    gradeLegend: `Stadium: <b class="gd">grønn = GD</b> sterkt stadium &nbsp;&nbsp; <b class="hd">oransje = HD</b> svakt stadium`,
    noForms: "FST-generatoren ga ingen bøyingsformer for dette ordet.",
    tapHint: "Trykk på en form: lytt eller kopier.",
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
    elsewhere: "Ordet andre steder",
    gtTitle: "Bøying i Giellateknos generator", satniTitle: "Ordet i ordbøkene på sátni.org",
    langName: { fin: "finsk", nob: "norsk", eng: "engelsk", smn: "enaresamisk", smj: "lulesamisk", sma: "sørsamisk" },
    langIn: { fin: "På finsk", nob: "På norsk", eng: "På engelsk", smn: "På enaresamisk", sms: "På skoltesamisk", smj: "På lulesamisk", sma: "På sørsamisk" },
    // Oversettelse av den finske teksten som er avtalt med Divvun (2026-10-29)
    aboutWeb: (v) => (v ? `Versjon ${v} (nett)` : "Nettversjon"), aboutDesktop: (v) => `Versjon ${v} (skrivebord)`,
    aboutAndroid: (v) => `Versjon ${v} (Android)`,
    aboutBody: `<p>Nordsamisk bøyingsverktøy og ordbok basert på åpen kildekode.</p>
      <p>Ordbokdataene og språkteknologien kommer fra Giellatekno og Divvun. Språkdataene og
         bøyingsreglene er beregnet med Giellateknos og Divvuns åpne FST-modeller og XML-ordbøker.</p>
      <p>Uttale: talesyntese fra Divvun og Giellatekno (UiT Norges arktiske universitet), stemmene Biret,
         Máhtte og Sunná. Lyden hentes fra tjenesten api-giellalt.uit.no på samme måte som på nettstedet sátni.org.</p>
      <p>Lisenser: ordbøkene © GiellaLT (CC BY 4.0, slått sammen og utvidet med bøyingsformer),
         bøying GiellaLT lang-sme (GPL-3.0), bøying av oversettelsene GiellaLT lang-fin (GPL-3.0) og Norsk ordbank
         (Språkbanken / Nasjonalbiblioteket, CC BY 4.0), skoltesamisk (eksperimentelt) GiellaLT dict-sms-mul, dict-fin-sms og
         dict-nob-sms (CC BY 4.0 / 3.0), sql.js (MIT). Eksperimentell tekstgjenkjenning i
         Android-appen: Google ML Kit (Googles vilkår). Bildet behandles på telefonen og forlater ikke enheten;
         ML Kit kan sende anonym bruksstatistikk til Google når tekstgjenkjenningen brukes. Sátni FST er fri programvare (GPL-3.0).
         Stadievekslingsgrupper: Oahpa (Giellatekno). Alle kilder, lisenser og endringer: Lisenser-knappen nedenfor.
         Kildekode: <a href="https://github.com/sombyduodji/satni-fst" target="_blank" rel="noopener">github.com/sombyduodji/satni-fst</a>.</p>
      <p>Hvis du finner et problem, ta kontakt på e-post <a href="mailto:satni@somby.fi">satni@somby.fi</a>
         eller meld det på GitHub: <a href="https://github.com/sombyduodji/satni-fst/issues" target="_blank" rel="noopener">github.com/sombyduodji/satni-fst/issues</a>.
         Tilbakemeldinger og forslag tas gjerne imot på e-post.</p>
      <p>Laget av: Juha Somby</p>
      <p class="about-coffee">Sátni FST er gratis. Har du nytte av den, kan du spandere en kaffe på utvikleren:
         <a class="coffee-btn" href="https://buymeacoffee.com/sombyduodji" target="_blank" rel="noopener"><img src="icons/coffee.svg" alt="">Buy me a coffee</a></p>`,
    close: "Lukk", licenses: "Lisenser", licensesTitle: "Lisenser og opphavsrett",
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
