"use strict";
/* Sátni FST – web-versio. Sama tietokanta kuin työpöytäversiossa (export_web_data.py), luetaan sql.js:llä. */

const DATA_URL = "data/satni-web.db.gz";
const TTS_URL = "https://api-giellalt.uit.no/tts/se/";
const VOICES = { "Biret": "biret", "Máhtte": "mahtte", "Sunná": "sunna" };
const GIELLATEKNO_URL = "https://gtweb.uit.no/cgi-bin/smi/smi.cgi?text={word}&pos={pos}&lang=sme&mode=full&action=paradigm";
const GIELLATEKNO_POS = { N: "N", V: "V", A: "A", ADV: "Adv", NUM: "Num", PRON: "Pron" };

const POS_NAMES = {
  V: "Verbi", N: "Substantiivi", A: "Adjektiivi", ADV: "Adverbi", PRON: "Pronomini", NUM: "Numeraali",
  CC: "Rinnastuskonjunktio", CS: "Alistuskonjunktio", PCLE: "Partikkeli", INTERJ: "Interjektio",
  PO: "Postpositio", PR: "Prepositio", CMP: "Yhdyssanan alkuosa", MWE: "Monisanainen ilmaus",
};
const SUBTYPE_NAMES = {
  Prop: "Erisnimi", NomAg: "Tekijännimi", Pers: "Persoonapronomini", Dem: "Demonstratiivipronomini",
  Indef: "Indefiniittipronomini", Interr: "Interrogatiivipronomini", Refl: "Refleksiivipronomini",
  Rel: "Relatiivipronomini", Ord: "Järjestysluku", Coll: "Kollektiivi",
};
const GEO_NAMES = { N: "Norjassa", S: "Suomessa", R: "Ruotsissa" };
// Käännöskielet (GiellaLT:n dict-sme-*-sanakirjat) ja niiden sarakkeet tietokannassa
const LANGUAGES = {
  fin: { name: "suomi", in: "Suomeksi", col: "finnish_translation" },
  nob: { name: "norja", in: "Norjaksi", col: "nob_translation" },
  eng: { name: "englanti", in: "Englanniksi", col: "eng_translation" },
  smn: { name: "inarinsaame", in: "Inarinsaameksi", col: "smn_translation" },
  smj: { name: "luulajansaame", in: "Luulajansaameksi", col: "smj_translation" },
  sma: { name: "eteläsaame", in: "Eteläsaameksi", col: "sma_translation" },
};
const TRANS_COLS = Object.values(LANGUAGES).map((l) => l.col).join(", ");

const PERSONS = ["Sg1", "Sg2", "Sg3", "Du1", "Du2", "Du3", "Pl1", "Pl2", "Pl3"];
const PRONOUNS = { Sg1: "mun", Sg2: "don", Sg3: "son", Du1: "moai", Du2: "doai", Du3: "soai", Pl1: "mii", Pl2: "dii", Pl3: "sii" };
// Kieltoverbin (ii) indikatiivi- ja imperatiivimuodot
const NEG_AUX = { Sg1: "in", Sg2: "it", Sg3: "ii", Du1: "ean", Du2: "eahppi", Du3: "eaba", Pl1: "eat", Pl2: "ehpet", Pl3: "eai" };
const NEG_AUX_IMPRT = { Sg1: "allon", Sg2: "ale", Sg3: "allos", Du1: "allu", Du2: "alli", Du3: "alloska", Pl1: "allot", Pl2: "allet", Pl3: "alloset" };
// Saamen koulukieliopin sijataulukko: genetiivi ja akkusatiivi samalla rivillä
const CASE_ROWS = [["Nom", ["Nom"]], ["Gen/Akk", ["Acc", "Gen"]], ["Ill", ["Ill"]], ["Lok", ["Loc"]], ["Kom", ["Com"]]];
const VERB_NONFINITE_ROWS = [
  ["Infinitiivi", "Inf"], ["Perfektipartisiippi", "PrfPrc"], ["Preesenspartisiippi", "PrsPrc"], ["Gerundi", "Ger"],
  ["Verbigenetiivi", "VGen"], ["Verbiabessiivi", "VAbess"], ["Supiini", "Sup"], ["Aktio (Nom)", "Actio+Nom"],
  ["Aktio (Loc)", "Actio+Loc"], ["Aktio (Com)", "Actio+Com"], ["Aktio (Ess)", "Actio+Ess"],
];
const UNINFLECTED_POS = ["ADV", "CC", "CS", "INTERJ", "PCLE", "PO", "PR", "CMP", "MWE"];
const EXAMPLE_WORDS = ["dahkat", "áhčči", "viessu", "mannat", "buorre", "golbma", "juolgi", "oastit"];

