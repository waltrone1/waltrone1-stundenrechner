# Stundenrechner v3 - Python + CustomTkinter
# DE UI, ASCII only
# Datum sichtbar DE (DD.MM.YYYY), intern ISO (YYYY-MM-DD)
#
# Features:
# - Modern UI (customtkinter), Light default, toggle Light/Dark
# - Monats-Dashboard links (Ampel: zu wenig / ok / zu viel)
# - Monatsuebertrag (Carry) automatisch (Saldo laeuft ueber Monate)
# - Abwesenheiten: Urlaub / Krank jeweils 1 Tag / 1/2 Tag
# - Urlaub/Krank Uebersicht pro Jahr
# - Kalender im Add-Dialog (optional via tkcalendar, fallback Entry)
# - Delete-Taste loescht Tag (Button "Delete" entfaellt)
# - Set Work/Urlaub/Krank Buttons nur im Add-Dialog (farblich)
# - Month Target / Urlaub Total farblich bei gueltigem Eintrag
# - Autosave + Backup JSON

import sys
import os
import json
import shutil
import datetime as dt
import re
import tkinter as tk
import webbrowser
from typing import Optional, Tuple, Dict, Any
from tkinter import messagebox
from tkinter import ttk

import customtkinter as ctk

# Optional: Logo support
try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

APP_TITLE = "Stundenrechner (Minijob) - v1.0.0.0"
DATA_FILE = "stunden.json"

# bis +5.0 Std ueber Ziel = OK, darueber "zu viel"
OVER_OK_MAX = 5.0

# ---------- UI Colors (Ampel) ----------
COL_OK = "#2e7d32"       # gruen
COL_WARN = "#f9a825"     # gelb/orange
COL_BAD = "#c62828"      # rot
# ---------- Brand Colors (waltrone1 look) ----------
BRAND_GREEN = "#4CAF50"
BRAND_GREEN_HOVER = "#43A047"

BRAND_INPUT_BG = "#EAF4FB"
BRAND_INPUT_BORDER = "#B0D4F1"

BRAND_LIST_BG = "#EAF4FB"
BRAND_LIST_FG = "#0F172A"
BRAND_LIST_SELECT_BG = "#B0D4F1"

BRAND_URL = "https://www.trigema.de"  # oder dein Link
LOGO_FILE = "logo.png"

def round_corners_rgba(img, radius: int):
    """High quality rounded icon with subtle shadow."""
    from PIL import ImageDraw, ImageFilter

    img = img.convert("RGBA")

    scale = 4
    w, h = img.size
    big = (w * scale, h * scale)

    # High-res resize
    img_big = img.resize(big, Image.LANCZOS)

    # Rounded mask
    mask = Image.new("L", big, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, big[0], big[1]),
        radius=radius * scale,
        fill=255
    )

    # No heavy blur anymore (clean edge)
    result = Image.new("RGBA", big)
    result.paste(img_big, (0, 0), mask)

    result = result.resize((w, h), Image.LANCZOS)

    # --- Subtle Shadow ---
    shadow = Image.new("RGBA", (w+12, h+12), (0,0,0,0))
    shadow_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(shadow_mask)
    draw.rounded_rectangle((0,0,w,h), radius=radius, fill=255)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(6))

    shadow.paste((0,0,0,90), (6,6), shadow_mask)

    final = Image.new("RGBA", shadow.size, (0,0,0,0))
    final.paste(shadow, (0,0))
    final.paste(result, (6,6), result)

    return final

def color_for_diff(diff: float) -> str:
    # diff = actual - target
    if diff < 0:
        return COL_BAD          # zu wenig
    if diff <= OVER_OK_MAX:
        return COL_OK           # ok
    return COL_WARN             # zu viel

def color_for_value(v: float) -> str:
    # fuer Uebertrag / Saldo / Urlaub offen: negativ rot, sonst gruen
    return COL_BAD if v < 0 else COL_OK

# Optional calendar
try:
    from tkcalendar import DateEntry  # pip install tkcalendar
    HAS_TKCAL = True
except Exception:
    HAS_TKCAL = False

# ---------- Types ----------
TYPE_WORK = "work"
TYPE_VAC_FULL = "vac_full"
TYPE_VAC_HALF = "vac_half"
TYPE_SICK_FULL = "sick_full"
TYPE_SICK_HALF = "sick_half"

TYPE_LABELS_DE = {
    TYPE_WORK: "Arbeit",
    TYPE_VAC_FULL: "Urlaub 1 Tag",
    TYPE_VAC_HALF: "Urlaub 1/2 Tag",
    TYPE_SICK_FULL: "Krank 1 Tag",
    TYPE_SICK_HALF: "Krank 1/2 Tag",
}

ABSENCE_TYPES = {TYPE_VAC_FULL, TYPE_VAC_HALF, TYPE_SICK_FULL, TYPE_SICK_HALF}

# ---------- Helpers: paths ----------
def app_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.expanduser(r"~\AppData\Local")
    target = os.path.join(base, "waltrone1", "Stundenrechner")
    os.makedirs(target, exist_ok=True)
    return target

def script_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def data_path() -> str:
    return os.path.join(app_data_dir(), DATA_FILE)

# ---------- Helpers: Date ----------
def de_to_iso(de_str: str) -> Optional[str]:
    if not de_str:
        return None
    s = de_str.strip()
    try:
        d = dt.datetime.strptime(s, "%d.%m.%Y").date()
        return d.strftime("%Y-%m-%d")
    except Exception:
        return None

def iso_to_de(iso_str: str) -> str:
    if not iso_str:
        return ""
    s = iso_str.strip()
    try:
        d = dt.datetime.strptime(s, "%Y-%m-%d").date()
        return d.strftime("%d.%m.%Y")
    except Exception:
        return iso_str

def month_key_from_iso(iso_str: str) -> str:
    return iso_str[:7] if iso_str and len(iso_str) >= 7 else ""

def month_display_from_key(mk: str) -> str:
    # YYYY-MM -> MM.YYYY
    try:
        y = mk[:4]
        m = mk[5:7]
        return f"{m}.{y}"
    except Exception:
        return mk

def month_key_from_display(md: str) -> Optional[str]:
    # MM.YYYY -> YYYY-MM
    try:
        s = md.strip()
        m, y = s.split(".")
        if len(y) != 4:
            return None
        mi = int(m)
        if mi < 1 or mi > 12:
            return None
        return f"{y}-{mi:02d}"
    except Exception:
        return None

def year_from_month_key(mk: str) -> Optional[int]:
    try:
        return int(mk[:4])
    except Exception:
        return None

WEEKDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def iso_to_weekday_de(iso_str: str) -> str:
    try:
        d = dt.datetime.strptime(iso_str, "%Y-%m-%d").date()
        return WEEKDAY_DE[d.weekday()]
    except Exception:
        return ""

def iso_to_kw(iso_str: str) -> int:
    try:
        d = dt.datetime.strptime(iso_str, "%Y-%m-%d").date()
        return int(d.isocalendar().week)
    except Exception:
        return 0

# ---------- Helpers: Time ----------
def normalize_time_input(s: str) -> Optional[str]:
    """
    Accept:
      - H or HH   -> HH:00
      - HH:MM
      - HHMM
    Return always HH:MM or None.
    Examples:
      "12"   -> "12:00"
      "7"    -> "07:00"
      "1200" -> "12:00"
      "12:30"-> "12:30"
    """
    if not s:
        return None
    t = s.strip()

    if re.fullmatch(r"\d{1,2}", t):
        hh = int(t)
        if 0 <= hh <= 23:
            return f"{hh:02d}:00"
        return None

    t2 = t.replace(":", "")
    if not re.fullmatch(r"\d{4}", t2):
        return None

    hh = int(t2[:2])
    mm = int(t2[2:])
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return f"{hh:02d}:{mm:02d}"
    return None

def try_parse_time_hhmm(s: str) -> Optional[dt.timedelta]:
    norm = normalize_time_input(s)
    if norm is None:
        return None
    hh = int(norm[0:2])
    mm = int(norm[3:5])
    return dt.timedelta(hours=hh, minutes=mm)

def calc_hours(start_s: str, end_s: str, break_min: int) -> Optional[float]:
    st = try_parse_time_hhmm(start_s)
    en = try_parse_time_hhmm(end_s)
    if st is None or en is None:
        return None

    dur = en - st
    if dur.total_seconds() < 0:
        dur += dt.timedelta(days=1)

    bm = max(0, int(break_min))
    dur -= dt.timedelta(minutes=bm)
    if dur.total_seconds() < 0:
        dur = dt.timedelta(0)

    return round(dur.total_seconds() / 3600.0, 2)

def fmt2(v: float) -> str:
    return f"{v:.2f}"

# ---------- Validators ----------
def validate_month_target(raw: str) -> Tuple[bool, str, float]:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return False, "Monatsziel ist Pflichtfeld.", 0.0
    try:
        v = float(s)
        if v < 0:
            return False, "Monatsziel muss >= 0 sein.", 0.0
        return True, "", round(v, 2)
    except Exception:
        return False, "Monatsziel ist ungueltig (z.B. 40 oder 40.5).", 0.0


def validate_vac_total(raw: str) -> Tuple[bool, str, float]:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return False, "Urlaub (Tage/Jahr) ist Pflichtfeld.", 0.0
    try:
        v = float(s)
        if v < 0:
            return False, "Urlaub (Tage/Jahr) muss >= 0 sein.", 0.0
        return True, "", round(v, 2)
    except Exception:
        return False, "Urlaub (Tage/Jahr) ungueltig (z.B. 24 oder 24.5).", 0.0


def validate_day_hours(raw: str) -> Tuple[bool, str, float]:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return False, "Std-Tag (h) ist Pflichtfeld.", 0.0
    try:
        v = float(s)
        if v <= 0:
            return False, "Std-Tag (h) muss > 0 sein.", 0.0
        return True, "", round(v, 2)
    except Exception:
        return False, "Std-Tag (h) ungueltig (z.B. 8 oder 4.5).", 0.0


def validate_break(raw: str) -> Tuple[bool, str, int]:
    try:
        v = int((raw or "0").strip() or "0")
        if v < 0:
            return False, "Pause muss >= 0 sein.", 0
        return True, "", v
    except Exception:
        return False, "Pause muss eine ganze Zahl sein.", 0


def validate_time(label: str, raw: str) -> Tuple[bool, str, str]:
    norm = normalize_time_input(raw)
    if norm is None:
        return False, f"{label} ungueltig (z.B. 12, 1200, 12:30).", ""
    return True, "", norm
    
