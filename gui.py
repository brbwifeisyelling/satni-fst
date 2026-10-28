#!/usr/bin/env python3
import os
import sys
import re
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont, ImageTk

import tts

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
            "SELECT meaning_nr, sme, fin, source FROM examples WHERE word_id = ? ORDER BY rowid", (word_id,)
        ):
            examples.setdefault(nr, []).append((sme, fin, source))
        for row in cursor.execute(
            "SELECT nr, translations, explanations, restrictions, labels, geo FROM meanings WHERE word_id = ? ORDER BY nr",
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


def make_giellatekno_icon(size=20):
    """Pieni "gt"-merkki napin kuvakkeeksi (piirretään koodissa, ei erillistä kuvatiedostoa)."""
    scale = 4  # piirretään isona ja pienennetään, jotta reunat ovat pehmeät
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=5 * scale, fill="#9f1239")
    try:
        font = ImageFont.load_default(size=12 * scale)
    except TypeError:  # vanha Pillow ilman koon valintaa
        font = ImageFont.load_default()
    draw.text((big / 2, big / 2 + scale), "gt", fill="#ffffff", font=font, anchor="mm")
    return ImageTk.PhotoImage(img.resize((size, size), Image.Resampling.LANCZOS))

# Sanakirjan aluekoodit (<geo>): missä maassa sana on käytössä
GEO_NAMES = {"N": "Norjassa", "S": "Suomessa", "R": "Ruotsissa"}

