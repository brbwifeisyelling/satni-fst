"use strict";
/* Sátni FST – web-versio. Sama tietokanta kuin työpöytäversiossa (export_web_data.py), luetaan sql.js:llä.
   LÄHTEET (ks. CREDITS.md): sanakirjat GiellaLT (CC BY 4.0), taivutus GiellaLT lang-sme (GPL-3.0),
   ääntäminen Divvunin ja Giellateknon puhesynteesi, sql.js (MIT, vendor/LICENSE-sql.js.txt). */

const DATA_URL = "data/satni-web.db.gz";
// Divvunin ja Giellateknon puhesynteesi (UiT), käyttö sovittu Divvunin kanssa 2026-10-29
const TTS_URL = "https://api-giellalt.uit.no/tts/se/";
const VOICES = { "Biret": "biret", "Máhtte": "mahtte", "Sunná": "sunna" };
// Giellateknon taivutusgeneraattori (vain linkki)
const GIELLATEKNO_URL = "https://gtweb.uit.no/cgi-bin/smi/smi.cgi?text={word}&pos={pos}&lang=sme&mode=full&action=paradigm";
// Haku muista lähteistä: sátni.org (Divvunin ja Giellateknon sanakirjat ja Giellagáldun termit) sekä ChatGPT
// valmiilla kysymyksellä (i18n.js: askAi), jossa mukana sanakirjan tiedot taustaksi
const SATNI_URL = "https://satni.org/{word}";
const AI_URL = "https://chatgpt.com/?q={prompt}";
const GIELLATEKNO_POS = { N: "N", V: "V", A: "A", ADV: "Adv", NUM: "Num", PRON: "Pron" };

// Käännöskielet (GiellaLT:n dict-sme-*-sanakirjat) ja niiden sarakkeet tietokannassa; main = pääkieli
// (suomi ja norja, joista on myös käänteinen sanakirja), muut näytetään valikossa omana ryhmänään.
// Kielten nimet ovat käyttöliittymän kielellä (i18n.js: langName, langIn).
const LANGUAGES = {
  fin: { col: "finnish_translation", main: true },
  nob: { col: "nob_translation", main: true },
  eng: { col: "eng_translation" },
  smn: { col: "smn_translation" },
  smj: { col: "smj_translation" },
  sma: { col: "sma_translation" },
};
const TRANS_COLS = Object.keys(LANGUAGES).map((l) => LANGUAGES[l].col).join(", ");

const PERSONS = ["Sg1", "Sg2", "Sg3", "Du1", "Du2", "Du3", "Pl1", "Pl2", "Pl3"];
const PRONOUNS = { Sg1: "mun", Sg2: "don", Sg3: "son", Du1: "moai", Du2: "doai", Du3: "soai", Pl1: "mii", Pl2: "dii", Pl3: "sii" };
// Kieltoverbin (ii) indikatiivi- ja imperatiivimuodot
const NEG_AUX = { Sg1: "in", Sg2: "it", Sg3: "ii", Du1: "ean", Du2: "eahppi", Du3: "eaba", Pl1: "eat", Pl2: "ehpet", Pl3: "eai" };
const NEG_AUX_IMPRT = { Sg1: "allon", Sg2: "ale", Sg3: "allos", Du1: "allu", Du2: "alli", Du3: "alloska", Pl1: "allot", Pl2: "allet", Pl3: "alloset" };
// Saamen koulukieliopin sijataulukko: genetiivi ja akkusatiivi samalla rivillä
const CASE_ROWS = [["Nom", ["Nom"]], ["Gen/Akk", ["Acc", "Gen"]], ["Ill", ["Ill"]], ["Lok", ["Loc"]], ["Kom", ["Com"]]];
// Nimet: i18n.js nonFiniteRows samassa järjestyksessä
const VERB_NONFINITE_TAGS = ["Inf", "PrfPrc", "PrsPrc", "Ger", "VGen", "VAbess", "Sup",
                             "Actio+Nom", "Actio+Loc", "Actio+Com", "Actio+Ess"];
const UNINFLECTED_POS = ["ADV", "CC", "CS", "INTERJ", "PCLE", "PO", "PR", "CMP", "MWE"];
const EXAMPLE_WORDS = ["dahkat", "áhčči", "viessu", "mannat", "buorre", "golbma", "juolgi", "oastit"];

const $ = (id) => document.getElementById(id);
let db = null;
const state = { query: "", results: [], index: 0, word: null, paradigm: null, grades: null, tab: "table" };

// --- Asetukset, historia ja suosikit (selaimen localStorage) ---

const DEFAULT_SETTINGS = {
  theme: "auto", voice: "Biret", uiLang: "fi", lang: "fin", showGrade: true, history: [], favourites: [],
  // Muut kielet (asetus valikossa): niiden käännökset näkyvät sanakortissa pääkäännöksen lisäksi; oletuksena
  // ei yhtään. Hakuun ne eivät vaikuta.
  extraLangs: [],
};
// Ensimmäinen käynnistys: asetuksia ei ole vielä tallennettu, joten kysytään käyttöliittymän kieli
const FIRST_RUN = (() => { try { return localStorage.getItem("satni-settings") === null; } catch (e) { return false; } })();
let settings = loadSettings();

function loadSettings() {
  try {
    return Object.assign({}, DEFAULT_SETTINGS, JSON.parse(localStorage.getItem("satni-settings") || "{}"));
  } catch (e) {
    return Object.assign({}, DEFAULT_SETTINGS);
  }
}
function saveSettings() {
  try { localStorage.setItem("satni-settings", JSON.stringify(settings)); } catch (e) { /* yksityinen tila */ }
}

// --- Käyttöliittymän kieli (i18n.js) ---

function t(key, ...args) {
  const texts = UI_TEXTS[settings.uiLang] || UI_TEXTS.fi;
  const value = key in texts ? texts[key] : UI_TEXTS.fi[key];
  return typeof value === "function" ? value(...args) : value;
}
const langName = (lang) => t("langName")[lang];

// index.html:n data-i18n-merkityt tekstit
function applyStaticTexts() {
  document.documentElement.lang = settings.uiLang;
  document.title = t("title");
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);
  for (const el of document.querySelectorAll("[data-i18n-placeholder]")) el.placeholder = t(el.dataset.i18nPlaceholder);
  for (const el of document.querySelectorAll("[data-i18n-aria]")) el.setAttribute("aria-label", t(el.dataset.i18nAria));
  for (const el of document.querySelectorAll("[data-i18n-title]")) el.title = t(el.dataset.i18nTitle);
  // Versionumeron antaa työpöytäsovellus (satni_desktop.py) tai Android-sovellus (android/)
  const version = window.SATNI_VERSION;
  $("about-version").textContent = !version ? t("aboutWeb")
    : window.SATNI_PLATFORM === "android" ? t("aboutAndroid", version) : t("aboutDesktop", version);
  $("random-btn").textContent = t("randomWord");
  renderExtraLangs();

  // Käyttöliittymän kieli valikossa ja aloitussivulla
  const langButtons = Object.entries(UI_LANGUAGES).map(([code, l]) =>
    `<button role="radio" aria-checked="${code === settings.uiLang}" data-lang="${code}"` +
    `${code === settings.uiLang ? ' class="active"' : ""}>${FLAGS[code]}<span>${esc(l.name)}</span></button>`).join("");
  $("welcome-lang").innerHTML = langButtons;
  $("drawer-lang").innerHTML = langButtons;
  renderVoiceList();
}

