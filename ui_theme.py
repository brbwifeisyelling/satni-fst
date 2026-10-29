"""Ulkoasu: vaalea ja tumma väripaletti, järjestelmän teeman tunnistus, fontti, asetukset ja ttk-tyylit."""
import json
import os
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

PALETTES = {
    "light": {
        "bg": "#f4f6fa", "surface": "#ffffff", "surface_alt": "#f6f8fb", "border": "#e2e8f0",
        "text": "#0f172a", "muted": "#64748b", "subtle": "#94a3b8",
        "accent": "#2563eb", "accent_hover": "#1d4ed8", "accent_text": "#ffffff",
        "chip": "#e8edf4", "chip_hover": "#dbe3ee", "chip_text": "#1e293b",
        "section": "#eef2f8", "entry": "#ffffff", "select": "#dbeafe",
        "gd_fg": "#15803d", "gd_bg": "#dcfce7", "hd_fg": "#c2410c", "hd_bg": "#ffedd5",
        "gt_fg": "#9f1239", "gt_bg": "#fff1f2", "gt_hover": "#ffe4e6",
        "speak_fg": "#1d4ed8", "speak_bg": "#eff6ff", "speak_hover": "#dbeafe",
    },
    "dark": {
        "bg": "#0f141b", "surface": "#171e27", "surface_alt": "#1b232e", "border": "#2a3441",
        "text": "#e5e9f0", "muted": "#94a3b8", "subtle": "#64748b",
        "accent": "#3b82f6", "accent_hover": "#60a5fa", "accent_text": "#ffffff",
        "chip": "#232c38", "chip_hover": "#2d3846", "chip_text": "#e2e8f0",
        "section": "#1f2834", "entry": "#0f141b", "select": "#1e3a5f",
        "gd_fg": "#4ade80", "gd_bg": "#123220", "hd_fg": "#fb923c", "hd_bg": "#3a2210",
        "gt_fg": "#fda4af", "gt_bg": "#35141d", "gt_hover": "#4a1c28",
        "speak_fg": "#93c5fd", "speak_bg": "#162447", "speak_hover": "#1e3160",
    },
}

THEME_NAMES = {"auto": "Automaattinen", "light": "Vaalea", "dark": "Tumma"}

# Fontit, joissa saamen kirjaimet (á č đ ŋ š ŧ ž) näkyvät hyvin; ensimmäinen saatavilla oleva valitaan
FONT_CANDIDATES = ["Noto Sans", "Segoe UI", "Cantarell", "Ubuntu", "DejaVu Sans", "Liberation Sans", "Helvetica"]

DEFAULT_SETTINGS = {"theme": "auto", "voice": "Biret", "show_grade": True}


# --- Asetukset ---

def settings_path():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "satni-fst", "settings.json")


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(settings_path(), encoding="utf-8") as f:
            settings.update({k: v for k, v in json.load(f).items() if k in DEFAULT_SETTINGS})
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(settings_path()), exist_ok=True)
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# --- Järjestelmän teema ---

def _kde_is_dark():
    path = os.path.join(os.path.expanduser("~"), ".config", "kdeglobals")
    try:
        section = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    section = line
                elif section == "[Colors:Window]" and line.startswith("BackgroundNormal="):
                    r, g, b = (int(x) for x in line.split("=", 1)[1].split(",")[:3])
                    return (0.299 * r + 0.587 * g + 0.114 * b) < 128
    except (OSError, ValueError):
        pass
    return None


def _gnome_is_dark():
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=1
        ).stdout
        if "dark" in out:
            return True
        if "default" in out or "light" in out:
            return False
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _windows_is_dark():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return None


def system_prefers_dark():
    if sys.platform == "win32":
        return bool(_windows_is_dark())
    if ":dark" in os.environ.get("GTK_THEME", "").lower():
        return True
    for check in (_kde_is_dark, _gnome_is_dark):
        result = check()
        if result is not None:
            return result
    return False


def resolve_mode(theme_setting):
    if theme_setting in ("light", "dark"):
        return theme_setting
    return "dark" if system_prefers_dark() else "light"


# --- Fontti ja näytön tarkkuus ---

def enable_windows_dpi_awareness():
    """Terävä teksti Windowsin skaalatuilla näytöillä (kutsuttava ennen tk.Tk():ta)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def choose_font_family(root):
    families = set(tkfont.families(root))
    for name in FONT_CANDIDATES:
        if name in families:
            return name
    return "TkDefaultFont"


# --- ttk-tyylit ---

def apply_ttk_style(root, c, font_family):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=c["bg"], foreground=c["text"], font=(font_family, 10),
                    bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"],
                    troughcolor=c["bg"], focuscolor=c["accent"])

    style.configure("TNotebook", background=c["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=c["bg"], foreground=c["muted"],
                    padding=(14, 8), borderwidth=1, font=(font_family, 10, "bold"),
                    bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"])
    style.map("TNotebook.Tab",
              lightcolor=[("selected", c["surface"])],
              background=[("selected", c["surface"]), ("active", c["chip"])],
              foreground=[("selected", c["accent"]), ("active", c["text"])])

    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background=c["chip"], troughcolor=c["surface"],
                        bordercolor=c["surface"], arrowcolor=c["muted"], gripcount=0,
                        lightcolor=c["chip"], darkcolor=c["chip"], relief="flat")
        style.map(f"{orient}.TScrollbar", background=[("active", c["chip_hover"])])

    style.configure("TCombobox", fieldbackground=c["entry"], background=c["chip"], foreground=c["text"],
                    arrowcolor=c["muted"], bordercolor=c["border"], padding=(6, 3),
                    selectbackground=c["entry"], selectforeground=c["text"])
    style.map("TCombobox",
              fieldbackground=[("readonly", c["entry"])],
              foreground=[("readonly", c["text"])],
              selectbackground=[("readonly", c["entry"])],
              selectforeground=[("readonly", c["text"])],
              bordercolor=[("focus", c["accent"])])
    # Comboboxin avautuva lista on tavallinen Tk-listbox
    root.option_add("*TCombobox*Listbox.background", c["surface"])
    root.option_add("*TCombobox*Listbox.foreground", c["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", c["accent_text"])
    root.option_add("*TCombobox*Listbox.font", (font_family, 10))
    return style