POS_NAMES = {
    "V": "Verbi",
    "N": "Substantiivi (Yleisnimi)",
    "A": "Adjektiivi",
    "ADV": "Adverbi",
    "PRON": "Pronomini",
    "NUM": "Numeraali (Lukusana)",
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

def analyze_word_behavior(lemma, pos, subtype=""):
    info = [POS_NAMES.get(pos.upper(), f"Sanaluokka ({pos})")]
    if subtype:
        info.append(SUBTYPE_NAMES.get(subtype, subtype))
    return " | ".join(info)


# --- GRAAFINEN KÄYTTÖLIITTYMÄ (GUI) ---

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

# Astevaihtelun värit: GD = gievrras dássi (vahva aste), HD = headju dássi (heikko aste)
GD_BG, GD_FG = "#dcfce7", "#166534"
HD_BG, HD_FG = "#ffedd5", "#9a3412"

NONFINITE_NAMES = {name for name, _ in VERB_NONFINITE_ROWS}

UNINFLECTED_POS = ["ADV", "CC", "CS", "INTERJ", "PCLE", "PO", "PR", "CMP", "MWE"]

class SatniGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sátni FST - Pohjoissaamen avoin sanakirja ja taivutin")
        self.root.geometry("1250x820")
        self.root.configure(bg="#f8fafc")

        self.header_frame = tk.Frame(root, bg="#ffffff", height=70, relief=tk.FLAT, bd=1)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)

        self.title_label = tk.Label(
            self.header_frame, 
            text="Sátni FST", 
            font=("Sans", 18, "bold"), 
            fg="#0f172a", 
            bg="#ffffff"
        )
        self.title_label.pack(side=tk.LEFT, padx=20, pady=15)

        self.subtitle_label = tk.Label(
            self.header_frame, 
            text="Pohjoissaamen avoin sanakirja ja taivutusgeneraattori", 
            font=("Sans", 10), 
            fg="#64748b", 
            bg="#ffffff"
        )
        self.subtitle_label.pack(side=tk.LEFT, pady=20)

        self.flag_label = tk.Label(self.header_frame, bg="#ffffff")
        self.flag_label.pack(side=tk.RIGHT, padx=20)
        self.load_sami_flag_image()

        self.color_bar = tk.Frame(root, height=6, bg="#f8fafc")
        self.color_bar.pack(fill=tk.X, side=tk.TOP)
        
        colors = ["#e11d48", "#facc15", "#2563eb", "#16a34a"]
        for c in colors:
            f = tk.Frame(self.color_bar, bg=c, height=6)
            f.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_frame = tk.Frame(root, bg="#f8fafc", height=80)
        self.search_frame.pack(fill=tk.X, padx=20, pady=15)

        self.search_label = tk.Label(
            self.search_frame, 
            text="Hae (suomi tai saame):", 
            font=("Sans", 11, "bold"), 
            fg="#0f172a", 
            bg="#f8fafc"
        )
        self.search_label.pack(side=tk.LEFT, padx=(0, 10))

        self.search_entry = tk.Entry(
            self.search_frame, 
            font=("Sans", 12), 
            width=25,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief=tk.SOLID,
            bd=1
        )
        self.search_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        self.search_entry.bind("<Return>", lambda event: self.perform_search())

        self.search_button = tk.Button(
            self.search_frame, 
            text="Hae", 
            font=("Sans", 10, "bold"), 
            bg="#2563eb", 
            fg="#ffffff", 
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=15, 
            pady=4,
            command=self.perform_search
        )
        self.search_button.pack(side=tk.LEFT, padx=10)

        self.info_button = tk.Button(
            self.search_frame, 
            text="i Tietoa", 
            font=("Sans", 10), 
            bg="#e2e8f0", 
            fg="#0f172a", 
            relief=tk.FLAT,
            padx=10, 
            pady=4,
            command=self.show_about
        )
        self.info_button.pack(side=tk.RIGHT, padx=5)

        # Astevaihtelu: GD = gievrras dássi (vahva aste), HD = headju dássi (heikko aste)
        self.show_grade = tk.BooleanVar(value=True)
        self.grade_check = tk.Checkbutton(
            self.search_frame,
            text="Näytä aste (GD/HD)",
            variable=self.show_grade,
            font=("Sans", 10),
            bg="#f8fafc",
            fg="#0f172a",
            activebackground="#f8fafc",
            highlightthickness=0,
            command=self.refresh_selected
        )
        self.grade_check.pack(side=tk.LEFT, padx=10)

        # Ääntämisen ääni (Divvunin puhesynteesi)
        tk.Label(self.search_frame, text="Ääni:", font=("Sans", 10), bg="#f8fafc", fg="#0f172a").pack(side=tk.LEFT, padx=(10, 4))
        self.voice = tk.StringVar(value=tts.DEFAULT_VOICE)
        self.voice_menu = ttk.Combobox(
            self.search_frame, textvariable=self.voice, values=list(tts.VOICES),
            state="readonly", width=8, font=("Sans", 10)
        )
        self.voice_menu.pack(side=tk.LEFT)

        self.selection_bar_frame = tk.Frame(root, bg="#e2e8f0")
        self.selection_bar_frame.pack(fill=tk.X, padx=20, pady=5)

        self.selection_label = tk.Label(
            self.selection_bar_frame, 
            text="Valitse:", 
            font=("Sans", 9, "bold"), 
            fg="#334155", 
            bg="#e2e8f0"
        )
        self.selection_label.pack(side=tk.LEFT, anchor="n", padx=(15, 10), pady=8)

        self.buttons_inner_frame = tk.Frame(self.selection_bar_frame, bg="#e2e8f0")
        self.buttons_inner_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)
        # Hakutulosnapit rivitetään ikkunan leveyden mukaan, myös ikkunan kokoa muutettaessa
        self.buttons_inner_frame.bind("<Configure>", lambda e: self.layout_result_buttons())

        self.meta_frame = tk.Frame(root, bg="#ffffff", height=65, relief=tk.SOLID, bd=1)
        self.meta_frame.pack(fill=tk.X, padx=20, pady=5)

        # Kuuntele: valitun sanan perusmuoto puhesynteesillä
        self.speaker_icon = make_speaker_icon()
        self.speak_button = tk.Button(
            self.meta_frame,
            text=" Kuuntele",
            image=self.speaker_icon,
            compound=tk.LEFT,
            font=("Sans", 9, "bold"),
            bg="#eff6ff",
            fg="#1d4ed8",
            activebackground="#dbeafe",
            activeforeground="#1d4ed8",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.speak_lemma
        )

        # Avaa valitun sanan taivutuksen Giellateknon sivulla oletusselaimessa
        self.giellatekno_icon = make_giellatekno_icon()
        self.giellatekno_button = tk.Button(
            self.meta_frame,
            text=" Giellatekno ↗",
            image=self.giellatekno_icon,
            compound=tk.LEFT,
            font=("Sans", 9, "bold"),
            bg="#fff1f2",
            fg="#9f1239",
            activebackground="#ffe4e6",
            activeforeground="#9f1239",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.open_giellatekno
        )
        
        self.meta_label = tk.Label(
            self.meta_frame, 
            text="Hae sana aloittaaksesi.", 
            font=("Sans", 10, "bold"), 
            fg="#0f172a", 
            bg="#ffffff",
            anchor="w"
        )
        self.meta_label.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 2))

        # Astevaihtelu (oahpa.no/sme/gramm/tabell_stadieveksling.html), esim. dahkat (GD) → dagan (HD)
        self.gradation_frame = tk.Frame(self.meta_frame, bg="#ffffff")
        self.gradation_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(2, 4))

        self.behavior_label = tk.Label(
            self.meta_frame, 
            text="", 
            font=("Sans", 9, "italic"), 
            fg="#64748b", 
            bg="#ffffff",
            anchor="w"
        )
        self.behavior_label.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 8))

        self.notebook_frame = tk.Frame(root, bg="#f8fafc")
        self.notebook_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TNotebook', background='#f8fafc', borderwidth=0)
        self.style.configure('TNotebook.Tab', font=('Sans', 10, 'bold'), padding=[12, 8], background='#e2e8f0', foreground='#334155')
        self.style.map('TNotebook.Tab', background=[('selected', '#ffffff')], foreground=[('selected', '#2563eb')])

        self.notebook = ttk.Notebook(self.notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_table = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab_table, text=" Taulukkonäkymä ")

        self.tab_meanings = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab_meanings, text=" Merkitykset ja esimerkit ")

        self.tab_raw = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab_raw, text=" Muut taivutukset / Raakateksti ")

        self.setup_table_view()
        self.setup_meanings_view()
        self.setup_raw_view()

        self.current_results = []
        self.last_query = ""
        self.selected_idx = 0
        self.grades = {}

    def load_sami_flag_image(self):
        possible_paths = [
            os.path.join(SCRIPT_DIR, "Sami_flag.svg.webp"),
            os.path.join(SCRIPT_DIR, "assets", "Sami_flag.svg.webp"),
            os.path.join(SCRIPT_DIR, "img", "Sami_flag.svg.webp"),
            os.path.join(SCRIPT_DIR, "sami_flag.png")
        ]
        
        flag_path = None
        for p in possible_paths:
            if os.path.exists(p):
                flag_path = p
                break

        if flag_path:
            try:
                pil_img = Image.open(flag_path)
                pil_img = pil_img.resize((50, 32), Image.Resampling.LANCZOS)
                self.flag_img = ImageTk.PhotoImage(pil_img)
                self.flag_label.config(image=self.flag_img)
            except Exception as e:
                print(f"Lipun latausvirhe: {e}")
                self.flag_label.config(text="[Lippu]", fg="#64748b")
        else:
            self.flag_label.config(text="[Lippua ei löydy]", fg="#64748b", font=("Sans", 8))

    def setup_table_view(self):
        table_container = tk.Frame(self.tab_table, bg="#ffffff")
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(table_container, columns=("col1", "col2", "col3", "col4", "col5"), show="headings", selectmode="browse")
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Sans", 10, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("Treeview", font=("Sans", 10), rowheight=26, background="#ffffff", foreground="#0f172a", fieldbackground="#ffffff")

        self.tree.heading("col1", text="Sijamuoto / Käyttö")
        self.tree.heading("col2", text="Yksikkö (Sg)")
        self.tree.heading("col3", text="Monikko (Pl)")
        self.tree.heading("col4", text="")
        self.tree.heading("col5", text="")

        self.tree.column("col1", width=200, anchor="w")
        self.tree.column("col2", width=300, anchor="w")
        self.tree.column("col3", width=300, anchor="w")
        self.tree.column("col4", width=0, stretch=False)
        self.tree.column("col5", width=0, stretch=False)

        scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        hint = tk.Label(
            self.tab_table, text="Kaksoisnapsauta muotoa kuullaksesi sen ääntämisen.",
            font=("Sans", 9, "italic"), fg="#64748b", bg="#ffffff", anchor="w"
        )
        hint.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 6))

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self.on_table_double_click)

    def setup_meanings_view(self):
        container = tk.Frame(self.tab_meanings, bg="#ffffff")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.meanings_text = tk.Text(
            container,
            font=("Sans", 11),
            bg="#ffffff",
            fg="#0f172a",
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=12,
            pady=8,
            spacing1=2,
            cursor="arrow"
        )
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.meanings_text.yview)
        self.meanings_text.configure(yscrollcommand=scrollbar.set)
        self.meanings_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        t = self.meanings_text
        t.tag_configure("title", font=("Sans", 14, "bold"), spacing3=6)
        t.tag_configure("notes", font=("Sans", 10, "italic"), foreground="#64748b", spacing3=8)
        t.tag_configure("nr", font=("Sans", 11, "bold"), foreground="#2563eb", spacing1=12)
        t.tag_configure("trans", font=("Sans", 11, "bold"), spacing1=12)
        t.tag_configure("expl", font=("Sans", 11, "italic"))
        t.tag_configure("restr", font=("Sans", 10, "italic"), foreground="#475569")
        t.tag_configure("label", font=("Sans", 9), foreground="#64748b", background="#f1f5f9")
        t.tag_configure("ex_sme", font=("Sans", 10), lmargin1=28, lmargin2=28, spacing1=4)
        t.tag_configure("ex_fin", font=("Sans", 10), foreground="#64748b", lmargin1=28, lmargin2=28)
        t.tag_configure("src", font=("Sans", 8), foreground="#94a3b8")
        t.configure(state=tk.DISABLED)

    def populate_meanings(self, lemma, pos, meanings, notes):
        t = self.meanings_text
        t.configure(state=tk.NORMAL)
        t.delete("1.0", tk.END)
        t.insert(tk.END, f"{lemma}  ", "title")
        t.insert(tk.END, f"({pos})\n", "notes")
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
            for label in labels:
                t.insert(tk.END, "  ")
                t.insert(tk.END, f" {label} ", "label")
            t.insert(tk.END, "\n")
            for sme, fin, source in meaning["examples"]:
                t.insert(tk.END, f"{sme}\n", "ex_sme")
                if fin:
                    t.insert(tk.END, f"{fin}", "ex_fin")
                if source:
                    t.insert(tk.END, f"   ({source})", "src")
                if fin or source:
                    t.insert(tk.END, "\n")

        if not meanings:
            t.insert(tk.END, "\nEi merkitystietoja.", "notes")
        t.configure(state=tk.DISABLED)

        examples = sum(len(m["examples"]) for m in meanings)
        tab_text = f" Merkitykset ({len(meanings)})"
        if examples:
            tab_text += f" ja esimerkit ({examples})"
        self.notebook.tab(self.tab_meanings, text=tab_text + " ")

    def setup_raw_view(self):
        raw_container = tk.Frame(self.tab_raw, bg="#ffffff")
        raw_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.raw_text = tk.Text(
            raw_container, 
            font=("Monospace", 10), 
            bg="#f8fafc", 
            fg="#0f172a", 
            insertbackground="#0f172a",
            relief=tk.FLAT
        )
        scrollbar = ttk.Scrollbar(raw_container, orient=tk.VERTICAL, command=self.raw_text.yview)
        self.raw_text.configure(yscrollcommand=scrollbar.set)

        self.raw_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return

        self.last_query = query
        self.current_results = query_database(query)
        
        for widget in self.buttons_inner_frame.winfo_children():
            widget.destroy()

        if not self.current_results:
            self.meta_label.config(text=f"Ei osumia haulle: '{query}'")
            self.giellatekno_button.place_forget()
            self.speak_button.place_forget()
            self.render_gradation(None)
            self.behavior_label.config(text="")
            self.clear_tables()
            return

        for idx, (word_id, lemma, pos, subtype, trans) in enumerate(self.current_results):
            # Karsitaan käyttöliittymän chip-napeissa näkyviä käännöksiä tarvittaessa siistiksi
            short_trans = ""
            if trans:
                trans_parts = [p.strip() for p in trans.split(",")]
                short_trans = ", ".join(trans_parts[:2])

            pos_label = f"{pos} {subtype}" if subtype else pos
            btn_text = f"{lemma} ({pos_label})" + (f" – {short_trans}" if short_trans else "")
            btn = tk.Button(
                self.buttons_inner_frame,
                text=btn_text,
                font=("Sans", 9, "bold"),
                bg="#2563eb" if idx == 0 else "#cbd5e1",
                fg="#ffffff" if idx == 0 else "#0f172a",
                relief=tk.FLAT,
                padx=10,
                pady=3,
                command=lambda i=idx: self.select_word_option(i)
            )

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

    def refresh_selected(self):
        if self.current_results:
            self.select_word_option(self.selected_idx)

    def select_word_option(self, selected_idx):
        self.selected_idx = selected_idx
        word_id, lemma, pos, subtype, trans = self.current_results[selected_idx]
        self.giellatekno_button.place(relx=1.0, x=-10, y=6, anchor="ne")
        self.giellatekno_button.lift()  # otsikkorivin label on luotu myöhemmin ja peittäisi napin
        self.root.update_idletasks()
        self.speak_button.place(relx=1.0, x=-18 - self.giellatekno_button.winfo_reqwidth(), y=6, anchor="ne")
        self.speak_button.lift()
        for idx, widget in enumerate(self.buttons_inner_frame.winfo_children()):
            if idx == selected_idx:
                widget.config(bg="#2563eb", fg="#ffffff")
            else:
                widget.config(bg="#cbd5e1", fg="#0f172a")

        behavior = analyze_word_behavior(lemma, pos, subtype)
        
        meanings, notes = get_word_details(word_id)

        # Otsikkoon ensimmäinen merkitys käyttörajoituksineen (esim. hyppiä – paksussa lumessa, porosta)
        if meanings:
            first = meanings[0]
            parts = [p.strip() for p in (first["translations"] or first["explanations"] or "").split(",") if p.strip()]
            display_trans = ", ".join(parts[:3])
            if first["restrictions"]:
                display_trans += f" ({first['restrictions']})"
            if len(meanings) > 1:
                display_trans += f"  +{len(meanings) - 1} merkitystä"
        else:
            trans_parts = [p.strip() for p in (trans or "").split(",") if p.strip()]
            display_trans = ", ".join(trans_parts[:2])

        self.meta_label.config(text=f"Saamen perusmuoto: {lemma}  |  Suomeksi: {display_trans if display_trans else '(ei määritetty)'}  |  Sanaluokka: {pos}")
        paradigm, self.grades, gradation = get_paradigms_from_db(word_id)

        info = f"Tyyppi: {behavior}"
        self.render_gradation(self.gradation_view(pos, paradigm, gradation))
        self.populate_meanings(lemma, pos, meanings, notes)

        # Jos haettiin taivutettua muotoa (esim. dagan), kerrotaan sen muoto ja aste
        query = fold(self.last_query)
        matches = []
        for tag, surfaces in paradigm.items():
            for surface in surfaces:
                if fold(surface) == query:
                    grade = self.grades.get((tag, surface))
                    matches.append(f"{tag}" + (f" {grade}" if grade else ""))
        if matches and query != fold(lemma):
            info += f"  |  Haettu muoto {self.last_query}: {', '.join(dict.fromkeys(matches))}"
        self.behavior_label.config(text=info)

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
        """Piirtää astevaihtelurivin: [Astevaihtelu] [GD dahkat] → [HD dagan]  hk → g  |  oahpa: ryhmä [hkk III][hk II][g I]"""
        for widget in self.gradation_frame.winfo_children():
            widget.destroy()
        if view is None:
            return

        def text(t, fg="#0f172a", font=("Sans", 10), padx=(0, 6)):
            tk.Label(self.gradation_frame, text=t, fg=fg, bg="#ffffff", font=font).pack(side=tk.LEFT, padx=padx)

        def chip(t, bg, fg, font=("Sans", 10, "bold"), padx=(0, 6)):
            tk.Label(self.gradation_frame, text=t, bg=bg, fg=fg, font=font, padx=6, pady=1).pack(side=tk.LEFT, padx=padx)

        text("Astevaihtelu:", font=("Sans", 10, "bold"))
        if not view:
            text("ei näkyvää astevaihtelua", fg="#64748b", font=("Sans", 10, "italic"))
            return

        chip(f"GD  {view['gd']}", GD_BG, GD_FG)
        text("→", fg="#64748b")
        chip(f"HD  {view['hd']}", HD_BG, HD_FG, padx=(0, 18))
        text(view["strong"], fg=GD_FG, font=("Sans", 12, "bold"), padx=(0, 4))
        text("→", fg="#64748b", padx=(0, 4))
        text(view["weak"], fg=HD_FG, font=("Sans", 12, "bold"), padx=(0, 18))

        text("oahpa:", fg="#64748b", font=("Sans", 9), padx=(0, 4))
        text(view["group"], fg="#64748b", font=("Sans", 9), padx=(0, 8))
        # Sama kirjoitusasu voi esiintyä kahdessa asteessa (ss III, ss II); korostetaan vain ensimmäinen
        strong_done = False
        for value, quantity in view["row"]:
            if value == view["strong"] and not strong_done:
                strong_done = True
                chip(f"{value} {quantity}", GD_BG, GD_FG, font=("Sans", 9, "bold"), padx=(0, 3))
            elif value == view["weak"]:
                chip(f"{value} {quantity}", HD_BG, HD_FG, font=("Sans", 9, "bold"), padx=(0, 3))
            else:
                chip(f"{value} {quantity}", "#f1f5f9", "#64748b", font=("Sans", 9), padx=(0, 3))

    def set_columns(self, headings_widths):
        for i, col in enumerate(("col1", "col2", "col3", "col4", "col5")):
            if i < len(headings_widths):
                text, width = headings_widths[i]
                self.tree.heading(col, text=text)
                self.tree.column(col, width=width, minwidth=20, stretch=True, anchor="w")
            else:
                self.tree.heading(col, text="")
                self.tree.column(col, width=0, minwidth=0, stretch=False)

    def populate_tables(self, pos, lemma, paradigm):
        for row in self.tree.get_children():
            self.tree.delete(row)

        self.raw_text.delete("1.0", tk.END)
        pos_upper = pos.upper()

        show_grade = self.show_grade.get()

        def mark(tag, surface):
            grade = self.grades.get((tag, surface)) if show_grade else None
            return f"{surface} ({grade})" if grade else surface

        def pairs(*tags):
            # [(tagi, muoto), ...] annetuista tageista, sama muoto vain kerran (Gen/Akk: viesu)
            result, seen = [], set()
            for tag in tags:
                for v in paradigm.get(tag, []):
                    if v not in seen:
                        seen.add(v)
                        result.append((tag, v))
            return result

        def joined(items):
            # Rinnakkaismuodot kauttaviivalla ja yhteinen aste vain kerran: dagalin / dagašin (HD)
            grades = {self.grades.get(item) for item in items} if show_grade else {None}
            if len(grades) == 1:
                grade = grades.pop()
                return " / ".join(v for _, v in items) + (f" ({grade})" if grade else "")
            return " / ".join(mark(tag, v) for tag, v in items)

        def forms(*tags):
            items = pairs(*tags)
            return joined(items) if items else "-"

        def with_pronoun(pronoun, tag, aux=""):
            items = pairs(tag)
            if not items:
                return "-"
            words = " ".join(w for w in (pronoun, aux) if w)
            return f"{words} {joined(items)}" if words else joined(items)

        def section(title, second_title=""):
            # Otsikko sarakkeen 2 kohdalle (ja toinen sarakkeen 4 kohdalle), ettei se katkea kapeaan 1. sarakkeeseen
            self.tree.insert("", tk.END, values=("", title, "", second_title, ""), tags=("section",))

        self.tree.tag_configure("section", background="#e2e8f0", font=("Sans", 10, "bold"))

        if not paradigm and pos_upper not in UNINFLECTED_POS:
            self.set_columns([("Huomio", 200), ("Perusmuoto", 500)])
            self.tree.insert("", tk.END, values=("Ei taivutusmuotoja", lemma))
            self.raw_text.insert(tk.END, "FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.")
            return

        if pos_upper == "V":
            self.set_columns([
                ("Persoona", 60), ("Myönteinen", 300), ("Kielteinen", 230),
                ("Myönteinen", 270), ("Kielteinen", 230),
            ])

            section("Indikatiivi – preesens", "Indikatiivi – preteriti")
            for p in PERSONS:
                pron = PRONOUNS[p]
                self.tree.insert("", tk.END, values=(
                    p,
                    with_pronoun(pron, f"Ind+Prs+{p}"),
                    with_pronoun(pron, "Ind+Prs+ConNeg", NEG_AUX[p]),
                    with_pronoun(pron, f"Ind+Prt+{p}"),
                    with_pronoun(pron, "Ind+Prt+ConNeg", NEG_AUX[p]),
                ))

            section("Konditionaali", "Potentiaali")
            for p in PERSONS:
                pron = PRONOUNS[p]
                self.tree.insert("", tk.END, values=(
                    p,
                    with_pronoun(pron, f"Cond+Prs+{p}"),
                    with_pronoun(pron, "Cond+Prs+ConNeg", NEG_AUX[p]),
                    with_pronoun(pron, f"Pot+Prs+{p}"),
                    with_pronoun(pron, "Pot+Prs+ConNeg", NEG_AUX[p]),
                ))

            section("Imperatiivi")
            for p in PERSONS:
                self.tree.insert("", tk.END, values=(
                    p,
                    forms(f"Imprt+{p}"),
                    with_pronoun("", "Imprt+ConNeg", NEG_AUX_IMPRT[p]),
                    "", "",
                ))

            section("Nominaalimuodot")
            for name, tag in VERB_NONFINITE_ROWS:
                # Nimi leveään 2. sarakkeeseen ja rinnakkaismuodot (gerundilla jopa 6) kaksittain sarakkeisiin 3–5
                items = pairs(tag)
                grades = {self.grades.get(item) for item in items} if show_grade else {None}
                uniform = len(grades) == 1
                chunks = [items[i:i + 2] for i in range(0, len(items), 2)][:3] or [[]]
                cells = [" / ".join(v if uniform else mark(t, v) for t, v in chunk) for chunk in chunks]
                cells[0] = cells[0] or "-"
                if uniform and items:
                    grade = grades.pop()
                    if grade:
                        cells[-1] += f" ({grade})"
                cells += [""] * (3 - len(cells))
                self.tree.insert("", tk.END, values=("", name, *cells))

        elif pos_upper in UNINFLECTED_POS:
            self.set_columns([("Käyttö / Tyyppi", 200), ("Perusmuoto", 500)])
            self.tree.insert("", tk.END, values=("Perusmuoto (taipumaton)", lemma))

        elif "Sg+Nom" not in paradigm and "Pl+Nom" not in paradigm and "Nom" in paradigm:
            # Persoona- ja refleksiivipronominit: luku ja persoona kuuluvat jo perusmuotoon
            self.set_columns([("Sijamuoto", 120), ("Muoto", 500)])
            for case_name, cases in CASE_ROWS + [("Ess", ["Ess"])]:
                self.tree.insert("", tk.END, values=(case_name, forms(*cases)))

        else:
            # Substantiivit, adjektiivit, numeraalit ja muut pronominit
            # ol. = ovttaidlohku (yksikkö), ml. = máŋggaidlohku (monikko)
            self.set_columns([("Sijamuoto", 120), ("ol. (yksikkö)", 340), ("ml. (monikko)", 340)])

            if "Attr" in paradigm:
                self.tree.insert("", tk.END, values=("Attr", forms("Attr"), ""))

            for case_name, cases in CASE_ROWS:
                self.tree.insert("", tk.END, values=(
                    case_name,
                    forms(*[f"Sg+{c}" for c in cases]),
                    forms(*[f"Pl+{c}" for c in cases]),
                ))
            self.tree.insert("", tk.END, values=("Ess", forms("Ess"), ""))

            if pos_upper == "A" and any(t.startswith(("Comp", "Superl")) for t in paradigm):
                section("Vertailumuodot")
                self.tree.insert("", tk.END, values=("Komparatiivi", forms("Comp+Sg+Nom"), f"attr. {forms('Comp+Attr')}"))
                self.tree.insert("", tk.END, values=("Superlatiivi", forms("Superl+Sg+Nom"), f"attr. {forms('Superl+Attr')}"))

        raw_output = [f"{tag:30} -> {', '.join(mark(tag, v) for v in surfaces)}" for tag, surfaces in paradigm.items()]
        if any(self.grades.values()) and show_grade:
            raw_output.insert(0, "GD = gievrras dássi (vahva aste), HD = headju dássi (heikko aste)\n")
        self.raw_text.insert(tk.END, "\n".join(raw_output) if raw_output else lemma)

    def clear_tables(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.raw_text.delete("1.0", tk.END)
        self.meanings_text.configure(state=tk.NORMAL)
        self.meanings_text.delete("1.0", tk.END)
        self.meanings_text.configure(state=tk.DISABLED)

    def speak_lemma(self):
        if self.current_results:
            self.speak(self.current_results[self.selected_idx][1])

    def speak(self, text):
        """Hakee äänen taustalla (3–5 s ensimmäisellä kerralla, sitten välimuistista) ja soittaa sen."""
        text = text.strip()
        if not text:
            return
        voice = self.voice.get()
        self.speak_button.config(text=" Haetaan…", state=tk.DISABLED)

        def done(path, error):
            self.speak_button.config(text=" Kuuntele", state=tk.NORMAL)
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

    def on_table_double_click(self, event):
        """Kaksoisnapsautus taulukon solussa ääntää solun muodon (esim. "mun dagan")."""
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not row or column in ("", "#1") or "section" in self.tree.item(row, "tags"):
            return
        values = self.tree.item(row, "values")
        index = int(column[1:]) - 1
        if index >= len(values):
            return
        text = str(values[index])
        if text in NONFINITE_NAMES:
            return
        text = re.sub(r"\s*\((GD|HD)\)", "", text).replace("attr. ", "").replace(" / ", ", ").strip()
        if text and text != "-":
            self.speak(text)

    def open_giellatekno(self):
        if not self.current_results:
            return
        _, lemma, pos, _, _ = self.current_results[self.selected_idx]
        webbrowser.open(giellatekno_url(lemma, pos))

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("Tietoa ohjelmasta")
        about_win.geometry("520x460")
        about_win.configure(bg="#ffffff")
        about_win.resizable(False, False)

        title_lbl = tk.Label(
            about_win, 
            text="Sátni FST jakeluversio", 
            font=("Sans", 12, "bold"), 
            bg="#ffffff", 
            fg="#0f172a"
        )
        title_lbl.pack(pady=(15, 0))

        version_lbl = tk.Label(
            about_win, 
            text=f"Versio {VERSION}", 
            font=("Sans", 9), 
            bg="#ffffff", 
            fg="#64748b"
        )
        version_lbl.pack(pady=(0, 8))

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
        
        text_lbl = tk.Label(
            about_win, 
            text=info_text, 
            font=("Sans", 9), 
            bg="#ffffff", 
            fg="#475569",
            justify=tk.LEFT,
            wraplength=480
        )
        text_lbl.pack(padx=20, pady=5)

        email_frame = tk.Frame(about_win, bg="#ffffff")
        email_frame.pack(pady=8)

        tk.Label(
            email_frame, 
            text="Virheilmoitukset ja palaute sähköpostitse: ", 
            font=("Sans", 9), 
            bg="#ffffff", 
            fg="#475569"
        ).pack(side=tk.LEFT)

        email_link = tk.Label(
            email_frame, 
            text="juha@somby.fi", 
            font=("Sans", 9, "underline"), 
            bg="#ffffff", 
            fg="#2563eb", 
            cursor="hand2"
        )
        email_link.pack(side=tk.LEFT)
        email_link.bind("<Button-1>", lambda e: webbrowser.open("mailto:juha@somby.fi"))

        close_btn = tk.Button(
            about_win, 
            text="Sulje", 
            font=("Sans", 9, "bold"), 
            bg="#e2e8f0", 
            fg="#0f172a", 
            relief=tk.FLAT,
            padx=18, 
            pady=4,
            command=about_win.destroy
        )
        close_btn.pack(pady=15)

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
    root = tk.Tk()
    app = SatniGUI(root)
    root.mainloop()
