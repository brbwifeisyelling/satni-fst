/* Service worker: sovellus ja sanakirja toimivat ilman verkkoyhteyttä ensimmäisen käynnin jälkeen.
   Kun tiedostoja päivitetään, kasvata VERSION, jolloin selaimet hakevat uudet tiedostot. */
const VERSION = "satni-v4";
const APP_SHELL = [
  "./", "index.html", "styles.css", "i18n.js", "app.js", "manifest.webmanifest",
  "vendor/sql-wasm.js", "vendor/sql-wasm.wasm",
  "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png",
];
const DATA = "data/satni-web.db.gz";
// Sanakirjalla on oma välimuistinsa, jottei 21 Mt ladata uudelleen joka sovelluspäivityksessä.
// Kasvata numeroa, kun tietokannan rakenne muuttuu (v2: käännökset kielittäin, v3: käänteiset sanakirjat)
const DATA_CACHE = "satni-data-v3";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // Poistetaan vanhojen versioiden välimuistit (sanakirja ja ääntämiset säilyvät)
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => ![VERSION, DATA_CACHE, "satni-tts"].includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;

  if (url.pathname.endsWith(DATA)) {
    // Sanakirja (~40 Mt): välimuistista, verkosta vain ensimmäisellä kerralla
    event.respondWith(caches.open(DATA_CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      if (cached) return cached;
      const response = await fetch(event.request);
      if (response.ok) cache.put(event.request, response.clone());
      return response;
    }));
    return;
  }

  // Sovelluksen tiedostot: verkosta, jotta päivitykset näkyvät heti; ilman verkkoa välimuistista
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true }).then((r) => r || caches.match("index.html")))
  );
});