const $ = (id) => document.getElementById(id);
let db = null;
const state = { query: "", results: [], index: 0, word: null, paradigm: null, grades: null, tab: "table" };

// --- Asetukset, historia ja suosikit (selaimen localStorage) ---

const DEFAULT_SETTINGS = { theme: "auto", voice: "Biret", lang: "fin", showGrade: true, history: [], favourites: [] };
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

// Valitun kielen käännös; jos sitä ei ole, ensimmäinen muu (kielen nimi suluissa): "talo" tai "(norja) hus"
function translationOf(row, max) {
  const order = [settings.lang, ...Object.keys(LANGUAGES).filter((l) => l !== settings.lang)];
  for (const lang of order) {
    const parts = splitList(row[LANGUAGES[lang].col]);
    if (parts.length) return (lang === settings.lang ? "" : `(${LANGUAGES[lang].name}) `) + parts.slice(0, max).join(", ");
  }
  return "";
}

// Merkitykset kielittäin, valittu kieli ensin
function meaningsByLanguage(meanings) {
  const groups = Object.keys(LANGUAGES).map((lang) => [lang, meanings.filter((m) => m.lang === lang)]).filter(([, ms]) => ms.length);
  return groups.sort(([a], [b]) => (b === settings.lang) - (a === settings.lang));
}

function wordClassLabel(pos, subtype) {
  let label = POS_NAMES[(pos || "").toUpperCase()] || pos;
  if (subtype) label += " · " + (SUBTYPE_NAMES[subtype] || subtype);
  return label;
}

// --- Tietokannan lataus ---

async function loadDatabase() {
  const SQL = await initSqlJs({ locateFile: (f) => "vendor/" + f });
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(`Sanakirjan lataus epäonnistui (${response.status})`);

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
    $("loading-text").textContent = "Puretaan…";
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  $("progress-bar").style.width = "100%";
  return new SQL.Database(bytes);
}

// --- Haku ---