// Äänet valikossa: valinta ja 🔈-näyte, sama lause kaikilla äänillä. Näytteet ovat sovelluspaketissa
// (web/voices/, hae_aaninaytteet.sh), joten ne toimivat ilman verkkoyhteyttä; jos tiedostoa ei ole, näyte haetaan
// Divvunin puhesynteesistä ja tallennetaan laitteelle kuten muutkin ääntämiset (speak).
const VOICE_SAMPLE = "Bures boahtin Sápmái";
async function playVoiceSample(name, button) {
  try {
    const res = await fetch(`voices/${VOICES[name]}.wav`);
    if (!res.ok) throw new Error(res.status);
    await new Audio(URL.createObjectURL(await res.blob())).play();
  } catch (e) {
    await speak(VOICE_SAMPLE, button, name);
  }
}
function renderVoiceList() {
  $("voice-list").innerHTML = Object.keys(VOICES).map((name) =>
    `<div class="voice-row"><label><input type="radio" name="voice" value="${name}"` +
    `${name === settings.voice ? " checked" : ""}> ${esc(name)}</label>` +
    `<button class="sample-btn" data-voice="${name}" aria-label="${esc(t("listenTo", name))}" ` +
    `title="${esc(VOICE_SAMPLE)}">🔈</button></div>`).join("");
}

// Ensimmäinen käynnistys: valitaan suomi tai norja (ääni on oletus Biret, vaihdettavissa valikosta)
function showFirstRun() {
  $("first-run-lang").innerHTML = Object.entries(UI_LANGUAGES).map(([code, l]) =>
    `<button data-lang="${code}">${FLAGS[code]}<span>${esc(l.name)}</span></button>`).join("");
  $("first-run-lang").onclick = (e) => {
    const b = e.target.closest("[data-lang]");
    if (!b) return;
    setUiLanguage(b.dataset.lang);
    $("first-run").close();
  };
  $("first-run").showModal();
}

// Valikon sulkeminen: taustan napautus, Esc tai Android-sovelluksen takaisin-ele (MainActivity.goBackOrFinish)
function closeDrawer() {
  const open = document.body.classList.contains("sidebar-open");
  document.body.classList.remove("sidebar-open");
  return open;
}

// Muut kielet valikossa: valittujen kielten käännökset näytetään sanakortissa (renderExtraTranslations)
function renderExtraLangs() {
  $("extra-langs").innerHTML = Object.keys(LANGUAGES).filter((l) => !LANGUAGES[l].main).map((l) =>
    `<label class="check"><input type="checkbox" value="${l}"${settings.extraLangs.includes(l) ? " checked" : ""}> ` +
    `${esc(capitalize(langName(l)))}</label>`).join("");
}

// Käännökset ovat aina käyttöliittymän kielellä (suomi -> suomi, norsk -> norja)
function setUiLanguage(code) {
  if (!UI_LANGUAGES[code]) return;
  settings.uiLang = code;
  settings.lang = UI_LANGUAGES[code].translationLang;
  saveSettings();
  applyStaticTexts();
  renderSidebar();
  if (db && state.query) searchAgainKeepingWord();
}

// Kielen vaihto muuttaa tulosten järjestystä (ks. queryDatabase): itse valittu sana pysyy valittuna,
// muuten näytetään uusi ensimmäinen tulos
function searchAgainKeepingWord() {
  const id = state.index ? state.results[state.index]?.id : undefined;
  const index = queryDatabase(state.query).findIndex((r) => r.id === id);
  search(state.query, Math.max(index, 0), false);
}

// --- Apufunktiot ---

// Haussa ä = æ ja ö = ø (norjalaiset nimet, esim. Bjørg)
const fold = (s) => (s || "").toLowerCase().replace(/æ/g, "ä").replace(/ø/g, "ö");
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const nordic = (s) => s.replace(/ä/g, "æ").replace(/ö/g, "ø");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const splitList = (s) => (s || "").split(",").map((p) => p.trim()).filter(Boolean);

function all(sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  return rows;
}

function toast(text, ms = 3500) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), ms);
}

// Vain valitun kielen käännös (muut kielet näkyvät Merkitykset-välilehdellä omina ryhminään)
function translationOf(row, max, lang = settings.lang) {
  return splitList(row[LANGUAGES[lang].col]).slice(0, max).join(", ");
}

// Merkitykset kielittäin, valittu kieli ensin
function meaningsByLanguage(meanings) {
  const groups = Object.keys(LANGUAGES).map((lang) => [lang, meanings.filter((m) => m.lang === lang)]).filter(([, ms]) => ms.length);
  return groups.sort(([a], [b]) => (b === settings.lang) - (a === settings.lang));
}

function wordClassLabel(pos, subtype) {
  let label = t("pos")[(pos || "").toUpperCase()] || pos;
  if (subtype) label += " · " + (t("subtype")[subtype] || subtype);
  return label;
}

// --- Tietokannan lataus ---

async function loadDatabase() {
  const SQL = await initSqlJs({ locateFile: (f) => "vendor/" + f });
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(t("loadFailed", response.status));

  // Ladataan osissa, jotta edistymispalkki liikkuu
  const total = Number(response.headers.get("content-length")) || 0;
  const reader = response.body.getReader();
  const chunks = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (total) $("progress-bar").style.width = `${Math.round((received / total) * 90)}%`;
  }
  let bytes = new Uint8Array(received);
  let offset = 0;
  for (const c of chunks) { bytes.set(c, offset); offset += c.length; }

  // Palvelin voi jo purkaa gzipin (Content-Encoding); puretaan vain jos tiedosto on yhä pakattu
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    $("loading-text").textContent = t("unpacking");
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  $("progress-bar").style.width = "100%";
  return new SQL.Database(bytes);
}

// --- Haku ---

// Haku löytää pohjoissaamen sanat ja muodot sekä käännökset vain suomeksi tai norjaksi: valittu käännöskieli,
// tai jos se on jokin muu kieli (englanti, inarin-, luulajan- tai eteläsaame), käyttöliittymän kieli. Muiden
// kielten sanat (luulajansaamen lea, norjan mus suomenkielisessä haussa) eivät siis peitä pohjoissaamen
// muotoja (lea = leahkit, mus = mun).
const COMMON_WORD = 50000;  // korpusfrekvenssi, jota yleisemmän sanan taivutusmuoto menee käännösten edelle

