// Kotisivun tekstit kolmella kielellä ja uusimman julkaisun lataukset GitHubin rajapinnasta.
const TEXTS = {
  fi: {
    tagline: "Pohjoissaamen sanakirja ja taivutin",
    title: "Pohjoissaamen sanakirja, joka taivuttaa jokaisen sanan",
    lead: "Noin 80 000 sanaa käännöksineen ja täydet taivutustaulukot. Toimii ilman verkkoyhteyttä tietokoneella, puhelimessa ja selaimessa.",
    open: "Avaa sanakirja selaimessa",
    download: "Lataa sovellus",
    openNote: "Selainversio lataa sanakirjan (40 Mt) ensimmäisellä kerralla ja toimii sen jälkeen myös ilman verkkoa.",
    newH: "Uutta versioissa 0.7.3–0.8",
    v080: "Versio 0.8", r1h: "Uudistettu sanakortti",
    r1: "Napauta mitä tahansa taivutusmuotoa: kuplasta voit kuunnella tai kopioida sen. Astevaihtelu näkyy selkeinä soluina (vahva → heikko aste, konsonantit, asteet), ja Giellateknon ja sátni.orgin napit ovat kohdassa Sanasta muualla. ChatGPT-nappi on poistettu. Kuvahaun merkinnät ovat saamelaislipun väreissä.",
    v076: "Versio 0.7.6.1", o1h: "Kokeiltavaksi: hae sanaa valokuvasta",
    o1: "Androidilla: ota kuva tekstistä tai valitse kuva, ja sanakirjan sanat merkitään kuvaan. Napauta sanaa: kuplassa on käännös ja 🔈-kuuntelu, ja kuplasta pääset sanakirjaan. Toimii saamesta suomeen ja suomesta saameen (myös taivutetuilla sanoilla: talossa → viessu), ja merkinnän tavan (kehys tai alleviivaus) ja värin voi valita. Teksti tunnistetaan puhelimessa, eikä kuva lähde laitteelta (Googlen ML Kit voi lähettää nimettömiä käyttötilastoja). Kytke päälle valikon lopusta: Kokeelliset ominaisuudet.",
    q1: "1. Ota tai valitse kuva", q2: "2. Napauta sanaa", q3: "3. Sanakirjassa",
    v075: "Versio 0.7.5", v074: "Versio 0.7.4", v073: "Versio 0.7.3",
    k1h: "Hae taivutetulla suomen sanalla", k1: "Perusmuotoa ei tarvita: juon löytää sanan juhkat ja taloon sanan viessu. Sanakortti näyttää myös saamen sanan samassa muodossa: juon = juoda ≈ jugan.",
    m1h: "Käännös haetussa muodossa", m1: "Taivutetulla sanalla haettaessa näet käännöksen samassa muodossa: viesus ≈ talossa / talosta, dagan ≈ teen.",
    m2h: "Parempi haku", m2: "Yleisimmät sanat löytyvät ensin (lea, lei, mus), ja haku toimii saameksi ja suomeksi. Sanakirjasta on siivottu kaksoissanat.",
    m3h: "Uusi valikko ja ääninäytteet", m3: "☰-valikossa ovat kieli, teema, aste, suosikit ja historia. Kuuntele äänet Biret, Máhtte ja Sunná ennen valintaa – näytteet toimivat ilman verkkoa. Englannin, inarin-, luulajan- ja eteläsaamen käännökset saa näkyviin valikosta.",
    n1h: "Jaa sana suoraan sovellukseen", n1: "Androidilla: valitse sana mistä tahansa sovelluksesta – selaimesta, sähköpostista tai viestistä – ja valitse Jaa → Sátni FST. Sana ja sen käännös avautuvat heti, myös taivutettuna (eamiálbmogiid → eamiálbmot).",
    n2h: "Hae myös muualta", n2: "Sanakortin napeista sana haetaan suoraan sátni.orgista tai kysytään ChatGPT:ltä valmiilla kysymyksellä – avuksi, kun sanakirjassa ei ole suomennosta.",
    n3h: "Lähes 1 300 suomennosta lisää", n3: "Suomi–saame-sanakirjasta haetaan käännös sanoille, joilta se puuttui (mas = jossa). Lisäksi pois satoja kaksoissanoja.",
    s1: "1. Valitse sana", s2: "2. Jaa → Sátni FST", s3: "3. Käännös heti",
    f1h: "80 000 sanaa", f1: "Käännökset suomeksi ja norjaksi, osalle sanoista myös englanniksi, inarin-, luulajan- ja eteläsaameksi.",
    f2h: "Täydet taivutukset", f2: "Verbien kaikki tapaluokat, nominien sijamuodot yksikössä ja monikossa – noin 74 000 sanalle.",
    f3h: "Hae millä tahansa muodolla", f3: "Taivutettu muoto löytää perusmuodon (dagan → dahkat). Hae myös suomeksi, taivutetullakin sanalla (juon → juhkat).",
    f4h: "Astevaihtelu näkyvissä", f4: "Vahva aste (GD) vihreällä, heikko aste (HD) oranssilla – taulukoissa ja sanakortissa.",
    f5h: "Ääntäminen", f5: "Kuuntele sanat ja taivutusmuodot Divvunin puhesynteesillä (äänet Biret, Máhtte ja Sunná).",
    f6h: "Suomeksi tai norjaksi", f6: "Käyttöliittymä suomeksi tai norjaksi, vaalea ja tumma teema, historia ja suosikit.",
    phonesH: "Puhelimessa",
    p1: "Sanakortti", p2: "Taivutustaulukko", p3: "Norjaksi, tumma teema", p4: "Merkitykset",
    downloadH: "Lataa",
    releaseLoading: "Haetaan uusinta versiota…",
    release: (v, d) => `Uusin versio ${v} (${d}). Ilmainen ja avoin, ei virallista tukea.`,
    releaseFail: "Uusimman version tietoja ei saatu – lataukset löytyvät GitHubista.",
    win: "Windows 10 ja 11. Pura zip ja käynnistä satni-fst.exe.",
    linux: "AppImage: salli suoritus ja käynnistä kaksoisnapsautuksella.",
    android: "Android 7.0+. Avaa tiedosto puhelimessa ja salli asennus.",
    webH: "Selaimessa", web: "Ei asennusta. Toimii nykyaikaisissa selaimissa myös puhelimessa.",
    allReleases: "Kaikki versiot ja muutokset:",
    madeH: "Näin se tehtiin",
    made: "Pohjoissaame oli äitini äidinkieli, ja Sátni FST alkoi omana apuvälineenäni, kun lähdin opettelemaan sitä – palaamaan juurilleni. Idea, suunta ja testaus ovat minun, koodin on kirjoittanut tekoäly (Claude, Anthropic) minun ohjauksessani. Itse kielitieto on saamen kieliteknologian asiantuntijoiden työtä (GiellaLT, Divvun, Giellatekno).",
    creditsH: "Kiitokset",
    credits: "Kaikki kielitieto on saamen kieliteknologiayhteisön työtä. Sátni FST kokoaa sen yhteen sovellukseen.",
    c1: "sanakirjat (dict-sme-fin, dict-sme-nob ym., CC BY 4.0) ja morfologia (lang-sme, GPL-3.0)",
    c2: "puhesynteesi (UiT Norjan arktinen yliopisto)",
    c3: "astevaihtelutaulukko",
    license: "Sátni FST on vapaata ohjelmistoa (GPL-3.0). Kaikki lähteet ja lisenssit:",
    feedback: "Palaute:",
  },
  nb: {
    tagline: "Nordsamisk ordbok og bøyingsverktøy",
    title: "Nordsamisk ordbok som bøyer hvert ord",
    lead: "Om lag 80 000 ord med oversettelser og fullstendige bøyingstabeller. Virker uten nett på datamaskin, mobil og i nettleseren.",
    open: "Åpne ordboka i nettleseren",
    download: "Last ned appen",
    openNote: "Nettversjonen laster ned ordboka (40 MB) første gang og virker deretter også uten nett.",
    newH: "Nytt i versjon 0.7.3–0.8",
    v080: "Versjon 0.8", r1h: "Fornyet ordkort",
    r1: "Trykk på en hvilken som helst bøyningsform: i boblen kan du lytte til eller kopiere den. Stadievekslingen vises i oversiktlige felt (sterkt → svakt stadium, konsonanter, stadier), og knappene til Giellatekno og sátni.org ligger under Ordet andre steder. ChatGPT-knappen er fjernet. Markeringene i bildesøket har fargene fra det samiske flagget.",
    v076: "Versjon 0.7.6.1", o1h: "Til utprøving: søk etter ord i et bilde",
    o1: "På Android: ta et bilde av tekst eller velg et bilde, så blir ordene fra ordboka merket i bildet. Trykk på et ord: boblen viser oversettelsen og 🔈 for uttale, og fra boblen kommer du til ordboka. Virker fra samisk til norsk og fra norsk til samisk (også med bøyde ord: huset → viessu), og du kan velge merking (ramme eller understreking) og farge. Teksten gjenkjennes på telefonen, og bildet forlater ikke enheten (Googles ML Kit kan sende anonym bruksstatistikk). Slås på nederst i menyen: Eksperimentelle funksjoner.",
    q1: "1. Ta eller velg et bilde", q2: "2. Trykk på et ord", q3: "3. I ordboka",
    v075: "Versjon 0.7.5", v074: "Versjon 0.7.4", v073: "Versjon 0.7.3",
    k1h: "Søk med bøyde norske ord", k1: "Du trenger ikke grunnformen: husene finner dállu og viessu, og drakk finner juhkat.",
    m1h: "Oversettelsen i den søkte formen", m1: "Når du søker med en bøyd form, viser ordkortet oversettelsen i samme form: viesus ≈ i huset / fra huset, dagan ≈ jeg lager.",
    m2h: "Bedre søk", m2: "De vanligste ordene kommer først (lea, lei, mus), og søket virker på samisk og norsk. Doble oppslagsord er ryddet bort.",
    m3h: "Ny meny og stemmeprøver", m3: "☰-menyen har språk, tema, stadium, favoritter og historikk. Hør stemmene Biret, Máhtte og Sunná før du velger – prøvene virker uten nett. Oversettelser til engelsk, enaresamisk, lulesamisk og sørsamisk kan slås på i menyen.",
    n1h: "Del et ord rett til appen", n1: "På Android: marker et ord i hvilken som helst app – nettleser, e-post eller melding – og velg Del → Sátni FST. Ordet og oversettelsen åpnes med en gang, også i bøyd form (eamiálbmogiid → eamiálbmot).",
    n2h: "Søk også andre steder", n2: "Knappene på ordkortet søker etter ordet direkte på sátni.org eller spør ChatGPT med et ferdig spørsmål – til hjelp når ordboka mangler en oversettelse.",
    n3h: "Flere oversettelser", n3: "Ord som manglet oversettelse får den nå fra finsk–samisk og norsk–samisk ordbok. I tillegg er flere hundre doble ord fjernet.",
    s1: "1. Marker ordet", s2: "2. Del → Sátni FST", s3: "3. Oversettelsen med en gang",
    f1h: "80 000 ord", f1: "Oversettelser til norsk og finsk, for noen ord også engelsk, enaresamisk, lulesamisk og sørsamisk.",
    f2h: "Fullstendig bøying", f2: "Alle modi for verb, kasus i entall og flertall for nomen – for om lag 74 000 ord.",
    f3h: "Søk med hvilken som helst form", f3: "En bøyd form finner grunnformen (dagan → dahkat). Søk også på norsk, også med bøyde ord (husene → viessu).",
    f4h: "Stadieveksling synlig", f4: "Sterkt stadium (GD) i grønt, svakt stadium (HD) i oransje – i tabellene og på ordkortet.",
    f5h: "Uttale", f5: "Lytt til ord og bøyingsformer med Divvuns talesyntese (stemmene Biret, Máhtte og Sunná).",
    f6h: "På norsk eller finsk", f6: "Brukergrensesnitt på norsk eller finsk, lyst og mørkt tema, historikk og favoritter.",
    phonesH: "På mobilen",
    p1: "Ordkort", p2: "Bøyingstabell", p3: "Norsk, mørkt tema", p4: "Betydninger",
    downloadH: "Last ned",
    releaseLoading: "Henter nyeste versjon…",
    release: (v, d) => `Nyeste versjon ${v} (${d}). Gratis og åpen, uten offisiell støtte.`,
    releaseFail: "Kunne ikke hente nyeste versjon – nedlastingene finnes på GitHub.",
    win: "Windows 10 og 11. Pakk ut zip-fila og start satni-fst.exe.",
    linux: "AppImage: tillat kjøring og start med dobbeltklikk.",
    android: "Android 7.0+. Åpne fila på mobilen og tillat installering.",
    webH: "I nettleseren", web: "Ingen installering. Virker i moderne nettlesere, også på mobilen.",
    allReleases: "Alle versjoner og endringer:",
    madeH: "Slik ble den laget",
    made: "Nordsamisk var min mors morsmål, og Sátni FST begynte som et hjelpemiddel for meg selv da jeg begynte å lære det – å vende tilbake til røttene mine. Idéen, retningen og testingen er mine, mens koden er skrevet av kunstig intelligens (Claude, Anthropic) under min veiledning. Selve språkdataene er arbeidet til eksperter på samisk språkteknologi (GiellaLT, Divvun, Giellatekno).",
    creditsH: "Takk",
    credits: "All språkdata er arbeidet til det samiske språkteknologimiljøet. Sátni FST samler det i én app.",
    c1: "ordbøker (dict-sme-fin, dict-sme-nob m.fl., CC BY 4.0) og morfologi (lang-sme, GPL-3.0)",
    c2: "talesyntese (UiT Norges arktiske universitet)",
    c3: "tabell over stadieveksling",
    license: "Sátni FST er fri programvare (GPL-3.0). Alle kilder og lisenser:",
    feedback: "Tilbakemelding:",
  },
  en: {
    tagline: "North Sámi dictionary and inflection",
    title: "A North Sámi dictionary that inflects every word",
    lead: "About 80 000 words with translations and full inflection tables. Works offline on your computer, your phone and in the browser.",
    open: "Open the dictionary in your browser",
    download: "Download the app",
    openNote: "The web version downloads the dictionary (40 MB) the first time and then works offline too.",
    newH: "New in versions 0.7.3–0.8",
    v080: "Version 0.8", r1h: "A redesigned word card",
    r1: "Tap any inflected form: a bubble lets you listen to it or copy it. Consonant gradation is shown in clear cells (strong → weak grade, consonants, grades), and the Giellatekno and sátni.org buttons sit under Word elsewhere. The ChatGPT button has been removed. Photo search marks come in the colours of the Sámi flag.",
    v076: "Version 0.7.6.1", o1h: "To try out: look up words from a photo",
    o1: "On Android: take a photo of text or pick one, and the words found in the dictionary are marked in the photo. Tap a word: the bubble shows the translation and 🔈 to listen, and takes you to the dictionary. Works from Sámi to Finnish or Norwegian and back (also with inflected words: talossa → viessu), and you can choose the marking (frame or underline) and its colour. The text is recognised on the phone, and the photo never leaves the device (Google ML Kit may send anonymous usage statistics). Switch it on at the bottom of the menu: Experimental features.",
    q1: "1. Take or pick a photo", q2: "2. Tap a word", q3: "3. In the dictionary",
    v075: "Version 0.7.5", v074: "Version 0.7.4", v073: "Version 0.7.3",
    k1h: "Search with inflected Finnish and Norwegian words", k1: "No need for the base form: juon finds juhkat, taloon finds viessu and husene finds dállu. For Finnish words the card also shows the Sámi word in the same form: juon = juoda ≈ jugan.",
    m1h: "Translation in the searched form", m1: "Search with an inflected word and the card shows the translation in the same form: viesus ≈ talossa / talosta in Finnish, i huset / fra huset in Norwegian.",
    m2h: "Better search", m2: "The most common words come first (lea, lei, mus), and the search works in Sámi and in the language of the user interface. Duplicate entries have been cleaned up.",
    m3h: "New menu and voice samples", m3: "The ☰ menu holds language, theme, gradation, favourites and history. Listen to the voices Biret, Máhtte and Sunná before choosing – the samples work offline. English, Inari, Lule and Southern Sámi translations can be switched on in the menu.",
    n1h: "Share a word straight to the app", n1: "On Android: select a word in any app – a browser, email or a message – and choose Share → Sátni FST. The word and its translation open right away, even in an inflected form (eamiálbmogiid → eamiálbmot).",
    n2h: "Search elsewhere too", n2: "Buttons on the word card search for the word directly on sátni.org or ask ChatGPT with a ready-made question – handy when the dictionary has no translation.",
    n3h: "More translations", n3: "Words that had no Finnish or Norwegian translation now get one from the Finnish–Sámi and Norwegian–Sámi dictionaries. Several hundred duplicate words are gone, too.",
    s1: "1. Select the word", s2: "2. Share → Sátni FST", s3: "3. The translation, right away",
    f1h: "80 000 words", f1: "Translations into Finnish and Norwegian, and for some words English, Inari, Lule and Southern Sámi.",
    f2h: "Full inflection", f2: "All moods for verbs, cases in singular and plural for nominals – for about 74 000 words.",
    f3h: "Search with any form", f3: "An inflected form finds its base form (dagan → dahkat). You can also search in Finnish or Norwegian, inflected words too (juon → juhkat).",
    f4h: "Consonant gradation shown", f4: "Strong grade (GD) in green, weak grade (HD) in orange – in the tables and on the word card.",
    f5h: "Pronunciation", f5: "Listen to words and inflected forms with Divvun's speech synthesis (voices Biret, Máhtte and Sunná).",
    f6h: "Finnish or Norwegian", f6: "User interface in Finnish or Norwegian, light and dark theme, history and favourites.",
    phonesH: "On your phone",
    p1: "Word card", p2: "Inflection table", p3: "Norwegian, dark theme", p4: "Meanings",
    downloadH: "Download",
    releaseLoading: "Looking up the latest version…",
    release: (v, d) => `Latest version ${v} (${d}). Free and open source, no official support.`,
    releaseFail: "Couldn't look up the latest version – the downloads are on GitHub.",
    win: "Windows 10 and 11. Unzip and run satni-fst.exe.",
    linux: "AppImage: allow running it, then double-click.",
    android: "Android 7.0+. Open the file on the phone and allow installing.",
    webH: "In the browser", web: "Nothing to install. Works in modern browsers, on phones too.",
    allReleases: "All versions and changes:",
    madeH: "How it was made",
    made: "North Sámi was my mother's native language, and Sátni FST started as a tool for myself when I set out to learn it – a way back to my roots. The idea, direction and testing are mine; the code was written by AI (Claude, by Anthropic) under my guidance. The language data itself is the work of Sámi language technology experts (GiellaLT, Divvun, Giellatekno).",
    creditsH: "Credits",
    credits: "All language data is the work of the Sámi language technology community. Sátni FST brings it together in one app.",
    c1: "dictionaries (dict-sme-fin, dict-sme-nob and others, CC BY 4.0) and morphology (lang-sme, GPL-3.0)",
    c2: "speech synthesis (UiT The Arctic University of Norway)",
    c3: "consonant gradation table",
    license: "Sátni FST is free software (GPL-3.0). All sources and licences:",
    feedback: "Feedback:",
  },
};
const TITLES = {
  fi: "Sátni FST – pohjoissaamen sanakirja ja taivutin",
  nb: "Sátni FST – nordsamisk ordbok og bøyingsverktøy",
  en: "Sátni FST – North Sámi dictionary and inflection",
};

