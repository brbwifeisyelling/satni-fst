#!/usr/bin/env python3
import os
import sys
import re
import sqlite3
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import webbrowser
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont, ImageTk

import tts
import ui_theme

try:
    from version import VERSION
except ImportError:
    VERSION = "kehitysversio"

# --- TIETOKANTA- JA POLUNMÄÄRITYS ---

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = sys._MEIPASS
    # PyInstaller ohjaa LD_LIBRARY_PATH:n omiin kirjastoihinsa. Palautetaan alkuperäinen, jotta
    # käynnistettävät ohjelmat (selain, äänisoitin) käyttävät järjestelmän kirjastoja.
    if sys.platform.startswith("linux"):
        if "LD_LIBRARY_PATH_ORIG" in os.environ:
            os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(SCRIPT_DIR, "satni.db")

# Haussa ä = æ ja ö = ø, jotta esim. "Björg" löytää norjalaisen nimen Bjørg
SEARCH_FOLD = str.maketrans({"æ": "ä", "ø": "ö"})

def fold(text):
    return text.lower().translate(SEARCH_FOLD) if isinstance(text, str) else text

def query_database(query):
    q_lower = fold(query.strip())
    results = []
    if not os.path.exists(DB_FILE):
        return results

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Haku saamen perusmuodolla, suomennoksella (myös pilkkulistoista) sekä taivutetulla muodolla
        # SQLiten LOWER() muuttaa vain ASCII-kirjaimet, joten käytetään Pythonin lower()-funktiota (Á, Č, Š...)
        conn.create_function("PYLOWER", 1, fold, deterministic=True)
        q_nordic = q_lower.replace("ä", "æ").replace("ö", "ø")
        cursor.execute(
            """
            SELECT * FROM (
                -- 1 = saamen perusmuoto; 6 = isolla kirjoitettu erisnimi, joka osui vain kirjainkoosta riippumatta
                -- (suomen "tulla" ei saa nostaa naisen nimeä Tulla verbin boahtit edelle)
                SELECT id, sme_lemma, pos, subtype, finnish_translation,
                       CASE WHEN sme_lemma = ? OR PYLOWER(substr(sme_lemma, 1, 1)) = substr(sme_lemma, 1, 1)
                            THEN 1 ELSE 6 END AS rank
                FROM dictionary WHERE PYLOWER(sme_lemma) = ?
                UNION ALL
                -- 2 = ainoa suomennos, 3 = ensimmäinen suomennos, 4 = jokin muu suomennos
                SELECT id, sme_lemma, pos, subtype, finnish_translation,
                       CASE WHEN PYLOWER(finnish_translation) = ? THEN 2
                            WHEN PYLOWER(finnish_translation) LIKE ? THEN 3 ELSE 4 END
                FROM dictionary
                WHERE PYLOWER(finnish_translation) = ?
                   OR PYLOWER(finnish_translation) LIKE ?
                   OR PYLOWER(finnish_translation) LIKE ?
                   OR PYLOWER(finnish_translation) LIKE ?
                UNION ALL
                -- 5 = taivutusmuoto (manan -> mannat)
                SELECT DISTINCT d.id, d.sme_lemma, d.pos, d.subtype, d.finnish_translation, 5
                FROM paradigms p JOIN dictionary d ON p.word_id = d.id
                WHERE p.surface COLLATE NOCASE IN (?, ?, ?, ?)
                UNION ALL
                -- 7 = perusmuoto alkaa hakusanalla
                SELECT id, sme_lemma, pos, subtype, finnish_translation, 7
                FROM dictionary WHERE PYLOWER(sme_lemma) LIKE ?
            )
            ORDER BY rank, CASE WHEN pos = 'V' THEN 1 ELSE 2 END, sme_lemma
            LIMIT 60
            """,
            (
                query.strip(),
                q_lower,
                q_lower,
                f"{q_lower},%",
                q_lower,
                f"{q_lower},%",       # Alkaa sanalla
                f"%, {q_lower},%",    # Keskellä listaa
                f"%, {q_lower}",      # Lopussa listaa
                q_lower,
                q_lower.capitalize(), # Erisnimet (Ánte), joiden ensimmäinen kirjain ei ole ASCII
                q_nordic,             # Norjalaiset kirjaimet taivutusmuodoissa (Bjørga)
                q_nordic.capitalize(),
                f"{q_lower}%",
            )
        )
        rows = cursor.fetchall()

        seen = set()
        for word_id, lemma, pos, subtype, trans, rank in rows:
            if word_id in seen:
                continue
            seen.add(word_id)
            results.append((word_id, lemma, pos, subtype or "", trans or ""))
            if len(results) >= 30:
                break
            
        conn.close()
    except Exception as e:
        print(f"Tietokantavirhe: {e}")
        
    return results

def get_paradigms_from_db(word_id):
    """Palauttaa (taivutusmuodot {tagi: [muodot]}, asteet {(tagi, muoto): "GD"/"HD"}, astevaihtelutiedot)."""
    paradigm, grades, gradation = {}, {}, {}
    if not os.path.exists(DB_FILE):
        return paradigm, grades, gradation

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT tag, surface, grade FROM paradigms WHERE word_id = ? ORDER BY rowid",
            (word_id,)
        )
        for tag, surface, grade in cursor.fetchall():
            if tag not in paradigm:
                paradigm[tag] = []
            if surface not in paradigm[tag]:
                paradigm[tag].append(surface)
            if grade:
                grades[(tag, surface)] = grade

        row = cursor.execute(
            "SELECT gradation, gd_cluster, hd_cluster, gradation_group, gradation_row FROM dictionary WHERE id = ?",
            (word_id,)
        ).fetchone()
        if row and row[0]:
            gradation = dict(zip(("summary", "strong", "weak", "group", "row"), row))
                
        conn.close()
    except Exception as e:
        print(f"Taivutusvirhe tietokannasta: {e}")
        
    return paradigm, grades, gradation

def get_word_details(word_id):
    """Palauttaa (merkitykset, sanatason huomautukset). Merkitys:
    {"nr", "translations", "explanations", "restrictions", "labels", "geo", "examples": [(saame, suomi, lähde)]}"""
    meanings, notes = [], ""
    if not os.path.exists(DB_FILE):
        return meanings, notes
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        examples = {}
        for nr, sme, fin, source in cursor.execute(
            "SELECT meaning_nr, sme, translation, source FROM examples WHERE word_id = ? AND lang = 'fin' ORDER BY rowid",
            (word_id,)
        ):
            examples.setdefault(nr, []).append((sme, fin, source))
        for row in cursor.execute(
            "SELECT nr, translations, explanations, restrictions, labels, geo FROM meanings "
            "WHERE word_id = ? AND lang = 'fin' ORDER BY nr",
            (word_id,)
        ):
            meaning = dict(zip(("nr", "translations", "explanations", "restrictions", "labels", "geo"), row))
            meaning["examples"] = examples.get(meaning["nr"], [])
            meanings.append(meaning)
        row = cursor.execute("SELECT notes FROM dictionary WHERE id = ?", (word_id,)).fetchone()
        notes = (row[0] or "") if row else ""
        conn.close()
    except Exception as e:
        print(f"Merkitysvirhe tietokannasta: {e}")
    return meanings, notes

def suggest_words(prefix, limit=8):
    """Hakuehdotukset kirjoitettaessa: saamen perusmuodot ja suomennokset, jotka alkavat annetulla tekstillä."""
    q = fold(prefix.strip())
    if len(q) < 2 or not os.path.exists(DB_FILE):
        return []
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.create_function("PYLOWER", 1, fold, deterministic=True)
        rows = conn.execute(
            """
            SELECT * FROM (
                SELECT sme_lemma, pos, finnish_translation, 1 AS rank FROM dictionary
                WHERE PYLOWER(sme_lemma) LIKE ?
                UNION ALL
                SELECT sme_lemma, pos, finnish_translation, 2 FROM dictionary
                WHERE PYLOWER(finnish_translation) LIKE ? OR PYLOWER(finnish_translation) LIKE ?
            )
            ORDER BY rank, length(sme_lemma), sme_lemma
            LIMIT 40
            """,
            (f"{q}%", f"{q}%", f"%, {q}%")
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"Ehdotusvirhe: {e}")
        return []
    result, seen = [], set()
    for lemma, pos, trans, _ in rows:
        if (lemma, pos) in seen:
            continue
        seen.add((lemma, pos))
        result.append((lemma, pos, ", ".join(p.strip() for p in (trans or "").split(",")[:2])))
        if len(result) >= limit:
            break
    return result