function queryDatabase(query) {
  const q = fold(query.trim());
  const found = new Map();
  const add = (row, rank) => {
    const prev = found.get(row.id);
    if (!prev || rank < prev.rank) found.set(row.id, { ...row, rank });
  };
  const cols = `id, sme_lemma, pos, subtype, freq, ${TRANS_COLS}`;
  const searchLang = settings.lang;

  // 1 = saamen perusmuoto; 6 = isolla kirjoitettu erisnimi, joka osui vain kirjainkoosta riippumatta.
  // Perusmuoto ilman käännöstä valitulla kielellä 5.5: ensin sana, jonka taivutusmuoto haku on
  // (mas: vain dict-sme-nob:ssa omana sananaan, suomeksi ensin mii "mikä", jonka paikallissija mas on)
  const col = LANGUAGES[settings.lang].col;
  for (const r of all(`SELECT ${cols} FROM dictionary WHERE lemma_fold = ?`, [q])) {
    const first = r.sme_lemma.charAt(0);
    add(r, r.sme_lemma !== query.trim() && first !== first.toLowerCase() ? 6 : r[col] ? 1 : 5.5);
  }
  // 1.5 = käänteisen sanakirjan (dict-fin-sme, dict-nob-sme) hakusana, sen ensisijainen saamennos ensin;
  // 2 = ainoa käännös, 3 = ensimmäinen käännös, 4 = jokin muu
  for (const r of all(
    `SELECT d.${cols.split(", ").join(", d.")}, t.fold, t.lang, t.nr FROM trans_search t JOIN dictionary d ON d.id = t.word_id
     WHERE t.lang = ? AND (t.fold = ? OR t.fold LIKE ? OR t.fold LIKE ? OR t.fold LIKE ?)`,
    [searchLang, q, `${q},%`, `%, ${q},%`, `%, ${q}`]
  )) {
    add(r, r.nr !== null ? (r.fold === q ? 1.5 + Math.min(r.nr, 9) / 100 : 4)
      : r.fold === q ? 2 : r.fold.startsWith(`${q},`) ? 3 : 4);
  }
  // 5 = taivutusmuoto (manan -> mannat); hyvin yleisen sanan muoto 1.2 eli käännösten edelle
  // (lei = leahkit eikä norjan "lei", mus = mun eikä norjan "mus")
  const forms = [q, capitalize(q), nordic(q), capitalize(nordic(q))];
  for (const r of all(
    `SELECT DISTINCT d.${cols.split(", ").join(", d.")}
     FROM paradigms p JOIN dictionary d ON d.id = p.word_id WHERE p.surface IN (?, ?, ?, ?)`, forms
  )) add(r, r.freq >= COMMON_WORD ? 1.2 : 5);
  // 7 = perusmuoto alkaa hakusanalla; monisanaiset ilmaukset (dahkat iežas ...) vain, jos haussa on välilyönti
  const phrases = q.includes(" ") ? "" : "AND instr(lemma_fold, ' ') = 0";
  for (const r of all(`SELECT ${cols} FROM dictionary WHERE lemma_fold >= ? AND lemma_fold < ? ${phrases} LIMIT 60`, [q, q + "￿"])) add(r, 7);

  // Tasatilanteessa saamen sanoista (perusmuoto tai taivutusmuoto) ensin korpuksessa yleisempi
  // (sutnje: son eikä suotnjat), sitten sana, jolla on käännös valitulla kielellä, sitten verbit.
  // Käännösosumien keskinäinen järjestys tulee sanakirjasta (nr), joten frekvenssiä ei käytetä niille.
  const translated = (r) => (r[col] ? 1 : 0);
  const samiFreq = (r) => ([1, 1.2, 5, 5.5].includes(r.rank) ? r.freq || 0 : 0);
  return [...found.values()]
    .sort((a, b) => a.rank - b.rank || samiFreq(b) - samiFreq(a) || translated(b) - translated(a)
      || (b.pos === "V") - (a.pos === "V") || a.sme_lemma.localeCompare(b.sme_lemma, "se"))
    .slice(0, 30);
}

function suggestWords(prefix) {
  const q = fold(prefix.trim());
  if (q.length < 2) return [];
  const rows = all(
    `SELECT sme_lemma, pos, ${TRANS_COLS} FROM dictionary
     WHERE lemma_fold >= ? AND lemma_fold < ? ORDER BY length(sme_lemma), sme_lemma LIMIT 8`, [q, q + "￿"]
  );
  if (rows.length < 8) {
    rows.push(...all(
      `SELECT DISTINCT d.sme_lemma, d.pos, ${TRANS_COLS.split(", ").map((c) => "d." + c).join(", ")}
       FROM trans_search t JOIN dictionary d ON d.id = t.word_id
       WHERE t.lang = ? AND (t.fold LIKE ? OR t.fold LIKE ?) ORDER BY length(d.sme_lemma) LIMIT 8`,
      [settings.lang, `${q}%`, `%, ${q}%`]
    ));
  }
  const seen = new Set();
  return rows.filter((r) => !seen.has(r.sme_lemma + r.pos) && seen.add(r.sme_lemma + r.pos)).slice(0, 8);
}

function loadWord(id) {
  const word = all(`SELECT * FROM dictionary WHERE id = ?`, [id])[0];
  const paradigm = new Map();
  const grades = new Map();
  for (const r of all(
    `SELECT t.tag, p.surface, p.grade FROM paradigms p JOIN tags t ON t.id = p.tag_id WHERE p.word_id = ? ORDER BY p.rowid`, [id]
  )) {
    if (!paradigm.has(r.tag)) paradigm.set(r.tag, []);
    if (!paradigm.get(r.tag).includes(r.surface)) paradigm.get(r.tag).push(r.surface);
    if (r.grade) grades.set(r.tag + "|" + r.surface, r.grade);
  }
  const examples = new Map();
  for (const r of all(`SELECT lang, meaning_nr, sme, translation, source FROM examples WHERE word_id = ? ORDER BY rowid`, [id])) {
    const key = r.lang + r.meaning_nr;
    if (!examples.has(key)) examples.set(key, []);
    examples.get(key).push(r);
  }
  const meanings = all(`SELECT * FROM meanings WHERE word_id = ? ORDER BY rowid`, [id])
    .map((m) => ({ ...m, examples: examples.get(m.lang + m.nr) || [] }));
  return { word, paradigm, grades, meanings };
}

// --- Näkymät ---

function showOnly(view) {
  $("welcome").hidden = view !== "welcome";
  $("loading").hidden = view !== "loading";
  for (const id of ["results", "word", "tabs"]) $(id).hidden = view !== "word";
  for (const t of ["table", "meanings", "raw"]) $("panel-" + t).hidden = view !== "word" || state.tab !== t;
}

function search(query, index = 0, pushHistory = true) {
  query = query.trim();
  if (!query || !db) return;
  hideSuggestions();
  $("search").value = query;
  state.query = query;
  state.results = queryDatabase(query);
  state.showPrefix = false;
  state.index = index;

  const hash = `#/sana/${encodeURIComponent(query)}${index ? "/" + index : ""}`;
  if (location.hash !== hash) history.pushState(null, "", hash);

  if (!state.results.length) {
    showOnly("word");
    $("results").hidden = true;
    $("tabs").hidden = true;
    for (const t of ["table", "meanings", "raw"]) $("panel-" + t).hidden = true;
    $("lemma").textContent = t("noHits", query);
    $("pos-badge").hidden = true;
    $("fav-btn").hidden = true;
    $("speak-btn").hidden = true;
    $("gt-link").hidden = true;
    $("satni-link").hidden = true;
    $("ai-link").hidden = true;
    $("translation").textContent = t("noHitsHint");
    $("more-meanings").textContent = "";
    $("gradation").innerHTML = "";
    $("word-info").textContent = "";
    return;
  }
  renderResults();
  selectResult(Math.min(index, state.results.length - 1), pushHistory);
}

// Pelkät "alkaa hakusanalla" -osumat (rank 7, esim. beana -> beanabálvalus) piilotetaan napin taakse,
// jos varsinaisia osumia on (perusmuoto, käännös, taivutusmuoto). Ilman niitä näytetään kaikki.
const PREFIX_RANK = 7;