function queryDatabase(query) {
  const q = fold(query.trim());
  const found = new Map();
  const add = (row, rank) => {
    const prev = found.get(row.id);
    if (!prev || rank < prev.rank) found.set(row.id, { ...row, rank });
  };
  const cols = `id, sme_lemma, pos, subtype, ${TRANS_COLS}`;

  // 1 = saamen perusmuoto; 6 = isolla kirjoitettu erisnimi, joka osui vain kirjainkoosta riippumatta
  for (const r of all(`SELECT ${cols} FROM dictionary WHERE lemma_fold = ?`, [q])) {
    const first = r.sme_lemma.charAt(0);
    add(r, r.sme_lemma === query.trim() || first === first.toLowerCase() ? 1 : 6);
  }
  // 2 = ainoa käännös, 3 = ensimmäinen käännös, 4 = jokin muu; muun kuin valitun kielen osuma hieman alempana
  for (const r of all(
    `SELECT d.${cols.split(", ").join(", d.")}, t.fold, t.lang FROM trans_search t JOIN dictionary d ON d.id = t.word_id
     WHERE t.fold = ? OR t.fold LIKE ? OR t.fold LIKE ? OR t.fold LIKE ?`,
    [q, `${q},%`, `%, ${q},%`, `%, ${q}`]
  )) {
    add(r, (r.fold === q ? 2 : r.fold.startsWith(`${q},`) ? 3 : 4) + (r.lang === settings.lang ? 0 : 0.5));
  }
  // 5 = taivutusmuoto (manan -> mannat)
  const forms = [q, capitalize(q), nordic(q), capitalize(nordic(q))];
  for (const r of all(
    `SELECT DISTINCT d.${cols.split(", ").join(", d.")}
     FROM paradigms p JOIN dictionary d ON d.id = p.word_id WHERE p.surface IN (?, ?, ?, ?)`, forms
  )) add(r, 5);
  // 7 = perusmuoto alkaa hakusanalla
  for (const r of all(`SELECT ${cols} FROM dictionary WHERE lemma_fold >= ? AND lemma_fold < ? LIMIT 60`, [q, q + "￿"])) add(r, 7);

  return [...found.values()]
    .sort((a, b) => a.rank - b.rank || (b.pos === "V") - (a.pos === "V") || a.sme_lemma.localeCompare(b.sme_lemma, "se"))
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

  const hash = `#/sana/${encodeURIComponent(query)}${index ? "/" + index : ""}`;
  if (location.hash !== hash) history.pushState(null, "", hash);

  if (!state.results.length) {
    showOnly("word");
    $("results").hidden = true;
    $("tabs").hidden = true;
    for (const t of ["table", "meanings", "raw"]) $("panel-" + t).hidden = true;
    $("lemma").textContent = `Ei osumia haulle ”${query}”`;
    $("pos-badge").hidden = true;
    $("fav-btn").hidden = true;
    $("speak-btn").hidden = true;
    $("gt-link").hidden = true;
    $("translation").textContent = "Kokeile toista kirjoitusasua, perusmuotoa tai käännöstä.";
    $("more-meanings").textContent = "";
    $("gradation").innerHTML = "";
    $("word-info").textContent = "";
    return;
  }
  renderResults();
  selectResult(Math.min(index, state.results.length - 1), pushHistory);
}

function renderResults() {
  const box = $("results");
  box.innerHTML = "";
  state.results.forEach((r, i) => {
    const b = document.createElement("button");
    const trans = translationOf(r, 2);
    const pos = r.subtype ? `${r.pos} ${r.subtype}` : r.pos;
    b.innerHTML = `${esc(r.sme_lemma)} <span class="trans">(${esc(pos)})${trans ? " – " + esc(trans) : ""}</span>`;
    b.onclick = () => selectResult(i);
    box.appendChild(b);
  });
}

function selectResult(i, pushHistory = true) {
  state.index = i;
  const r = state.results[i];
  [...$("results").children].forEach((b, k) => b.classList.toggle("selected", k === i));
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
  updateFavButton();

  // Ensimmäinen merkitys käyttörajoituksineen (esim. hyppiä – paksussa lumessa, porosta), valitulla
  // kielellä tai sen puuttuessa ensimmäisellä muulla kielellä
  const groups = meaningsByLanguage(data.meanings);
  const [firstLang, firstGroup] = groups[0] || [settings.lang, []];
  const first = firstGroup[0];
  let trans = first ? splitList(first.translations || first.explanations).slice(0, 4).join(", ") : translationOf(w, 3);
  if (first && first.restrictions) trans += ` (${first.restrictions})`;
  if (first && trans && firstLang !== settings.lang) trans = `(${LANGUAGES[firstLang].name}) ${trans}`;
  $("translation").textContent = trans || "(ei käännöstä)";
  $("more-meanings").textContent = firstGroup.length > 1 ? `+${firstGroup.length - 1} merkitystä` :
    groups.length > 1 ? "muut kielet" : "";

  renderGradation();
  renderInfo(w);
  renderTable();
  renderMeanings(data.meanings);
  renderRaw();
  if (pushHistory) addHistory(w.sme_lemma);
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
  if (matches.length && q !== fold(w.sme_lemma)) info.push(`Haettu muoto ${state.query}: ${[...new Set(matches)].join(", ")}`);
  if (w.notes) info.push(w.notes);
  $("word-info").textContent = info.join("  ·  ");
}