let release = null;  // null = haetaan, false = haku epäonnistui

function setLang(lang) {
  if (!TEXTS[lang]) lang = "fi";
  const t = TEXTS[lang];
  document.documentElement.lang = lang;
  document.title = TITLES[lang];
  for (const el of document.querySelectorAll("[data-t]")) {
    const text = t[el.dataset.t];
    if (typeof text === "string") el.textContent = text;
  }
  for (const b of document.querySelectorAll(".langs button")) b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
  // Norjankielisellä sivulla norjankieliset kuvat
  const hero = document.querySelector(".hero-shot");
  hero.querySelector("source").srcset = `screenshots/desktop-dark-${lang === "nb" ? "nb" : "fi"}.png`;
  hero.querySelector("img").src = `screenshots/desktop-light-${lang === "nb" ? "nb" : "fi"}.png`;
  showRelease();
}

function showRelease() {
  const t = TEXTS[document.documentElement.lang] || TEXTS.fi;
  const info = document.getElementById("release-info");
  if (release === null) return;
  if (release === false) { info.textContent = t.releaseFail; return; }
  const date = new Date(release.published_at).toLocaleDateString(document.documentElement.lang === "en" ? "en-GB" : document.documentElement.lang);
  info.textContent = t.release(release.tag_name, date);
}

// Uusin julkaisu, myös esijulkaisu (GitHubin "latest" ohittaa esijulkaisut)
async function loadRelease() {
  try {
    const res = await fetch("https://api.github.com/repos/sombyduodji/satni-fst/releases?per_page=10");
    if (!res.ok) throw new Error(res.status);
    release = (await res.json()).find((r) => !r.draft) || false;
  } catch (e) {
    release = false;
  }
  if (release) {
    for (const card of document.querySelectorAll(".card[data-file]")) {
      const asset = release.assets.find((a) => a.name === card.dataset.file);
      if (!asset) continue;
      card.href = asset.browser_download_url;
      card.querySelector(".size").textContent = `${asset.name} · ${Math.round(asset.size / 1e6)} MB`;
    }
  }
  showRelease();
}

for (const b of document.querySelectorAll(".langs button")) {
  b.onclick = () => {
    try { localStorage.setItem("satni-site-lang", b.dataset.lang); } catch (e) {}
    setLang(b.dataset.lang);
  };
}
setLang(document.documentElement.lang);
loadRelease();