# ---------- Data ----------
def new_empty_data() -> dict:
    return {
        "MonthlyTargetHours": {},
        "Entries": [],
        "Settings": {
            "VacationTotalPerYear": 24.0,
            "StandardDayHours": 8.0,
            "DefaultMonthlyTargetHours": 0.0,
            "FixedBreakEnabled": False,
            "FixedBreakMinutes": 30,
        }
    }

def normalize_entry(e: dict) -> Optional[dict]:
    iso_raw = str(e.get("Date", "") or "").strip()
    iso_from_de = de_to_iso(iso_raw)
    if iso_from_de:
        iso = iso_from_de
    else:
        try:
            dt.datetime.strptime(iso_raw, "%Y-%m-%d")
            iso = iso_raw
        except Exception:
            return None

    start = str(e.get("Start", "") or "")
    end = str(e.get("End", "") or "")

    ns = normalize_time_input(start) if start.strip() else ""
    ne = normalize_time_input(end) if end.strip() else ""

    try:
        bm = int(e.get("BreakMin", 0) or 0)
    except Exception:
        bm = 0

    t = str(e.get("Type", TYPE_WORK) or TYPE_WORK).strip()
    if t not in TYPE_LABELS_DE:
        t = TYPE_WORK
    use_fixed = bool(e.get("UseFixedBreak", False))

    return {
        "Date": iso,
        "Start": ns,
        "End": ne,
        "BreakMin": max(0, bm),
        "UseFixedBreak": use_fixed,
        "ShortNote": str(e.get("ShortNote", "") or ""),
        "Report": str(e.get("Report", "") or ""),
        "Type": t,
    }

def load_data() -> dict:
    fp = data_path()
    if not os.path.exists(fp):
        return new_empty_data()

    try:
        with open(fp, "r", encoding="utf-8") as f:
            obj = json.load(f)

        data = new_empty_data()

        mth = obj.get("MonthlyTargetHours", {})
        if isinstance(mth, dict):
            for k, v in mth.items():
                try:
                    data["MonthlyTargetHours"][str(k)] = float(v)
                except Exception:
                    data["MonthlyTargetHours"][str(k)] = 0.0

        ent = obj.get("Entries", [])
        if isinstance(ent, list):
            for item in ent:
                if isinstance(item, dict):
                    ne = normalize_entry(item)
                    if ne:
                        data["Entries"].append(ne)

        settings = obj.get("Settings", {})
        if isinstance(settings, dict):
            try:
                data["Settings"]["VacationTotalPerYear"] = float(settings.get("VacationTotalPerYear", 24.0))
            except Exception:
                pass
            try:
                data["Settings"]["StandardDayHours"] = float(settings.get("StandardDayHours", 8.0))
            except Exception:
                pass

            # Default Monatsziel (0.0 = "leer/unset")
            
            try:
                data["Settings"]["FixedBreakEnabled"] = bool(settings.get("FixedBreakEnabled", False))
            except Exception:
                data["Settings"]["FixedBreakEnabled"] = False

            try:
                data["Settings"]["FixedBreakMinutes"] = int(settings.get("FixedBreakMinutes", 30))
            except Exception:
                data["Settings"]["FixedBreakMinutes"] = 30            
            
            try:
                data["Settings"]["DefaultMonthlyTargetHours"] = float(settings.get("DefaultMonthlyTargetHours", 0.0))
            except Exception:
                data["Settings"]["DefaultMonthlyTargetHours"] = 0.0

        data["Entries"].sort(key=lambda x: x["Date"])
        return data

    except Exception as ex:
        messagebox.showerror("Fehler", f"stunden.json konnte nicht geladen werden:\n{ex}")
        return new_empty_data()

def save_data(data: dict) -> bool:
    fp = data_path()
    try:
        # Backup-Files (optional)
        # if os.path.exists(fp):
        #     ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        #     bak = os.path.join(script_dir(), f"stunden_backup_{ts}.json")
        #     try:
        #         shutil.copy2(fp, bak)
        #     except Exception:
        #         pass

        data["Entries"].sort(key=lambda x: x["Date"])
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=2)
        return True
    except Exception as ex:
        messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{ex}")
        return False

# ---------- Absence credit hours ----------
def credit_hours_for_type(day_hours: float, t: str) -> float:
    if t == TYPE_VAC_FULL:
        return round(day_hours, 2)
    if t == TYPE_VAC_HALF:
        return round(day_hours / 2.0, 2)
    if t == TYPE_SICK_FULL:
        return round(day_hours, 2)
    if t == TYPE_SICK_HALF:
        return round(day_hours / 2.0, 2)
    return 0.0

def count_days_for_type(t: str) -> float:
    if t in (TYPE_VAC_FULL, TYPE_SICK_FULL):
        return 1.0
    if t in (TYPE_VAC_HALF, TYPE_SICK_HALF):
        return 0.5
    return 0.0