function renderGradation() {
  const w = state.word;
  const el = $("gradation");
  if (UNINFLECTED_POS.includes(w.pos.toUpperCase()) || !state.paradigm.size) { el.innerHTML = ""; return; }
  if (!w.gradation) { el.innerHTML = `<span class="label">Astevaihtelu</span><span class="muted"><i>ei näkyvää astevaihtelua</i></span>`; return; }

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
    <span class="label">Astevaihtelu</span>
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
      return `<span class="form ${cls}" data-speak="${esc(speak)}" title="Kuuntele: ${esc(speak)}">${esc(v)}</span>`;
    }).join('<span class="sep"> / </span>');
    return `<td>${prefix ? `<span class="pron">${esc(prefix)}</span> ` : ""}${forms}</td>`;
  };
  const label = (t) => `<td class="label">${esc(t)}</td>`;
  const section = (...cells) => `<tr class="section">${cells.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`;

  let html = "";
  if (!p.size && !UNINFLECTED_POS.includes(pos)) {
    html = `<p class="muted">FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.</p>`;
  } else if (pos === "V") {
    let rows = section("Indikatiivi", "preesens", "", "preteriti", "");
    for (const pp of PERSONS) {
      const pr = PRONOUNS[pp];
      rows += `<tr>${label(pp)}${cell(pairs(`Ind+Prs+${pp}`), pr)}${cell(pairs("Ind+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}` +
              `${cell(pairs(`Ind+Prt+${pp}`), pr)}${cell(pairs("Ind+Prt+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}</tr>`;
    }
    rows += section("", "Konditionaali", "", "Potentiaali", "");
    for (const pp of PERSONS) {
      const pr = PRONOUNS[pp];
      rows += `<tr>${label(pp)}${cell(pairs(`Cond+Prs+${pp}`), pr)}${cell(pairs("Cond+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}` +
              `${cell(pairs(`Pot+Prs+${pp}`), pr)}${cell(pairs("Pot+Prs+ConNeg"), `${pr} ${NEG_AUX[pp]}`)}</tr>`;
    }
    rows += section("", "Imperatiivi", "", "", "");
    for (const pp of PERSONS) {
      rows += `<tr>${label(pp)}${cell(pairs(`Imprt+${pp}`))}${cell(pairs("Imprt+ConNeg"), NEG_AUX_IMPRT[pp])}<td></td><td></td></tr>`;
    }
    let nf = section("Nominaalimuodot", "");
    for (const [name, tag] of VERB_NONFINITE_ROWS) nf += `<tr>${label(name)}${cell(pairs(tag))}</tr>`;
    html = table(["", "Myönteinen", "Kielteinen", "Myönteinen", "Kielteinen"], rows) + table(null, nf);
  } else if (UNINFLECTED_POS.includes(pos)) {
    html = table(["", "Perusmuoto"], `<tr>${label("Taipumaton")}${cell([["", w.sme_lemma]])}</tr>`);
  } else if (!p.has("Sg+Nom") && !p.has("Pl+Nom") && p.has("Nom")) {
    // Persoona- ja refleksiivipronominit: luku ja persoona kuuluvat jo perusmuotoon
    let rows = "";
    for (const [name, cases] of [...CASE_ROWS, ["Ess", ["Ess"]]]) rows += `<tr>${label(name)}${cell(pairs(...cases))}</tr>`;
    html = table(["Sijamuoto", "Muoto"], rows);
  } else {
    // ol. = ovttaidlohku (yksikkö), ml. = máŋggaidlohku (monikko)
    let rows = p.has("Attr") ? `<tr>${label("Attr")}${cell(pairs("Attr"))}<td></td></tr>` : "";
    for (const [name, cases] of CASE_ROWS) {
      rows += `<tr>${label(name)}${cell(pairs(...cases.map((c) => "Sg+" + c)))}${cell(pairs(...cases.map((c) => "Pl+" + c)))}</tr>`;
    }
    rows += `<tr>${label("Ess")}${cell(pairs("Ess"))}<td></td></tr>`;
    if (pos === "A" && [...p.keys()].some((t) => t.startsWith("Comp") || t.startsWith("Superl"))) {
      rows += section("Vertailumuodot", "predikatiivi", "attribuutti");
      rows += `<tr>${label("Komparatiivi")}${cell(pairs("Comp+Sg+Nom"))}${cell(pairs("Comp+Attr"))}</tr>`;
      rows += `<tr>${label("Superlatiivi")}${cell(pairs("Superl+Sg+Nom"))}${cell(pairs("Superl+Attr"))}</tr>`;
    }
    html = table(["Sijamuoto", "ol. (yksikkö)", "ml. (monikko)"], rows);
  }

  $("panel-table").innerHTML =
    (legend ? `<p class="legend">Aste: <b class="gd">vihreä = GD</b> vahva aste &nbsp;&nbsp; <b class="hd">oranssi = HD</b> heikko aste</p>` : "") +
    html + `<p class="hint">Napauta muotoa kuullaksesi sen ääntämisen.</p>`;
}

