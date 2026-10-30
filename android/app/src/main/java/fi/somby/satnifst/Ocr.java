package fi.somby.satnifst;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.graphics.Point;
import android.graphics.Rect;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import androidx.core.content.FileProvider;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Tekstintunnistus valokuvasta (ML Kit, laitteella; kuva ei lähde laitteelta). Web-käyttöliittymä kutsuu
 * SatniOcr.scan("camera" | "gallery"), ja tulos palaa funktiolle ocrResult (web/app.js):
 * {width, height, image: JPEG data-URL, words: [{t, cx, cy, w, h, a}]} (sanan keskipiste, leveys ja korkeus
 * tekstin suunnassa sekä kulma asteina), peruttaessa null, virheessä {error}.
 *
 * Lupia ei tarvita: kuvan ottaa järjestelmän kamerasovellus (tallentaa sen FileProviderin kautta
 * välimuistiin), ja kuvan valinta tehdään järjestelmän kuvanvalitsimella (Android 13+) tai tiedostovalitsimella.
 */
final class Ocr {
    static final int REQUEST_CAMERA = 41;
    static final int REQUEST_GALLERY = 42;
    /** Kuvan pidempi sivu: riittää tekstille, ja web-näkymälle lähetettävä kuva pysyy pienenä. */
    private static final int MAX_SIDE = 2048;

    private final Activity activity;
    private final WebView web;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private TextRecognizer recognizer;

    Ocr(Activity activity, WebView web) {
        this.activity = activity;
        this.web = web;
    }

    @JavascriptInterface
    public void scan(String source) {
        activity.runOnUiThread(() -> start("camera".equals(source)));
    }

    private File photoFile() {
        File dir = new File(activity.getCacheDir(), "ocr");
        dir.mkdirs();
        return new File(dir, "photo.jpg");
    }

    private void start(boolean camera) {
        Intent intent;
        if (camera) {
            Uri uri = FileProvider.getUriForFile(activity, activity.getPackageName() + ".files", photoFile());
            intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                    .putExtra(MediaStore.EXTRA_OUTPUT, uri)
                    .addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } else if (Build.VERSION.SDK_INT >= 33) {
            intent = new Intent(MediaStore.ACTION_PICK_IMAGES).setType("image/*");
        } else {
            intent = new Intent(Intent.ACTION_GET_CONTENT).addCategory(Intent.CATEGORY_OPENABLE).setType("image/*");
        }
        try {
            activity.startActivityForResult(intent, camera ? REQUEST_CAMERA : REQUEST_GALLERY);
        } catch (ActivityNotFoundException e) {
            sendError("noApp");
        }
    }

    /** MainActivity.onActivityResult: true, jos pyyntö oli tekstintunnistuksen. */
    boolean onResult(int requestCode, int resultCode, Intent data) {
        if (requestCode != REQUEST_CAMERA && requestCode != REQUEST_GALLERY) {
            return false;
        }
        Uri uri = requestCode == REQUEST_CAMERA ? Uri.fromFile(photoFile()) : data == null ? null : data.getData();
        if (resultCode != Activity.RESULT_OK || uri == null) {
            send("null");
            return true;
        }
        worker.execute(() -> {
            Bitmap bitmap;
            try {
                bitmap = load(uri);
            } catch (IOException | RuntimeException e) {
                sendError("image");
                return;
            }
            if (recognizer == null) {
                recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            }
            recognizer.process(InputImage.fromBitmap(bitmap, 0))
                    .addOnSuccessListener(worker, text -> send(toJson(bitmap, text)))
                    .addOnFailureListener(worker, e -> sendError("ocr"));
        });
        return true;
    }

