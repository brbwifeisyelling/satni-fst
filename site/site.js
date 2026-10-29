// Kotisivun tekstit kolmella kielellä ja uusimman julkaisun lataukset GitHubin rajapinnasta.
const TEXTS = {
  fi: {
    tagline: "Pohjoissaamen sanakirja ja taivutin",
    title: "Pohjoissaamen sanakirja, joka taivuttaa jokaisen sanan",
    lead: "Noin 80 000 sanaa käännöksineen ja täydet taivutustaulukot. Toimii ilman verkkoyhteyttä tietokoneella, puhelimessa ja selaimessa.",
    open: "Avaa sanakirja selaimessa",
    download: "Lataa sovellus",
    openNote: "Selainversio lataa sanakirjan (40 Mt) ensimmäisellä kerralla ja toimii sen jälkeen myös ilman verkkoa.",
    f1h: "80 000 sanaa", f1: "Käännökset suomeksi ja norjaksi, osalle sanoista myös englanniksi, inarin-, luulajan- ja eteläsaameksi.",
    f2h: "Täydet taivutukset", f2: "Verbien kaikki tapaluokat, nominien sijamuodot yksikössä ja monikossa – noin 74 000 sanalle.",
    f3h: "Hae millä tahansa muodolla", f3: "Taivutettu muoto löytää perusmuodon (dagan → dahkat). Hae myös suomeksi tai norjaksi.",
    f4h: "Astevaihtelu näkyvissä", f4: "Vahva aste (GD) vihreällä, heikko aste (HD) oranssilla – taulukoissa ja sanakortissa.",
    f5h: "Ääntäminen", f5: "Kuuntele sanat ja taivutusmuodot Divvunin puhesynteesillä (äänet Biret, Máhtte ja Sunná).",
    f6h: "Suomeksi tai norjaksi", f6: "Käyttöliittymä suomeksi tai norjaksi, vaalea ja tumma teema, historia ja suosikit.",
    phonesH: "Puhelimessa",
    p1: "Sanakortti", p2: "Taivutustaulukko", p3: "Norjaksi, tumma teema", p4: "Merkitykset",
    downloadH: "Lataa",
    releaseLoading: "Haetaan uusinta versiota…",
    release: (v, d) => `Uusin versio ${v} (${d}). Testiversio: ilmainen ja avoin, ei virallista tukea.`,
    releaseFail: "Uusimman version tietoja ei saatu – lataukset löytyvät GitHubista.",
    win: "Windows 10 ja 11. Pura zip ja käynnistä satni-fst.exe.",
    linux: "AppImage: salli suoritus ja käynnistä kaksoisnapsautuksella.",
    android: "Android 7.0+. Avaa tiedosto puhelimessa ja salli asennus.",
    webH: "Selaimessa", web: "Ei asennusta. Toimii nykyaikaisissa selaimissa myös puhelimessa.",
    allReleases: "Kaikki versiot ja muutokset:",
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
    f1h: "80 000 ord", f1: "Oversettelser til norsk og finsk, for noen ord også engelsk, enaresamisk, lulesamisk og sørsamisk.",
    f2h: "Fullstendig bøying", f2: "Alle modi for verb, kasus i entall og flertall for nomen – for om lag 74 000 ord.",
    f3h: "Søk med hvilken som helst form", f3: "En bøyd form finner grunnformen (dagan → dahkat). Søk også på norsk eller finsk.",
    f4h: "Stadieveksling synlig", f4: "Sterkt stadium (GD) i grønt, svakt stadium (HD) i oransje – i tabellene og på ordkortet.",
    f5h: "Uttale", f5: "Lytt til ord og bøyingsformer med Divvuns talesyntese (stemmene Biret, Máhtte og Sunná).",
    f6h: "På norsk eller finsk", f6: "Brukergrensesnitt på norsk eller finsk, lyst og mørkt tema, historikk og favoritter.",
    phonesH: "På mobilen",
    p1: "Ordkort", p2: "Bøyingstabell", p3: "Norsk, mørkt tema", p4: "Betydninger",
    downloadH: "Last ned",
    releaseLoading: "Henter nyeste versjon…",
    release: (v, d) => `Nyeste versjon ${v} (${d}). Testversjon: gratis og åpen, uten offisiell støtte.`,
    releaseFail: "Kunne ikke hente nyeste versjon – nedlastingene finnes på GitHub.",
    win: "Windows 10 og 11. Pakk ut zip-fila og start satni-fst.exe.",
    linux: "AppImage: tillat kjøring og start med dobbeltklikk.",
    android: "Android 7.0+. Åpne fila på mobilen og tillat installering.",
    webH: "I nettleseren", web: "Ingen installering. Virker i moderne nettlesere, også på mobilen.",
    allReleases: "Alle versjoner og endringer:",
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
    f1h: "80 000 words", f1: "Translations into Finnish and Norwegian, and for some words English, Inari, Lule and Southern Sámi.",
    f2h: "Full inflection", f2: "All moods for verbs, cases in singular and plural for nominals – for about 74 000 words.",
    f3h: "Search with any form", f3: "An inflected form finds its base form (dagan → dahkat). You can also search in Finnish or Norwegian.",
    f4h: "Consonant gradation shown", f4: "Strong grade (GD) in green, weak grade (HD) in orange – in the tables and on the word card.",
    f5h: "Pronunciation", f5: "Listen to words and inflected forms with Divvun's speech synthesis (voices Biret, Máhtte and Sunná).",
    f6h: "Finnish or Norwegian", f6: "User interface in Finnish or Norwegian, light and dark theme, history and favourites.",
    phonesH: "On your phone",
    p1: "Word card", p2: "Inflection table", p3: "Norwegian, dark theme", p4: "Meanings",
    downloadH: "Download",
    releaseLoading: "Looking up the latest version…",
    release: (v, d) => `Latest version ${v} (${d}). Test version: free and open source, no official support.`,
    releaseFail: "Couldn't look up the latest version – the downloads are on GitHub.",
    win: "Windows 10 and 11. Unzip and run satni-fst.exe.",
    linux: "AppImage: allow running it, then double-click.",
    android: "Android 7.0+. Open the file on the phone and allow installing.",
    webH: "In the browser", web: "Nothing to install. Works in modern browsers, on phones too.",
    allReleases: "All versions and changes:",
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
    const res = await fetch("https://api.github.com/repos/brbwifeisyelling/satni-fst/releases?per_page=10");
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