function renderResults() {
  const box = $("results");
  box.innerHTML = "";
  const strong = state.results.filter((r) => r.rank < PREFIX_RANK).length;
  const prefixOnly = state.results.length - strong;
  const collapsed = strong > 0 && prefixOnly > 0 && !state.showPrefix && state.index < strong;
  state.results.slice(0, collapsed ? strong : state.results.length).forEach((r, i) => {
    const b = document.createElement("button");
    const trans = translationOf(r, 2);
    const pos = r.subtype ? `${r.pos} ${r.subtype}` : r.pos;
    b.innerHTML = `${esc(r.sme_lemma)} <span class="trans">(${esc(pos)})${trans ? " – " + esc(trans) : ""}</span>`;
    b.dataset.i = i;
    b.onclick = () => selectResult(i);
    box.appendChild(b);
  });
  if (strong > 0 && prefixOnly > 0) {
    const more = document.createElement("button");
    more.className = "more-results";
    more.textContent = collapsed ? t("morePrefix", prefixOnly, state.query) : t("fewerPrefix");
    more.onclick = () => {
      state.showPrefix = collapsed;
      renderResults();
      [...box.children].forEach((b) => b.classList.toggle("selected", Number(b.dataset.i) === state.index));
    };
    box.appendChild(more);
  }
}

function selectResult(i, pushHistory = true) {
  state.index = i;
  const r = state.results[i];
  if (i >= state.results.filter((x) => x.rank < PREFIX_RANK).length && !state.showPrefix) {
    state.showPrefix = true;  // osoitteessa (#/sana/beana/12) valittu alkuosuma näkyviin
    state.index = i;
    renderResults();
  }
  [...$("results").children].forEach((b) => b.classList.toggle("selected", b.dataset.i !== undefined && Number(b.dataset.i) === i));
  const hash = `#/sana/${encodeURIComponent(state.query)}${i ? "/" + i : ""}`;
  if (location.hash !== hash) history.replaceState(null, "", hash);

  const data = loadWord(r.id);
  state.word = data.word;
  state.paradigm = data.paradigm;
  state.grades = data.grades;
  showOnly("word");

  const w = data.word;
  $("lemma").textContent = w.sme_lemma;
  $("pos-badge").hidden = false;
  $("pos-badge").textContent = wordClassLabel(w.pos, w.subtype);
  $("fav-btn").hidden = false;
  $("speak-btn").hidden = false;
  $("gt-link").hidden = false;
  $("gt-link").href = GIELLATEKNO_URL.replace("{word}", encodeURIComponent(w.sme_lemma))
    .replace("{pos}", GIELLATEKNO_POS[w.pos.toUpperCase()] || "Any");
  $("satni-link").hidden = false;
  $("satni-link").href = SATNI_URL.replace("{word}", encodeURIComponent(w.sme_lemma));
  // Kysymykseen sanakirjan käännökset pääkielillä (esim. vain norjaksi: politiijameašttir = politimester)
  const known = Object.keys(LANGUAGES).filter((l) => LANGUAGES[l].main && w[LANGUAGES[l].col])
    .map((l) => `${langName(l)}: ${splitList(w[LANGUAGES[l].col]).slice(0, 3).join(", ")}`);
  $("ai-link").hidden = false;
  $("ai-link").href = AI_URL.replace("{prompt}",
    encodeURIComponent(t("askAi", w.sme_lemma, wordClassLabel(w.pos, w.subtype).toLowerCase(), known)));
  updateFavButton();

  // Ensimmäinen merkitys käyttörajoituksineen (esim. hyppiä – paksussa lumessa, porosta), valitulla
  // kielellä tai sen puuttuessa ensimmäisellä muulla kielellä
  // vain valitulla kielellä; jos sitä ei ole, "(ei suomennosta)" ja linkki muihin kieliin
  const groups = meaningsByLanguage(data.meanings);
  const ownGroup = (groups.find(([lang]) => lang === settings.lang) || [settings.lang, []])[1];
  const first = ownGroup[0];
  let trans = first ? splitList(first.translations || first.explanations).slice(0, 4).join(", ") : translationOf(w, 3);
  state.transWords = first ? splitList(first.translations).slice(0, 4) : splitList(w[LANGUAGES[settings.lang].col]).slice(0, 3);
  if (first && first.restrictions) trans += ` (${first.restrictions})`;
  $("translation").textContent = trans || t("noTranslationIn")[settings.lang];
  renderExtraTranslations(w, groups);
  $("more-meanings").textContent = ownGroup.length > 1 ? t("moreMeanings", ownGroup.length - 1) :
    groups.some(([lang]) => lang !== settings.lang) ? t("otherLangs") : "";

  renderGradation();
  renderInfo(w);
  renderTable();
  renderMeanings(data.meanings);
  renderRaw();
  if (pushHistory) addHistory(w.sme_lemma);
}

// Muut kielet -asetuksessa valittujen kielten käännökset pääkäännöksen alle (Englanniksi: house)
function renderExtraTranslations(w, groups) {
  const lines = settings.extraLangs.filter((l) => LANGUAGES[l]).map((lang) => {
    const own = (groups.find(([l]) => l === lang) || [lang, []])[1][0];
    const text = own ? splitList(own.translations || own.explanations).slice(0, 4).join(", ") : translationOf(w, 3, lang);
    return text && `<span class="muted">${esc(t("langIn")[lang])}:</span> ${esc(text)}`;
  }).filter(Boolean);
  $("extra-translations").hidden = !lines.length;
  $("extra-translations").innerHTML = lines.join("<br>");
}

function renderInfo(w) {
  const info = [];
  const q = fold(state.query);
  const matches = [];
  for (const [tag, forms] of state.paradigm) {
    for (const f of forms) {
      if (fold(f) === q) {
        const g = state.grades.get(tag + "|" + f);
        matches.push(tag + (g ? ` (${g})` : ""));
      }
    }
  }
  let formTrans = "";
  if (matches.length && q !== fold(w.sme_lemma)) {
    info.push(t("searchedForm", state.query, [...new Set(matches)].join(", ")));
    if (FORM_PHRASES[settings.lang]) formTrans = translationOfForm(w, matches.map((m) => m.split(" ")[0]));
  }
  // Haetun muodon käännös omalle rivilleen käännöksen alle (viesus ≈ talossa / talosta, i huset / fra huset)
  $("form-translation").hidden = !formTrans;
  $("form-translation").innerHTML = formTrans ? t("formIn", esc(state.query), esc(formTrans), settings.lang) : "";
  if (w.notes) info.push(w.notes);
  $("word-info").textContent = info.join("  ·  ");
}

// --- Käännöksen taivutus: haetun saamen muodon vastine suomeksi tai norjaksi ---
// Muodot taulukoissa fin_forms (GiellaLT lang-fin, ks. fin_forms.py) ja nob_forms (Norsk ordbank, nob_forms.py).

const NOB_PRONOUNS = { Sg1: "jeg", Sg2: "du", Sg3: "han/hun", Du1: "vi to", Du2: "dere to", Du3: "de to",
                       Pl1: "vi", Pl2: "dere", Pl3: "de" };
// Saamen duaali on suomeksi monikko (moai dagaime = me (kaksi) teemme)
const FIN_PERSON = { Sg1: "Sg1", Sg2: "Sg2", Sg3: "Sg3", Du1: "Pl1", Du2: "Pl2", Du3: "Pl3", Pl1: "Pl1", Pl2: "Pl2", Pl3: "Pl3" };

