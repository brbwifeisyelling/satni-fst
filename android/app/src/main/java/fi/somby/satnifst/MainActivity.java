package fi.somby.satnifst;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * Sátni FST Androidille: sama web-käyttöliittymä kuin PWA:ssa ja työpöytäversiossa (web/).
 *
 * Tiedostot luetaan APK:n assets-kansiosta osoitteella https://appassets.androidplatform.net/,
 * koska file://-osoitteista selain ei salli sanakirjan lataamista eikä välimuistia (sama syy kuin
 * työpöytäversion satni://-osoitteessa). Ulkoiset linkit (Giellatekno, sähköposti) avataan muissa
 * sovelluksissa, ja takaisin-painike kulkee sovelluksen omassa historiassa (#/sana/...).
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START_URL = "https://" + HOST + "/index.html";

    private static final Map<String, String> MIME_TYPES = new HashMap<>();
    static {
        MIME_TYPES.put("html", "text/html");
        MIME_TYPES.put("js", "text/javascript");
        MIME_TYPES.put("css", "text/css");
        MIME_TYPES.put("json", "application/json");
        MIME_TYPES.put("webmanifest", "application/manifest+json");
        MIME_TYPES.put("wasm", "application/wasm");
        MIME_TYPES.put("png", "image/png");
        MIME_TYPES.put("svg", "image/svg+xml");
        MIME_TYPES.put("gz", "application/octet-stream");  // sanakirja, ks. openAsset
    }

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        // Android 15 piirtää sovelluksen tilarivin ja navigointipalkin alle: sisältö niiden väliin.
        // Reunus asetetaan ympäröivälle kehykselle, koska WebView ei huomioi omaa reunustaan.
        FrameLayout root = new FrameLayout(this);
        root.addView(web, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        // Tilarivin alue yläpalkin värillä, jottei se näy erillisenä harmaana raitana
        View statusBar = new View(this);
        statusBar.setBackgroundColor(getColor(R.color.topbar));
        root.addView(statusBar, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, 0, Gravity.TOP));
        root.setClipToPadding(false);  // tilarivin väri piirretään reunuksen alueelle
        setContentView(root);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            // Yläreunassa vain tilarivin korkeus (puhelimissa tilarivi kattaa myös kameran loven)
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                        insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            }
            statusBar.getLayoutParams().height = view.getPaddingTop();
            statusBar.setTranslationY(-view.getPaddingTop());  // reunuksen alueelle, WebViewin yläpuolelle
            statusBar.requestLayout();
            return insets;
        });

        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);  // asetukset, historia ja suosikit (localStorage)
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        // Ääntäminen soitetaan vasta, kun ääni on haettu verkosta (napautuksen jälkeen)
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setTextZoom(100);

        // Ei venytystä reunojen yli vierittäessä (sovellus ei ole verkkosivu)
        web.setOverScrollMode(android.view.View.OVER_SCROLL_NEVER);
        web.setWebViewClient(new Client());
        // Android 13+: takaisin-ele tulee tätä kautta (onBackPressed ei aina tule kutsutuksi)
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::goBackOrFinish);
        }
        if (savedInstanceState == null || web.restoreState(savedInstanceState) == null) {
            web.loadUrl(START_URL);
        }
    }

    /** Tietoa-ikkunaan sovelluksen versionumero (teksti käyttöliittymän kielellä, ks. web/i18n.js). */
    private void showVersion(WebView view) {
        String version;
        try {
            version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (android.content.pm.PackageManager.NameNotFoundException e) {
            return;
        }
        view.evaluateJavascript("window.SATNI_VERSION = '" + version + "'; window.SATNI_PLATFORM = 'android';"
                + " if (window.applyStaticTexts) applyStaticTexts();", null);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    /** Takaisin: edellinen haku (#/sana/...) tai aloitussivu; vasta sen jälkeen sovellus suljetaan. */
    private void goBackOrFinish() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            finish();
        }
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        goBackOrFinish();  // Android 12 ja vanhemmat
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }

    /**
     * Android-käännös purkaa .gz-päätteiset assetit ja tallentaa ne ilman päätettä: data/satni-web.db.gz
     * on APK:ssa data/satni-web.db. Web-käyttöliittymä purkaa tiedoston vain, jos se on yhä pakattu.
     */
    private InputStream openAsset(String path) throws IOException {
        try {
            return getAssets().open(path);
        } catch (IOException e) {
            if (!path.endsWith(".gz")) {
                throw e;
            }
            return getAssets().open(path.substring(0, path.length() - 3));
        }
    }

    private class Client extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri url = request.getUrl();
            if (HOST.equals(url.getHost())) {
                return false;
            }
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, url));
            } catch (ActivityNotFoundException e) {
                // Ei sovellusta, joka osaisi avata linkin
            }
            return true;
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            showVersion(view);
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri url = request.getUrl();
            if (!HOST.equals(url.getHost())) {
                return null;  // Ääntäminen: api-giellalt.uit.no verkosta
            }
            String path = url.getPath() == null || url.getPath().equals("/") ? "index.html" : url.getPath().substring(1);
            String ext = path.contains(".") ? path.substring(path.lastIndexOf('.') + 1) : "";
            String mime = MIME_TYPES.containsKey(ext) ? MIME_TYPES.get(ext) : "application/octet-stream";
            Map<String, String> headers = new HashMap<>();
            headers.put("Cache-Control", "no-cache");
            try {
                InputStream stream = openAsset(path);
                // Koko, jotta sanakirjan latauspalkki liikkuu (assetin available() = koko avattaessa)
                headers.put("Content-Length", String.valueOf(stream.available()));
                return new WebResourceResponse(mime, mime.startsWith("text/") ? "utf-8" : null, 200, "OK", headers, stream);
            } catch (IOException e) {
                return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", headers, null);
            }
        }
    }
}