# ---------- Dialog: Add Day ----------
class AddDayDialog(ctk.CTkToplevel):
    def __init__(self, parent, default_date_de: str, existing: Optional[dict] = None):
        super().__init__(parent)
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._type = TYPE_WORK
        self._existing = existing or {}
        self.title("Tag bearbeiten" if self._existing else "Tag hinzufuegen")

        self.grid_columnconfigure(0, weight=1)

        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
        frm.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="Datum (DD.MM.YYYY):").grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._date_widget = None
        self._date_entry = None

        if HAS_TKCAL:
            # tkcalendar is a tk widget -> embed inside a small tk.Frame
            host = tk.Frame(frm)
            host.grid(row=0, column=1, sticky="w", pady=(0, 8))
            self._date_widget = DateEntry(host, date_pattern="dd.mm.yyyy", width=16)
            self._date_widget.pack()
            try:
                self._date_widget.set_date(dt.datetime.strptime(default_date_de, "%d.%m.%Y").date())
            except Exception:
                pass
        else:
            self._date_entry = ctk.CTkEntry(frm, width=180)
            self._date_entry.grid(row=0, column=1, sticky="w", pady=(0, 8))
            self._date_entry.insert(0, default_date_de)

        ctk.CTkLabel(frm, text="Start Uhr (1230/12:30):").grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.ent_start = ctk.CTkEntry(frm, width=180)
        self.ent_start.grid(row=1, column=1, sticky="w", pady=(0, 8))

        ctk.CTkLabel(frm, text="Ende Uhr (1230/12:30):").grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.ent_end = ctk.CTkEntry(frm, width=180)
        self.ent_end.grid(row=2, column=1, sticky="w", pady=(0, 8))

        ctk.CTkLabel(frm, text="Pause Minuten:").grid(row=3, column=0, sticky="w", pady=(0, 12))
        self.ent_break = ctk.CTkEntry(frm, width=180)
        self.ent_break.grid(row=3, column=1, sticky="w", pady=(0, 12))
        self.ent_break.insert(0, "0")

        ctk.CTkLabel(frm, text="Typ (Buttons):").grid(row=4, column=0, sticky="w", pady=(0, 8))

        row_btn = ctk.CTkFrame(frm, fg_color="transparent")
        row_btn.grid(row=4, column=1, sticky="w", pady=(0, 8))

        self.btn_work = ctk.CTkButton(row_btn, text="Arbeit", width=90,
                                     fg_color=BRAND_GREEN,
                                     hover_color=BRAND_GREEN_HOVER,
                                     command=lambda: self._set_type(TYPE_WORK))
        self.btn_work.grid(row=0, column=0, padx=(0, 8), pady=4)

        self.btn_v1 = ctk.CTkButton(row_btn, text="Urlaub 1", width=90,
                                    fg_color="#1976d2", hover_color="#135ea6",
                                    command=lambda: self._set_type(TYPE_VAC_FULL))
        self.btn_v1.grid(row=0, column=1, padx=(0, 8), pady=4)

        self.btn_vh = ctk.CTkButton(row_btn, text="Urlaub 1/2", width=100,
                                    fg_color="#1976d2", hover_color="#135ea6",
                                    command=lambda: self._set_type(TYPE_VAC_HALF))
        self.btn_vh.grid(row=0, column=2, padx=(0, 8), pady=4)

        self.btn_s1 = ctk.CTkButton(row_btn, text="Krank 1", width=90,
                                    fg_color="#c62828", hover_color="#9e1f1f",
                                    command=lambda: self._set_type(TYPE_SICK_FULL))
        self.btn_s1.grid(row=1, column=1, padx=(0, 8), pady=4)

        self.btn_sh = ctk.CTkButton(row_btn, text="Krank 1/2", width=100,
                                    fg_color="#c62828", hover_color="#9e1f1f",
                                    command=lambda: self._set_type(TYPE_SICK_HALF))
        self.btn_sh.grid(row=1, column=2, padx=(0, 8), pady=4)

        self.lbl_type = ctk.CTkLabel(frm, text="Aktueller Typ: Arbeit")
        self.lbl_type.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 12))

        row2 = ctk.CTkFrame(frm, fg_color="transparent")
        row2.grid(row=6, column=0, columnspan=2, sticky="e")

        self.btn_ok = ctk.CTkButton(row2, text="OK", width=120, command=self.on_ok)
        self.btn_ok.grid(row=0, column=0, padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(row2, text="Abbrechen", width=120, fg_color="#777777",
                                        hover_color="#666666", command=self.on_cancel)
        self.btn_cancel.grid(row=0, column=1)

        self.bind("<Return>", lambda _e: self.on_ok())
        self.bind("<Escape>", lambda _e: self.on_cancel())

        self.ent_start.focus_set()

        # center
        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")

        self._set_type(TYPE_WORK)

    def _get_date_de(self) -> str:
        if HAS_TKCAL and self._date_widget is not None:
            try:
                d = self._date_widget.get_date()
                return d.strftime("%d.%m.%Y")
            except Exception:
                return ""
        if self._date_entry is not None:
            return self._date_entry.get().strip()
        return ""

    def _set_type(self, t: str):
        self._type = t
        self.lbl_type.configure(text=f"Aktueller Typ: {TYPE_LABELS_DE.get(t, t)}")

        # dummensicher: Abwesenheit -> Zeiten aus / leeren
        if t in ABSENCE_TYPES:
            self.ent_start.delete(0, "end")
            self.ent_end.delete(0, "end")
            self.ent_break.delete(0, "end")
            self.ent_break.insert(0, "0")
            self.ent_start.configure(state="disabled")
            self.ent_end.configure(state="disabled")
            self.ent_break.configure(state="disabled")
        else:
            self.ent_start.configure(state="normal")
            self.ent_end.configure(state="normal")
            self.ent_break.configure(state="normal")

    def on_ok(self):
        date_de = self._get_date_de()
        iso = de_to_iso(date_de)
        if not iso:
            messagebox.showinfo("Info", "Datum ungueltig. Bitte DD.MM.YYYY nutzen.", parent=self)
            return

        t = self._type

        if t in ABSENCE_TYPES:
            self.result = (iso, "", "", 0, t)
            self.destroy()
            return

        start_raw = self.ent_start.get().strip()
        end_raw = self.ent_end.get().strip()
        brk_raw = self.ent_break.get().strip()

        ok, msg, start = validate_time("Start", start_raw)
        if not ok:
            messagebox.showinfo("Info", msg, parent=self)
            return

        ok, msg, end = validate_time("Ende", end_raw)
        if not ok:
            messagebox.showinfo("Info", msg, parent=self)
            return

        ok, msg, brk = validate_break(brk_raw)
        if not ok:
            messagebox.showinfo("Info", msg, parent=self)
            return

        self.result = (iso, start, end, brk, t)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

# ---------- Main App ----------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        if ctk.get_appearance_mode().lower() == "light":
            self.configure(fg_color="#FFFFFF")

        self.title(APP_TITLE)
        self.geometry("1320x820")
        self.minsize(1200, 760)

        self.data = load_data()

        self.autosave_after_id = None
        self.autosave_delay_ms = 900

        self._month_display_to_key = {}
        self._month_list_keys = []
        self._last_selected_iso = None
        self._suppress_month_select = False
        self._entry_clipboard = None
        self._paste_next_iso = None  # merkt sich das naechste Default-Datum fuer Ctrl+V

        self._build_ui()

        self.refresh_months()
        self.select_default_month()
        self.refresh_all_views(select_iso=None)

        # Delete key: Tag loeschen
        self.bind("<Delete>", self.on_delete_key)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def _build_ui(self):
        # Top bar - Rahmenfarbe
        top = ctk.CTkFrame(self, fg_color="#F1F5F9")
        top.pack(side="top", fill="x", padx=14, pady=(14, 8))

        # Appearance selector
      #  ctk.CTkLabel(top, text="Design:").grid(row=0, column=0, padx=(10, 6), pady=10, sticky="w")
      #  self.opt_mode = ctk.CTkOptionMenu(top, values=["light", "dark"], command=self.on_mode_change)
      #  self.opt_mode.grid(row=0, column=1, padx=(0, 18), pady=10, sticky="w")
      #  self.opt_mode.set("light")

        # Month selector
        ctk.CTkLabel(top, text="Monat:").grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        self.cmb_month = ctk.CTkOptionMenu(top, values=["--"], command=self.on_month_changed)
        self.cmb_month.grid(row=0, column=3, padx=(0, 18), pady=10, sticky="w")

        # Big Add button
        self.btn_add = ctk.CTkButton(
            top,
            text=" +  Tag hinzufuegen",
            width=220,
            height=42,
            fg_color=BRAND_GREEN,
            hover_color=BRAND_GREEN_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_add_day,
        )
        self.btn_add.grid(row=0, column=4, padx=(0, 12), pady=10, sticky="w")

        self.btn_save = ctk.CTkButton(top, text="Speichern", width=140, command=self.on_save)
        self.btn_save.grid(row=0, column=5, padx=(0, 12), pady=10, sticky="w")

        self.btn_open = ctk.CTkButton(top, text="Ordner oeffnen", width=160, command=self.on_open_folder)
        self.btn_open.grid(row=0, column=6, padx=(0, 12), pady=10, sticky="w")

        self.lbl_status = ctk.CTkLabel(top, text="Bereit.")
        self.lbl_status.grid(row=0, column=7, padx=(6, 10), pady=10, sticky="w")

        # Platz nach rechts schieben
        top.grid_columnconfigure(8, weight=1)

        # Reset Button ganz rechts
        self.btn_reset = ctk.CTkButton(
            top,
            text="Reset",
            width=120,
            fg_color="#c62828",
            hover_color="#9e1f1f",
            command=self.on_reset_all
        )
        self.btn_reset.grid(row=0, column=9, padx=(0, 10), pady=10, sticky="e")

        # Settings row
        settings = ctk.CTkFrame(self, fg_color="#FFFFFF")
        settings.pack(side="top", fill="x", padx=14, pady=(0, 10))
        settings.grid_columnconfigure(10, weight=1)

        ctk.CTkLabel(settings, text="Monatsziel (h):").grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.txt_target = ctk.CTkEntry(settings, width=120)
        self.txt_target.grid(row=0, column=1, padx=(0, 18), pady=10, sticky="w")
        self.txt_target.bind("<Return>", lambda _e: self.on_target_commit())
        self.txt_target.bind("<FocusOut>", lambda _e: self.on_target_commit())

        ctk.CTkLabel(settings, text="Urlaub (Tage/Jahr):").grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        self.txt_vac_total = ctk.CTkEntry(settings, width=120)
        self.txt_vac_total.grid(row=0, column=3, padx=(0, 18), pady=10, sticky="w")
        self.txt_vac_total.bind("<Return>", lambda _e: self.on_vac_total_commit())
        self.txt_vac_total.bind("<FocusOut>", lambda _e: self.on_vac_total_commit())

        ctk.CTkLabel(settings, text="Std-Tag (h) (fuer Urlaub/Krank):").grid(row=0, column=4, padx=(0, 6), pady=10, sticky="w")
        self.txt_day_hours = ctk.CTkEntry(settings, width=120)
        self.txt_day_hours.grid(row=0, column=5, padx=(0, 18), pady=10, sticky="w")
        self.txt_day_hours.bind("<Return>", lambda _e: self.on_day_hours_commit())
        self.txt_day_hours.bind("<FocusOut>", lambda _e: self.on_day_hours_commit())
        
        self.var_fixed_break = tk.BooleanVar(value=bool(self.data["Settings"].get("FixedBreakEnabled", False)))

        self.chk_fixed_break = ctk.CTkCheckBox(
            settings,
            text="Feste Pause",
            variable=self.var_fixed_break,
            command=self.on_fixed_break_toggle
        )
        self.chk_fixed_break.grid(row=0, column=6, padx=(0, 10), pady=10, sticky="w")

        ctk.CTkLabel(settings, text="Min:").grid(row=0, column=7, padx=(0, 6), pady=10, sticky="w")

        self.txt_fixed_break_min = ctk.CTkEntry(settings, width=70)
        self.txt_fixed_break_min.grid(row=0, column=8, padx=(0, 18), pady=10, sticky="w")
        self.txt_fixed_break_min.bind("<Return>", lambda _e: self.on_fixed_break_minutes_commit())
        self.txt_fixed_break_min.bind("<FocusOut>", lambda _e: self.on_fixed_break_minutes_commit())

        # --- Summary wrapper (keeps all 3 lines perfectly aligned) ---
        summary = ctk.CTkFrame(settings, fg_color="transparent")
        summary.grid(row=1, column=0, columnspan=6, padx=12, pady=(8, 10), sticky="nw")

        # Zeilenabstand einheitlich
        ROW_GAP = 4

        # --- BIG total balance (prominent) ---
        self.lbl_total_balance = ctk.CTkLabel(
            summary,
            text="GESAMTSALDO: --",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_total_balance.grid(row=0, column=0, sticky="w", pady=(0, ROW_GAP))

        # --- Month summary row (clean grid with fixed separators) ---
        self.monthsum_row = ctk.CTkFrame(summary, fg_color="transparent")
        self.monthsum_row.grid(row=1, column=0, sticky="w", pady=(0, ROW_GAP))

        PAD = 6
        f_norm = ctk.CTkFont(size=14, weight="bold")
        f_ist  = ctk.CTkFont(size=16, weight="bold")

        for c in range(9):
            self.monthsum_row.grid_columnconfigure(c, weight=0)

        self.lbl_month_prefix = ctk.CTkLabel(self.monthsum_row, text="Monat --:", font=f_norm)
        self.lbl_month_prefix.grid(row=0, column=0, padx=(0, PAD), sticky="w")

        self.sep1 = ctk.CTkLabel(self.monthsum_row, text="|", font=f_norm, text_color="#666666")
        self.sep1.grid(row=0, column=1, padx=(0, PAD), sticky="w")

        self.lbl_month_ist = ctk.CTkLabel(self.monthsum_row, text="Ist --", font=f_ist)
        self.lbl_month_ist.grid(row=0, column=2, padx=(0, PAD), sticky="w")

        self.sep2 = ctk.CTkLabel(self.monthsum_row, text="|", font=f_norm, text_color="#666666")
        self.sep2.grid(row=0, column=3, padx=(0, PAD), sticky="w")

        self.lbl_month_goal = ctk.CTkLabel(self.monthsum_row, text="Ziel --", font=f_norm)
        self.lbl_month_goal.grid(row=0, column=4, padx=(0, PAD), sticky="w")

        self.sep3 = ctk.CTkLabel(self.monthsum_row, text="|", font=f_norm, text_color="#666666")
        self.sep3.grid(row=0, column=5, padx=(0, PAD), sticky="w")

        self.lbl_month_diff = ctk.CTkLabel(self.monthsum_row, text="Diff --", font=f_norm)
        self.lbl_month_diff.grid(row=0, column=6, padx=(0, PAD), sticky="w")

        self.sep4 = ctk.CTkLabel(self.monthsum_row, text="|", font=f_norm, text_color="#666666")
        self.sep4.grid(row=0, column=7, padx=(0, PAD), sticky="w")

        self.lbl_month_status = ctk.CTkLabel(self.monthsum_row, text="--", font=f_norm)
        self.lbl_month_status.grid(row=0, column=8, sticky="w")

        # --- Carry / balance line ---
        self.lbl_balance = ctk.CTkLabel(
            summary,
            text="Saldo: --",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_balance.grid(row=2, column=0, sticky="w")

        # Urlaub/Krank + Logo (nach links, genug Platz fuer Text)
        TEXT_W = 340   # mehr Platz fuer Text (300..380 testen)
        LOGO_W = 110   # muss zu SIZE passen

        abs_wrap = ctk.CTkFrame(settings, fg_color="transparent")
        abs_wrap.grid(row=1, column=6, columnspan=5, padx=(12, 0), pady=(8, 10), sticky="nw")

        abs_wrap.grid_columnconfigure(0, minsize=TEXT_W)
        abs_wrap.grid_columnconfigure(1, minsize=LOGO_W)
        abs_wrap.grid_rowconfigure(0, minsize=LOGO_W)

        self.lbl_absence = ctk.CTkLabel(
            abs_wrap,
            text="Urlaub/Krank: --",
            justify="left",
            anchor="w",
            width=TEXT_W,
            wraplength=TEXT_W
        )
        self.lbl_absence.grid(row=0, column=0, sticky="nw", padx=(0, 6), pady=(12, 0))

        # Logo-Label IMMER anlegen (sonst "verschwindet" es je nach Fehlerfall)
        self.logo_label = ctk.CTkLabel(abs_wrap, text="")
        self.logo_label.grid(row=0, column=1, sticky="ne")

        # --- Logo rechts neben Urlaub/Krank (robust: erst lokal, dann optional URL) ---
        if HAS_PIL:
            try:
                SIZE = LOGO_W
                RADIUS = 2

                logo_path = os.path.join(script_dir(), LOGO_FILE)  # z.B. "logo.png" neben der .py/.exe

                img = None
                if os.path.exists(logo_path):
                    img = Image.open(logo_path).convert("RGBA")
                else:
                    # Fallback: URL (nur wenn kein lokales Logo vorhanden ist)
                    import urllib.request
                    from io import BytesIO

                    logo_url = "https://yt3.googleusercontent.com/zXzem7bbA0rm0FKIe8svIoqYl6FS3re2kqx31psWGF3W8SAzpc_kxg_N-y_LLwIHQHOc90nS8w=s900-c-k-c0x00ffffff-no-rj"
                    req = urllib.request.Request(logo_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        raw = resp.read()
                    img = Image.open(BytesIO(raw)).convert("RGBA")

                img = img.resize((SIZE, SIZE), Image.LANCZOS)
                img = round_corners_rgba(img, RADIUS)

                cimg = ctk.CTkImage(light_image=img, dark_image=img, size=(SIZE, SIZE))
                self.logo_label.configure(image=cimg, text="")
                self.logo_label.image = cimg  # wichtig gegen GC

                self.logo_label.configure(cursor="hand2")
                self.logo_label.bind(
                    "<Button-1>",
                    lambda _e: webbrowser.open_new_tab("https://waltrone1.de/wltones-admin-tools/")
                )

            except Exception:
                # wenn was schiefgeht: kein Crash, Logo bleibt einfach leer
                try:
                    self.logo_label.configure(text="")
                except Exception:
                    pass

        # Main split
        # Farbhintergrund hinter Monats und Tagesfelder
        main = ctk.CTkFrame(self, fg_color="#FFFFFF")
        main.pack(side="top", fill="both", expand=True, padx=14, pady=(0, 14))

        # Monats-Uebersicht links breiter machen
        # Linke Spalte soll nicht zusammenschrumpfen
        main.grid_columnconfigure(0, weight=0, minsize=250)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Monats-Uebersicht Farbarahmen
        CARD_RADIUS = 16  # <--- HIER definieren

        left = ctk.CTkFrame(
            main,
            fg_color="#F1F5F9",
            border_color="#E2E8F0",
            border_width=1,
            corner_radius=CARD_RADIUS
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Monats-Uebersicht", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 8), sticky="w"
        )

        # Tabellen-Inhalte groesser schreiben (Brand-Look)
        self.month_list = tk.Listbox(left, height=18)
        self.month_list.configure(
            font=("Segoe UI", 10),
            bg=BRAND_LIST_BG,
            fg=BRAND_LIST_FG,
            selectbackground=BRAND_LIST_SELECT_BG,
            selectforeground=BRAND_LIST_FG,
            highlightthickness=1,
            highlightbackground=BRAND_INPUT_BORDER,
            relief="flat",
            bd=0
        )
        self.month_list.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.month_list.bind("<<ListboxSelect>>", self.on_month_list_select)

         # Tages-Uebersicht Farbarahmen
        right = ctk.CTkFrame(
            main,
            fg_color="#F1F5F9",
            border_color="#E2E8F0",
            border_width=1,
            corner_radius=CARD_RADIUS
        )
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_rowconfigure(4, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Tage im Monat", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 8), sticky="w"
        )

        # --- Days table (Excel-like columns) ---
        table_host = tk.Frame(right)
        table_host.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")
        table_host.grid_rowconfigure(0, weight=1)
        table_host.grid_columnconfigure(0, weight=1)

        cols = ("date", "dow", "kw", "type", "start", "end", "break", "hours", "note")
        self._note_col_id = f"#{cols.index('note') + 1}"  # robust fuer Doppelklick
        self.day_tree = ttk.Treeview(table_host, columns=cols, show="headings", selectmode="browse")
        self.day_tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(table_host, orient="vertical", command=self.day_tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.day_tree.configure(yscrollcommand=vsb.set)

        self.day_tree.heading("date", text="Datum")
        self.day_tree.heading("type", text="Typ")
        self.day_tree.heading("start", text="Start")
        self.day_tree.heading("end", text="Ende")
        self.day_tree.heading("break", text="Pause")
        self.day_tree.heading("hours", text="Std")
        self.day_tree.heading("note", text="Kurznotiz")

        self.day_tree.heading("date", text="Datum")
        self.day_tree.heading("dow",  text="Tag")
        self.day_tree.heading("kw",   text="KW")
        self.day_tree.heading("type", text="Typ")
        self.day_tree.heading("start", text="Start")
        self.day_tree.heading("end", text="Ende")
        self.day_tree.heading("break", text="Pause")
        self.day_tree.heading("hours", text="Std")
        self.day_tree.heading("note", text="Kurznotiz")

        self.day_tree.column("date",  width=90,  anchor="w", stretch=False)
        self.day_tree.column("dow",   width=45,  anchor="w", stretch=False)
        self.day_tree.column("kw",    width=45,  anchor="e", stretch=False)
        self.day_tree.column("type",  width=95,  anchor="w", stretch=False)
        self.day_tree.column("start", width=70,  anchor="w", stretch=False)
        self.day_tree.column("end",   width=70,  anchor="w", stretch=False)
        self.day_tree.column("break", width=90,  anchor="e", stretch=False)
        self.day_tree.column("hours", width=70,  anchor="e", stretch=False)
        self.day_tree.column("note",  width=260, anchor="w", stretch=True)

        self.day_tree.bind("<<TreeviewSelect>>", self.on_day_select)
        self.day_tree.bind("<Double-1>", self.on_day_tree_double_click)
        
        self.day_tree.bind("<Control-c>", self.on_copy_day_ctrl)
        self.day_tree.bind("<Control-v>", self.on_paste_day_ctrl)
        self.day_tree.bind("<Control-C>", self.on_copy_day_ctrl)
        self.day_tree.bind("<Control-V>", self.on_paste_day_ctrl)
        # --- Visual feedback tags (flash) ---
        self.day_tree.tag_configure("flash_copy", background="#E6F4EA")   # hellgruen
        self.day_tree.tag_configure("flash_paste", background="#E8F0FE")  # hellblau
        # --- Clipboard/Copy-Paste Status direkt unter der Tabelle ---
        self.lbl_clip = ctk.CTkLabel(
            right,
            text="",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_clip.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="w")

        ctk.CTkLabel(right, text="Tagesbericht (lang) fuer markierten Tag:").grid(
            row=3, column=0, padx=12, pady=(0, 6), sticky="w"
        )

        # tk.Text (simpler + stabil)
        host = tk.Frame(right)
        host.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="nsew")
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)

        self.txt_report = tk.Text(host, height=8, wrap="word", font=("Segoe UI", 11))
        self.txt_report.grid(row=0, column=0, sticky="nsew")
        self.txt_report.bind("<<Modified>>", self.on_report_modified)

    # ---------- Mode ----------
    def on_mode_change(self, mode: str):
        try:
            ctk.set_appearance_mode(mode)
        except Exception:
            pass

    # ---------- Autosave ----------
    def request_autosave(self):
        self.lbl_status.configure(text="Aenderung erkannt...")
        if self.autosave_after_id is not None:
            self.after_cancel(self.autosave_after_id)
        self.autosave_after_id = self.after(self.autosave_delay_ms, self._do_autosave)

    def _do_autosave(self):
        self.autosave_after_id = None
        self._save_report_for_selected()
        if save_data(self.data):
            self.lbl_status.configure(text=f"Auto-Save ({dt.datetime.now().strftime('%H:%M:%S')})")

    def _flash_status(self, text: str, ok: bool = True, ms: int = 1200):
        # vorherigen Status merken
        prev_text = ""
        try:
            prev_text = self.lbl_status.cget("text")
        except Exception:
            prev_text = ""

        col = BRAND_GREEN if ok else COL_BAD
        try:
            self.lbl_status.configure(text=text, text_color=col)
        except Exception:
            self.lbl_status.configure(text=text)

        def _reset():
            try:
                self.lbl_status.configure(text=prev_text, text_color=None)
            except Exception:
                self.lbl_status.configure(text=prev_text)

        self.after(ms, _reset)


    def _flash_tree_item(self, iid: str, tag: str, ms: int = 700):
        try:
            cur_tags = set(self.day_tree.item(iid, "tags") or ())
            cur_tags.add(tag)
            self.day_tree.item(iid, tags=tuple(cur_tags))
        except Exception:
            return

        def _clear():
            try:
                tags2 = set(self.day_tree.item(iid, "tags") or ())
                if tag in tags2:
                    tags2.remove(tag)
                    self.day_tree.item(iid, tags=tuple(tags2))
            except Exception:
                pass

        self.after(ms, _clear)

    # ---------- Data helpers ----------
    def find_entry(self, iso: str) -> Optional[dict]:
        for e in self.data["Entries"]:
            if e["Date"] == iso:
                return e
        return None

    def ensure_entry(self, iso: str) -> dict:
        e = self.find_entry(iso)
        if e:
            return e
        ne = {"Date": iso, "Start": "", "End": "", "BreakMin": 0, "UseFixedBreak": False,
              "ShortNote": "", "Report": "", "Type": TYPE_WORK}
        self.data["Entries"].append(ne)
        self.data["Entries"].sort(key=lambda x: x["Date"])
        return ne

    def effective_break_min(self, e: dict) -> int:
        # Abwesenheiten haben nie Pause
        if e.get("Type") in ABSENCE_TYPES:
            return 0

        # Global: wenn feste Pause aktiv, gilt sie fuer alle Arbeitstage
        if bool(self.data["Settings"].get("FixedBreakEnabled", False)):
            try:
                return max(0, int(self.data["Settings"].get("FixedBreakMinutes", 0) or 0))
            except Exception:
                return 0

        # sonst normale Pause aus dem Entry
        try:
            return max(0, int(e.get("BreakMin", 0) or 0))
        except Exception:
            return 0

    def _all_month_keys(self):
        """
        Alle Monate, die irgendwo vorkommen (Entries oder Monatsziele).
        - Entries: Date -> YYYY-MM (nur wenn gueltig)
        - MonthlyTargetHours Keys: akzeptiert "YYYY-MM" oder "YYYY-MM-..." (nimmt [:7])
        Ergebnis: sortierte Liste ["2025-01", "2025-02", ...]
        """
        months = set()

        # 1) aus Entries
        for e in (self.data.get("Entries") or []):
            if not isinstance(e, dict):
                continue
            iso = str(e.get("Date", "") or "").strip()
            mk = month_key_from_iso(iso)
            if mk and len(mk) == 7:
                months.add(mk)

        # 2) aus MonthlyTargetHours Keys
        mth = self.data.get("MonthlyTargetHours") or {}
        if isinstance(mth, dict):
            for k in mth.keys():
                if not isinstance(k, str):
                    continue
                ks = k.strip()
                if len(ks) >= 7:
                    mk = ks[:7]
                    # ganz simple Plausibilitaet: "YYYY-MM"
                    if mk[4:5] == "-" and mk[:4].isdigit() and mk[5:7].isdigit():
                        m_int = int(mk[5:7])
                        if 1 <= m_int <= 12:
                            months.add(mk)

        return sorted(months)


    def _effective_month_target(self, mk: str) -> float:
        """
        Ziel fuer mk:
        1) MonthlyTargetHours[mk] wenn Zahl und > 0
        2) sonst Settings.DefaultMonthlyTargetHours wenn Zahl und > 0
        3) sonst 0
        Rueckgabe immer auf 2 Dezimalen gerundet.
        """
        def _safe_pos_float(v) -> float:
            try:
                x = float(str(v).strip().replace(",", "."))
            except Exception:
                return 0.0
            # NaN/Inf abfangen
            if x != x or x in (float("inf"), float("-inf")):
                return 0.0
            return x if x > 0.0 else 0.0

        # 1) Monatsziel direkt
        mth = self.data.get("MonthlyTargetHours") or {}
        raw = 0.0
        if isinstance(mth, dict):
            raw = _safe_pos_float(mth.get(mk, 0.0))
        if raw > 0.0:
            return round(raw, 2)

        # 2) Default
        settings = self.data.get("Settings") or {}
        default_val = 0.0
        if isinstance(settings, dict):
            default_val = _safe_pos_float(settings.get("DefaultMonthlyTargetHours", 0.0))

        return round(default_val, 2) if default_val > 0.0 else 0.0

    def _iso_next_day(self, iso: str) -> str:
        try:
            d = dt.datetime.strptime(iso, "%Y-%m-%d").date()
            return (d + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            return iso

    def _select_next_day_row(self):
        sel = self.day_tree.selection()
        if not sel:
            return

        cur = sel[0]
        kids = list(self.day_tree.get_children())

        try:
            idx = kids.index(cur)
        except ValueError:
            return

        # naechste Zeile (wenn vorhanden)
        if idx + 1 < len(kids):
            nxt = kids[idx + 1]
            self.day_tree.selection_set(nxt)
            self.day_tree.focus(nxt)
            self.day_tree.see(nxt)

            # Report / Auswahl-Logik sauber nachziehen
            try:
                self.on_day_select()
            except Exception:
                pass

    # ---------- Months ----------
    def refresh_months(self):
        # Alle Monate sammeln (Entries + MonthlyTargetHours)
        months = self._all_month_keys()

        # Fallback: wenn gar nichts vorhanden ist -> aktueller Monat
        if not months:
            months = [dt.date.today().strftime("%Y-%m")]

        displays = [month_display_from_key(mk) for mk in months]
        self._month_display_to_key = {month_display_from_key(mk): mk for mk in months}

        self.cmb_month.configure(values=displays if displays else ["--"])

    def select_default_month(self):
        today_mk = dt.date.today().strftime("%Y-%m")
        disp_today = month_display_from_key(today_mk)
        values = list(self._month_display_to_key.keys())
        if disp_today in values:
            self.cmb_month.set(disp_today)
        elif values:
            self.cmb_month.set(values[-1])
        else:
            self.cmb_month.set("--")

    def get_selected_month_key(self) -> Optional[str]:
        md = (self.cmb_month.get() or "").strip()
        return self._month_display_to_key.get(md) or month_key_from_display(md)

    def _autofill_month_target_if_missing(self):
        mk = self.get_selected_month_key()
        if not mk:
            return

        if mk in self.data["MonthlyTargetHours"] and float(self.data["MonthlyTargetHours"].get(mk, 0.0)) > 0.0:
            return

        default_val = float(self.data["Settings"].get("DefaultMonthlyTargetHours", 0.0))
        if default_val <= 0.0:
            return

        self.data["MonthlyTargetHours"][mk] = round(default_val, 2)
        try:
            self.txt_target.delete(0, "end")
            self.txt_target.insert(0, fmt2(default_val))
            self._set_entry_ok(self.txt_target)
        except Exception:
            pass

    # ---------- Month dashboard listbox ----------
    def diff_tag_text(self, diff: float) -> str:
        # simple text marker
        if diff < 0:
            return "(-)"
        if diff <= OVER_OK_MAX:
            return "(OK)"
        return "(+)"

    def compute_month_actual(self, mk: str) -> float:
        day_hours = float(self.data["Settings"].get("StandardDayHours", 8.0))
        s = 0.0
        for e in self.data["Entries"]:
            if month_key_from_iso(e["Date"]) != mk:
                continue
            t = e.get("Type", TYPE_WORK)
            if t in ABSENCE_TYPES:
                s += credit_hours_for_type(day_hours, t)
            else:
                h = calc_hours(e.get("Start", ""), e.get("End", ""), self.effective_break_min(e))
                if h is not None:
                    s += h
        return round(s, 2)

    def compute_balance_up_to(self, mk_sel: str) -> Tuple[float, float]:
        months = self._all_month_keys()
        if not months:
            return 0.0, 0.0

        carry = 0.0
        bal = 0.0

        for mk in months:
            actual = self.compute_month_actual(mk)
            target = self._effective_month_target(mk)
            diff = round(actual - target, 2)

            if mk == mk_sel:
                carry = bal
                bal = round(bal + diff, 2)
                return round(carry, 2), round(bal, 2)

            bal = round(bal + diff, 2)

        return 0.0, 0.0

    def compute_total_actual(self) -> float:
        day_hours = float(self.data["Settings"].get("StandardDayHours", 8.0))
        total = 0.0

        for e in self.data["Entries"]:
            t = e.get("Type", TYPE_WORK)
            if t in ABSENCE_TYPES:
                total += credit_hours_for_type(day_hours, t)
            else:
                h = calc_hours(
                    e.get("Start", ""),
                    e.get("End", ""),
                    self.effective_break_min(e)
                )
                if h is not None:
                    total += h

        return round(total, 2)

    def compute_total_target(self) -> float:
        total = 0.0
        for mk in self._all_month_keys():
            total += self._effective_month_target(mk)
        return round(total, 2)

    def compute_total_balance(self) -> float:
        return round(
            self.compute_total_actual() - self.compute_total_target(),
            2
        )

    def compute_absence_year(self, year: int) -> dict:
        vac = 0.0
        sick = 0.0
        for e in self.data["Entries"]:
            try:
                y = int(e["Date"][:4])
            except Exception:
                continue
            if y != year:
                continue
            t = e.get("Type", TYPE_WORK)
            if t.startswith("vac_"):
                vac += count_days_for_type(t)
            if t.startswith("sick_"):
                sick += count_days_for_type(t)
        return {"vac": round(vac, 2), "sick": round(sick, 2)}

    def refresh_month_dashboard(self):
        mk_sel = self.get_selected_month_key()
        self.month_list.delete(0, "end")

        months = self._all_month_keys()
        self._month_list_keys = months[:]  # wichtig: gleiche Reihenfolge fuer Auswahl

        bal = 0.0
        for mk in months:
            actual = self.compute_month_actual(mk)
            target = self._effective_month_target(mk)
            diff = round(actual - target, 2)
            bal = round(bal + diff, 2)

            txt = f"{month_display_from_key(mk)}  Diff {fmt2(diff)} {self.diff_tag_text(diff)}  Saldo {fmt2(bal)}"
            self.month_list.insert("end", txt)

            try:
                idx = self.month_list.size() - 1
                self.month_list.itemconfig(idx, fg=color_for_diff(diff))
            except Exception:
                pass

        # reselect
        if mk_sel and months:
            try:
                idx = months.index(mk_sel)
                self.month_list.selection_clear(0, "end")
                self.month_list.selection_set(idx)
                self.month_list.see(idx)
            except Exception:
                pass

    def on_month_list_select(self, _evt=None):
        if self._suppress_month_select:
            return
        mk_list = self._get_month_key_from_month_list_selection()
        if not mk_list:
            return
        # avoid duplicate refresh if already selected
        if self.get_selected_month_key() == mk_list:
            return
        self.cmb_month.set(month_display_from_key(mk_list))
        self.refresh_all_views(select_iso=None)

    def _get_month_key_from_month_list_selection(self) -> Optional[str]:
        sel = self.month_list.curselection()
        if not sel:
            return None
        idx = sel[0]

        months = getattr(self, "_month_list_keys", []) or []
        if 0 <= idx < len(months):
            return months[idx]
        return None

    # ---------- Days ----------
    def refresh_day_list(self, select_iso: Optional[str] = None):
        mk = self.get_selected_month_key()
        if not mk:
            return

        # Tree leeren
        for iid in self.day_tree.get_children():
            self.day_tree.delete(iid)

        entries = [e for e in self.data["Entries"] if month_key_from_iso(e["Date"]) == mk]
        entries.sort(key=lambda x: x["Date"])

        day_hours = float(self.data["Settings"].get("StandardDayHours", 8.0))

        iso_to_iid = {}
        last_kw = None
        
        for e in entries:
            t = e.get("Type", TYPE_WORK)

            # --- NEU: Wochentag + KW aus ISO-Datum ---
            dow = iso_to_weekday_de(e["Date"])   # "Mo", "Di", ...
            kw  = iso_to_kw(e["Date"])           # 1..53
            kw_disp = f"{kw:02d}" if (kw and kw != last_kw) else ""
            last_kw = kw

            # --- Stunden berechnen (wie vorher / unveraendert) ---
            if t in ABSENCE_TYPES:
                h = credit_hours_for_type(day_hours, t)
                start, end, brk = "-", "-", "-"
            else:
                h = calc_hours(
                    e.get("Start", ""),
                    e.get("End", ""),
                    self.effective_break_min(e)
                )

                start_raw = (e.get("Start", "") or "").strip()
                end_raw = (e.get("End", "") or "").strip()

                start = f"{start_raw} Uhr" if start_raw else "-"
                end = f"{end_raw} Uhr" if end_raw else "-"

                brk_val = self.effective_break_min(e)
                brk = f"{brk_val} Minuten" if brk_val > 0 else "-"

            # --- Anzeige robust machen (nur UI) ---
            hours_val = 0.0
            try:
                if h is not None:
                    hours_val = float(h)
            except Exception:
                hours_val = 0.0

            note = (e.get("ShortNote", "") or "").strip()
            if len(note) > 120:
                note = note[:120] + "..."

            iid = self.day_tree.insert(
                "", "end",
                values=(
                    iso_to_de(e["Date"]),            # date
                    dow,                             # dow (NEU)
                    kw_disp,                         # kw (nur bei Wechsel)
                    TYPE_LABELS_DE.get(t, t),        # type
                    start,
                    end,
                    brk,
                    fmt2(hours_val),
                    note
                )
            )
            iso_to_iid[e["Date"]] = iid

        # Auswahl setzen wie vorher
        if select_iso and select_iso in iso_to_iid:
            iid = iso_to_iid[select_iso]
            self.day_tree.selection_set(iid)
            self.day_tree.see(iid)
        elif entries:
            first_iid = iso_to_iid.get(entries[0]["Date"])
            if first_iid:
                self.day_tree.selection_set(first_iid)
                self.day_tree.see(first_iid)

        self._last_selected_iso = self.get_selected_iso()
        self.load_report_for_iso(self._last_selected_iso)

    def get_selected_iso(self) -> Optional[str]:
        sel = self.day_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        vals = self.day_tree.item(iid, "values")
        if not vals:
            return None
        de_date = str(vals[0])
        return de_to_iso(de_date)

    def on_day_select(self, _evt=None):
        iso = self.get_selected_iso()
        self._last_selected_iso = iso
        self.load_report_for_iso(iso)

    # ---------- Report ----------
    def _set_report_text(self, text: str):
        self.txt_report.unbind("<<Modified>>")
        self.txt_report.delete("1.0", "end")
        self.txt_report.insert("end", text)
        self.txt_report.edit_modified(False)
        self.txt_report.bind("<<Modified>>", self.on_report_modified)

    def _save_report_for_selected(self):
        iso = self._last_selected_iso
        if not iso:
            return
        e = self.ensure_entry(iso)
        e["Report"] = self.txt_report.get("1.0", "end").rstrip("\n")

    def load_report_for_iso(self, iso: Optional[str]):
        if not iso:
            self._set_report_text("")
            return
        e = self.find_entry(iso)
        self._set_report_text(e.get("Report", "") if e else "")

    def on_report_modified(self, _evt=None):
        if self.txt_report.edit_modified():
            iso = self.get_selected_iso()
            if iso:
                e = self.ensure_entry(iso)
                e["Report"] = self.txt_report.get("1.0", "end").rstrip("\n")
            self.txt_report.edit_modified(False)
            self.request_autosave()

    def refresh_settings_boxes(self):
        mk = self.get_selected_month_key()
        if not mk:
            return

        # Month target
        self.txt_target.delete(0, "end")
        self.txt_target.insert(0, fmt2(self._effective_month_target(mk)))
        self._set_entry_neutral(self.txt_target)

        # Vacation total
        self.txt_vac_total.delete(0, "end")
        self.txt_vac_total.insert(0, fmt2(float(self.data["Settings"].get("VacationTotalPerYear", 24.0))))
        self._set_entry_neutral(self.txt_vac_total)

        # Std day hours
        self.txt_day_hours.delete(0, "end")
        self.txt_day_hours.insert(0, fmt2(float(self.data["Settings"].get("StandardDayHours", 8.0))))
        self._set_entry_neutral(self.txt_day_hours)

        # ---- Feste Pause (NEU) ----
        # Checkbox-Status aus Settings setzen
        self.var_fixed_break.set(bool(self.data["Settings"].get("FixedBreakEnabled", False)))

        # Minutenfeld fuellen
        self.txt_fixed_break_min.delete(0, "end")
        self.txt_fixed_break_min.insert(0, str(int(self.data["Settings"].get("FixedBreakMinutes", 30))))
        self._set_entry_neutral(self.txt_fixed_break_min)

        # Minutenfeld nur aktiv, wenn Checkbox an
        if self.var_fixed_break.get():
            self.txt_fixed_break_min.configure(state="normal")
        else:
            self.txt_fixed_break_min.configure(state="disabled")

    def on_day_double_click(self, evt=None):
        # geklickte Zeile sauber selektieren
        try:
            iid = self.day_tree.identify_row(evt.y) if evt else ""
            if iid:
                self.day_tree.selection_set(iid)
                self.day_tree.focus(iid)
        except Exception:
            pass

        iso = self.get_selected_iso()
        if not iso:
            return

        iso_old = iso  # <<< ALT merken >>>
        e = self.ensure_entry(iso_old)

        # >>> AddDayDialog im Bearbeiten-Modus Ã¶ffnen <<<
        dlg = AddDayDialog(
            self,
            iso_to_de(iso_old),
            existing=e
        )

        # Vorhandene Werte in Dialog einsetzen
        dlg._type = e.get("Type", TYPE_WORK)
        dlg._set_type(e.get("Type", TYPE_WORK))

        # Zeiten nur bei Arbeit
        if dlg._type not in ABSENCE_TYPES:
            dlg.ent_start.insert(0, e.get("Start", "") or "")
            dlg.ent_end.insert(0, e.get("End", "") or "")
            dlg.ent_break.delete(0, "end")
            dlg.ent_break.insert(0, str(int(e.get("BreakMin", 0) or 0)))

        self.wait_window(dlg)

        if dlg.result is None:
            return

        iso_new, start, end, brk, t = dlg.result

        # --- Datum Ã¤ndern (inkl. Kollisionsschutz) ---
        if iso_new != iso_old:
            # existiert bereits ein anderer Eintrag auf diesem Datum?
            if self.find_entry(iso_new) is not None:
                messagebox.showinfo("Info", f"Datum existiert bereits: {iso_to_de(iso_new)}")
                return

            e["Date"] = iso_new
            self.data["Entries"].sort(key=lambda x: x["Date"])

        # Werte aktualisieren
        e["Type"] = t
        e["Start"] = start
        e["End"] = end
        e["BreakMin"] = brk

        # optional: falls in anderen Monat verschoben -> Monat umschalten
        new_mk = month_key_from_iso(iso_new)
        cur_mk = self.get_selected_month_key()
        if new_mk and new_mk != cur_mk:
            self.cmb_month.set(month_display_from_key(new_mk))

        self.refresh_all_views(select_iso=iso_new)
        self.request_autosave()

    def on_day_tree_double_click(self, evt):
        # Zeile + Spalte unter Maus ermitteln
        iid = self.day_tree.identify_row(evt.y)
        col = self.day_tree.identify_column(evt.x)

        if not iid:
            return

        # Wenn NICHT Kurznotiz-Spalte: normal "Tag bearbeiten"
        note_col = getattr(self, "_note_col_id", "#9")  # fallback falls nicht gesetzt
        if col != note_col:
            self.on_day_double_click(evt)
            return

        # --- Kurznotiz bearbeiten ---
        self.day_tree.selection_set(iid)
        self.day_tree.focus(iid)

        iso = self.get_selected_iso()
        if not iso:
            return

        e = self.ensure_entry(iso)
        cur = e.get("ShortNote", "") or ""

        val = simple_input_dialog(self, "Kurznotiz", "Kurznotiz fuer den Tag:", cur)
        if val is None:
            return

        e["ShortNote"] = val.strip()
        self.refresh_all_views(select_iso=iso)
        self.request_autosave()

    # ---------- Calculations ----------
    def recalc_all(self):
        mk = self.get_selected_month_key()
        if not mk:
            return

        actual = self.compute_month_actual(mk)
        target = self._effective_month_target(mk)
        diff = round(actual - target, 2)

        carry_in, balance_after = self.compute_balance_up_to(mk)

        if diff < 0:
            status = f"ZU WENIG ({fmt2(abs(diff))} h fehlen)"
        elif diff <= OVER_OK_MAX:
            status = "OK"
        else:
            status = f"ZU VIEL ({fmt2(diff)} h drueber)"

        # --- Month summary (split labels) ---
        self.lbl_month_prefix.configure(text=f"Monat {month_display_from_key(mk)}:")

        # IST hervorheben: groesser + farbig (z.B. rot wenn unter Ziel, sonst gruen)
        ist_color = COL_BAD if actual < target else COL_OK
        self.lbl_month_ist.configure(text=f"Ist {fmt2(actual)}", text_color=ist_color)

        self.lbl_month_goal.configure(text=f"| Ziel {fmt2(target)}")
        self.lbl_month_diff.configure(text=f"Diff {fmt2(diff)}")

        # Status farblich wie diff-Ampel
        self.lbl_month_status.configure(text=f"{status}", text_color=color_for_diff(diff))

        self.lbl_balance.configure(
            text=f"Uebertrag rein: {fmt2(carry_in)} h | Saldo nach Monat: {fmt2(balance_after)} h"
        )

        # --------- Gesamtwerte seit Beginn ----------
        total_actual = self.compute_total_actual()
        total_target = self.compute_total_target()
        total_balance = self.compute_total_balance()

        try:
            self.lbl_total_balance.configure(
                text=f"GESAMTSALDO: {fmt2(total_balance)} h",
                text_color=color_for_value(total_balance)
            )
        except Exception:
            pass

        # Ampel-Farbe fuer Uebertrag/Saldos (wir faerben die Zeile nach Saldo)
        try:
            self.lbl_balance.configure(text_color=color_for_value(balance_after))
        except Exception:
            pass

        y = year_from_month_key(mk) or dt.date.today().year
        totals = self.compute_absence_year(y)
        vac_total_days = float(self.data["Settings"].get("VacationTotalPerYear", 24.0))
        vac_taken = totals["vac"]
        vac_left = round(vac_total_days - vac_taken, 2)
        # Ampel-Farbe fuer Urlaub offen
        try:
            self.lbl_absence.configure(text_color=color_for_value(vac_left))
        except Exception:
            pass
        sick_taken = totals["sick"]

        self.lbl_absence.configure(
            text=(
                f"Jahr {y}\n"
                f"Urlaub total: {fmt2(vac_total_days)} Tage\n"
                f"Urlaub genommen: {fmt2(vac_taken)} Tage\n"
                f"Urlaub offen: {fmt2(vac_left)} Tage\n"
                f"Krank: {fmt2(sick_taken)} Tage"
            )
        )

    # ---------- Settings commits + highlighting ----------
    def _apply_brand_entry_style(self, entry: ctk.CTkEntry):
        entry.configure(
            fg_color=BRAND_INPUT_BG,
            border_color=BRAND_INPUT_BORDER
        )

    def _set_entry_ok(self, entry: ctk.CTkEntry):
        entry.configure(
            fg_color=BRAND_INPUT_BG,
            border_color=BRAND_GREEN
        )

    def _set_entry_bad(self, entry: ctk.CTkEntry):
        entry.configure(
            fg_color=BRAND_INPUT_BG,
            border_color=COL_BAD
        )

    def _set_entry_neutral(self, entry: ctk.CTkEntry):
        entry.configure(
            fg_color=BRAND_INPUT_BG,
            border_color=BRAND_INPUT_BORDER
        )

    def on_target_commit(self):
        mk = self.get_selected_month_key()
        if not mk:
            return
        raw = self.txt_target.get()
        ok, msg, val = validate_month_target(raw)
        if not ok:
            self.lbl_status.configure(text="Monatsziel ungueltig.")
            self._set_entry_bad(self.txt_target)
            return

        self.data["MonthlyTargetHours"][mk] = val
        self.data["Settings"]["DefaultMonthlyTargetHours"] = val  # <- DAS HIER

        self.txt_target.delete(0, "end")
        self.txt_target.insert(0, fmt2(val))
        self._set_entry_ok(self.txt_target)
        self.refresh_month_dashboard()
        self.recalc_all()
        self.request_autosave()

    def on_vac_total_commit(self):
        raw = self.txt_vac_total.get()
        ok, msg, val = validate_vac_total(raw)
        if not ok:
            self.lbl_status.configure(text="Urlaub (Tage/Jahr) ungueltig.")
            self._set_entry_bad(self.txt_vac_total)
            return
        self.data["Settings"]["VacationTotalPerYear"] = val
        self.txt_vac_total.delete(0, "end")
        self.txt_vac_total.insert(0, fmt2(val))
        self._set_entry_ok(self.txt_vac_total)
        self.recalc_all()
        self.request_autosave()

    def on_day_hours_commit(self):
        raw = self.txt_day_hours.get()
        ok, msg, val = validate_day_hours(raw)
        if not ok:
            self.lbl_status.configure(text="Std-Tag (h) ungueltig.")
            self._set_entry_bad(self.txt_day_hours)
            return
        self.data["Settings"]["StandardDayHours"] = val
        self.txt_day_hours.delete(0, "end")
        self.txt_day_hours.insert(0, fmt2(val))
        self._set_entry_ok(self.txt_day_hours)
        self.refresh_all_views(select_iso=self.get_selected_iso())
        self.request_autosave()

    # ---- Feste Pause (NEU) direkt darunter ----
    def on_fixed_break_toggle(self):
        self.data["Settings"]["FixedBreakEnabled"] = bool(self.var_fixed_break.get())

        # Minutenfeld aktiv/deaktiv
        if self.var_fixed_break.get():
            self.txt_fixed_break_min.configure(state="normal")
        else:
            self.txt_fixed_break_min.configure(state="disabled")

        self.refresh_all_views(select_iso=self.get_selected_iso())
        self.request_autosave()

    def on_fixed_break_minutes_commit(self):
        raw = (self.txt_fixed_break_min.get() or "").strip()
        ok, _msg, v = validate_break(raw)
        if not ok:
            self.lbl_status.configure(text="Feste Pause ungueltig.")
            self._set_entry_bad(self.txt_fixed_break_min)
            return

        self.data["Settings"]["FixedBreakMinutes"] = int(v)

        self.txt_fixed_break_min.delete(0, "end")
        self.txt_fixed_break_min.insert(0, str(int(v)))
        self._set_entry_ok(self.txt_fixed_break_min)

        self.refresh_all_views(select_iso=self.get_selected_iso())
        self.request_autosave()

    # ---------- Refresh all ----------
    def refresh_all_views(self, select_iso: Optional[str]):
        self.refresh_months()

        # wichtig: stellt sicher, dass Monatsziel fuer den gewaehlten Monat gesetzt wird
        self._autofill_month_target_if_missing()

        self.refresh_settings_boxes()
        self.refresh_month_dashboard()
        self.refresh_day_list(select_iso=select_iso)
        self.recalc_all()

    # ---------- Events ----------
    def on_month_changed(self, _val=None):
        self._save_report_for_selected()
        self._autofill_month_target_if_missing()
        self.refresh_all_views(select_iso=None)
        self._paste_next_iso = None

    # ---------- Actions ----------
    def on_add_day(self):
        mk = self.get_selected_month_key()
        if not mk:
            self.lbl_status.configure(text="Kein Monat ausgewaehlt.")
            return

        # Monatsziel muss gesetzt und gueltig sein (sonst kein Add-Day)
        raw = (self.txt_target.get() or "").strip()
        ok, _msg, val = validate_month_target(raw)
        if not ok:
            self._set_entry_bad(self.txt_target)
            messagebox.showinfo("Info", "Bitte zuerst ein gueltiges Monatsziel eintragen (Monatsziel (h)).")
            self.txt_target.focus_set()
            return

        today = dt.date.today()
        sug_iso = f"{mk}-01"
        if today.strftime("%Y-%m") == mk:
            sug_iso = today.strftime("%Y-%m-%d")
        sug_de = iso_to_de(sug_iso)

        dlg = AddDayDialog(self, sug_de)
        self.wait_window(dlg)
        if dlg.result is None:
            return

        iso, start, end, brk, t = dlg.result

        if self.find_entry(iso):
            messagebox.showinfo("Info", f"Datum existiert bereits: {iso_to_de(iso)}")
            return

        e = self.ensure_entry(iso)
        e["Type"] = t
        e["Start"] = start
        e["End"] = end
        e["BreakMin"] = brk

        # switch month if needed
        new_mk = month_key_from_iso(iso)

        # --- AUTO: Monatsziel fuer neuen Monat automatisch setzen ---
        if new_mk and float(self.data["MonthlyTargetHours"].get(new_mk, 0.0)) <= 0.0:
            default_val = float(self.data["Settings"].get("DefaultMonthlyTargetHours", 0.0))
            if default_val > 0:
                self.data["MonthlyTargetHours"][new_mk] = round(default_val, 2)

        if new_mk and new_mk != mk:
            self.cmb_month.set(month_display_from_key(new_mk))

        self.refresh_all_views(select_iso=iso)
        self.lbl_status.configure(text=f"Hinzugefuegt: {iso_to_de(iso)}")
        self.request_autosave()

    def _entry_border_is_bad(self, entry: ctk.CTkEntry) -> bool:
        try:
            return entry.cget("border_color") == "#c62828"
        except Exception:
            return False

    def on_delete_key(self, _evt=None):
        iso = self.get_selected_iso()
        if not iso:
            return
        if not messagebox.askyesno("Bestaetigen", f"Tag loeschen?\n{iso_to_de(iso)}"):
            return

        self._save_report_for_selected()
        self.data["Entries"] = [e for e in self.data["Entries"] if e["Date"] != iso]

        self.refresh_all_views(select_iso=None)
        self.lbl_status.configure(text=f"Geloescht: {iso_to_de(iso)}")
        self.request_autosave()

    def on_copy_day_ctrl(self, _evt=None):
        iso = self.get_selected_iso()
        if not iso:
            messagebox.showinfo("Info", "Bitte zuerst einen Tag in der Tabelle auswaehlen.")
            # iso ist hier None -> daher NICHT iso_to_de(iso)
            self.lbl_clip.configure(text="Kein Tag ausgewaehlt.", text_color=COL_BAD)
            return "break"

        e = self.find_entry(iso)
        if not e:
            messagebox.showinfo("Info", "Eintrag nicht gefunden.")
            self.lbl_clip.configure(text="Eintrag nicht gefunden.", text_color=COL_BAD)
            return "break"

        self._entry_clipboard = {
            "Type": e.get("Type", TYPE_WORK),
            "Start": e.get("Start", ""),
            "End": e.get("End", ""),
            "BreakMin": int(e.get("BreakMin", 0) or 0),
            "ShortNote": e.get("ShortNote", "") or "",
            "Report": "",
        }

        self._paste_next_iso = self._iso_next_day(iso)  # nach Copy: Default = naechster Tag

        try:
            self.clipboard_clear()
            self.clipboard_append(json.dumps(self._entry_clipboard, ensure_ascii=True))
        except Exception:
            pass

        sel = self.day_tree.selection()
        if sel:
            self._flash_tree_item(sel[0], "flash_copy", ms=700)

        # Status unter der Tabelle + optional oben (flash)
        self.lbl_clip.configure(text=f"Kopiert: {iso_to_de(iso)}", text_color=BRAND_GREEN)
        self._flash_status(f"Kopiert: {iso_to_de(iso)}", ok=True, ms=1200)

        # nach dem Kopieren direkt einen Tag weiter springen
        self._select_next_day_row()

        return "break"

    def on_paste_day_ctrl(self, _evt=None):
        src = self._entry_clipboard

        if not src:
            try:
                clip = self.clipboard_get()
                src = json.loads(clip)
            except Exception:
                src = None

        if not isinstance(src, dict):
            messagebox.showinfo("Info", "Zwischenablage ist leer oder ungueltig. Erst Tag markieren und Strg+C.")
            self.lbl_clip.configure(
                text="Zwischenablage leer/ungueltig. Erst Tag markieren und Strg+C.",
                text_color=COL_BAD
            )
            return "break"
            
        base_iso = self._paste_next_iso or self.get_selected_iso() or dt.date.today().strftime("%Y-%m-%d")

        ans = messagebox.askquestion(
            "Einfuegen",
            "Wie moechtest du einfuegen?",
            icon="question",
            type="yesnocancel",
            default="no",      # default = Einzeldatum
            detail="Ja = Bereich (Von/Bis)\nNein = Einzeldatum\nAbbrechen = nichts tun"
        )
        if ans == "cancel":
            return "break"
        use_range = (ans == "yes")

        # ---------- Einzelnes Datum (wie bisher) ----------
        if not use_range:
            default_de = iso_to_de(base_iso)

            target_de = simple_input_dialog(self, "Einfuegen", "Zieldatum (DD.MM.YYYY):", default_de)
            if target_de is None:
                return "break"

            target_iso = de_to_iso(target_de)
            if not target_iso:
                messagebox.showinfo("Info", "Datum ungueltig. Bitte DD.MM.YYYY nutzen.")
                return "break"

            existing = self.find_entry(target_iso)
            if existing:
                if not messagebox.askyesno(
                    "Bestaetigen",
                    f"Am {iso_to_de(target_iso)} existiert schon ein Eintrag.\nUeberschreiben?"
                ):
                    return "break"
                e = existing
            else:
                e = self.ensure_entry(target_iso)

            e["Type"] = src.get("Type", TYPE_WORK)
            e["Start"] = src.get("Start", "")
            e["End"] = src.get("End", "")
            e["BreakMin"] = int(src.get("BreakMin", 0) or 0)
            e["ShortNote"] = src.get("ShortNote", "") or ""
            e["Report"] = ""

            if e["Type"] in ABSENCE_TYPES:
                e["Start"] = ""
                e["End"] = ""
                e["BreakMin"] = 0

            mk = month_key_from_iso(target_iso)
            if mk and mk != self.get_selected_month_key():
                self.cmb_month.set(month_display_from_key(mk))

            self.refresh_all_views(select_iso=target_iso)
            self.request_autosave()

            # naechstes Default-Datum merken (1 Tag weiter)
            self._paste_next_iso = self._iso_next_day(target_iso)

            # optional: Auswahl im Tree 1 Zeile weiter
            self.after(10, self._select_next_day_row)

            self.lbl_clip.configure(text=f"Eingefuegt nach: {iso_to_de(target_iso)}", text_color=BRAND_GREEN)

            sel = self.day_tree.selection()
            if sel:
                self._flash_tree_item(sel[0], "flash_paste", ms=700)
            self._flash_status(f"Eingefuegt nach: {iso_to_de(target_iso)}", ok=True, ms=1400)

            return "break"

        # ---------- Bereich Von/Bis ----------
        default_from = iso_to_de(base_iso)

        from_de = simple_input_dialog(self, "Bereich einfuegen", "Von (DD.MM.YYYY):", default_from)
        if from_de is None:
            return "break"

        to_de = simple_input_dialog(self, "Bereich einfuegen", "Bis (DD.MM.YYYY):", from_de)
        if to_de is None:
            return "break"

        from_iso = de_to_iso(from_de)
        to_iso = de_to_iso(to_de)
        if not from_iso or not to_iso:
            messagebox.showinfo("Info", "Datum ungueltig. Bitte DD.MM.YYYY nutzen.")
            return "break"

        d1 = dt.datetime.strptime(from_iso, "%Y-%m-%d").date()
        d2 = dt.datetime.strptime(to_iso, "%Y-%m-%d").date()
        if d2 < d1:
            messagebox.showinfo("Info", "Bis-Datum liegt vor Von-Datum.")
            return "break"

        ans = messagebox.askquestion(
            "Wochenende",
            "Wochenenden behandeln:",
            icon="question",
            type="yesnocancel",
            default="no",   # default = ohne Sa/So (meist sinnvoll)
            detail="Ja = Mit Sa/So einfuegen\nNein = Ohne Sa/So (Sa/So ueberspringen)\nAbbrechen = nichts tun"
        )
        if ans == "cancel":
            return "break"
        include_weekend = (ans == "yes")

        ans = messagebox.askquestion(
            "Vorhandene Eintraege",
            "Was soll mit bestehenden Eintraegen passieren?",
            icon="warning",
            type="yesnocancel",
            default="no",  # default = ueberspringen (sicherer)
            detail="Ja = Ueberschreiben\nNein = Ueberspringen\nAbbrechen = nichts tun"
        )
        if ans == "cancel":
            return "break"
        overwrite = (ans == "yes")

        count_done = 0
        last_iso = None

        cur = d1
        while cur <= d2:
            wd = cur.weekday()  # 0=Mo ... 5=Sa 6=So
            if (wd >= 5) and (not include_weekend):
                cur += dt.timedelta(days=1)
                continue

            iso = cur.strftime("%Y-%m-%d")
            existing = self.find_entry(iso)

            if existing and not overwrite:
                cur += dt.timedelta(days=1)
                continue

            e = existing if existing else self.ensure_entry(iso)

            e["Type"] = src.get("Type", TYPE_WORK)
            e["Start"] = src.get("Start", "")
            e["End"] = src.get("End", "")
            e["BreakMin"] = int(src.get("BreakMin", 0) or 0)
            e["ShortNote"] = src.get("ShortNote", "") or ""
            e["Report"] = ""

            if e["Type"] in ABSENCE_TYPES:
                e["Start"] = ""
                e["End"] = ""
                e["BreakMin"] = 0

            count_done += 1
            last_iso = iso
            cur += dt.timedelta(days=1)

        if not last_iso:
            self._flash_status("Nichts eingefuegt (alles uebersprungen).", ok=False, ms=2000)
            return "break"

        mk = month_key_from_iso(last_iso)
        if mk and mk != self.get_selected_month_key():
            self.cmb_month.set(month_display_from_key(mk))

        self.refresh_all_views(select_iso=last_iso)
        self.request_autosave()

        sel = self.day_tree.selection()
        if sel:
            self._flash_tree_item(sel[0], "flash_paste", ms=700)

        we_txt = "inkl Sa/So" if include_weekend else "ohne Sa/So"
        
        # naechstes Default-Datum merken (1 Tag nach dem letzten eingefuegten Tag)
        self._paste_next_iso = self._iso_next_day(last_iso)

        # optional: Auswahl im Tree 1 Zeile weiter
        self.after(10, self._select_next_day_row)
        
        self._flash_status(
            f"Bereich eingefuegt: {count_done} Tage ({from_de} - {to_de}, {we_txt})",
            ok=True,
            ms=2200
        )

        return "break"

    def on_save(self):
        self._save_report_for_selected()

        # normalize data for work entries
        for e in self.data["Entries"]:
            t = e.get("Type", TYPE_WORK)
            if t in ABSENCE_TYPES:
                e["Start"] = ""
                e["End"] = ""
                e["BreakMin"] = 0
                continue

            if (e.get("Start") or "").strip():
                n = normalize_time_input(e["Start"])
                if not n:
                    messagebox.showinfo("Info", f"{iso_to_de(e['Date'])}: Start ungueltig.")
                    return
                e["Start"] = n
            if (e.get("End") or "").strip():
                n = normalize_time_input(e["End"])
                if not n:
                    messagebox.showinfo("Info", f"{iso_to_de(e['Date'])}: Ende ungueltig.")
                    return
                e["End"] = n

        if save_data(self.data):
            self.lbl_status.configure(text=f"Gespeichert ({dt.datetime.now().strftime('%H:%M:%S')})")

    def on_open_folder(self):
        try:
            os.startfile(script_dir())
        except Exception as ex:
            messagebox.showerror("Fehler", f"Ordner konnte nicht geoeffnet werden:\n{ex}")

    def on_reset_all(self):
        if not messagebox.askyesno(
            "Bestaetigen",
            "Wirklich ALLES zuruecksetzen?\n\n"
            "- Alle Tage/Eintraege werden geloescht\n"
            "- Alle Monatsziele werden geloescht\n"
            "- Einstellungen werden auf Standard gesetzt\n\n"
            "Das kann nicht rueckgaengig gemacht werden."
        ):
            return

        # laufenden Autosave abbrechen
        try:
            if self.autosave_after_id is not None:
                self.after_cancel(self.autosave_after_id)
                self.autosave_after_id = None
        except Exception:
            pass

        # Report sicherheitshalber noch einmal in die Daten schreiben (falls was offen war)
        try:
            self._save_report_for_selected()
        except Exception:
            pass

        # Alles neu
        self.data = new_empty_data()
        save_data(self.data)

        # Copy/Paste-Zwischenablage leeren
        self._entry_clipboard = None
        self._paste_next_iso = None

        # UI neu aufbauen
        self.refresh_months()
        self.select_default_month()
        self.refresh_all_views(select_iso=None)

        self.lbl_status.configure(text="Zurueckgesetzt.")


    def on_close(self):
        # laufenden Autosave abbrechen
        try:
            if self.autosave_after_id is not None:
                self.after_cancel(self.autosave_after_id)
                self.autosave_after_id = None
        except Exception:
            pass

        # Report speichern + Daten schreiben
        try:
            self._save_report_for_selected()
        except Exception:
            pass

        save_data(self.data)
        self.destroy()

# ---------- Simple input dialog ----------
def simple_input_dialog(parent, title: str, label: str, default: str) -> Optional[str]:
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.grab_set()

    frm = ctk.CTkFrame(dlg)
    frm.pack(padx=14, pady=14, fill="both", expand=True)

    ctk.CTkLabel(frm, text=label).grid(row=0, column=0, sticky="w", pady=(0, 8))
    ent = ctk.CTkEntry(frm, width=420)
    ent.grid(row=1, column=0, sticky="w", pady=(0, 10))
    ent.insert(0, default or "")
    ent.focus_set()
    ent.select_range(0, "end")

    res = {"val": None}

    def ok():
        res["val"] = ent.get()
        dlg.destroy()

    def cancel():
        res["val"] = None
        dlg.destroy()

    row = ctk.CTkFrame(frm, fg_color="transparent")
    row.grid(row=2, column=0, sticky="e")

    ctk.CTkButton(row, text="OK", width=110, command=ok).grid(row=0, column=0, padx=(0, 10))
    ctk.CTkButton(row, text="Abbrechen", width=110, fg_color="#777777", hover_color="#666666", command=cancel).grid(row=0, column=1)

    dlg.bind("<Return>", lambda _e: ok())
    dlg.bind("<Escape>", lambda _e: cancel())

    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    w = dlg.winfo_width()
    h = dlg.winfo_height()
    dlg.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")

    parent.wait_window(dlg)
    return res["val"]

# ---------- main ----------
def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