// "Sg+Indef=hus;Sg+Def=huset;..." -> {"Sg+Indef": "hus", ...}; vaihtoehdoista (husene/husa) ensimmäinen
function translationForms(lang, word, pos) {
  try {
    const row = all(`SELECT forms FROM ${lang}_forms WHERE word = ? AND pos = ?`, [word, pos])[0];
    return row && Object.fromEntries(row.forms.split(";").map((c) => c.split("=")).map(([k, v]) => [k, v.split("/")[0]]));
  } catch (e) {
    return null;  // vanha tietokanta ilman taulua
  }
}

// Saamen muodon tagi (Sg+Loc, Ind+Prs+Sg1 ...) -> norjankielinen ilmaus, esim. "i huset / fra huset".
// Saamessa ei ole määräistä artikkelia: prepositioiden kanssa käytetään määräistä muotoa.
function nobPhrase(tag, pos, f) {
  const parts = tag.split("+");
  if (pos === "V") {
    const person = parts.find((p) => NOB_PRONOUNS[p]);
    if (tag === "Inf") return f.Inf && `å ${f.Inf}`;
    if (tag === "PrfPrc") return f.PrfPrc && `har ${f.PrfPrc}`;
    // Kieltoverbin kanssa käytettävä muoto (ii daga = gjør ikke)
    if (tag === "Ind+Prs+ConNeg") return f.Prs && `(ikke) ${f.Prs}`;
    if (tag === "Ind+Prt+ConNeg") return f.Prt && `(ikke) ${f.Prt}`;
    if (tag === "Imprt+ConNeg") return f.Imp && `ikke ${f.Imp}!`;
    if (!person) return null;
    const who = NOB_PRONOUNS[person];
    if (parts[0] === "Ind") return parts[1] === "Prs" ? f.Prs && `${who} ${f.Prs}` : f.Prt && `${who} ${f.Prt}`;
    if (parts[0] === "Cond") return f.Inf && `${who} ville ${f.Inf}`;
    if (parts[0] === "Pot") return f.Prs && `${who} ${f.Prs} kanskje`;
    if (parts[0] === "Imprt") return ["Sg2", "Du2", "Pl2"].includes(person) ? f.Imp && `${f.Imp}!` : f.Inf && `la ${person === "Sg1" ? "meg" : person.endsWith("1") ? "oss" : "dem"} ${f.Inf}`;
    return null;
  }
  if (pos === "A") {
    if (parts[0] === "Comp") return f.Comp;
    if (parts[0] === "Superl") return f.Superl;
    return parts[0] === "Pl" ? f.Pl : f.Pos;
  }
  const pl = parts[0] === "Pl";
  const indef = f[pl ? "Pl+Indef" : "Sg+Indef"], def = f[pl ? "Pl+Def" : "Sg+Def"];
  switch (parts[parts.length - 1]) {
    case "Nom": case "Acc": return indef;
    case "Gen": return def && def + (/[sxz]$/.test(def) ? "'" : "s");
    case "Ill": return def && `til ${def}`;
    case "Loc": return def && `i ${def} / fra ${def}`;
    case "Com": return def && `med ${def}`;
    case "Ess": return f["Sg+Indef"] && `som ${f["Sg+Indef"]}`;
  }
  return null;
}

// Saamen muodon tagi -> suomenkielinen muoto. Saamen lokatiivi on suomeksi sisä- tai ulkopaikallissija
// (viesus = talossa / talosta), illatiivi illatiivi tai allatiivi (taloon / talolle), komitatiivi "kanssa".
function finPhrase(tag, pos, f) {
  const parts = tag.split("+");
  const join = (...forms) => forms.filter(Boolean).join(" / ") || null;
  if (pos === "V") {
    const person = FIN_PERSON[parts[parts.length - 1]];
    if (tag === "Inf") return f.Inf;
    if (tag === "PrfPrc") return f.PrfPrc;
    if (tag === "Ind+Prs+ConNeg") return f["Prs+ConNeg"] && `(ei) ${f["Prs+ConNeg"]}`;
    if (tag === "Ind+Prt+ConNeg") return f.PrfPrc && `(ei) ${f.PrfPrc}`;
    if (tag === "Cond+Prs+ConNeg") return f["Cond+ConNeg"] && `(ei) ${f["Cond+ConNeg"]}`;
    if (tag === "Pot+Prs+ConNeg") return f["Pot+ConNeg"] && `(ei) ${f["Pot+ConNeg"]}`;
    if (tag === "Imprt+ConNeg") return f["Prs+ConNeg"] && `(älä) ${f["Prs+ConNeg"]}`;
    if (!person) return null;
    if (parts[0] === "Ind") return f[`${parts[1]}+${person}`];
    if (parts[0] === "Cond" || parts[0] === "Pot" || parts[0] === "Imprt") return f[`${parts[0]}+${person}`];
    return null;
  }
  if (pos === "A") {
    if (parts[0] === "Comp") return f.Comp;
    if (parts[0] === "Superl") return f.Superl;
    if (tag === "Attr") return f["Sg+Nom"];
  }
  const n = parts[0] === "Pl" ? "Pl" : "Sg";
  switch (parts[parts.length - 1]) {
    case "Nom": return f[`${n}+Nom`];
    case "Acc": return join(f[n === "Sg" ? "Sg+Gen" : "Pl+Nom"], f[`${n}+Par`]);  // talon / taloa (objekti)
    case "Gen": return f[`${n}+Gen`];
    case "Ill": return join(f[`${n}+Ill`], f[`${n}+All`]);
    case "Loc": return join(f[`${n}+Ine`], f[`${n}+Ela`]);
    case "Com": return f[`${n}+Gen`] && `${f[`${n}+Gen`]} kanssa`;
    case "Ess": return f["Sg+Ess"];
  }
  return null;
}

const FORM_PHRASES = { fin: finPhrase, nob: nobPhrase };

// Haetun muodon tagit -> "jeg lager, jeg gjør" (yksi ilmaus käännöstä kohden, tagien vaihtoehdot /-merkillä)
function translationOfForm(w, tags) {
  const pos = ["N", "V", "A"].find((p) => p === w.pos.toUpperCase());
  if (!pos) return "";
  const out = [];
  for (const word of state.transWords || []) {
    const forms = translationForms(settings.lang, word.replace(/\(.*?\)/g, "").trim(), pos);
    if (!forms) continue;
    const phrases = [...new Set(tags.map((tag) => FORM_PHRASES[settings.lang](tag, pos, forms)).filter(Boolean))];
    if (phrases.length) out.push(phrases.join(" / "));
  }
  return [...new Set(out)].join(", ");
}