    /** Kuva pienennettynä (pidempi sivu enintään MAX_SIDE) ja EXIF-tiedon mukaan oikein päin käännettynä. */
    private Bitmap load(Uri uri) throws IOException {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        try (InputStream in = open(uri)) {
            BitmapFactory.decodeStream(in, null, bounds);
        }
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = 1;
        while (Math.max(bounds.outWidth, bounds.outHeight) / (options.inSampleSize * 2) >= MAX_SIDE) {
            options.inSampleSize *= 2;
        }
        Bitmap bitmap;
        try (InputStream in = open(uri)) {
            bitmap = BitmapFactory.decodeStream(in, null, options);
        }
        if (bitmap == null) {
            throw new IOException("decode");
        }
        int rotation = 0;
        try (InputStream in = open(uri)) {
            switch (new ExifInterface(in).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                case ExifInterface.ORIENTATION_ROTATE_90: rotation = 90; break;
                case ExifInterface.ORIENTATION_ROTATE_180: rotation = 180; break;
                case ExifInterface.ORIENTATION_ROTATE_270: rotation = 270; break;
                default: break;
            }
        } catch (IOException e) {
            // Ei EXIF-tietoa: kuva sellaisenaan
        }
        float scale = Math.min(1f, (float) MAX_SIDE / Math.max(bitmap.getWidth(), bitmap.getHeight()));
        if (rotation == 0 && scale == 1f) {
            return bitmap;
        }
        Matrix matrix = new Matrix();
        matrix.postScale(scale, scale);
        matrix.postRotate(rotation);
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
    }

    private InputStream open(Uri uri) throws IOException {
        InputStream in = activity.getContentResolver().openInputStream(uri);
        if (in == null) {
            throw new IOException("open");
        }
        return in;
    }

    /** Sanat lukujärjestyksessä (tekstilohko, rivi, sana) sijainteineen kuvan pikseleinä. Vino teksti: kulmapisteistä
     *  (vasen ylä, oikea ylä, oikea ala, vasen ala) sanan oma leveys, korkeus ja kulma, jotta sanan päälle piirretty
     *  teksti kääntyy samaan asentoon. */
    private static String toJson(Bitmap bitmap, Text text) {
        try {
            JSONArray words = new JSONArray();
            for (Text.TextBlock block : text.getTextBlocks()) {
                for (Text.Line line : block.getLines()) {
                    for (Text.Element element : line.getElements()) {
                        JSONObject word = new JSONObject().put("t", element.getText());
                        Point[] p = element.getCornerPoints();
                        Rect r = element.getBoundingBox();
                        if (p != null && p.length == 4) {
                            word.put("cx", (p[0].x + p[1].x + p[2].x + p[3].x) / 4.0)
                                    .put("cy", (p[0].y + p[1].y + p[2].y + p[3].y) / 4.0)
                                    .put("w", Math.hypot(p[1].x - p[0].x, p[1].y - p[0].y))
                                    .put("h", Math.hypot(p[3].x - p[0].x, p[3].y - p[0].y))
                                    .put("a", Math.toDegrees(Math.atan2(p[1].y - p[0].y, p[1].x - p[0].x)));
                        } else if (r != null) {
                            word.put("cx", r.exactCenterX()).put("cy", r.exactCenterY())
                                    .put("w", r.width()).put("h", r.height()).put("a", 0);
                        } else {
                            continue;
                        }
                        words.put(word);
                    }
                }
            }
            ByteArrayOutputStream jpeg = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.JPEG, 80, jpeg);
            return new JSONObject()
                    .put("width", bitmap.getWidth()).put("height", bitmap.getHeight())
                    .put("image", "data:image/jpeg;base64," + Base64.encodeToString(jpeg.toByteArray(), Base64.NO_WRAP))
                    .put("words", words).toString();
        } catch (JSONException e) {
            return "{\"error\":\"ocr\"}";
        }
    }

    private void sendError(String code) {
        send("{\"error\":" + JSONObject.quote(code) + "}");
    }

    private void send(String json) {
        web.post(() -> web.evaluateJavascript("window.ocrResult && ocrResult(" + json + ")", null));
    }

    void close() {
        if (recognizer != null) {
            recognizer.close();
        }
        worker.shutdown();
    }
}