def random_word():
    """Satunnainen tavallinen sana aloitusnäkymän "Satunnainen sana" -napille."""
    try:
        conn = sqlite3.connect(DB_FILE)
        row = conn.execute(
            "SELECT sme_lemma FROM dictionary WHERE pos IN ('N', 'V', 'A') AND gradation IS NOT NULL "
            "AND finnish_translation != '' AND (subtype IS NULL OR subtype = '') ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


# Giellateknon taivutusgeneraattori (gtweb.uit.no); pos-kenttä hyväksyy vain nämä sanaluokat
GIELLATEKNO_URL = "https://gtweb.uit.no/cgi-bin/smi/smi.cgi?text={word}&pos={pos}&lang=sme&mode=full&action=paradigm"
GIELLATEKNO_POS = {"N": "N", "V": "V", "A": "A", "ADV": "Adv", "NUM": "Num", "PRON": "Pron"}


def giellatekno_url(lemma, pos):
    return GIELLATEKNO_URL.format(word=quote(lemma), pos=GIELLATEKNO_POS.get(pos.upper(), "Any"))


def make_speaker_icon(size=18, color="#1d4ed8"):
    """Kaiutinkuvake (piirretään koodissa; emoji ei piirry Tk:ssa luotettavasti)."""
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    u = big / 18
    draw.polygon([(2 * u, 6.5 * u), (5.5 * u, 6.5 * u), (10 * u, 2.5 * u), (10 * u, 15.5 * u),
                  (5.5 * u, 11.5 * u), (2 * u, 11.5 * u)], fill=color)
    for r in (3.5, 6.5):
        draw.arc((10 * u - r * u, 9 * u - r * u, 10 * u + r * u, 9 * u + r * u),
                 start=-50, end=50, fill=color, width=int(1.6 * u))
    return ImageTk.PhotoImage(img.resize((size, size), Image.Resampling.LANCZOS))


def make_giellatekno_icon(size=20, color="#9f1239"):
    """Pieni "gt"-merkki napin kuvakkeeksi (piirretään koodissa, ei erillistä kuvatiedostoa)."""
    scale = 4  # piirretään isona ja pienennetään, jotta reunat ovat pehmeät
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=5 * scale, fill=color)
    try:
        font = ImageFont.load_default(size=12 * scale)
    except TypeError:  # vanha Pillow ilman koon valintaa
        font = ImageFont.load_default()
    draw.text((big / 2, big / 2 + scale), "gt", fill="#ffffff", font=font, anchor="mm")
    return ImageTk.PhotoImage(img.resize((size, size), Image.Resampling.LANCZOS))


def find_flag_image():
    for p in (
        os.path.join(SCRIPT_DIR, "Sami_flag.svg.webp"),
        os.path.join(SCRIPT_DIR, "assets", "Sami_flag.svg.webp"),
        os.path.join(SCRIPT_DIR, "sami_flag.png"),
    ):
        if os.path.exists(p):
            return p
    return None


# Sanakirjan aluekoodit (<geo>): missä maassa sana on käytössä
GEO_NAMES = {"N": "Norjassa", "S": "Suomessa", "R": "Ruotsissa"}

POS_NAMES = {
    "V": "Verbi",
    "N": "Substantiivi",
    "A": "Adjektiivi",
    "ADV": "Adverbi",
    "PRON": "Pronomini",
    "NUM": "Numeraali",
    "CC": "Rinnastuskonjunktio",
    "CS": "Alistuskonjunktio",
    "PCLE": "Partikkeli",
    "INTERJ": "Interjektio",
    "PO": "Postpositio",
    "PR": "Prepositio",
    "CMP": "Yhdyssanan alkuosa",
    "MWE": "Monisanainen ilmaus",
}

SUBTYPE_NAMES = {
    "Prop": "Erisnimi",
    "NomAg": "Tekijännimi",
    "Pers": "Persoonapronomini",
    "Dem": "Demonstratiivipronomini",
    "Indef": "Indefiniittipronomini",
    "Interr": "Interrogatiivipronomini",
    "Refl": "Refleksiivipronomini",
    "Rel": "Relatiivipronomini",
    "Ord": "Järjestysluku",
    "Coll": "Kollektiivi",
}


def word_class_label(pos, subtype=""):
    label = POS_NAMES.get(pos.upper(), pos)
    if subtype:
        label += f" · {SUBTYPE_NAMES.get(subtype, subtype)}"
    return label


PERSONS = ["Sg1", "Sg2", "Sg3", "Du1", "Du2", "Du3", "Pl1", "Pl2", "Pl3"]

PRONOUNS = {
    "Sg1": "mun", "Sg2": "don", "Sg3": "son",
    "Du1": "moai", "Du2": "doai", "Du3": "soai",
    "Pl1": "mii", "Pl2": "dii", "Pl3": "sii"
}

# Kieltoverbin (ii) indikatiivimuodot: käytetään preesensissä, preteritissä, konditionaalissa ja potentiaalissa
NEG_AUX = {
    "Sg1": "in", "Sg2": "it", "Sg3": "ii",
    "Du1": "ean", "Du2": "eahppi", "Du3": "eaba",
    "Pl1": "eat", "Pl2": "ehpet", "Pl3": "eai"
}

# Kieltoverbin imperatiivimuodot
NEG_AUX_IMPRT = {
    "Sg1": "allon", "Sg2": "ale", "Sg3": "allos",
    "Du1": "allu", "Du2": "alli", "Du3": "alloska",
    "Pl1": "allot", "Pl2": "allet", "Pl3": "alloset"
}

# Saamen koulukieliopin sijataulukko: genetiivi ja akkusatiivi samalla rivillä (Gen/Akk).
# Akkusatiivin muoto ensin, koska genetiivillä on lisäksi usein harvinaisempi rinnakkaismuoto (vieso).
CASE_ROWS = [
    ("Nom", ["Nom"]),
    ("Gen/Akk", ["Acc", "Gen"]),
    ("Ill", ["Ill"]),
    ("Lok", ["Loc"]),
    ("Kom", ["Com"]),
]

VERB_NONFINITE_ROWS = [
    ("Infinitiivi", "Inf"),
    ("Perfektipartisiippi", "PrfPrc"),
    ("Preesenspartisiippi", "PrsPrc"),
    ("Gerundi", "Ger"),
    ("Verbigenetiivi", "VGen"),
    ("Verbiabessiivi", "VAbess"),
    ("Supiini", "Sup"),
    ("Aktio (Nom)", "Actio+Nom"),
    ("Aktio (Loc)", "Actio+Loc"),
    ("Aktio (Com)", "Actio+Com"),
    ("Aktio (Ess)", "Actio+Ess"),
]

UNINFLECTED_POS = ["ADV", "CC", "CS", "INTERJ", "PCLE", "PO", "PR", "CMP", "MWE"]

# Aloitusnäkymän esimerkkisanat
EXAMPLE_WORDS = ["dahkat", "áhčči", "viessu", "mannat", "buorre", "golbma", "juolgi", "oastit"]


class SatniGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sátni FST - Pohjoissaamen avoin sanakirja ja taivutin")
        self.root.minsize(900, 600)

        self.settings = ui_theme.load_settings()
        self.restore_window()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.font = ui_theme.choose_font_family(root)
        self.set_window_icon()

        self.current_results = []
        self.last_query = ""
        self.selected_idx = 0
        self.grades = {}
        self.cells = {}
        self.suggestions = []
        self.suggest_job = None

        voice = self.settings.get("voice")
        self.voice = tk.StringVar(value=voice if voice in tts.VOICES else tts.DEFAULT_VOICE)
        self.show_grade = tk.BooleanVar(value=bool(self.settings.get("show_grade", True)))
        self.voice.trace_add("write", lambda *_: self.save_setting("voice", self.voice.get()))

        self.root.bind_all("<Control-f>", self.focus_search)
        self.root.bind_all("<Control-l>", self.focus_search)
        self.build_ui()
        # Avataan sama sana ja välilehti, joihin edellinen käyttökerta jäi
        if self.settings.get("last_query"):
            self.restore_view(self.settings["last_query"], self.settings.get("last_index", 0),
                              self.settings.get("tab", 0))

    # --- Ikkunan ja näkymän tallennus ---

    def restore_window(self):
        """Ikkunan koko ja paikka edelliseltä kerralta; varmistetaan, että ikkuna osuu näytölle."""
        match = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", self.settings.get("geometry") or "")
        if match:
            w, h, x, y = (int(v) for v in match.groups())
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            w, h = min(max(w, 900), sw), min(max(h, 600), sh)
            x, y = min(max(x, 0), max(sw - 200, 0)), min(max(y, 0), max(sh - 200, 0))
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            # Linuxissa ikkunan sijainti luetaan otsikkopalkin alapuolelta, mutta asetetaan reunasta.
            # Mitataan ero, jotta tallennettu paikka ei valu joka käynnistyksellä alemmas.
            self.root.after(400, lambda: self.measure_frame_offset(x, y))
        else:
            self.root.geometry("1250x860")
        if self.settings.get("maximized"):
            self.root.after(50, self.maximize)

    def measure_frame_offset(self, x, y, tries=30):
        # Mitataan vasta, kun ikkuna on oikeasti näkyvissä (käynnistys voi viivästyttää sitä)
        if not self.root.winfo_ismapped() or (self.root.winfo_rootx(), self.root.winfo_rooty()) == (0, 0):
            if tries:
                self.root.after(100, lambda: self.measure_frame_offset(x, y, tries - 1))
            return
        dx, dy = self.root.winfo_rootx() - x, self.root.winfo_rooty() - y
        if 0 <= dx < 100 and 0 <= dy < 100:
            self.frame_offset = (dx, dy)

    def maximize(self):
        try:
            if sys.platform == "win32":
                self.root.state("zoomed")
            else:
                self.root.attributes("-zoomed", True)
        except tk.TclError:
            pass

    def is_maximized(self):
        try:
            if sys.platform == "win32":
                return self.root.state() == "zoomed"
            return bool(self.root.attributes("-zoomed"))
        except tk.TclError:
            return False

    def on_close(self):
        maximized = self.is_maximized()
        self.settings["maximized"] = maximized
        if not maximized:  # suurennetun ikkunan koko ei ole hyödyllinen palautettava koko
            dx, dy = getattr(self, "frame_offset", (0, 0))
            self.settings["geometry"] = (f"{self.root.winfo_width()}x{self.root.winfo_height()}"
                                         f"+{self.root.winfo_rootx() - dx}+{self.root.winfo_rooty() - dy}")
        ui_theme.save_settings(self.settings)
        self.root.destroy()

    def on_tab_changed(self, event=None):
        if self.current_results:
            self.save_setting("tab", self.notebook.index(self.notebook.select()))

    def restore_view(self, query, idx, tab):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, query)
        self.perform_search()
        if self.current_results:
            if 0 < idx < len(self.current_results):
                self.select_word_option(idx)
            try:
                self.notebook.select(tab)
            except tk.TclError:
                pass

    # --- Yleiset apuvälineet ---

    def F(self, size=10, *style):
        return (self.font, size, *style)

    def save_setting(self, key, value):
        self.settings[key] = value
        ui_theme.save_settings(self.settings)

    def set_window_icon(self):
        """Saamen lippu ikkunan ja tehtäväpalkin kuvakkeeksi."""
        path = find_flag_image()
        if not path:
            return
        try:
            flag = Image.open(path).convert("RGBA")
            flag.thumbnail((64, 64), Image.Resampling.LANCZOS)
            icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            icon.paste(flag, ((64 - flag.width) // 2, (64 - flag.height) // 2), flag)
            self.window_icon = ImageTk.PhotoImage(icon)
            self.root.iconphoto(True, self.window_icon)
        except Exception as e:
            print(f"Ikkunan kuvakkeen latausvirhe: {e}")

    def card(self, parent, **pack):
        """Pehmeäreunainen kortti: vaalea pinta ja ohut harmaa reuna."""
        frame = tk.Frame(parent, bg=self.c["surface"], highlightthickness=1,
                         highlightbackground=self.c["border"], highlightcolor=self.c["border"])
        if pack:
            frame.pack(**pack)
        return frame

    def flat_button(self, parent, text, command, bg, fg, hover, font=None, image=None, padx=12, pady=5):
        btn = tk.Button(
            parent, text=text, command=command, image=image, compound=tk.LEFT if image else None,
            font=font or self.F(10, "bold"), bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
            relief=tk.FLAT, bd=0, highlightthickness=0, padx=padx, pady=pady, cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover) if str(btn["state"]) != "disabled" else None)
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # --- Käyttöliittymän rakentaminen ---

    def build_ui(self):
        self.mode = ui_theme.resolve_mode(self.settings.get("theme", "auto"))
        c = self.c = ui_theme.PALETTES[self.mode]
        ui_theme.apply_ttk_style(self.root, c, self.font)
        self.root.configure(bg=c["bg"])

        self.build_header()
        self.build_search_bar()

        self.results_frame = tk.Frame(self.root, bg=c["bg"])
        tk.Label(self.results_frame, text="Valitse:", font=self.F(9, "bold"),
                 fg=c["muted"], bg=c["bg"]).pack(side=tk.LEFT, anchor="n", padx=(0, 10), pady=6)
        self.buttons_inner_frame = tk.Frame(self.results_frame, bg=c["bg"], height=1)
        self.buttons_inner_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)
        # Hakutulosnapit rivitetään ikkunan leveyden mukaan, myös ikkunan kokoa muutettaessa
        self.buttons_inner_frame.bind("<Configure>", lambda e: self.layout_result_buttons())

        self.content = tk.Frame(self.root, bg=c["bg"])
        self.content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 16))

        self.build_welcome()
        self.build_word_view()
        self.build_suggestions()
        self.show_welcome()
        self.search_entry.focus_set()

    def build_header(self):
        c = self.c
        header = tk.Frame(self.root, bg=c["surface"])
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(header, text="Sátni FST", font=self.F(18, "bold"), fg=c["text"],
                 bg=c["surface"]).pack(side=tk.LEFT, padx=(20, 12), pady=14)
        tk.Label(header, text="Pohjoissaamen avoin sanakirja ja taivutusgeneraattori",
                 font=self.F(10), fg=c["muted"], bg=c["surface"]).pack(side=tk.LEFT, pady=14)

        self.flag_label = tk.Label(header, bg=c["surface"])
        self.flag_label.pack(side=tk.RIGHT, padx=(10, 20))
        path = find_flag_image()
        if path:
            try:
                img = Image.open(path).resize((44, 28), Image.Resampling.LANCZOS)
                self.flag_img = ImageTk.PhotoImage(img)
                self.flag_label.config(image=self.flag_img)
            except Exception as e:
                print(f"Lipun latausvirhe: {e}")

        self.flat_button(header, "Tietoa", self.show_about, c["chip"], c["chip_text"], c["chip_hover"],
                         font=self.F(9, "bold")).pack(side=tk.RIGHT, padx=6)

        self.theme_var = tk.StringVar(value=ui_theme.THEME_NAMES.get(self.settings.get("theme", "auto")))
        theme_box = ttk.Combobox(header, textvariable=self.theme_var, values=list(ui_theme.THEME_NAMES.values()),
                                 state="readonly", width=13, font=self.F(9))
        theme_box.pack(side=tk.RIGHT, padx=(4, 10))
        theme_box.bind("<<ComboboxSelected>>", self.on_theme_change)
        tk.Label(header, text="Teema:", font=self.F(9), fg=c["muted"], bg=c["surface"]).pack(side=tk.RIGHT)

        # Saamen lipun värit
        stripe = tk.Frame(self.root, height=4, bg=c["bg"])
        stripe.pack(fill=tk.X, side=tk.TOP)
        for color in ("#e11d48", "#facc15", "#2563eb", "#16a34a"):
            tk.Frame(stripe, bg=color, height=4).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def build_search_bar(self):
        c = self.c
        bar = tk.Frame(self.root, bg=c["bg"])
        bar.pack(fill=tk.X, padx=20, pady=(14, 8))

        tk.Label(bar, text="Hae", font=self.F(11, "bold"), fg=c["text"], bg=c["bg"]).pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry = tk.Entry(
            bar, font=self.F(13), width=28, bg=c["entry"], fg=c["text"], insertbackground=c["text"],
            relief=tk.FLAT, highlightthickness=1, highlightbackground=c["border"], highlightcolor=c["accent"],
            selectbackground=c["select"], selectforeground=c["text"]
        )
        self.search_entry.pack(side=tk.LEFT, ipady=6)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        self.search_entry.bind("<KeyRelease>", self.on_search_key)
        self.search_entry.bind("<Down>", self.focus_suggestions)
        self.search_entry.bind("<Escape>", lambda e: self.hide_suggestions())

        self.flat_button(bar, "Hae", self.perform_search, c["accent"], c["accent_text"], c["accent_hover"],
                         padx=18, pady=7).pack(side=tk.LEFT, padx=(8, 18))

        tk.Label(bar, text="saameksi, suomeksi tai taivutusmuodolla", font=self.F(9),
                 fg=c["subtle"], bg=c["bg"]).pack(side=tk.LEFT)

        voice_box = ttk.Combobox(bar, textvariable=self.voice, values=list(tts.VOICES),
                                 state="readonly", width=8, font=self.F(10))
        voice_box.pack(side=tk.RIGHT)
        tk.Label(bar, text="Ääni:", font=self.F(10), fg=c["muted"], bg=c["bg"]).pack(side=tk.RIGHT, padx=(16, 4))

        tk.Checkbutton(
            bar, text="Näytä aste (GD/HD)", variable=self.show_grade, command=self.on_grade_toggle,
            font=self.F(10), bg=c["bg"], fg=c["text"], activebackground=c["bg"], activeforeground=c["text"],
            selectcolor=c["entry"], highlightthickness=0, bd=0
        ).pack(side=tk.RIGHT)

    def build_welcome(self):
        """Aloitusnäkymä: ohjeet, esimerkkisanat ja satunnainen sana."""
        c = self.c
        self.welcome = self.card(self.content)
        inner = tk.Frame(self.welcome, bg=c["surface"])
        inner.pack(fill=tk.BOTH, expand=True, padx=36, pady=30)

        tk.Label(inner, text="Bures boahtin! – Tervetuloa", font=self.F(20, "bold"),
                 fg=c["text"], bg=c["surface"]).pack(anchor="w")
        tk.Label(inner, text="Pohjoissaamen–suomen sanakirja, jossa on sanojen koko taivutus.",
                 font=self.F(11), fg=c["muted"], bg=c["surface"]).pack(anchor="w", pady=(4, 20))

        tips = [
            ("Hae", "saamen sanalla (dahkat), suomen sanalla (tehdä) tai taivutetulla muodolla (dagan)."),
            ("Taivutus", "näkyy taulukkona: verbeillä kaikki tapaluokat, nomineilla sijamuodot (ol. ja ml.)."),
            ("Astevaihtelu", "vahva aste GD näkyy vihreänä ja heikko aste HD oranssina."),
            ("Ääntäminen", "Kuuntele-nappi tai kaksoisnapsautus taulukon muodossa."),
            ("Pikanäppäin", "Ctrl+F vie hakukenttään."),
        ]
        for title, text in tips:
            row = tk.Frame(inner, bg=c["surface"])
            row.pack(anchor="w", pady=3)
            tk.Label(row, text=title, font=self.F(10, "bold"), fg=c["accent"], bg=c["surface"],
                     width=13, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=text, font=self.F(10), fg=c["text"], bg=c["surface"]).pack(side=tk.LEFT)

        tk.Label(inner, text="Kokeile:", font=self.F(10, "bold"), fg=c["muted"],
                 bg=c["surface"]).pack(anchor="w", pady=(24, 8))
        chips = tk.Frame(inner, bg=c["surface"])
        chips.pack(anchor="w")
        for word in EXAMPLE_WORDS:
            self.flat_button(chips, word, lambda w=word: self.search_for(w), c["chip"], c["chip_text"],
                             c["chip_hover"], font=self.F(10, "bold"), padx=12, pady=5).pack(side=tk.LEFT, padx=(0, 6))
        self.flat_button(chips, "Satunnainen sana", self.search_random, c["speak_bg"], c["speak_fg"],
                         c["speak_hover"], font=self.F(10, "bold"), padx=12, pady=5).pack(side=tk.LEFT, padx=(12, 0))

    def build_word_view(self):
        c = self.c
        self.word_view = tk.Frame(self.content, bg=c["bg"])

        # Sanakortti: perusmuoto isolla, sanaluokka, suomennos, astevaihtelu ja lisätiedot
        self.word_card = self.card(self.word_view, fill=tk.X)
        inner = tk.Frame(self.word_card, bg=c["surface"])
        inner.pack(fill=tk.X, padx=20, pady=(14, 12))

        top = tk.Frame(inner, bg=c["surface"])
        top.pack(fill=tk.X)
        self.lemma_label = tk.Label(top, text="", font=self.F(22, "bold"), fg=c["text"], bg=c["surface"])
        self.lemma_label.pack(side=tk.LEFT)
        self.pos_badge = tk.Label(top, text="", font=self.F(9, "bold"), fg=c["chip_text"], bg=c["chip"],
                                  padx=8, pady=2)
        self.pos_badge.pack(side=tk.LEFT, padx=(14, 0), pady=(6, 0))

        self.giellatekno_icon = make_giellatekno_icon(color=c["gt_fg"] if self.mode == "light" else "#be123c")
        self.flat_button(top, " Giellatekno ↗", self.open_giellatekno, c["gt_bg"], c["gt_fg"], c["gt_hover"],
                         font=self.F(9, "bold"), image=self.giellatekno_icon, padx=10, pady=4
                         ).pack(side=tk.RIGHT, padx=(8, 0))
        self.speaker_icon = make_speaker_icon(color=c["speak_fg"])
        self.speak_button = self.flat_button(top, " Kuuntele", self.speak_lemma, c["speak_bg"], c["speak_fg"],
                                             c["speak_hover"], font=self.F(9, "bold"), image=self.speaker_icon,
                                             padx=10, pady=4)
        self.speak_button.pack(side=tk.RIGHT)

        trans_row = tk.Frame(inner, bg=c["surface"])
        trans_row.pack(fill=tk.X, pady=(2, 8))
        self.trans_label = tk.Label(trans_row, text="", font=self.F(13), fg=c["text"], bg=c["surface"],
                                    anchor="w", justify=tk.LEFT)
        self.trans_label.pack(side=tk.LEFT)
        self.more_label = tk.Label(trans_row, text="", font=self.F(10), fg=c["accent"], bg=c["surface"], cursor="hand2")
        self.more_label.pack(side=tk.LEFT, padx=(10, 0))
        self.more_label.bind("<Button-1>", lambda e: self.notebook.select(self.tab_meanings))

        self.gradation_frame = tk.Frame(inner, bg=c["surface"])
        self.gradation_frame.pack(fill=tk.X, pady=(0, 4))
        self.info_label = tk.Label(inner, text="", font=self.F(9), fg=c["muted"], bg=c["surface"], anchor="w")
        self.info_label.pack(fill=tk.X)

        # Välilehdet
        self.notebook = ttk.Notebook(self.word_view)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.tab_table = tk.Frame(self.notebook, bg=c["surface"])
        self.tab_meanings = tk.Frame(self.notebook, bg=c["surface"])
        self.tab_raw = tk.Frame(self.notebook, bg=c["surface"])
        self.notebook.add(self.tab_table, text="Taivutus")
        self.notebook.add(self.tab_meanings, text="Merkitykset ja esimerkit")
        self.notebook.add(self.tab_raw, text="Kaikki muodot")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Ohjerivi pakataan ennen taulukkoa, jotta laajeneva taulukko ei peitä sitä
        hint = tk.Label(self.tab_table, text="Kaksoisnapsauta muotoa kuullaksesi sen  ·  "
                        "oikea painike: kuuntele tai kopioi  ·  Ctrl+C kopioi valinnan",
                        font=self.F(9), fg=c["subtle"], bg=c["surface"], anchor="w")
        hint.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(2, 8))
        self.table = self.make_text(self.tab_table, font=self.F(10), hscroll=True, spacing=5)
        self.setup_table_tags()
        self.table.bind("<Double-1>", self.on_table_double_click)
        self.table.bind("<Button-3>", self.on_table_right_click)

        self.meanings_text = self.make_text(self.tab_meanings, font=self.F(11), wrap=tk.WORD, spacing=2)
        self.setup_meanings_tags()
        self.raw_text = self.make_text(self.tab_raw, font=("Monospace", 10), spacing=1)
        self.raw_text.tag_configure("gd", foreground=c["gd_fg"])
        self.raw_text.tag_configure("hd", foreground=c["hd_fg"])
        self.raw_text.tag_configure("muted", foreground=c["muted"])

    def make_text(self, parent, font, wrap=tk.NONE, hscroll=False, spacing=0):
        c = self.c
        container = tk.Frame(parent, bg=c["surface"])
        container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        text = tk.Text(
            container, font=font, wrap=wrap, bg=c["surface"], fg=c["text"], relief=tk.FLAT, bd=0,
            highlightthickness=0, padx=16, pady=12, spacing1=spacing, spacing3=spacing, cursor="arrow",
            selectbackground=c["select"], selectforeground=c["text"], inactiveselectbackground=c["select"],
            insertbackground=c["surface"]
        )
        vbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        if hscroll:
            hbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=text.xview)
            text.configure(xscrollcommand=hbar.set)
            hbar.pack(side=tk.BOTTOM, fill=tk.X)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text.configure(state=tk.DISABLED)
        # Ctrl+C toimii myös lukutilassa olevassa tekstissä, kun kenttä saa fokuksen
        text.bind("<Button-1>", lambda e: text.focus_set(), add="+")
        return text

    def build_suggestions(self):
        """Hakuehdotuslista hakukentän alle (piilossa kunnes kirjoitetaan)."""
        c = self.c
        self.suggest_box = tk.Listbox(
            self.root, font=self.F(10), bg=c["surface"], fg=c["text"], selectbackground=c["accent"],
            selectforeground=c["accent_text"], activestyle="none", relief=tk.FLAT, bd=0,
            highlightthickness=1, highlightbackground=c["border"], highlightcolor=c["accent"], height=8
        )
        self.suggest_box.bind("<Return>", self.choose_suggestion)
        self.suggest_box.bind("<Double-1>", self.choose_suggestion)
        self.suggest_box.bind("<ButtonRelease-1>", self.choose_suggestion)
        self.suggest_box.bind("<Escape>", lambda e: (self.hide_suggestions(), self.search_entry.focus_set()))
        self.suggest_box.bind("<Up>", self.suggestion_up)
        self.root.bind("<Button-1>", self.on_root_click, add="+")

    # --- Teema ---

    def on_theme_change(self, event=None):
        names = {v: k for k, v in ui_theme.THEME_NAMES.items()}
        self.save_setting("theme", names.get(self.theme_var.get(), "auto"))
        self.rebuild_ui()

    def rebuild_ui(self):
        """Rakentaa käyttöliittymän uusilla väreillä ja palauttaa haun ja valitun sanan."""
        query, idx = self.last_query, self.selected_idx
        tab = self.notebook.index(self.notebook.select()) if self.current_results else 0
        for widget in self.root.winfo_children():
            widget.destroy()
        self.current_results = []
        self.build_ui()
        if query:
            self.restore_view(query, idx, tab)

    def on_grade_toggle(self):
        self.save_setting("show_grade", bool(self.show_grade.get()))
        self.refresh_selected()

    # --- Haku ---

    def focus_search(self, event=None):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break"

    def search_for(self, word):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, word)
        self.perform_search()

    def search_random(self):
        word = random_word()
        if word:
            self.search_for(word)

    def show_welcome(self):
        self.word_view.pack_forget()
        self.results_frame.pack_forget()
        self.welcome.pack(fill=tk.BOTH, expand=True)

    def show_word_view(self):
        self.welcome.pack_forget()
        self.results_frame.pack(fill=tk.X, padx=20, pady=(0, 8), before=self.content)
        self.word_view.pack(fill=tk.BOTH, expand=True)

    def perform_search(self):
        self.hide_suggestions()
        query = self.search_entry.get().strip()
        if not query:
            return

        self.last_query = query
        self.current_results = query_database(query)
        if self.current_results:
            self.settings["last_query"] = query

        for widget in self.buttons_inner_frame.winfo_children():
            widget.destroy()

        if not self.current_results:
            self.show_word_view()
            self.results_frame.pack_forget()
            self.lemma_label.config(text=f"Ei osumia haulle ”{query}”")
            self.pos_badge.pack_forget()
            self.trans_label.config(text="Kokeile toista kirjoitusasua, perusmuotoa tai suomenkielistä sanaa.")
            self.more_label.config(text="")
            self.render_gradation(None)
            self.info_label.config(text="")
            self.clear_tables()
            return

        self.show_word_view()
        c = self.c
        for idx, (word_id, lemma, pos, subtype, trans) in enumerate(self.current_results):
            short_trans = ", ".join(p.strip() for p in (trans or "").split(",")[:2] if p.strip())
            pos_label = f"{pos} {subtype}" if subtype else pos
            btn_text = f"{lemma}  ({pos_label})" + (f"  –  {short_trans}" if short_trans else "")
            self.flat_button(self.buttons_inner_frame, btn_text, lambda i=idx: self.select_word_option(i),
                             c["chip"], c["chip_text"], c["chip_hover"], font=self.F(9, "bold"), padx=10, pady=4)

        self.layout_result_buttons()
        self.select_word_option(0)

    def layout_result_buttons(self):
        """Asettelee hakutulosnapit vasemmalta oikealle ja aloittaa uuden rivin, kun leveys loppuu."""
        buttons = self.buttons_inner_frame.winfo_children()
        if not buttons:
            self.buttons_inner_frame.config(height=1)
            return
        width = self.buttons_inner_frame.winfo_width()
        if width <= 1:
            width = self.root.winfo_width() - 150
        gap = 6
        x = y = row_height = 0
        for btn in buttons:
            w, h = btn.winfo_reqwidth(), btn.winfo_reqheight()
            if x > 0 and x + w > width:
                x, y = 0, y + row_height + gap
                row_height = 0
            btn.place(x=x, y=y)
            x += w + gap
            row_height = max(row_height, h)
        new_height = y + row_height
        if int(self.buttons_inner_frame.cget("height")) != new_height:
            self.buttons_inner_frame.config(height=new_height)

    # --- Hakuehdotukset ---

    def on_search_key(self, event):
        if event.keysym in ("Return", "Down", "Up", "Escape", "Tab"):
            return
        if self.suggest_job:
            self.root.after_cancel(self.suggest_job)
        self.suggest_job = self.root.after(180, self.update_suggestions)

    def update_suggestions(self):
        self.suggest_job = None
        text = self.search_entry.get()
        self.suggestions = suggest_words(text) if self.search_entry.focus_get() == self.search_entry else []
        if not self.suggestions or (len(self.suggestions) == 1 and fold(self.suggestions[0][0]) == fold(text)):
            self.hide_suggestions()
            return
        self.suggest_box.delete(0, tk.END)
        for lemma, pos, trans in self.suggestions:
            self.suggest_box.insert(tk.END, f"  {lemma}   ({pos})" + (f"   –  {trans}" if trans else ""))
        self.suggest_box.config(height=len(self.suggestions))
        x = self.search_entry.winfo_rootx() - self.root.winfo_rootx()
        y = self.search_entry.winfo_rooty() - self.root.winfo_rooty() + self.search_entry.winfo_height() + 2
        self.suggest_box.place(x=x, y=y, width=max(self.search_entry.winfo_width() + 160, 420))
        self.suggest_box.lift()

    def hide_suggestions(self):
        if self.suggest_job:
            self.root.after_cancel(self.suggest_job)
            self.suggest_job = None
        if hasattr(self, "suggest_box"):
            self.suggest_box.place_forget()

    def focus_suggestions(self, event=None):
        if self.suggest_box.winfo_ismapped() and self.suggestions:
            self.suggest_box.focus_set()
            self.suggest_box.selection_clear(0, tk.END)
            self.suggest_box.selection_set(0)
            self.suggest_box.activate(0)
            return "break"

    def suggestion_up(self, event):
        if self.suggest_box.curselection() == (0,):
            self.search_entry.focus_set()
            return "break"

    def choose_suggestion(self, event=None):
        selection = self.suggest_box.curselection()
        if not selection:
            return
        lemma = self.suggestions[selection[0]][0]
        self.search_for(lemma)
        self.search_entry.focus_set()

    def on_root_click(self, event):
        if event.widget not in (self.suggest_box, self.search_entry):
            self.hide_suggestions()

    # --- Valittu sana ---

    def refresh_selected(self):
        if self.current_results:
            self.select_word_option(self.selected_idx)

    def select_word_option(self, selected_idx):
        c = self.c
        self.selected_idx = selected_idx
        self.save_setting("last_index", selected_idx)
        word_id, lemma, pos, subtype, trans = self.current_results[selected_idx]
        for idx, widget in enumerate(self.buttons_inner_frame.winfo_children()):
            selected = idx == selected_idx
            bg = c["accent"] if selected else c["chip"]
            fg = c["accent_text"] if selected else c["chip_text"]
            hover = c["accent_hover"] if selected else c["chip_hover"]
            widget.config(bg=bg, fg=fg, activebackground=hover, activeforeground=fg)
            widget.bind("<Enter>", lambda e, w=widget, h=hover: w.config(bg=h))
            widget.bind("<Leave>", lambda e, w=widget, b=bg: w.config(bg=b))

        meanings, notes = get_word_details(word_id)

        # Otsikkoon ensimmäinen merkitys käyttörajoituksineen (esim. hyppiä – paksussa lumessa, porosta)
        if meanings:
            first = meanings[0]
            parts = [p.strip() for p in (first["translations"] or first["explanations"] or "").split(",") if p.strip()]
            display_trans = ", ".join(parts[:4])
            if first["restrictions"]:
                display_trans += f"  ({first['restrictions']})"
        else:
            display_trans = ", ".join(p.strip() for p in (trans or "").split(",")[:3] if p.strip())

        self.lemma_label.config(text=lemma)
        self.pos_badge.config(text=word_class_label(pos, subtype))
        self.pos_badge.pack(side=tk.LEFT, padx=(14, 0), pady=(6, 0), after=self.lemma_label)
        self.trans_label.config(text=display_trans or "(ei suomennosta)")
        self.more_label.config(text=f"+{len(meanings) - 1} merkitystä" if len(meanings) > 1 else "")

        paradigm, self.grades, gradation = get_paradigms_from_db(word_id)
        self.render_gradation(self.gradation_view(pos, paradigm, gradation))
        self.populate_meanings(lemma, pos, meanings, notes)

        # Jos haettiin taivutettua muotoa (esim. dagan), kerrotaan sen muoto ja aste
        info = []
        query = fold(self.last_query)
        matches = []
        for tag, surfaces in paradigm.items():
            for surface in surfaces:
                if fold(surface) == query:
                    grade = self.grades.get((tag, surface))
                    matches.append(f"{tag}" + (f" ({grade})" if grade else ""))
        if matches and query != fold(lemma):
            info.append(f"Haettu muoto {self.last_query}: {', '.join(dict.fromkeys(matches))}")
        if notes:
            info.append(notes)
        self.info_label.config(text="   ·   ".join(info))

        self.populate_tables(pos, lemma, paradigm)

    def gradation_view(self, pos, paradigm, gradation):
        """Astevaihtelun näyttötiedot: None (ei näytetä), {} (ei näkyvää vaihtelua) tai
        {"gd": "dahkat", "hd": "dagan", "strong": "hk", "weak": "g", "group": ..., "row": [(arvo, aste), ...]}"""
        if pos.upper() in UNINFLECTED_POS or not paradigm:
            return None
        if not gradation:
            return {}

        # Esimerkkimuodot: perusmuoto ja tavallisin vastakkaisen asteen muoto (verbeillä Sg1, nomineilla akk./gen.)
        # (genetiivillä on usein kaksi muotoa, joista akkusatiivin muoto on tavallisempi: juolggi eikä juolgge)
        preferred = ["Inf", "Sg+Nom", "Nom", "Ind+Prs+Sg1", "Sg+Acc", "Acc", "Sg+Gen", "Pl+Nom"]
        tags = preferred + [t for t in paradigm if t not in preferred]
        examples = {}
        # Haettu taivutusmuoto (esim. dagan) esimerkiksi omalle asteelleen
        query = fold(self.last_query)
        for (tag, surface), grade in self.grades.items():
            if fold(surface) == query:
                examples.setdefault(grade, surface)
        for tag in tags:
            for surface in paradigm.get(tag, []):
                grade = self.grades.get((tag, surface))
                if grade and grade not in examples:
                    examples[grade] = surface

        # "hkk (III) · hk (II) · g (I)" -> [("hkk", "III"), ("hk", "II"), ("g", "I")]
        row = [tuple(part.rstrip(")").split(" (")) for part in gradation["row"].split(" · ")]
        return {
            "gd": examples.get("GD", "-"), "hd": examples.get("HD", "-"),
            "strong": gradation["strong"], "weak": gradation["weak"],
            "group": gradation["group"], "row": row,
        }

    def render_gradation(self, view):
        """Piirtää astevaihtelurivin: [GD dahkat] → [HD dagan]  hk → g  |  oahpa: ryhmä [hkk III][hk II][g I]"""
        c = self.c
        for widget in self.gradation_frame.winfo_children():
            widget.destroy()
        if view is None:
            return

        def text(t, fg=None, font=None, padx=(0, 6)):
            tk.Label(self.gradation_frame, text=t, fg=fg or c["text"], bg=c["surface"],
                     font=font or self.F(10)).pack(side=tk.LEFT, padx=padx)

        def chip(t, bg, fg, font=None, padx=(0, 6)):
            tk.Label(self.gradation_frame, text=t, bg=bg, fg=fg, font=font or self.F(10, "bold"),
                     padx=7, pady=2).pack(side=tk.LEFT, padx=padx)

        text("Astevaihtelu", fg=c["muted"], font=self.F(9, "bold"), padx=(0, 10))
        if not view:
            text("ei näkyvää astevaihtelua", fg=c["muted"], font=self.F(10, "italic"))
            return

        chip(f"GD  {view['gd']}", c["gd_bg"], c["gd_fg"])
        text("→", fg=c["subtle"])
        chip(f"HD  {view['hd']}", c["hd_bg"], c["hd_fg"], padx=(0, 18))
        text(view["strong"], fg=c["gd_fg"], font=self.F(12, "bold"), padx=(0, 4))
        text("→", fg=c["subtle"], padx=(0, 4))
        text(view["weak"], fg=c["hd_fg"], font=self.F(12, "bold"), padx=(0, 18))

        text("oahpa:", fg=c["subtle"], font=self.F(9), padx=(0, 4))
        text(view["group"], fg=c["muted"], font=self.F(9), padx=(0, 8))
        # Sama kirjoitusasu voi esiintyä kahdessa asteessa (ss III, ss II); korostetaan vain ensimmäinen
        strong_done = False
        for value, quantity in view["row"]:
            if value == view["strong"] and not strong_done:
                strong_done = True
                chip(f"{value} {quantity}", c["gd_bg"], c["gd_fg"], font=self.F(9, "bold"), padx=(0, 3))
            elif value == view["weak"]:
                chip(f"{value} {quantity}", c["hd_bg"], c["hd_fg"], font=self.F(9, "bold"), padx=(0, 3))
            else:
                chip(f"{value} {quantity}", c["chip"], c["muted"], font=self.F(9), padx=(0, 3))

    # --- Taivutustaulukko ---

    def setup_table_tags(self):
        c, t = self.c, self.table
        t.tag_configure("header", font=self.F(9, "bold"), foreground=c["muted"])
        t.tag_configure("section", font=self.F(10, "bold"), foreground=c["accent"],
                        background=c["section"], spacing1=10, spacing3=6)
        t.tag_configure("odd", background=c["surface_alt"])
        t.tag_configure("label", font=self.F(10, "bold"), foreground=c["muted"])
        t.tag_configure("muted", foreground=c["muted"])
        t.tag_configure("form", foreground=c["text"])
        t.tag_configure("gd", foreground=c["gd_fg"])
        t.tag_configure("hd", foreground=c["hd_fg"])
        t.tag_configure("legend", font=self.F(9), foreground=c["muted"], spacing3=8)
        t.tag_configure("legend_gd", font=self.F(9, "bold"), foreground=c["gd_fg"])
        t.tag_configure("legend_hd", font=self.F(9, "bold"), foreground=c["hd_fg"])
        t.tag_raise("sel")

    def render_table(self, rows, legend):
        """rows: [(laji, [solu, ...])], laji = "header" | "section" | "row".
        Solu on lista (teksti, tagi) -pareja tai None; datasolussa lisäksi kuunneltava ja kopioitava teksti:
        {"segments": [...], "speak": "mun dagan", "copy": "dagan"}."""
        t = self.table
        bold = tkfont.Font(family=self.font, size=10, weight="bold")
        normal = tkfont.Font(family=self.font, size=10)

        # Sarakeleveydet pisimmän solun mukaan, jotta sarakkeet pysyvät linjassa
        widths = []
        for kind, cells in rows:
            for i, cell in enumerate(cells):
                segments = cell["segments"] if isinstance(cell, dict) else (cell or [])
                font = bold if kind != "row" or i == 0 else normal
                w = sum(font.measure(text) for text, _ in segments)
                if kind == "section" and i > 0:
                    w = 0  # väliotsikko saa jatkua seuraavan sarakkeen puolelle
                while len(widths) <= i:
                    widths.append(0)
                widths[i] = max(widths[i], w)
        tabs, x = [], 0
        for i, w in enumerate(widths[:-1]):
            x += max(w, 70 if i == 0 else 130) + 34
            tabs.append(x)

        t.configure(state=tk.NORMAL, tabs=tuple(tabs) or ("4c",))
        t.delete("1.0", tk.END)
        for tag in [tag for tag in t.tag_names() if tag.startswith("cell")]:
            t.tag_delete(tag)
        self.cells = {}

        if legend:
            t.insert(tk.END, "Aste:  ", "legend")
            t.insert(tk.END, "vihreä = GD", "legend_gd")
            t.insert(tk.END, " vahva aste     ", "legend")
            t.insert(tk.END, "oranssi = HD", "legend_hd")
            t.insert(tk.END, " heikko aste\n", "legend")

        data_row = 0
        for kind, cells in rows:
            start = t.index("end-1c")
            for i, cell in enumerate(cells):
                if i > 0:
                    t.insert(tk.END, "\t")
                if isinstance(cell, dict):
                    cell_tag = f"cell{len(self.cells)}"
                    self.cells[cell_tag] = cell
                    for text, tag in cell["segments"]:
                        t.insert(tk.END, text, (tag, cell_tag))
                else:
                    for text, tag in cell or []:
                        t.insert(tk.END, text, tag)
            t.insert(tk.END, "\n")
            if kind == "row":
                if data_row % 2:
                    t.tag_add("odd", start, "end-1c")
                data_row += 1
            else:
                t.tag_add(kind, start, "end-1c")
                data_row = 0
        t.configure(state=tk.DISABLED)
        t.yview_moveto(0)
        t.xview_moveto(0)

    def populate_tables(self, pos, lemma, paradigm):
        pos_upper = pos.upper()
        show_grade = self.show_grade.get()
        legend = show_grade and any(self.grades.values())

        def pairs(*tags):
            # [(tagi, muoto), ...] annetuista tageista, sama muoto vain kerran (Gen/Akk: viesu)
            result, seen = [], set()
            for tag in tags:
                for v in paradigm.get(tag, []):
                    if v not in seen:
                        seen.add(v)
                        result.append((tag, v))
            return result

        def cell(items, prefix=""):
            """Muotosolu: pronomini/kieltoverbi harmaana, muodot asteen värillä, rinnakkaismuodot kauttaviivalla."""
            if not items:
                return [("-", "muted")]
            segments = [(prefix + " ", "muted")] if prefix else []
            for k, (tag, value) in enumerate(items):
                if k:
                    segments.append((" / ", "muted"))
                grade = self.grades.get((tag, value)) if show_grade else None
                segments.append((value, {"GD": "gd", "HD": "hd"}.get(grade, "form")))
            values = [v for _, v in items]
            return {
                "segments": segments,
                "speak": ", ".join(f"{prefix} {v}".strip() for v in values),
                "copy": " / ".join(values),
            }

        def label(text):
            return [(text, "label")]

        def header(*texts):
            return ("header", [[(t, "header")] for t in texts])

        def section(*texts):
            return ("section", [[(t, "section")] if t else None for t in texts])

        rows = []
        if not paradigm and pos_upper not in UNINFLECTED_POS:
            rows.append(("row", [label("Ei taivutusmuotoja"), [(lemma, "form")]]))
            rows.append(("row", [None, [("FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.", "muted")]]))
            self.render_table(rows, False)
            self.populate_raw(paradigm, lemma)
            return

        if pos_upper == "V":
            rows.append(header("", "Myönteinen", "Kielteinen", "Myönteinen", "Kielteinen"))
            rows.append(section("Indikatiivi", "preesens", "", "preteriti", ""))
            for p in PERSONS:
                pron = PRONOUNS[p]
                rows.append(("row", [label(p),
                                     cell(pairs(f"Ind+Prs+{p}"), pron),
                                     cell(pairs("Ind+Prs+ConNeg"), f"{pron} {NEG_AUX[p]}"),
                                     cell(pairs(f"Ind+Prt+{p}"), pron),
                                     cell(pairs("Ind+Prt+ConNeg"), f"{pron} {NEG_AUX[p]}")]))
            rows.append(section("", "Konditionaali", "", "Potentiaali", ""))
            for p in PERSONS:
                pron = PRONOUNS[p]
                rows.append(("row", [label(p),
                                     cell(pairs(f"Cond+Prs+{p}"), pron),
                                     cell(pairs("Cond+Prs+ConNeg"), f"{pron} {NEG_AUX[p]}"),
                                     cell(pairs(f"Pot+Prs+{p}"), pron),
                                     cell(pairs("Pot+Prs+ConNeg"), f"{pron} {NEG_AUX[p]}")]))
            rows.append(section("", "Imperatiivi"))
            for p in PERSONS:
                rows.append(("row", [label(p), cell(pairs(f"Imprt+{p}")),
                                     cell(pairs("Imprt+ConNeg"), NEG_AUX_IMPRT[p])]))
            rows.append(section("", "Nominaalimuodot"))
            for name, tag in VERB_NONFINITE_ROWS:
                # Rinnakkaismuodot (gerundilla jopa 6) kaksittain sarakkeisiin, ettei taulukko leviä
                items = pairs(tag)
                chunks = [items[i:i + 2] for i in range(0, len(items), 2)][:4] or [[]]
                rows.append(("row", [label(name)] + [cell(chunk) for chunk in chunks]))

        elif pos_upper in UNINFLECTED_POS:
            rows.append(header("", "Perusmuoto"))
            rows.append(("row", [label("Taipumaton"), cell([("", lemma)])]))

        elif "Sg+Nom" not in paradigm and "Pl+Nom" not in paradigm and "Nom" in paradigm:
            # Persoona- ja refleksiivipronominit: luku ja persoona kuuluvat jo perusmuotoon
            rows.append(header("Sijamuoto", "Muoto"))
            for case_name, cases in CASE_ROWS + [("Ess", ["Ess"])]:
                rows.append(("row", [label(case_name), cell(pairs(*cases))]))

        else:
            # Substantiivit, adjektiivit, numeraalit ja muut pronominit
            # ol. = ovttaidlohku (yksikkö), ml. = máŋggaidlohku (monikko)
            rows.append(header("Sijamuoto", "ol. (yksikkö)", "ml. (monikko)"))
            if "Attr" in paradigm:
                rows.append(("row", [label("Attr"), cell(pairs("Attr"))]))
            for case_name, cases in CASE_ROWS:
                rows.append(("row", [label(case_name),
                                     cell(pairs(*[f"Sg+{c}" for c in cases])),
                                     cell(pairs(*[f"Pl+{c}" for c in cases]))]))
            rows.append(("row", [label("Ess"), cell(pairs("Ess"))]))

            if pos_upper == "A" and any(t.startswith(("Comp", "Superl")) for t in paradigm):
                rows.append(section("Vertailumuodot", "predikatiivi", "attribuutti"))
                rows.append(("row", [label("Komparatiivi"), cell(pairs("Comp+Sg+Nom")), cell(pairs("Comp+Attr"))]))
                rows.append(("row", [label("Superlatiivi"), cell(pairs("Superl+Sg+Nom")), cell(pairs("Superl+Attr"))]))

        self.render_table(rows, legend)
        self.populate_raw(paradigm, lemma)

    def populate_raw(self, paradigm, lemma):
        t = self.raw_text
        show_grade = self.show_grade.get()
        t.configure(state=tk.NORMAL)
        t.delete("1.0", tk.END)
        if not paradigm:
            t.insert(tk.END, lemma)
        for tag, surfaces in paradigm.items():
            t.insert(tk.END, f"{tag:28}", "muted")
            for k, surface in enumerate(surfaces):
                if k:
                    t.insert(tk.END, ", ")
                grade = self.grades.get((tag, surface)) if show_grade else None
                t.insert(tk.END, surface, {"GD": "gd", "HD": "hd"}.get(grade, ()))
                if grade:
                    t.insert(tk.END, f" {grade}", "muted")
            t.insert(tk.END, "\n")
        t.configure(state=tk.DISABLED)

    def clear_tables(self):
        for text in (self.table, self.raw_text, self.meanings_text):
            text.configure(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            text.configure(state=tk.DISABLED)
        self.cells = {}

    def cell_at(self, event):
        index = self.table.index(f"@{event.x},{event.y}")
        for tag in self.table.tag_names(index):
            if tag in self.cells:
                return self.cells[tag]
        return None

    def on_table_double_click(self, event):
        """Kaksoisnapsautus muodossa ääntää sen (esim. "mun dagan")."""
        cell = self.cell_at(event)
        if cell:
            self.speak(cell["speak"])
        return "break"

    def on_table_right_click(self, event):
        cell = self.cell_at(event)
        if not cell:
            return
        c = self.c
        menu = tk.Menu(self.root, tearoff=0, bg=c["surface"], fg=c["text"], activebackground=c["accent"],
                       activeforeground=c["accent_text"], font=self.F(10), bd=1)
        menu.add_command(label=f"Kuuntele: {cell['speak']}", command=lambda: self.speak(cell["speak"]))
        menu.add_command(label=f"Kopioi: {cell['copy']}", command=lambda: self.copy_text(cell["copy"]))
        menu.add_command(label=f"Kopioi pronominin kanssa: {cell['speak']}",
                         command=lambda: self.copy_text(cell["speak"]))
        menu.tk_popup(event.x_root, event.y_root)

    def copy_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    # --- Merkitykset ---

    def setup_meanings_tags(self):
        c, t = self.c, self.meanings_text
        t.tag_configure("title", font=self.F(15, "bold"), spacing3=4)
        t.tag_configure("notes", font=self.F(10, "italic"), foreground=c["muted"], spacing3=6)
        t.tag_configure("nr", font=self.F(11, "bold"), foreground=c["accent"], spacing1=14)
        t.tag_configure("trans", font=self.F(11, "bold"), spacing1=14)
        t.tag_configure("expl", font=self.F(11, "italic"))
        t.tag_configure("restr", font=self.F(10, "italic"), foreground=c["muted"])
        t.tag_configure("label", font=self.F(9), foreground=c["muted"], background=c["chip"])
        t.tag_configure("ex_sme", font=self.F(10), lmargin1=28, lmargin2=28, spacing1=6)
        t.tag_configure("ex_fin", font=self.F(10), foreground=c["muted"], lmargin1=28, lmargin2=28)
        t.tag_configure("src", font=self.F(8), foreground=c["subtle"])
        t.tag_configure("ex_missing", font=self.F(9, "italic"), foreground=c["subtle"], lmargin1=28, lmargin2=28)

    def populate_meanings(self, lemma, pos, meanings, notes):
        t = self.meanings_text
        t.configure(state=tk.NORMAL)
        t.delete("1.0", tk.END)
        t.insert(tk.END, f"{lemma}  ", "title")
        t.insert(tk.END, f"{word_class_label(pos)}\n", "notes")
        if notes:
            t.insert(tk.END, notes + "\n", "notes")

        numbered = len(meanings) > 1
        for meaning in meanings:
            t.insert(tk.END, "\n")
            if numbered:
                t.insert(tk.END, f"{meaning['nr']}.  ", "nr")
            if meaning["translations"]:
                t.insert(tk.END, meaning["translations"], "trans")
            if meaning["explanations"]:
                sep = "  " if meaning["translations"] else ""
                t.insert(tk.END, f"{sep}({meaning['explanations']})", "expl")
            if meaning["restrictions"]:
                t.insert(tk.END, f"  – {meaning['restrictions']}", "restr")
            labels = [l for l in (meaning["labels"] or "").split(", ") if l]
            labels += [f"käytössä {GEO_NAMES.get(g, g)} ({g})" for g in (meaning["geo"] or "").split(",") if g]
            for lbl in labels:
                t.insert(tk.END, "  ")
                t.insert(tk.END, f" {lbl} ", "label")
            t.insert(tk.END, "\n")
            for sme, fin, source in meaning["examples"]:
                t.insert(tk.END, f"{sme}\n", "ex_sme")
                if fin:
                    t.insert(tk.END, f"{fin}", "ex_fin")
                else:
                    # Lähteessä on suomennoksen paikalla vain täyttämätön _FIN_-merkintä
                    t.insert(tk.END, "(ei suomennosta lähteessä)", "ex_missing")
                if source:
                    t.insert(tk.END, f"   ({source})", "src")
                t.insert(tk.END, "\n")

        if not meanings:
            t.insert(tk.END, "\nEi merkitystietoja.", "notes")
        t.configure(state=tk.DISABLED)

        examples = sum(len(m["examples"]) for m in meanings)
        tab_text = f"Merkitykset ({len(meanings)})"
        if examples:
            tab_text += f" ja esimerkit ({examples})"
        self.notebook.tab(self.tab_meanings, text=tab_text)

    # --- Ääntäminen ja Giellatekno ---

    def speak_lemma(self):
        if self.current_results:
            self.speak(self.current_results[self.selected_idx][1])

    def speak(self, text):
        """Hakee äänen taustalla (3–5 s ensimmäisellä kerralla, sitten välimuistista) ja soittaa sen."""
        text = text.strip()
        if not text:
            return
        voice = self.voice.get()
        button = self.speak_button
        button.config(text=" Haetaan…", state=tk.DISABLED)

        def done(path, error):
            if button.winfo_exists():
                button.config(text=" Kuuntele", state=tk.NORMAL)
            if error:
                messagebox.showwarning(
                    "Ääntäminen",
                    f"Ääntämistä ei saatu sanalle \"{text}\".\n\n{error}\n\n"
                    "Ääni haetaan Divvunin palvelusta (api-giellalt.uit.no), joten ensimmäinen "
                    "kuuntelu vaatii verkkoyhteyden."
                )
                return
            try:
                tts.play(path)
            except Exception as e:
                messagebox.showwarning("Ääntäminen", f"Äänen toisto epäonnistui: {e}")

        def worker():
            try:
                path, error = tts.fetch(text, voice), None
            except Exception as e:
                path, error = None, e
            self.root.after(0, done, path, error)

        threading.Thread(target=worker, daemon=True).start()

    def open_giellatekno(self):
        if not self.current_results:
            return
        _, lemma, pos, _, _ = self.current_results[self.selected_idx]
        webbrowser.open(giellatekno_url(lemma, pos))

    # --- Tietoa ---

    def show_about(self):
        c = self.c
        about_win = tk.Toplevel(self.root)
        about_win.title("Tietoa ohjelmasta")
        about_win.geometry("540x500")
        about_win.configure(bg=c["surface"])
        about_win.resizable(False, False)
        about_win.transient(self.root)

        tk.Label(about_win, text="Sátni FST", font=self.F(16, "bold"), bg=c["surface"],
                 fg=c["text"]).pack(pady=(22, 0))
        tk.Label(about_win, text=f"Versio {VERSION}", font=self.F(9), bg=c["surface"],
                 fg=c["muted"]).pack(pady=(0, 12))

        info_text = (
            "Pohjoissaamen taivutin ja sanakirja, joka perustuu avoimeen lähdekoodiin.\n\n"
            "Sanakirjadata ja kieliteknologiapohja ovat peräisin Giellateknolta ja Divvunilta. "
            "Kielidata ja taivutussäännöt on laskettu ja tuotettu Giellateknon / Divvunin "
            "avoimilla FST-malleilla ja XML-sanakirjoilla.\n\n"
            "Ääntäminen: Divvunin ja Giellateknon puhesynteesi (UiT Norjan arktinen yliopisto), "
            "äänet Biret, Máhtte ja Sunná. Äänet haetaan palvelusta api-giellalt.uit.no samaan tapaan "
            "kuin sátni.org-sivustolla.\n\n"
            "Ohjelma on tuore ja voi sisältää huomattavia virheitä, eikä sille ole virallista tukea.\n\n"
            "Tekijä: Juha Somby"
        )
        tk.Label(about_win, text=info_text, font=self.F(10), bg=c["surface"], fg=c["text"],
                 justify=tk.LEFT, wraplength=470).pack(padx=30, pady=5)

        email_frame = tk.Frame(about_win, bg=c["surface"])
        email_frame.pack(pady=8)
        tk.Label(email_frame, text="Virheilmoitukset ja palaute: ", font=self.F(10), bg=c["surface"],
                 fg=c["muted"]).pack(side=tk.LEFT)
        email_link = tk.Label(email_frame, text="satni@somby.fi", font=self.F(10, "underline"),
                              bg=c["surface"], fg=c["accent"], cursor="hand2")
        email_link.pack(side=tk.LEFT)
        email_link.bind("<Button-1>", lambda e: webbrowser.open("mailto:satni@somby.fi"))

        self.flat_button(about_win, "Sulje", about_win.destroy, c["chip"], c["chip_text"], c["chip_hover"],
                         padx=22, pady=6).pack(pady=16)


def self_test_tts():
    """--testaa-aani: hakee äänen ilman välimuistia ja ilman toistoa (HTTPS- ja varmennetarkistus)."""
    import tempfile
    os.environ["XDG_CACHE_HOME"] = tempfile.mkdtemp()
    os.environ["LOCALAPPDATA"] = os.environ["XDG_CACHE_HOME"]
    try:
        path = tts.fetch("bures", tts.DEFAULT_VOICE)
        print(f"OK: ääni haettu ({os.path.getsize(path)} tavua)")
        return 0
    except Exception as e:
        print(f"VIRHE: {e}")
        return 1


if __name__ == "__main__":
    if "--testaa-aani" in sys.argv:
        sys.exit(self_test_tts())
    ui_theme.enable_windows_dpi_awareness()
    # className näkyy ikkunanhallinnalle (WM_CLASS) ja vastaa AppImagen .desktop-tiedostoa
    root = tk.Tk(className="satni-fst")
    app = SatniGUI(root)
    root.mainloop()