function renderGradation() {
  const w = state.word;
  const el = $("gradation");
  if (UNINFLECTED_POS.includes(w.pos.toUpperCase()) || !state.paradigm.size) { el.innerHTML = ""; return; }
  if (!w.gradation) { el.innerHTML = `<span class="label">${esc(t("gradation"))}</span><span class="muted"><i>${esc(t("noGradation"))}</i></span>`; return; }

  // Esimerkkimuodot: haettu muoto tai perusmuoto ja tavallisin vastakkaisen asteen muoto
  const preferred = ["Inf", "Sg+Nom", "Nom", "Ind+Prs+Sg1", "Sg+Acc", "Acc", "Sg+Gen", "Pl+Nom"];
  const tags = [...preferred, ...[...state.paradigm.keys()].filter((t) => !preferred.includes(t))];
  const examples = {};
  const q = fold(state.query);
  for (const [key, g] of state.grades) {
    const surface = key.split("|")[1];
    if (fold(surface) === q && !examples[g]) examples[g] = surface;
  }
  for (const tag of tags) {
    for (const f of state.paradigm.get(tag) || []) {
      const g = state.grades.get(tag + "|" + f);
      if (g && !examples[g]) examples[g] = f;
    }
  }
  // "hkk (III) · hk (II) · g (I)" -> laatikot; vahva vihreä, heikko oranssi
  let strongDone = false;
  const row = (w.gradation_row || "").split(" · ").map((part) => {
    const [value, q2] = part.replace(/\)$/, "").split(" (");
    let cls = "other";
    if (value === w.gd_cluster && !strongDone) { cls = "gd"; strongDone = true; }
    else if (value === w.hd_cluster) cls = "hd";
    return `<span class="pill ${cls}">${esc(value)} ${esc(q2)}</span>`;
  }).join("");
  el.innerHTML = `
    <span class="label">${esc(t("gradation"))}</span>
    <span class="pill gd">GD ${esc(examples.GD || "-")}</span><span class="arrow">→</span>
    <span class="pill hd">HD ${esc(examples.HD || "-")}</span>
    <span class="clusters"><span class="gd">${esc(w.gd_cluster)}</span> <span class="arrow">→</span> <span class="hd">${esc(w.hd_cluster)}</span></span>
    <span class="oahpa">oahpa: ${esc(w.gradation_group)}</span> ${row}`;
}

// --- Taivutustaulukko ---

function renderTable() {
  const w = state.word;
  const pos = w.pos.toUpperCase();
  const p = state.paradigm;
  const showGrade = settings.showGrade;
  const legend = showGrade && state.grades.size;

  const pairs = (...tags) => {
    const out = [], seen = new Set();
    for (const tag of tags) for (const v of p.get(tag) || []) if (!seen.has(v)) { seen.add(v); out.push([tag, v]); }
    return out;
  };
  // Muotosolu: pronomini harmaana, muodot asteen värillä; napautus ääntää muodon
  const cell = (items, prefix = "") => {
    if (!items.length) return `<td class="pron">-</td>`;
    const forms = items.map(([tag, v]) => {
      const g = showGrade ? state.grades.get(tag + "|" + v) : null;
      const cls = g === "GD" ? "gd" : g === "HD" ? "hd" : "";
      const speak = (prefix ? prefix + " " : "") + v;
      return `<span class="form ${cls}" data-speak="${esc(speak)}" title="${esc(t("listenTo", speak))}">${esc(v)}</span>`;
    }).join('<span class="sep"> / </span>');
    return `<td>${prefix ? `<span class="pron">${esc(prefix)}</span> ` : ""}${forms}</td>`;
  };
  const label = (t) => `<td class="label">${esc(t)}</td>`;
  const section = (...cells) => `<tr class="section">${cells.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`;

  let html = "";
  if (!p.size && !UNINFLECTED_POS.includes(pos)) {
    html = `<p class="muted">${esc(t("noForms"))}</p>`;
  } else if (pos === "V") {
    let rows = section(t("indicative"), t("present"), "", t("preterite"), "");
    for (const pp of PERSONS) {
      const pr = PRONOUNS[pp];
      rows += `<tr>${label(pp)}${cell(pairs(`Ind+Prs+${pp}`), pr)}${cell(pairs("Ind+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}` +
              `${cell(pairs(`Ind+Prt+${pp}`), pr)}${cell(pairs("Ind+Prt+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}</tr>`;
    }
    rows += section("", t("conditional"), "", t("potential"), "");
    for (const pp of PERSONS) {
      const pr = PRONOUNS[pp];
      rows += `<tr>${label(pp)}${cell(pairs(`Cond+Prs+${pp}`), pr)}${cell(pairs("Cond+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}` +
              `${cell(pairs(`Pot+Prs+${pp}`), pr)}${cell(pairs("Pot+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}</tr>`;
    }
    rows += section("", t("imperative"), "", "", "");
    for (const pp of PERSONS) {
      rows += `<tr>${label(pp)}${cell(pairs(`Imprt+${pp}`))}${cell(pairs("Imprt+ConNeg"), NEG_AUX_IMPRT[pp])}<td></td><td></td></tr>`;
    }
    let nf = section(t("nonFinite"), "");
    VERB_NONFINITE_TAGS.forEach((tag, i) => { nf += `<tr>${label(t("nonFiniteRows")[i])}${cell(pairs(tag))}</tr>`; });
    html = table(["", t("affirmative"), t("negative"), t("affirmative"), t("negative")], rows) + table(null, nf);
  } else if (UNINFLECTED_POS.includes(pos)) {
    html = table(["", t("baseForm")], `<tr>${label(t("uninflected"))}${cell([["", w.sme_lemma]])}</tr>`);
  } else if (!p.has("Sg+Nom") && !p.has("Pl+Nom") && p.has("Nom")) {
    // Persoona- ja refleksiivipronominit: luku ja persoona kuuluvat jo perusmuotoon
    let rows = "";
    for (const [name, cases] of [...CASE_ROWS, ["Ess", ["Ess"]]]) rows += `<tr>${label(name)}${cell(pairs(...cases))}</tr>`;
    html = table([t("caseCol"), t("formCol")], rows);
  } else {
    // ol. = ovttaidlohku (yksikkö), ml. = máŋggaidlohku (monikko)
    let rows = p.has("Attr") ? `<tr>${label("Attr")}${cell(pairs("Attr"))}<td></td></tr>` : "";
    for (const [name, cases] of CASE_ROWS) {
      rows += `<tr>${label(name)}${cell(pairs(...cases.map((c) => "Sg+" + c)))}${cell(pairs(...cases.map((c) => "Pl+" + c)))}</tr>`;
    }
    rows += `<tr>${label("Ess")}${cell(pairs("Ess"))}<td></td></tr>`;
    if (pos === "A" && [...p.keys()].some((t) => t.startsWith("Comp") || t.startsWith("Superl"))) {
      rows += section(t("comparison"), t("predicative"), t("attributive"));
      rows += `<tr>${label(t("comparative"))}${cell(pairs("Comp+Sg+Nom"))}${cell(pairs("Comp+Attr"))}</tr>`;
      rows += `<tr>${label(t("superlative"))}${cell(pairs("Superl+Sg+Nom"))}${cell(pairs("Superl+Attr"))}</tr>`;
    }
    html = table([t("caseCol"), t("singular"), t("plural")], rows);
  }

  $("panel-table").innerHTML =
    (legend ? `<p class="legend">${t("gradeLegend")}</p>` : "") +
    html + `<p class="hint">${esc(t("tapHint"))}</p>`;
}

function table(headers, rows) {
  const head = headers ? `<thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` : "";
  return `<div class="table-wrap"><table class="paradigm">${head}<tbody>${rows}</tbody></table></div>`;
}

