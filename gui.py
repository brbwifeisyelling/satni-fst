#!/usr/bin/env python3
import os
import sys
import sqlite3
import tkinter as tk
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk

try:
    from version import VERSION
except ImportError:
    VERSION = "kehitysversio"

# --- TIETOKANTA- JA POLUNMÄÄRITYS ---

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = sys._MEIPASS
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
                SELECT id, sme_lemma, pos, subtype, finnish_translation, 1 AS rank
                FROM dictionary WHERE PYLOWER(sme_lemma) = ?
                UNION ALL
                SELECT id, sme_lemma, pos, subtype, finnish_translation, 2
                FROM dictionary
                WHERE PYLOWER(finnish_translation) = ?
                   OR PYLOWER(finnish_translation) LIKE ?
                   OR PYLOWER(finnish_translation) LIKE ?
                   OR PYLOWER(finnish_translation) LIKE ?
                UNION ALL
                SELECT DISTINCT d.id, d.sme_lemma, d.pos, d.subtype, d.finnish_translation, 3
                FROM paradigms p JOIN dictionary d ON p.word_id = d.id
                WHERE p.surface COLLATE NOCASE IN (?, ?, ?, ?)
                UNION ALL
                SELECT id, sme_lemma, pos, subtype, finnish_translation, 4
                FROM dictionary WHERE PYLOWER(sme_lemma) LIKE ?
            )
            ORDER BY rank, CASE WHEN pos = 'V' THEN 1 ELSE 2 END, sme_lemma
            LIMIT 60
            """,
            (
                q_lower,
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
    paradigm = {}
    if not os.path.exists(DB_FILE):
        return paradigm

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT tag, surface FROM paradigms WHERE word_id = ? ORDER BY rowid",
            (word_id,)
        )
        for tag, surface in cursor.fetchall():
            if tag not in paradigm:
                paradigm[tag] = []
            if surface not in paradigm[tag]:
                paradigm[tag].append(surface)
                
        conn.close()
    except Exception as e:
        print(f"Taivutusvirhe tietokannasta: {e}")
        
    return paradigm

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

CASE_ROWS = [
    ("Nominatiivi (Nom)", "Nom"),
    ("Genetiivi (Gen)", "Gen"),
    ("Akkusatiivi (Acc)", "Acc"),
    ("Illatiivi (Ill)", "Ill"),
    ("Lokatiivi (Loc)", "Loc"),
    ("Komitatiivi (Com)", "Com"),
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

class SatniGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sátni FST - Pohjoissaamen avoin sanakirja ja taivutin")
        self.root.geometry("1150x800")
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

        self.meta_frame = tk.Frame(root, bg="#ffffff", height=65, relief=tk.SOLID, bd=1)
        self.meta_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.meta_label = tk.Label(
            self.meta_frame, 
            text="Hae sana aloittaaksesi.", 
            font=("Sans", 10, "bold"), 
            fg="#0f172a", 
            bg="#ffffff",
            anchor="w"
        )
        self.meta_label.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 2))

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

        self.tab_raw = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab_raw, text=" Muut taivutukset / Raakateksti ")

        self.setup_table_view()
        self.setup_raw_view()

        self.current_results = []

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

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

        self.current_results = query_database(query)
        
        for widget in self.buttons_inner_frame.winfo_children():
            widget.destroy()

        if not self.current_results:
            self.meta_label.config(text=f"Ei osumia haulle: '{query}'")
            self.behavior_label.config(text="")
            self.clear_tables()
            return

        col_max = 6
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
            r = idx // col_max
            c = idx % col_max
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="w")

        self.select_word_option(0)

    def select_word_option(self, selected_idx):
        word_id, lemma, pos, subtype, trans = self.current_results[selected_idx]
        for idx, widget in enumerate(self.buttons_inner_frame.winfo_children()):
            if idx == selected_idx:
                widget.config(bg="#2563eb", fg="#ffffff")
            else:
                widget.config(bg="#cbd5e1", fg="#0f172a")

        behavior = analyze_word_behavior(lemma, pos, subtype)
        
        # Rajataan tarvittaessa näytettävät käännökset kahden ensimmäisen mittaisiksi myös otsikkopalkissa
        display_trans = trans
        if trans:
            trans_parts = [p.strip() for p in trans.split(",")]
            display_trans = ", ".join(trans_parts[:2])

        self.meta_label.config(text=f"Saamen perusmuoto: {lemma}  |  Suomeksi: {display_trans if display_trans else '(ei määritetty)'}  |  Sanaluokka: {pos}")
        self.behavior_label.config(text=f"Tyyppi: {behavior}")

        paradigm = get_paradigms_from_db(word_id)
        self.populate_tables(pos, lemma, paradigm)

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

        def forms(tag):
            return ", ".join(paradigm.get(tag, [])) or "-"

        def with_pronoun(pronoun, tag, aux=""):
            vals = paradigm.get(tag, [])
            if not vals:
                return "-"
            words = " ".join(w for w in (pronoun, aux) if w)
            return ", ".join(f"{words} {v}" if words else v for v in vals)

        def section(title):
            self.tree.insert("", tk.END, values=(f"— {title} —", "", "", "", ""), tags=("section",))

        self.tree.tag_configure("section", background="#e2e8f0", font=("Sans", 10, "bold"))

        if not paradigm and pos_upper not in UNINFLECTED_POS:
            self.set_columns([("Huomio", 200), ("Perusmuoto", 500)])
            self.tree.insert("", tk.END, values=("Ei taivutusmuotoja", lemma))
            self.raw_text.insert(tk.END, "FST-generaattori ei tuottanut tälle sanalle taivutusmuotoja.")
            return

        if pos_upper == "V":
            self.set_columns([
                ("Persoona", 90), ("Myönteinen", 230), ("Kielteinen", 250),
                ("Myönteinen", 230), ("Kielteinen", 250),
            ])

            section("Indikatiivi: preesens (sarakkeet 2–3) ja preteriti (sarakkeet 4–5)")
            for p in PERSONS:
                pron = PRONOUNS[p]
                self.tree.insert("", tk.END, values=(
                    p,
                    with_pronoun(pron, f"Ind+Prs+{p}"),
                    with_pronoun(pron, "Ind+Prs+ConNeg", NEG_AUX[p]),
                    with_pronoun(pron, f"Ind+Prt+{p}"),
                    with_pronoun(pron, "Ind+Prt+ConNeg", NEG_AUX[p]),
                ))

            section("Konditionaali (sarakkeet 2–3) ja potentiaali (sarakkeet 4–5)")
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
                self.tree.insert("", tk.END, values=(name, forms(tag), "", "", ""))

        elif pos_upper in UNINFLECTED_POS:
            self.set_columns([("Käyttö / Tyyppi", 200), ("Perusmuoto", 500)])
            self.tree.insert("", tk.END, values=("Perusmuoto (taipumaton)", lemma))

        elif "Sg+Nom" not in paradigm and "Pl+Nom" not in paradigm and "Nom" in paradigm:
            # Persoona- ja refleksiivipronominit: luku ja persoona kuuluvat jo perusmuotoon
            self.set_columns([("Sijamuoto", 200), ("Muoto", 500)])
            for case_name, case in CASE_ROWS + [("Essiivi (Ess)", "Ess")]:
                self.tree.insert("", tk.END, values=(case_name, forms(case)))

        else:
            # Substantiivit, adjektiivit, numeraalit ja muut pronominit
            self.set_columns([("Sijamuoto / Käyttö", 200), ("Yksikkö (Sg)", 300), ("Monikko (Pl)", 300)])

            if "Attr" in paradigm:
                self.tree.insert("", tk.END, values=("Attribuutti (Attr)", forms("Attr"), ""))

            for case_name, case in CASE_ROWS:
                self.tree.insert("", tk.END, values=(case_name, forms(f"Sg+{case}"), forms(f"Pl+{case}")))
            self.tree.insert("", tk.END, values=("Essiivi (Ess)", forms("Ess"), ""))

            if pos_upper == "A" and any(t.startswith(("Comp", "Superl")) for t in paradigm):
                section("Vertailumuodot")
                self.tree.insert("", tk.END, values=("Komparatiivi", forms("Comp+Sg+Nom"), f"attr. {forms('Comp+Attr')}"))
                self.tree.insert("", tk.END, values=("Superlatiivi", forms("Superl+Sg+Nom"), f"attr. {forms('Superl+Attr')}"))

        raw_output = [f"{tag:30} -> {', '.join(surfaces)}" for tag, surfaces in paradigm.items()]
        self.raw_text.insert(tk.END, "\n".join(raw_output) if raw_output else lemma)

    def clear_tables(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.raw_text.delete("1.0", tk.END)

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("Tietoa ohjelmasta")
        about_win.geometry("520x380")
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

if __name__ == "__main__":
    root = tk.Tk()
    app = SatniGUI(root)
    root.mainloop()