function table(headers, rows) {
  const head = headers ? `<thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` : "";
  return `<div class="table-wrap"><table class="paradigm">${head}<tbody>${rows}</tbody></table></div>`;
}

function meaningHtml(m, numbered) {
  const tags = splitList(m.labels).map((l) => `<span class="tag">${esc(l)}</span>`).join("") +
    (m.geo || "").split(",").filter(Boolean).map((g) => `<span class="tag">käytössä ${esc(GEO_NAMES[g] || g)} (${esc(g)})</span>`).join("");
  let html = `<div class="meaning"><div class="head">${numbered ? `<span class="nr">${m.nr}.</span>` : ""}` +
    `${esc(m.translations)}${m.explanations ? ` <span class="expl">(${esc(m.explanations)})</span>` : ""}` +
    `${m.restrictions ? ` <span class="restr">– ${esc(m.restrictions)}</span>` : ""}${tags}</div>`;
  for (const ex of m.examples) {
    html += `<div class="example"><span class="sme">${esc(ex.sme)}</span>` +
      (ex.translation ? `<span class="fin">${esc(ex.translation)}</span>` : `<span class="missing">(ei käännöstä lähteessä)</span>`) +
      (ex.source ? `<span class="muted small">(${esc(ex.source)})</span>` : "") + `</div>`;
  }
  return html + `</div>`;
}