function meaningHtml(m, numbered) {
  const tags = splitList(m.labels).map((l) => `<span class="tag">${esc(l)}</span>`).join("") +
    (m.geo || "").split(",").filter(Boolean).map((g) => `<span class="tag">${esc(t("usedIn", t("geo")[g] || g, g))}</span>`).join("");
  let html = `<div class="meaning"><div class="head">${numbered ? `<span class="nr">${m.nr}.</span>` : ""}` +
    `${esc(m.translations)}${m.explanations ? ` <span class="expl">(${esc(m.explanations)})</span>` : ""}` +
    `${m.restrictions ? ` <span class="restr">– ${esc(m.restrictions)}</span>` : ""}${tags}</div>`;
  for (const ex of m.examples) {
    html += `<div class="example"><span class="sme">${esc(ex.sme)}</span>` +
      (ex.translation ? `<span class="fin">${esc(ex.translation)}</span>` : `<span class="missing">${esc(t("noExampleTranslation"))}</span>`) +
      (ex.source ? `<span class="muted small">(${esc(ex.source)})</span>` : "") + `</div>`;
  }
  return html + `</div>`;
}

function renderMeanings(meanings) {
  const w = state.word;
  let html = `<h2 style="margin-top:0">${esc(w.sme_lemma)} <span class="muted small"><i>${esc(wordClassLabel(w.pos))}</i></span></h2>`;
  if (w.notes) html += `<p class="muted small"><i>${esc(w.notes)}</i></p>`;
  // Kielittäin, valittu kieli ensin; otsikko, jos kieliä on useampi tai ainoa kieli ei ole valittu kieli
  const groups = meaningsByLanguage(meanings);
  for (const [lang, ms] of groups) {
    if (groups.length > 1 || lang !== settings.lang) html += `<h3 class="lang-head">${esc(t("langIn")[lang])}</h3>`;
    html += ms.map((m) => meaningHtml(m, ms.length > 1)).join("");
  }
  if (!meanings.length) html += `<p class="muted">${esc(t("noMeanings"))}</p>`;
  $("panel-meanings").innerHTML = html;
  const examples = meanings.reduce((n, m) => n + m.examples.length, 0);
  $("meanings-tab").textContent = t("tabMeanings", meanings.length, examples);
}

function renderRaw() {
  let html = "";
  for (const [tag, forms] of state.paradigm) {
    html += `<div><span class="tag">${esc(tag)}</span>` + forms.map((f) => {
      const g = settings.showGrade ? state.grades.get(tag + "|" + f) : null;
      return `<span class="${g === "GD" ? "gd" : g === "HD" ? "hd" : ""}">${esc(f)}</span>${g ? ` <span class="muted">${g}</span>` : ""}`;
    }).join(", ") + `</div>`;
  }
  $("panel-raw").innerHTML = `<div class="raw">${html || esc(state.word.sme_lemma)}</div>`;
}

function setTab(tab) {
  state.tab = tab;
  for (const b of $("tabs").children) b.classList.toggle("active", b.dataset.tab === tab);
  for (const t of ["table", "meanings", "raw"]) $("panel-" + t).hidden = t !== tab;
}

// --- Ääntäminen: Divvunin puhesynteesi, välimuisti selaimen Cache Storagessa ---

const memoryCache = new Map();
const IS_DESKTOP = location.protocol === "satni:";
// Android-sovellus (android/) näyttää tiedostot APK:sta tällä osoitteella
const IS_ANDROID = location.hostname === "appassets.androidplatform.net";
async function speak(text, button, voiceName = settings.voice) {
  const voice = VOICES[voiceName] || "biret";
  const key = `tts-cache/${voice}/${encodeURIComponent(text)}`;
  if (button) button.disabled = true;
  if (button === $("speak-btn")) button.lastChild.textContent = t("fetching");
  try {
    let blob = memoryCache.get(key);
    // Selaimen välimuisti vain verkkosivulla: Cache Storage hyväksyy vain http(s)-osoitteet.
    // Työpöytäsovelluksessa Python tallentaa äänet levylle (~/.cache/satni-fst/tts).
    const cache = !IS_DESKTOP && "caches" in window ? await caches.open("satni-tts") : null;
    if (!blob && cache) {
      const hit = await cache.match(key);
      if (hit) blob = await hit.blob();
    }
    if (!blob) {
      let res;
      try {
        res = IS_DESKTOP
          ? await fetch(`tts/${voice}?text=${encodeURIComponent(text)}`)
          : await fetch(TTS_URL + voice, {
              method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
            });
      } catch (e) {
        throw new Error(t("ttsOffline"));
      }
      if (!res.ok) throw new Error(IS_DESKTOP ? t("ttsOffline") : t("ttsStatus", res.status));
      blob = await res.blob();
      if (cache) cache.put(key, new Response(blob, { headers: { "Content-Type": "audio/wav" } })).catch(() => {});
    }
    memoryCache.set(key, blob);
    const audio = new Audio(URL.createObjectURL(blob));
    await audio.play();
  } catch (e) {
    toast(t("ttsFailed", e.message));
  } finally {
    if (button) button.disabled = false;
    if (button === $("speak-btn")) button.lastChild.textContent = t("listen");
  }
}

// --- Historia ja suosikit ---

function addHistory(lemma) {
  settings.history = [lemma, ...settings.history.filter((h) => h !== lemma)].slice(0, 30);
  saveSettings();
  renderSidebar();
}
function toggleFavourite() {
  const lemma = state.word.sme_lemma;
  const favs = settings.favourites;
  settings.favourites = favs.includes(lemma) ? favs.filter((f) => f !== lemma) : [lemma, ...favs];
  saveSettings();
  updateFavButton();
  renderSidebar();
}
function updateFavButton() {
  const on = state.word && settings.favourites.includes(state.word.sme_lemma);
  $("fav-btn").textContent = on ? "★" : "☆";
  $("fav-btn").classList.toggle("on", on);
  $("fav-btn").title = on ? t("removeFavourite") : t("addFavourite");
  $("fav-btn").setAttribute("aria-label", $("fav-btn").title);
}
function renderSidebar() {
  const fill = (id, words, empty) => {
    $(id).innerHTML = words.length
      ? words.map((w) => `<li><a href="#/sana/${encodeURIComponent(w)}">${esc(w)}</a></li>`).join("")
      : `<li class="empty">${empty}</li>`;
  };
  fill("favourites", settings.favourites, esc(t("noFavourites")));
  fill("history", settings.history, esc(t("noHistory")));
}

// --- Hakuehdotukset ---

let suggestTimer = null, suggestions = [], activeSuggestion = -1;
function updateSuggestions() {
  suggestions = suggestWords($("search").value);
  activeSuggestion = -1;
  const list = $("suggestions");
  if (!suggestions.length || (suggestions.length === 1 && fold(suggestions[0].sme_lemma) === fold($("search").value))) {
    hideSuggestions();
    return;
  }
  list.innerHTML = suggestions.map((s, i) =>
    `<li role="option" data-i="${i}"><b>${esc(s.sme_lemma)}</b><span class="pos">${esc(s.pos)}</span>` +
    `<span class="trans">${esc(translationOf(s, 2))}</span></li>`).join("");
  list.hidden = false;
}
function hideSuggestions() { $("suggestions").hidden = true; activeSuggestion = -1; }
function moveSuggestion(delta) {
  const items = $("suggestions").children;
  if ($("suggestions").hidden || !items.length) return false;
  activeSuggestion = (activeSuggestion + delta + items.length) % items.length;
  [...items].forEach((li, i) => li.classList.toggle("active", i === activeSuggestion));
  return true;
}

