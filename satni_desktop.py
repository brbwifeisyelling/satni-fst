#!/usr/bin/env python3
"""Sátni FST työpöytäsovellus: Qt-ikkuna (PySide6), joka näyttää saman web-käyttöliittymän kuin PWA.

Web-tiedostot (web/) tarjotaan sisäiselle selaimelle omalla satni://app/ -osoitteella, koska
file://-osoitteista selain ei salli sanakirjan lataamista eikä välimuistia. Ulkoiset linkit
(Giellatekno, sähköposti) avataan käyttäjän tavallisessa selaimessa.
"""
import mimetypes
import os
import sys
import threading
from urllib.parse import parse_qs

from PySide6.QtCore import QBuffer, QByteArray, QObject, QSettings, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

import tts

try:
    from version import VERSION
except ImportError:
    VERSION = "kehitysversio"

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    # PyInstaller ohjaa LD_LIBRARY_PATH:n omiin kirjastoihinsa; palautetaan alkuperäinen, jotta
    # avattava selain käyttää järjestelmän kirjastoja
    if sys.platform.startswith("linux"):
        if "LD_LIBRARY_PATH_ORIG" in os.environ:
            os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEB_DIR = os.path.join(BASE_DIR, "web")
SCHEME = b"satni"
START_URL = QUrl("satni://app/index.html")
DEBUG = bool(os.environ.get("SATNI_DEBUG"))

MIME_TYPES = {
    ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".wasm": "application/wasm",
    ".json": "application/json", ".webmanifest": "application/manifest+json", ".png": "image/png",
    # Pakattu sanakirja tarjotaan sellaisenaan; web-käyttöliittymä purkaa sen itse
    ".gz": "application/octet-stream",
}


class WebFileHandler(QWebEngineUrlSchemeHandler):
    """Tarjoaa web/-kansion tiedostot osoitteesta satni://app/<polku>.

    Lisäksi satni://app/tts/<ääni>?text=... hakee ääntämisen Pythonilla (tts.py: oma varmennepaketti
    ja välimuisti ~/.cache/satni-fst/tts), koska sisäinen selain ei salli hakua omasta osoitteestaan
    puhepalveluun.
    """

    tts_ready = Signal(object, object, object)  # job, äänitiedoston polku, virhe

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tts_ready.connect(self.reply_tts)
        self.pending = set()

    def requestStarted(self, job):
        path = job.requestUrl().path().lstrip("/") or "index.html"
        if path.startswith("tts/"):
            self.start_tts(job, path[4:])
            return
        full = os.path.normpath(os.path.join(WEB_DIR, path))
        if not full.startswith(os.path.normpath(WEB_DIR) + os.sep) or not os.path.isfile(full):
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return
        with open(full, "rb") as f:
            data = f.read()
        mime = MIME_TYPES.get(os.path.splitext(full)[1]) or mimetypes.guess_type(full)[0] or "application/octet-stream"
        buffer = QBuffer(parent=job)  # vapautuu pyynnön mukana
        buffer.setData(QByteArray(data))
        buffer.open(QBuffer.OpenModeFlag.ReadOnly)
        job.reply(mime.encode(), buffer)

    def start_tts(self, job, voice_id):
        text = parse_qs(job.requestUrl().query()).get("text", [""])[0].strip()
        voice = next((name for name, vid in tts.VOICES.items() if vid == voice_id), tts.DEFAULT_VOICE)
        if not text:
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return
        # Pyyntö voi peruuntua kesken (sivu vaihtuu); silloin vastausta ei enää lähetetä
        self.pending.add(job)
        job.destroyed.connect(lambda *_: self.pending.discard(job))

        def worker():
            try:
                self.tts_ready.emit(job, tts.fetch(text, voice), None)
            except Exception as e:
                self.tts_ready.emit(job, None, e)

        threading.Thread(target=worker, daemon=True).start()

    def reply_tts(self, job, path, error):
        if job not in self.pending:
            return
        self.pending.discard(job)
        if error or not path:
            if DEBUG:
                print(f"[tts] {error}")
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return
        with open(path, "rb") as f:
            data = f.read()
        buffer = QBuffer(parent=job)
        buffer.setData(QByteArray(data))
        buffer.open(QBuffer.OpenModeFlag.ReadOnly)
        job.reply(b"audio/wav", buffer)


class AppPage(QWebEnginePage):
    """Sovelluksen omat sivut näytetään ikkunassa, ulkoiset linkit avataan järjestelmän selaimessa."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() == SCHEME.decode():
            return True
        QDesktopServices.openUrl(url)
        return False

    def createWindow(self, window_type):
        # target="_blank" -linkit (esim. Giellatekno): väliaikainen sivu ohjaa osoitteen selaimeen
        return ExternalLinkPage(self.profile(), self)

    def javaScriptConsoleMessage(self, level, message, line, source):
        if DEBUG:
            print(f"[js] {message} ({source}:{line})")


class ExternalLinkPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
        self.deleteLater()
        return False


class MainWindow(QMainWindow):
    def __init__(self, profile):
        super().__init__()
        self.setWindowTitle("Sátni FST - Pohjoissaamen avoin sanakirja ja taivutin")
        self.setWindowIcon(QIcon(os.path.join(WEB_DIR, "icons", "icon-512.png")))
        self.setMinimumSize(420, 500)

        self.view = QWebEngineView(self)
        self.page = AppPage(profile, self.view)
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self.on_loaded)
        self.setCentralWidget(self.view)

        # Ikkunan koko, paikka ja suurennus säilyvät (Linux: ~/.config/Satni FST/, Windows: rekisteri)
        self.settings = QSettings()
        if not self.restoreGeometry(self.settings.value("window/geometry", QByteArray())):
            self.resize(1250, 860)
        self.view.load(START_URL)

    def on_loaded(self, ok):
        # Tietoa-ikkunaan työpöytäversion versionumero
        self.page.runJavaScript(
            f"var v = document.getElementById('about-version'); if (v) v.textContent = 'Versio {VERSION} (työpöytä)';"
        )

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        super().closeEvent(event)


def main():
    # Oma osoitejärjestelmä rekisteröidään ennen QApplicationia; "secure" mahdollistaa
    # selaimen välimuistin (ääntämiset) ja fetchin kuten https-sivulla
    scheme = QWebEngineUrlScheme(SCHEME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.LocalScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.CorsEnabled
        | QWebEngineUrlScheme.Flag.FetchApiAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)

    QApplication.setOrganizationName("Satni FST")
    QApplication.setApplicationName("Satni FST")
    QApplication.setDesktopFileName("satni-fst")
    app = QApplication(sys.argv)

    # Pysyvä profiili: asetukset, historia, suosikit ja ääntämisten välimuisti säilyvät
    profile = QWebEngineProfile("satni-fst", app)
    handler = WebFileHandler(app)
    profile.installUrlSchemeHandler(SCHEME, handler)

    window = MainWindow(profile)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
