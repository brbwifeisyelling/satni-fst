"""Ääntäminen Divvunin/Giellateknon puhesynteesillä (sama palvelu, jota satni.org käyttää).

Äänitiedostot haetaan osoitteesta https://api-giellalt.uit.no/tts/se/<ääni> ja tallennetaan
välimuistiin, joten sama sana soi seuraavalla kerralla heti ja ilman verkkoyhteyttä.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request

TTS_URL = "https://api-giellalt.uit.no/tts/se/{voice}"
VOICES = {"Biret": "biret", "Máhtte": "mahtte", "Sunná": "sunna"}
DEFAULT_VOICE = "Biret"
TIMEOUT = 30

# Linuxin soittimet järjestyksessä; jokin näistä löytyy käytännössä jokaisesta työpöytäjakelusta
LINUX_PLAYERS = [
    ["pw-play"],
    ["paplay"],
    ["aplay", "-q"],
    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
]


def cache_dir():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "satni-fst", "tts")


def cached_path(text, voice):
    voice_id = VOICES.get(voice, voice)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir(), voice_id, f"{digest}.wav")


def fetch(text, voice=DEFAULT_VOICE):
    """Palauttaa polun äänitiedostoon; hakee sen palvelusta, jos sitä ei ole välimuistissa."""
    path = cached_path(text, voice)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    request = urllib.request.Request(
        TTS_URL.format(voice=VOICES.get(voice, voice)),
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        audio = response.read()
    if not audio.startswith(b"RIFF"):
        raise RuntimeError("palvelu ei palauttanut äänitiedostoa")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(audio)
    os.replace(tmp, path)
    return path


def play(path):
    """Soittaa WAV-tiedoston taustalla."""
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    for player in LINUX_PLAYERS:
        if shutil.which(player[0]):
            subprocess.Popen(player + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    raise RuntimeError("äänisoitinta ei löytynyt (pw-play, paplay, aplay tai ffplay)")