function renderMeanings(meanings) {
  const w = state.word;
  let html = `<h2 style="margin-top:0">${esc(w.sme_lemma)} <span class="muted small"><i>${esc(wordClassLabel(w.pos))}</i></span></h2>`;
  if (w.notes) html += `<p class="muted small"><i>${esc(w.notes)}</i></p>`;
  // Kielittäin, valittu kieli ensin; otsikko vain jos kieliä on useampi
  const groups = meaningsByLanguage(meanings);
  for (const [lang, ms] of groups) {
    if (groups.length > 1) html += `<h3 class="lang-head">${esc(LANGUAGES[lang].in)}</h3>`;
    html += ms.map((m) => meaningHtml(m, ms.length > 1)).join("");
  }
  if (!meanings.length) html += `<p class="muted">Ei merkitystietoja.</p>`;
  $("panel-meanings").innerHTML = html;
  const examples = meanings.reduce((n, m) => n + m.examples.length, 0);
  $("meanings-tab").textContent = `Merkitykset (${meanings.length})` + (examples ? ` ja esimerkit (${examples})` : "");
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
async function speak(text, button) {
  const voice = VOICES[settings.voice] || "biret";
  const key = `tts-cache/${voice}/${encodeURIComponent(text)}`;
  if (button) button.disabled = true;
  if (button === $("speak-btn")) button.lastChild.textContent = " Haetaan…";
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
        throw new Error("puhepalveluun ei saatu yhteyttä. Ensimmäinen kuuntelu vaatii verkkoyhteyden");
      }
      if (!res.ok) throw new Error(IS_DESKTOP
        ? "puhepalveluun ei saatu yhteyttä. Ensimmäinen kuuntelu vaatii verkkoyhteyden"
        : `puhepalvelu vastasi ${res.status}`);
      blob = await res.blob();
      if (cache) cache.put(key, new Response(blob, { headers: { "Content-Type": "audio/wav" } })).catch(() => {});
    }
    memoryCache.set(key, blob);
    const audio = new Audio(URL.createObjectURL(blob));
    await audio.play();
  } catch (e) {
    toast(`Ääntämistä ei saatu: ${e.message}.`);
  } finally {
    if (button) button.disabled = false;
    if (button === $("speak-btn")) button.lastChild.textContent = " Kuuntele";
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
  $("fav-btn").title = on ? "Poista suosikeista" : "Lisää suosikkeihin";
}
function renderSidebar() {
  const fill = (id, words, empty) => {
    $(id).innerHTML = words.length
      ? words.map((w) => `<li><a href="#/sana/${encodeURIComponent(w)}">${esc(w)}</a></li>`).join("")
      : `<li class="empty">${empty}</li>`;
  };
  fill("favourites", settings.favourites, "Ei vielä suosikkeja");
  fill("history", settings.history, "Ei hakuja");
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
  $("voice-select").value = settings.voice;
  $("voice-select").onchange = (e) => { settings.voice = e.target.value; saveSettings(); };
  if (!LANGUAGES[settings.lang]) settings.lang = "fin";
  $("lang-select").value = settings.lang;
  $("lang-select").onchange = (e) => {
    settings.lang = e.target.value; saveSettings();
    if (state.results.length) search(state.query, 0, false);
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
  $("sidebar-toggle").onclick = () => document.body.classList.toggle("sidebar-open");
  $("sidebar").addEventListener("click", (e) => { if (e.target.closest("a")) document.body.classList.remove("sidebar-open"); });
  $("clear-history").onclick = () => { settings.history = []; saveSettings(); renderSidebar(); };
  window.addEventListener("popstate", routeFromHash);
  window.addEventListener("hashchange", routeFromHash);
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f" && db) { e.preventDefault(); input.focus(); input.select(); }
  });
}

async function main() {
  applyTheme();
  bindEvents();
  renderSidebar();
  const ex = $("examples");
  for (const w of EXAMPLE_WORDS) {
    const b = document.createElement("button");
    b.textContent = w;
    b.onclick = () => search(w);
    ex.appendChild(b);
  }
  const rnd = document.createElement("button");
  rnd.className = "random";
  rnd.textContent = "Satunnainen sana";
  rnd.onclick = () => {
    const r = all(`SELECT sme_lemma FROM dictionary WHERE pos IN ('N','V','A') AND gradation IS NOT NULL
                   AND ${LANGUAGES[settings.lang].col} != '' AND (subtype IS NULL OR subtype = '') ORDER BY RANDOM() LIMIT 1`)[0];
    if (r) search(r.sme_lemma);
  };
  ex.appendChild(rnd);

  // Service worker vain verkkosivuna (PWA); työpöytäsovellus (satni://) lukee tiedostot suoraan levyltä
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("sw.js").catch((e) => console.warn("Service worker:", e));
  }

  try {
    showOnly("loading");
    db = await loadDatabase();
  } catch (e) {
    $("loading-text").textContent = `Sanakirjan lataus epäonnistui: ${e.message}`;
    return;
  }
  $("search").disabled = false;
  $("search-btn").disabled = false;
  routeFromHash();
  if (!location.hash) $("search").focus();
}

main();