// --- Teema ---

function applyTheme() {
  const t = settings.theme;
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
}

// --- Osoite (#/sana/dahkat/1) ---

// Muusta sovelluksesta jaettu teksti (Android: Jaa -> Sátni FST; asennettu selainversio:
// share_target, ?text=...). Ensin koko ilmaus (dahkat iežas), sitten sanat järjestyksessä:
// haetaan ensimmäinen, josta löytyy osumia. Välimerkit ja linkit pois. Ennen sanakirjan latautumista
// teksti odottaa (pendingShared).
let pendingShared = null;
function openShared(text) {
  const words = text.replace(/https?:\/\/\S+/g, " ").split(/\s+/)
    .map((w) => w.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "")).filter(Boolean);
  if (!words.length) return;
  if (!db) { pendingShared = text; return; }
  const tries = [words.slice(0, 4).join(" "), ...words.slice(0, 20)];
  search(tries.find((q) => queryDatabase(q).length) || words[0]);
}

function routeFromHash() {
  const m = location.hash.match(/^#\/sana\/([^/]+)(?:\/(\d+))?/);
  if (m) search(decodeURIComponent(m[1]), Number(m[2] || 0));
  else { showOnly("welcome"); $("search").value = ""; }
}

// --- Käynnistys ---

function bindEvents() {
  const input = $("search");
  input.addEventListener("input", () => { clearTimeout(suggestTimer); suggestTimer = setTimeout(updateSuggestions, 120); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && moveSuggestion(1)) e.preventDefault();
    else if (e.key === "ArrowUp" && moveSuggestion(-1)) e.preventDefault();
    else if (e.key === "Escape") hideSuggestions();
    else if (e.key === "Enter") {
      e.preventDefault();
      const s = activeSuggestion >= 0 ? suggestions[activeSuggestion] : null;
      search(s ? s.sme_lemma : input.value);
      input.blur();
    }
  });
  input.addEventListener("blur", () => setTimeout(hideSuggestions, 150));
  $("suggestions").addEventListener("mousedown", (e) => {
    const li = e.target.closest("li");
    if (li) { e.preventDefault(); search(suggestions[li.dataset.i].sme_lemma); input.blur(); }
  });
  $("search-btn").onclick = () => search(input.value);

  $("grade-toggle").checked = settings.showGrade;
  $("grade-toggle").onchange = (e) => {
    settings.showGrade = e.target.checked; saveSettings();
    if (state.word) { renderTable(); renderRaw(); }
  };
  $("voice-list").addEventListener("change", (e) => { settings.voice = e.target.value; saveSettings(); });
  $("voice-list").addEventListener("click", (e) => {
    const b = e.target.closest(".sample-btn");
    if (b) playVoiceSample(b.dataset.voice, b);
  });
  $("drawer-lang").addEventListener("click", (e) => {
    const b = e.target.closest("[data-lang]");
    if (b) setUiLanguage(b.dataset.lang);
  });
  $("extra-langs").onchange = (e) => {
    const lang = e.target.value;
    settings.extraLangs = e.target.checked ? [...settings.extraLangs, lang] : settings.extraLangs.filter((l) => l !== lang);
    saveSettings();
    if (state.results.length) searchAgainKeepingWord();
  };
  $("theme-select").value = settings.theme;
  $("theme-select").onchange = (e) => { settings.theme = e.target.value; saveSettings(); applyTheme(); };

  $("tabs").onclick = (e) => { if (e.target.dataset.tab) setTab(e.target.dataset.tab); };
  $("more-meanings").onclick = (e) => { e.preventDefault(); setTab("meanings"); };
  $("speak-btn").onclick = () => speak(state.word.sme_lemma, $("speak-btn"));
  $("fav-btn").onclick = toggleFavourite;
  $("panel-table").addEventListener("click", (e) => {
    const form = e.target.closest(".form");
    if (!form) return;
    form.classList.add("playing");
    speak(form.dataset.speak).finally(() => form.classList.remove("playing"));
  });
  $("about-btn").onclick = () => $("about").showModal();
  $("welcome-lang").addEventListener("click", (e) => {
    const b = e.target.closest("[data-lang]");
    if (b) setUiLanguage(b.dataset.lang);
  });
  $("sidebar-toggle").onclick = () => document.body.classList.toggle("sidebar-open");
  $("drawer-scrim").onclick = closeDrawer;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  $("sidebar").addEventListener("click", (e) => { if (e.target.closest("a")) document.body.classList.remove("sidebar-open"); });
  $("clear-history").onclick = () => { settings.history = []; saveSettings(); renderSidebar(); };
  window.addEventListener("popstate", routeFromHash);
  window.addEventListener("hashchange", routeFromHash);
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f" && db) { e.preventDefault(); input.focus(); input.select(); }
  });
}

async function main() {
  if (!UI_LANGUAGES[settings.uiLang]) settings.uiLang = "fi";
  // Käännökset käyttöliittymän kielellä. Aiemmin käännöskieleksi valittu muu kieli (englanti, inarin-, luulajan-
  // tai eteläsaame) siirtyy Muut kielet -asetukseen, jolloin sen käännökset näkyvät edelleen sanakortissa.
  settings.extraLangs = (settings.extraLangs || []).filter((l) => LANGUAGES[l] && !LANGUAGES[l].main);
  if (LANGUAGES[settings.lang] && !LANGUAGES[settings.lang].main && !settings.extraLangs.includes(settings.lang)) {
    settings.extraLangs.push(settings.lang);
  }
  settings.lang = UI_LANGUAGES[settings.uiLang].translationLang;
  applyTheme();
  const ex = $("examples");
  for (const w of EXAMPLE_WORDS) {
    const b = document.createElement("button");
    b.textContent = w;
    b.onclick = () => search(w);
    ex.appendChild(b);
  }
  const rnd = document.createElement("button");
  rnd.className = "random";
  rnd.id = "random-btn";
  rnd.onclick = () => {
    const r = all(`SELECT sme_lemma FROM dictionary WHERE pos IN ('N','V','A') AND gradation IS NOT NULL
                   AND ${LANGUAGES[settings.lang].col} != '' AND (subtype IS NULL OR subtype = '') ORDER BY RANDOM() LIMIT 1`)[0];
    if (r) search(r.sme_lemma);
  };
  ex.appendChild(rnd);
  applyStaticTexts();
  bindEvents();
  renderSidebar();
  if (FIRST_RUN) showFirstRun();

  // Service worker vain verkkosivuna (PWA); työpöytä- ja Android-sovellus lukevat tiedostot omasta paketistaan
  if ("serviceWorker" in navigator && location.protocol.startsWith("http") && !IS_ANDROID) {
    navigator.serviceWorker.register("sw.js").catch((e) => console.warn("Service worker:", e));
  }

  pendingShared = new URLSearchParams(location.search).get("text");
  if (pendingShared) history.replaceState(null, "", location.pathname);

  try {
    showOnly("loading");
    db = await loadDatabase();
  } catch (e) {
    $("loading-text").textContent = t("loadFailedLong", e.message);
    return;
  }
  $("search").disabled = false;
  $("search-btn").disabled = false;
  if (pendingShared) openShared(pendingShared);
  else routeFromHash();
  if (!location.hash) $("search").focus();
}

main();
