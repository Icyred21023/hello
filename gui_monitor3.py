

import tkinter as tk
import config
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab,  ImageDraw, ImageChops,ImageOps
import os
import random
from typing import Any, Literal
import sys
from fGui_Ui import SuperFrame, HeroImager
USED_HERO_BGS = []
DB = None
icon_idx =0
MANUAL_DEBUG = 1
import helpers
if not config.mobile_mode:
    from fonts_registry import register_ttf_private
#from main3 import HeroMatch
#import numpy as np
import config
bLiveDebug = False
bLiveDebug = False
bTrackerDebug = False
bTrackerNames = ["EyeingFlux", "AtlasCarried", "BicZilla", "Kaes", "ProfChloroform"]
bUseRivalsDataNames = True
#if bUseRivalsDataNames:
#    import curlRivals



if not config.mobile_mode:
    
    import win32gui
    import win32con
    import win32api
    # import win32process
    # import win32com.client
    # import ctypes
    import keyboard

    import ctypes
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    BASE_DPI = 96
    dpi = user32.GetDpiForSystem()

# =========================
# Monitor selection helpers (Windows desktop)
# =========================
MONITOR_CONFIG_PATH = os.path.join(config.script_dir, "monitor_selection.json")


def get_monitors():
    """Return all Windows monitors in virtual-desktop coordinates."""
    if config.mobile_mode:
        return []

    monitors = []
    try:
        for index, (handle, _hdc, _rect) in enumerate(win32api.EnumDisplayMonitors()):
            info = win32api.GetMonitorInfo(handle)
            left, top, right, bottom = info["Monitor"]
            monitors.append({
                "index": index,
                "handle": handle,
                "device": info.get("Device", f"DISPLAY{index + 1}"),
                "left": int(left),
                "top": int(top),
                "right": int(right),
                "bottom": int(bottom),
                "width": int(right - left),
                "height": int(bottom - top),
                "primary": bool(info.get("Flags", 0) & 1),
            })
    except Exception as e:
        print(f"Monitor enumeration failed: {e}")

    return monitors


def load_monitor_selection(monitors):
    """Load saved monitor. Prefer device name so monitor ordering can change."""
    if not monitors:
        return 0

    try:
        with open(MONITOR_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        saved_device = data.get("device")
        if saved_device:
            for i, mon in enumerate(monitors):
                if mon.get("device") == saved_device:
                    return i

        saved_index = int(data.get("index", 0))
        if 0 <= saved_index < len(monitors):
            return saved_index
    except Exception:
        pass

    # Default to the first non-primary monitor when one exists.
    for i, mon in enumerate(monitors):
        if not mon.get("primary"):
            return i
    return 0


def save_monitor_selection(index, monitors):
    if not monitors:
        return
    index = max(0, min(int(index), len(monitors) - 1))
    mon = monitors[index]
    try:
        with open(MONITOR_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "index": index,
                "device": mon.get("device"),
            }, f, indent=4)
    except Exception as e:
        print(f"Could not save monitor selection: {e}")


SHEETS_DIR = os.path.join(config.script_dir, "assets_match_hd")
CROP_CACHE_PATH = os.path.join(SHEETS_DIR, "_mastery_crop_cache.json")
import _Mastery_Sheet_Editor 
crop_cache = _Mastery_Sheet_Editor.load_crop_cache(CROP_CACHE_PATH) if os.path.exists(CROP_CACHE_PATH) else {}
bTest = True
bSpecialBG = False
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageChops

def punch_text_out_of_image(
    img_rgba: Image.Image,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: int = 255,
    text_anchor: str = "lt",
) -> Image.Image:
    """
    Returns a new RGBA image where alpha is cleared (transparent)
    ONLY where the text is drawn.
    """
    img = img_rgba.convert("RGBA")
    w, h = img.size

    # 1) Build a text mask (white text on black background)
    text_mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(text_mask)
    d.text(xy, text, fill=fill, font=font, anchor=text_anchor)

    # 2) Subtract text mask from existing alpha
    r, g, b, a = img.split()
    new_a = ImageChops.subtract(a, text_mask)  # alpha reduced where text is
    img.putalpha(new_a)
    return img
def split_edges(total: int, parts: int) -> list[int]:
        base = total // parts
        rem = total % parts
        edges = [0]
        acc = 0
        for i in range(parts):
            acc += base + (1 if i < rem else 0)
            edges.append(acc)
        return edges



script_dir = os.path.dirname(os.path.abspath(__file__))
assets_nameplates = os.path.join(script_dir, "assets_nameplates")
assets_lords = os.path.join(script_dir, "assets_match_hd")
assets_chars = os.path.join(script_dir, "assets_characters_hd")
assets_ui = os.path.join(script_dir, "assets_ui")

CACHED_IMGS = {}


import time
t = time.perf_counter()
for path_folder in [assets_chars, assets_ui]:
    for filename in os.listdir(path_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(path_folder, filename)
            CACHED_IMGS[key] = Image.open(path)
            


def image_loader(img_key):
    img_raw = CACHED_IMGS.get(img_key) or CACHED_IMGS.get("Default")
    if not img_raw:

        for directory in [assets_nameplates,assets_lords]:

            try:
                img_path = os.path.join(directory, f"{img_key}.png")
                img_raw = Image.open(img_path)
                
                CACHED_IMGS[img_key] = img_raw  # Cache it

            except FileNotFoundError:
                #print(f"Image not found: {img_key} in {directory}")
                continue

        if not img_raw:
            return False
    return img_raw

    
            



dpi = 120
BASE_DPI = 96
NAMEPLATES = []
BASE_DPI_SCALE = 96 / 72  # 96 DPI = 1.333 scaling internally

RANK_FG = {
    "eternity": "#FAC4FF",
    "celestial": "#FAA141",
    "grandmaster": "#D3A7FB",
    "diamond": "#8FBAFF",
    "platinum": "#3ABCD5",
    "gold": "#FCDA30",
    "silver": "#BBD5E1",
    "bronze": "#D98B6D",

}

RANK_FG2 = {
    "eternity": "#fa8df4",
    "celestial": "#FAA141",
    "grandmaster": "#be8eff",
    "diamond": "#8FBAFF",
    "platinum": "#3ABCD5",
    "gold": "#FCDA30",
    "silver": "#BBD5E1",
    "bronze": "#D98B6D",

}
HERO_MASTERY_OFFSETS = {
            # ( x, y )
            # x: + RIGHT, - left
            # y: + DOWN, - UP
                  "Adam Warlock":(0,0),
                  "Angela":(0,0),
                  "Black Panther":(0,-32),
                  "Black Widow":(-2,-16),
                  "Blade":(0,0),
                  "Bruce Banner":(0,0),
                  "Captain America":(0,0),
                  "Cloak & Dagger":(-25,0),
                    "Daredevil":(5,-22),
                    "Deadpool":(-5,-14),
                    "Deadpool (Vanguard)":(-5,-14),
                    "Deadpool (Duelist)":(-5,-14),
                    "Deadpool (Strategist)":(-5,-14),
                    "Doctor Strange":(4,-32),
                    "Emma Frost":(0,-32),
                    "Gambit":(3,10),
                    "Groot":(0,0),
                    "Hawkeye":(0,0),
                    "Hela":(0,-25),
                    "Human Torch":(0,0),
                  "Invisible Woman":(0,-32),
                  "Iron Fist":(0,0),
                  "Iron Man":(0,0),
                  "Jeff The Land Shark":(0,-32),
                  "Loki":(7,-10),
                  "Luna Snow":(11,0),
                    "Magik":(0,0),
                    "Magneto":(0,-22),
                    "Mantis":(0,0),
                    "Mister Fantastic":(0,-20),
                    "Moon Knight":(-7,-7),
                    "Namor":(7,-7),
                    "Peni Parker":(0,0),
                    "Phoenix":(-10,-20),
                    "Psylocke":(0,0),
                  "Rocket Raccoon":(11,-5),
                  "Rogue": (10,-15),
                  "Scarlet Witch":(4,-10),
                  "Spider-Man":(0,-25),
                  "Squirrel Girl":(5,-32),
                    "Star-Lord":(0,0),
                    "Storm":(0,0),
                    "The Punisher":(0,0),
                    "The Thing":(0,0),
                    "Thor":(0,0),
                    "Ultron":(0,0),
                    "Venom":(10,-25),
                    "Winter Soldier":(0,0),
                    "Wolverine":(0,-5)
                    }

HERO_MASTERY_OFFSETS = {
            # ( x, y )
            # x: + RIGHT, - left
            # y: + DOWN, - UP
                  "Adam Warlock":(0,0),
                  "Angela":(0,0),
                  "Black Panther":(0,0),
                  "Black Widow":(0,0),
                  "Blade":(0,0),
                  "Bruce Banner":(0,0),
                  "Captain America":(0,0),
                  "Cloak & Dagger":(0,0),
                    "Daredevil":(0,0),
                    "Deadpool":(0,0),
                    "Deadpool (Vanguard)":(0,0),
                    "Deadpool (Duelist)":(0,0),
                    "Deadpool (Strategist)":(0,0),
                    "Doctor Strange":(0,0),
                    "Emma Frost":(0,0),
                    "Gambit":(0,0),
                    "Groot":(0,0),
                    "Hawkeye":(0,0),
                    "Hela":(0,0),
                    "Human Torch":(0,0),
                  "Invisible Woman":(0,0),
                  "Iron Fist":(0,0),
                  "Iron Man":(0,0),
                  "Jeff The Land Shark":(0,0),
                  "Loki":(0,0),
                  "Luna Snow":(0,0),
                    "Magik":(0,0),
                    "Magneto":(0,0),
                    "Mantis":(0,0),
                    "Mister Fantastic":(0,0),
                    "Moon Knight":(0,0),
                    "Namor":(0,0),
                    "Peni Parker":(0,0),
                    "Phoenix":(0,0),
                    "Psylocke":(0,0),
                  "Rocket Raccoon":(0,0),
                  "Rogue": (0,0),
                  "Scarlet Witch":(0,0),
                  "Spider-Man":(0,0),
                  "Squirrel Girl":(0,0),
                    "Star-Lord":(0,0),
                    "Storm":(0,0),
                    "The Punisher":(0,0),
                    "The Thing":(0,0),
                    "Thor":(0,0),
                    "Ultron":(0,0),
                    "Venom":(0,0),
                    "Winter Soldier":(0,0),
                    "Wolverine":(0,0)
                    }

HERO_SHORT_NAMES = {"Adam Warlock":"Warlock",
                  "Angela":"Angela",
                  "Black Panther":"Panther",
                  "Black Widow":"Widow",
                  "Blade":"Blade",
                  "Bruce Banner":"Hulk",
                  "Captain America":"Captain",
                  "Cloak & Dagger":"Cloak",
                    "Daredevil":"Daredevil",
                    "Deadpool (Vanguard)":"Deadpool",
                    "Deadpool (Duelist)":"Deadpool",
                    "Deadpool (Strategist)":"Deadpool",
                    "Devil Dinosaur":"Dinosaur",
                    "Doctor Strange":"Strange",
                    "Elsa Bloodstone":"Elsa",
                    "Emma Frost":"Emma",
                    "Gambit":"Gambit",
                    "Groot":"Groot",
                    "Hawkeye":"Hawkeye",
                    "Hela":"Hela",
                    "Human Torch":"Torch",
                  "Invisible Woman":"Invisible",
                  "Iron Fist":"Iron Fist",
                  "Iron Man":"Iron Man",
                  "Jeff The Land Shark":"Jeff",
                  "Loki":"Loki",
                  "Luna Snow":"Luna Snow",
                    "Magik":"Magik",
                    "Magneto":"Magneto",
                    "Mantis":"Mantis",
                    "Mister Fantastic":"Fantastic",
                    "Moon Knight":"MoonKnight",
                    "Namor":"Namor",
                    "Peni Parker":"Peni",
                    "Phoenix":"Phoenix",
                    "Psylocke":"Psylocke",
                  "Rocket Raccoon":"Rocket",
                  "Rogue": "Rogue",
                  "Scarlet Witch":"Scarlet",
                  "Spider-Man":"Spidey",
                  "Squirrel Girl":"Squirrel",
                    "Star-Lord":"Star-Lord",
                    "Storm":"Storm",
                    "The Punisher":"Punisher",
                    "The Thing":"Thing",
                    "Thor":"Thor",
                    "Ultron":"Ultron",
                    "Venom":"Venom",
                    "Winter Soldier":"Winter",
                    "Wolverine":"Wolverine"}

SPECIAL_IMAGE_MAP = None
root = tk.Tk()

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
w2 = screen_w
h2 = screen_h
if config.mobile_mode:
    if w2 < h2:
        screen_w = h2
        screen_h = w2
print(f'screen w: {screen_w}')
print(f'screen h: {screen_h}')
BASE_W, BASE_H = 2440, 1440  # whatever resolution you originally designed for
scale_x = screen_w / BASE_W
scale_y = screen_h / BASE_H
SCALE = min(scale_x, scale_y)  # preserve aspect ratio
root.destroy()
TARGET_DPI_SCALE = (SCALE * 96) / 72 
print(SCALE)
if config.mobile_mode:
   
    SCALE =TARGET_DPI_SCALE
def s(v):
    if isinstance(v, (tuple, list)):
        return tuple(int(x * SCALE) for x in v)
    return int(v * SCALE)

def create_root(scale=None):
    if scale:
        s = scale
    else:
        s = TARGET_DPI_SCALE
    root = tk.Tk()
    root.tk.call('tk', 'scaling', s)
    return root
font_families = set()
hide_function, debug_frame_global, main_frame_global, hide_button_global = None, None, None, None
BG_PATH = helpers.create_path("season_bg2.png", 'gui_assets')
BG_IMG = Image.open(BG_PATH)
hotkeyoo = None
NAME_BANNER = "#2D304B"
SEASON_BANNER = "#1F252B"
HERO_BG = "#1C2126"   #"#1C2126"
HERO_STATS_BG = "#2E3643"   
def create_teamup_image_map(icon_folder):
    image_map = {}
    for filename in os.listdir(icon_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(icon_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead
    return image_map
def list_fonts(filename=helpers.create_path("__FONTS.txt", "debug")):

    families = sorted(set(tkFont.families(root)))
    weights = ["normal", "bold"]
    slants = ["roman", "italic"]

    with open(filename, "w", encoding="utf-8") as f:

        for fam in families:
            

            f.write(f"\nFamily: {fam}\n")

            for w in weights:
                for s in slants:
                    try:
                        font_obj = tkFont.Font(family=fam, size=12, weight=w, slant=s)

                        # Tk falls back silently if style doesn't exist
                        actual = font_obj.actual()

                        f.write(
                            f"  Style: weight={actual['weight']}, slant={actual['slant']}\n"
                        )

                    except tk.TclError:
                        pass
def list_fonts2():

    families = sorted(set(tkFont.families(root)))
    weights = ["normal", "bold"]
    slants = ["roman", "italic"]

    for fam in families:
        if "tt" not in fam.lower():
            continue
        print(f"\nFamily: {fam}")
        for w in weights:
            for s in slants:
                try:
                    f = tkFont.Font(family=fam, size=12, weight=w, slant=s)
                    # Tk falls back silently if the combo doesn’t exist, so check actual font info
                    actual = f.actual()
                    print(f"  Style: weight={actual['weight']}, slant={actual['slant']}")
                except tk.TclError:
                    pass

def load_font(family_name, font_file_name):
    font_path = os.path.join(os.path.dirname(__file__), "fonts", font_file_name)

    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # On Tkinter, you can load a TTF directly with @path
    return f"@{font_path}"
    #font_families.add(family_name)

fonts_list = ["Rajdhani.ttf", "Rajdhani Medium.ttf", 'Rajdhani SemiBold.ttf',"Rajdhani Bold.ttf",
              "Saira Semi Condensed Medium.ttf",
              'SairaCondensed-Medium.ttf','SairaCondensed-Bold.ttf','SairaCondensed-Regular.ttf','SairaCondensed-SemiBold.ttf','SairaCondensed-Thin.ttf','SairaCondensed-ExtraBold.ttf',
              "Saira Thin Medium.ttf",'SairaExtraCondensed-Medium.ttf','SairaExtraCondensed-Bold.ttf','SairaExtraCondensed-Regular.ttf','SairaExtraCondensed-SemiBold.ttf','SairaExtraCondensed-Thin.ttf',
              'Saira_SemiCondensed-Medium.ttf','Saira_SemiCondensed-Black.ttf', 'Saira_SemiCondensed-Bold.ttf','Saira_SemiCondensed-ExtraBold.ttf','Saira_SemiCondensed-Medium.ttf','Saira_SemiCondensed-Regular.ttf', 'Saira_SemiCondensed-SemiBold.ttf','Saira_SemiCondensed-Thin.ttf',
              'Saira-Black.ttf','Saira-Bold.ttf','Saira-ExtraBold.ttf','Saira-Light.ttf','Saira-Medium.ttf','Saira-Regular.ttf','Saira-SemiBold.ttf','Saira-Thin.ttf',
              "Refrigerator-Deluxe-Bold.ttf","Refrigerator-Deluxe-Heavy.ttf", 'Refrigerator-Deluxe-Extrabold.ttf', 'Refrigerator-Deluxe.ttf','Refrigerator-Deluxe-Light.ttf',
              'KelsonSans.ttf','KelsonSansBold.ttf',
              "Exo Demi Bold.ttf","Exo Light.ttf",
              "Roboto_SemiCondensed-Bold.ttf","Roboto_SemiCondensed-Medium.ttf","Roboto_SemiCondensed-Regular.ttf","Roboto_SemiCondensed-SemiBold.ttf",
              "Roboto-Regular.ttf","Roboto-Bold.ttf","Roboto-Medium.ttf","Roboto-SemiBold.ttf",
              "CarbonRegular.ttf","CarbonBold Italic.ttf","CarbonRegular Italic.ttf",
              "Cairo Black.ttf","Cairo Bold.ttf",
              'TT_Supermolot_Neue_Bold.ttf','TT_Supermolot_Neue_Bold_Italic.ttf', 
              'TT_Supermolot_Neue_DemiBold_Italic.ttf','TT_Supermolot_Neue_DemiBold.ttf',
              'TT_Supermolot_Neue_Medium.ttf','TT_Supermolot_Neue_Medium_Italic.ttf',
              'TT_Supermolot_Neue_Condensed_ExtraBold.ttf',
              'Neue_Condensed_Bold.ttf', 'S.ttf','TTSCMD.ttf','Neue_Condensed_Medium.ttf', 'Neue_Condensed_DemiBold.ttf','Neue_Condensed_DemiBold_Italic.ttf', 'Neue_Condensed_Bold_Italic.ttf',
              'TT_Supermolot_Neue_Italic.ttf', 'TT_Supermolot_Neue_Regular.ttf','TTSupermolotCondensed-ThinItalic.ttf','TTSupermolotCondensed-Thin.ttf','TTSupermolotCondensed-LightItalic.ttf','TTSupermolotCondensed-Light.ttf','TTSupermolotCondensed-Italic.ttf',
              'TT-Supermolot-Neue-Trial-Condensed-Thin-BF65fcfb4d4e8d0.ttf','TT-Supermolot-Neue-Trial-Condensed-Thin-Italic-BF65fcfb4d47398.ttf','TT-Supermolot-Neue-Trial-Condensed-Medium-Italic-BF65fcfb4d300d5.ttf','TT-Supermolot-Neue-Trial-Condensed-Light-BF65fcfb4d352d8.ttf','TT-Supermolot-Neue-Trial-Condensed-Italic-BF65fcfb4d44da1.ttf','TT-Supermolot-Neue-Trial-Condensed-Light-Italic-BF65fcfb4d453ff.ttf',]
font_names = [os.path.splitext(f)[0] for f in fonts_list]
rajdhani = font_names[0] # Normal or Bold
rajdhani_medium = font_names[1] # Normal or Bold
saira_semi = 'Saira SemiCondensed Medium' # Normal or Bold
saira_thin = 'Saira Thin Medium' # Normal or Bold
refrig_bold = 'Refrigerator Deluxe' # Bold
refrig_heavy = 'Refrigerator Deluxe Heavy' # Bold
exo = 'Exo' # Normal or Bold
carbon = 'CarbonRegular' # Normal or Bold
carbon_italic = 'CarbonRegular Italic' # Normal or Bold
carbon_bold_italic = 'CarbonBold Italic' # Normal or Bold

def fonttk_obj(family, size=12, weight="normal", **kwargs):
    font = tkFont.Font(family=family, size=size, weight=weight)
    if "linespace" in kwargs:
        font.configure(linespace=kwargs["linespace"])
    return font


def fonttk(family, *args, size=None, weight="normal",
           italic=False, underline=False, overstrike=False):
    """Flexible Tk font tuple builder."""
    if args:
        if len(args) == 1:
            a = args[0]
            if isinstance(a, str):
                weight = a
            else:
                size = s(a)
        elif len(args) >= 2:
            a, b = args[0], args[1]
            if isinstance(a, str):
                weight, size = a, s(b)
            elif isinstance(b, str):
                size, weight = s(a), b
            else:
                size = s(a)

    if size is None:
        size = s(12)

    # Normalize
    w = (str(weight).lower() if isinstance(weight, str) else weight)
    weight_map = {
        "regular": "normal", "normal": "normal", "book": "normal",
        "light": "normal", "thin": "normal", "medium": "normal",
        "demi": "bold", "demibold": "bold", "semibold": "bold",
        "bold": "bold", "heavy": "bold", "black": "bold", "extrabold": "bold",
    }
    if isinstance(w, (int, float)):
        w = "bold" if w >= 600 else "normal"
    w = weight_map.get(w, "bold" if w in ("700", "800", "900") else "normal")

    # Adjust for internal naming
    family_lower = family.lower()
    if "bd" in family_lower or "bold" in family_lower:
        w = "normal"
    if "it" in family_lower or "italic" in family_lower:
        italic = False  # already italic face

    styles = []
    if w == "bold":
        styles.append("bold")
    if italic:
        styles.append("italic")
    if underline:
        styles.append("underline")
    if overstrike:
        styles.append("overstrike")

    return (family, int(size), *styles)




_registered_fonts = set()
def call_register_fonts(root: tk.Tk, fonts_list=fonts_list):
    """Load TTFs privately for this process and refresh Tk once.
    Returns (loaded_paths, available_families_set)."""
    #print("Registering fonts...")
    if fonts_list is None:
        fonts_list = []  # or provide your default list here

    base = os.path.join(os.path.dirname(__file__), "fonts")
    loaded = []

    for font_file in fonts_list:
        path = os.path.join(base, font_file)

        if not os.path.exists(path):
            print(f"Font file not found: {path}")
            continue

        if path in _registered_fonts:
            # Already loaded once in this process
            #print(f"Font file already registed: {font_file}")
            continue

        try:
            ok = register_ttf_private(path)  # should return True if OS accepted the font
            if ok:
                _registered_fonts.add(path)
                loaded.append(path)
                num = len(loaded)
                #print(f"{num}: {font_file} registered.")
        except Exception as e:
            print(f"Error loading font {font_file}: {e}")

    # Refresh Tk’s font list once after batch
    if loaded:
        root.update_idletasks()

    families = set(tkFont.families(root))
    return loaded, families

lock = None
bhidden = False
bHide = False
bdebug_menu = False
is_clickthrough = False
indicator_label = None
hwnd = None
global_random_matchup = False
global_random_ban = False
global_dex = False
global_debugmode = False
global_debugflag = False
main = None
var1 = None
var2 = None
trigger2_func = None
trigger_func = None
root = None
cb1 = None
cb2 = None
cb3 = None


fonts = {}



def handle_f8():
    global main, var1, trigger_func, root, is_clickthrough, indicator_label
    try:

        if is_clickthrough:
                    make_interactive()
                    is_clickthrough = False
                    if indicator_label:
                        indicator_label.config(text="", bg="#1C2026")
                        indicator_label.update_idletasks()

        if main and main.winfo_ismapped() and root and root.winfo_exists():
            # Schedule both actions in the Tkinter main thread
            root.after(0, lambda: (root.destroy(), trigger_func(var1.get())))
    except Exception as e:
        print(f"F8 error: {e}")

def toggle_lock(lock_button):
    current = lock_button.cget("text")

    print(current)
    lock_button.config(text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)")
    toggle_clickthrough()
        
def make_clickthrough():
    global hwnd
    if not config.mobile_mode:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    print("LOCKED")

def make_interactive():
    global hwnd
    if not config.mobile_mode:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    print("UNLOCKED")

def widget_exists(widget):
    try:
        return bool(widget.winfo_exists())
    except:
        return False

def toggle_clickthrough(hide_function1=None, debug_frame=None, main_frame=None, hide_button=None):
    global is_clickthrough, indicator_label, lock, bhidden, hide_function, debug_frame_global, main_frame_global, hide_button_global
    if is_clickthrough:

        make_interactive()
        if hide_function and debug_frame_global and main_frame_global and hide_button_global:
            if bhidden:
                hide_function(debug_frame_global, main_frame_global, hide_button_global)
            #hide_function(debug_frame_global, main_frame_global, hide_button_global)
        if indicator_label:
            indicator_label.config(text="")
            indicator_label.update_idletasks()
            indicator_label.update()
        if widget_exists(lock):
            
        
            current = lock.cget("text")

            
            lock.config(
                    text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)",
                    fg="#ffa0a0" if current == "Lock(F6)" else "#ffffff",
                )
    else:
        make_clickthrough()
        if indicator_label:
            indicator_label.config(text="🔒", fg="red")
            indicator_label.update_idletasks()
            indicator_label.update()
        if widget_exists(lock):
            
            current = lock.cget("text")

            
            lock.config(
                    text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)",
                    fg="#ffa0a0" if current == "Lock(F6)" else "#ffffff",
                )
            
    is_clickthrough = not is_clickthrough


def scale_font(scale, size):
    return int(size / scale)                            
def change_color(value):
    value = int(value)
    if value > 2:
        return "#3ecbff"
    elif value > 0:
        return "#5de791"
    elif value == 0:
        return "white"
    elif value  > -3:
        return "#FFA800"
    else:
        return "#FF3737"
    
def _grid_bounds(parent):
    """Return (max_row, max_col) considering row/col spans, or (-1,-1) if empty."""
    max_row = -1
    max_col = -1
    for w in parent.grid_slaves():
        info = w.grid_info()
        r  = int(info["row"])
        rs = int(info.get("rowspan", 1))
        c  = int(info["column"])
        cs = int(info.get("columnspan", 1))
        max_row = max(max_row, r + rs - 1)
        max_col = max(max_col, c + cs - 1)
    return max_row, max_col

def add_separator_grid(parent, sides, thickness=1, color=None, adjust_color_fn=None):
    """
    Add a 1D border strip to a grid-managed parent on any of: 'top','bottom','left','right'.
    - thickness: pixels
    - color: explicit color string; if None and adjust_color_fn provided, uses that to darken bg.
    - adjust_color_fn: callable(parent, bg, factor)->color (to mimic your adjust_color)
    """
    # sanity: don't mix managers in same parent
    if any(ch.winfo_manager() == "pack" for ch in parent.winfo_children()):
        raise RuntimeError("Parent already uses pack; can't add grid separators here.")

    bg = parent.cget("bg")
    sep_color = color or (adjust_color_fn(parent, bg, 0.4) if adjust_color_fn else bg)

    for side in sides:
        side = side.lower()
        max_row, max_col = _grid_bounds(parent)

        if side == "top":
            # shift all existing rows down by '1'
            for w in parent.grid_slaves():
                w.grid_configure(row=int(w.grid_info()["row"]) + 1)

            strip = tk.Frame(parent, bg=sep_color, height=thickness)
            strip.grid(row=0, column=0, columnspan=(max_col + 1 if max_col >= 0 else 1), sticky="ew")
            parent.grid_rowconfigure(0, minsize=thickness, weight=0)

        elif side == "bottom":
            row = max_row + 1
            strip = tk.Frame(parent, bg=sep_color, height=thickness)
            strip.grid(row=row, column=0, columnspan=(max_col + 1 if max_col >= 0 else 1), sticky="ew")
            parent.grid_rowconfigure(row, minsize=thickness, weight=0)

        elif side == "left":
            # shift all existing columns right by '1'
            for w in parent.grid_slaves():
                w.grid_configure(column=int(w.grid_info()["column"]) + 1)

            strip = tk.Frame(parent, bg=sep_color, width=thickness)
            # recompute max_row after shifting (optional, but safe)
            max_row, _ = _grid_bounds(parent)
            strip.grid(row=0, column=0, rowspan=(max_row + 1 if max_row >= 0 else 1), sticky="ns")
            parent.grid_columnconfigure(0, minsize=thickness, weight=0)

        elif side == "right":
            col = max_col + 1
            strip = tk.Frame(parent, bg=sep_color, width=thickness)
            strip.grid(row=0, column=col, rowspan=(max_row + 1 if max_row >= 0 else 1), sticky="ns")
            parent.grid_columnconfigure(col, minsize=thickness, weight=0)

        else:
            raise ValueError("side must be one of: 'top','bottom','left','right'")

# optional: keep your original name as an alias
add_seperator_grid = add_separator_grid
    
    


def get_image_from_map(image_map, base_name, full_name):
    variants = image_map.get(base_name, [])
    for variant in variants:
        if variant["name"] == full_name:
            return variant["image"]
    return image_map["Default"][0]["image"]  # fallback



    
def convert_color(value):
    mapping = {
        "#456093": "#2C334B",  # bg_c blue
        "#A15444": "#6B382E",  # bg_c red
    }
    return mapping.get(value, value)  # Return the mapped value, or original if not found

def titlecase_name(s):
    return re.sub(r"[A-Za-z]+(?:-[A-Za-z]+)*", 
                  lambda m: '-'.join(w.capitalize() for w in m.group(0).split('-')), 
                  s.title())






SEASONS = {"0":0,"1": 0,  "2": 1, "3": 1.5, "4": 2, "5": 2.5, "6": 3, "7": 3.5, '8': 4}

def load_list(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        items = [line.strip() for line in f if line.strip()]
    return items






    
    
import json
import os

#t= time.perf_counter()
#from player2 import Player2
from RDMO import Hero, Player
#print("player2 import:", time.perf_counter() - t)

import helpers

#t = time.perf_counter()
import random
#print("random import:", time.perf_counter() - t)

#t = time.perf_counter()
from collections import Counter
#print("collections import:", time.perf_counter() - t)

import re

def save_json(path,data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "debug", path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
def generate_random_team(character_pool):
    count = Counter()
    total = 0
    team = []
    while total < 6:
        char = random.choice(list(character_pool.values()))
        if char.name == "Unknown":
            continue
        if count[char.name] >= 1:
            continue
        if count[char.role] > 1:
            continue
        count[char.name] += 1
        count[char.role] += 1
        team.append(char.name)
        total += 1
    return team


def make_circle(img: Image.Image) -> Image.Image:
    # Ensure RGBA
    img = img.convert("RGBA")
    w, h = img.size

    # 1) Create circular mask (white inside circle, black outside)
    circle_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(circle_mask)
    draw.ellipse((0, 0, w, h), fill=255)

    # 2) Get existing alpha (original transparency)
    existing_alpha = img.getchannel("A")

    # 3) Combine: keep original transparency *inside* the circle
    #    (multiply scales existing_alpha by circle_mask / 255)
    combined_alpha = ImageChops.multiply(existing_alpha, circle_mask)

    # 4) Put the combined alpha back
    img.putalpha(combined_alpha)

    return img
        
def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def norm_pct(pct):
    """Normalize 0–100 → 0–1."""
    return clamp(pct, 0, 100) / 100.0

def norm_pct2(pct, baseline=75):
    """
    Normalize 0–baseline → 0–1
    Values above baseline are clamped to 1.
    """
    pct = clamp(pct, 0, baseline)
    return pct / baseline


def norm_kd(kd):
    """
    Normalize KD with your thresholds in mind:
    - KD ~0.5  -> bad (≈0.0)
    - KD  =2.0 -> good  (≈0.5)
    - KD ≥3.5  -> excellent (≈1.0)
    """
    low, high = 0.5, 4.5
    kd = clamp(kd, 0.0, 6.0)  # hard cap vs trolls
    return clamp((kd - low) / (high - low), 0.0, 1.0)


def norm_kda(kda):
    """Similar idea; tweak as needed."""
    low, high = 1.0, 6.0  # KDA 1=bad, 6=excellent
    kda = clamp(kda, 0.0, 10.0)
    return clamp((kda - low) / (high - low), 0.0, 1.0)


def apply_games_confidence(raw_score, games_played, full_conf_games, baseline=0.6):
    """
    Pull extreme values toward a neutral baseline when games are low.

    - raw_score: 0–1 stat (e.g. normalized KD)
    - games_played: how many games this stat is based on
    - full_conf_games: after this many games, we fully trust the stat
    - baseline: neutral 'average' value (0.5 by default)

    Returns adjusted score in 0–1.
    """
    games_played = max(0, games_played or 0)
    conf = clamp(games_played / float(full_conf_games), 0.0, 1.0)
    return (baseline + (raw_score - baseline)) * conf

def rank_players(players):
    # First compute all score dictionaries
    scored = []
    for p in players:
        scores = score_player(p)
        scored.append((p, scores["final"], scores))

    # Sort by final score (best first)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Assign rank + store results inside each player object
    for rank_index, (player, final_score, comp) in enumerate(scored, start=1):
        player.ranking = rank_index
        player.final_score = final_score
        player.overall_score = comp["overall"]
        player.char1_score = comp["char1"]

    return scored
def to_float_pct(val):
    """
    Convert percent-like values to float.
    Accepts: 52, '52', '52%', ' 52 % ', None, 'N/A'
    Returns 0.0 on failure.
    """
    if val is None:
        return 0.0

    try:
        if isinstance(val, str):
            cleaned = val.strip().replace("%", "")
            return float(cleaned)
        return float(val)
    except:
        return 0.0
    
def to_float_ratio(val):
    try:
        return float(str(val).strip())
    except:
        return 0.0


def score_player(player: Player = None, hero: Hero = None):
    # ======================
    # Overall stats
    # ======================
    ov = getattr(player, "full_overview", None)
    kda_raw = norm_kda(to_float_ratio(getattr(ov, "kda_ratio", 0.0)))
    kd_raw  = norm_kd(to_float_ratio(getattr(ov, "kd_ratio", 0.0)))
    win_raw = norm_pct2(to_float_pct(getattr(ov, "win_pct", 0.0)), baseline=75)
    mvp_raw = norm_pct2(to_float_pct(getattr(ov, "mvp_pct", 0.0)), baseline=60)

    overall_games = int(to_float_ratio(getattr(ov, "matches_played", 0)))

    

    # Trust overall stats fully around 100 games
    kda_n = apply_games_confidence(kda_raw, overall_games, full_conf_games=20)
    kd_n  = apply_games_confidence(kd_raw,  overall_games, full_conf_games=20)
    win_n = apply_games_confidence(win_raw, overall_games, full_conf_games=20)
    mvp_n = apply_games_confidence(mvp_raw, overall_games, full_conf_games=20)

    # Overall score weighting
    # KDA = 25%, KD = 30%, Win% = 30%, MVP% = 15%
    overall_score = (
        0.10 * kda_n +
        0.40 * kd_n +
        0.30 * win_n +
        0.20 * mvp_n
    )

    # ======================
    # Best character stats (char1)
    # ======================
    best = 0
    best_name = "Unknown"
    
    for hero in player.top_heroes:

        
        hero1 = getattr(hero, "heroname", "Unknown")
        if hero1 == "Unknown" or hero1 == "Null":
            continue
        #mvp = getattr(hero, f"total_mvp", 0.0)
        win1_raw = norm_pct2(to_float_pct(hero.getHeroWinPct()), baseline=75)
        kd1_raw  = norm_kd(to_float_ratio(hero.getHeroKDRatio()))
        

        char1_games = int(to_float_ratio(hero.getHeroMatchesPlayed()))
        mvp_pctt = hero.getHeroMvpPct()
        if isinstance(mvp_pctt, str):
            mvp_pctt = float(mvp_pctt.strip().replace("%", ""))
        else:
            mvp_pctt = float(mvp_pctt)
        mvp1_raw = norm_pct2(to_float_pct(mvp_pctt), baseline=75)
        # Char1 has fewer games, so full trust around 40 games
        win1_n = apply_games_confidence(win1_raw, char1_games, full_conf_games=20)
        kd1_n  = apply_games_confidence(kd1_raw,  char1_games, full_conf_games=20)
        mvp1_n = apply_games_confidence(mvp1_raw, char1_games, full_conf_games=20)
        secon = max(min(hero.getHeroTimePlayed()/10000, 5.0), 0.25) if hero.getHeroTimePlayed() > 0 else 0.25

        win = hero.getHeroWinRaw()/100
        mvp = hero.getHeroMvpPctRaw()/100
        kd = hero.getHeroKDRatio()
        w = max(min(win / 0.65, 1.0), 0.25) if win > 0.0 else 0.25
        m = max(min(mvp / 0.65, 1.0), 0.25) if mvp > 0.0 else 0.25
        k = max(min(kd / 4, 1.0), 0.25) if kd > 0.0 else 0.25
        # Char1 score: emphasize win% and KD
        # Win% = 45%, KD = 40%, MVP% = 15%
        char1_score = (
            ((0.30 * w) +
            (0.35 * k) +
            (0.30 * m) ) * secon
        )
        print(f"Hero {hero1}: win={w:.2f}, kd={k:.2f}, mvp={m:.2f}, games={char1_games}, score={char1_score:.3f}")
        setattr(hero, f"score", char1_score)
        if char1_score > best:
            best = char1_score
            best_name = hero1
    char1_score = best

    setattr(player, "best_hero", best_name)

    # win1_raw = norm_pct(to_float_pct(getattr(player, "win_pct1", 0.0)))
    # kd1_raw  = norm_kd(to_float_ratio(getattr(player, "kd1", 0.0)))
    # mvp1_raw = norm_pct(to_float_pct(getattr(player, "mvp1", 0.0)))

    # char1_games = int(to_float_ratio(getattr(player, "matches_played1", 0)))

    # # Char1 has fewer games, so full trust around 40 games
    # win1_n = apply_games_confidence(win1_raw, char1_games, full_conf_games=20)
    # kd1_n  = apply_games_confidence(kd1_raw,  char1_games, full_conf_games=20)
    # mvp1_n = apply_games_confidence(mvp1_raw, char1_games, full_conf_games=20)

    # # Char1 score: emphasize win% and KD
    # # Win% = 45%, KD = 40%, MVP% = 15%
    # char1_score = (
    #     0.10 * win1_n +
    #     0.50 * kd1_n +
    #     0.40 * mvp1_n
    # )

    # ======================
    # Final combined score
    # ======================
    # Overall = 60%, Char1 = 40%
    final_score = 0.60 * overall_score + 0.40 * char1_score

    return {
        "overall": overall_score,
        "char1": char1_score,
        "final": final_score,
        "best_hero": best_name
    }


def toggle_transparency(root,btn):
    if hasattr(root, "_is_transparent") and root._is_transparent:
        # Restore to opaque
        btn.config(text="Hide")
        root.attributes("-alpha", 1.0)
        root._is_transparent = False
    else:
        # Set to transparent
        btn.config(text="Show")
        root.attributes("-alpha", 0.25)  # You can adjust this value (0.0 to 1.0)
        root._is_transparent = True


def save_list_file(data, filename):
    path = os.path.join(config.script_dir, "debug", filename)    
    with open(path, "w", encoding="utf-8") as f:
        for family in sorted(data):  # sorted is optional
            f.write(family + "\n")

def close(root,script_dir,hy):
    if not config.mobile_mode:
        keyboard.remove_hotkey(hy)
    debug_path = os.path.join(script_dir, "debug")
    debug_img = os.path.join(debug_path, "Last Banner.png")
    root.update()  # Make sure geometry info is up-to-date
    x = root.winfo_rootx()
    y = root.winfo_rooty()
    w = x + root.winfo_width()
    h = y + root.winfo_height()

    # Capture region and save
    img = ImageGrab.grab(bbox=(x, y, w, h))
    img.save(debug_img)
    print(f"Saved screenshot to {debug_img}")
    root.destroy()
    
    #main3()

def close2(root):
    
    root.destroy()
    sys.exit(0)

def close3(root):
    root.destroy()
def getRoles(player):
    # player._roleName = "name"
    # player._roleMatchesPlayed = None
    # player._roleTimePlayed = None
    # player._roleHealing = None
    # player._roleDamage = None
    # player._roleDamageTaken = None
    # player._roleMvps = None


    # player._roleWinPct = None
    # player._roleKdRatio = None
    # player._roleKdaRation = None

    # # Role 2
    # player._role2Name = None
    # player._role2MatchesPlayed = None
    # player._role2TimePlayed = None
    # player._role2Healing = None
    # player._role2Damage = None
    # player._role2DamageTaken = None
    # player._role2Mvps = None
    # player._role2WinPct = None
    # player._role2KdRatio = None
    # player._role2KdaRation = None

    name1 = player._roleName
    matches1 = player._roleMatchesPlayed
    time1 = player._roleTimePlayed
    healing1 = player._roleHealing
    damage1 = player._roleDamage
    damagetaken1 = player._roleDamageTaken
    mvps1 = player._roleMvps
    winpct1 = player._roleWinPct
    kdratio1 = player._roleKdRatio
    kdaratio1 = player._roleKdaRatio

    name2 = player._role2Name
    matches2 = player._role2MatchesPlayed
    time2 = player._role2TimePlayed
    healing2 = player._role2Healing
    damage2 = player._role2Damage
    damagetaken2 = player._role2DamageTaken
    mvps2 = player._role2Mvps
    winpct2 = player._role2WinPct
    kdratio2 = player._role2KdRatio
    kdaratio2 = player._role2KdaRatio

    return (name1, matches1, time1, healing1, damage1, damagetaken1, mvps1, winpct1, kdratio1, kdaratio1), (name2, matches2, time2, healing2, damage2, damagetaken2, mvps2, winpct2, kdratio2, kdaratio2)


  
        

def initialize_hide_pass(hide_func, debug_frame, main_frame,hide_btn):
    global hide_function, debug_frame_global, main_frame_global,hide_button_global
    hide_button_global = hide_btn
    hide_function = hide_func
    debug_frame_global = debug_frame
    main_frame_global = main_frame


# =========================
# 2560 x 1440 player layout canvas
# =========================
SUPER_FRAME_WIDTH = 2560
SUPER_FRAME_HEIGHT = 1440 - 30



# def register_f8():
#     if config.OCR.is_set():
#         config.f8hotkey = keyboard.add_hotkey('f8', handle_f8)
#         #print("✅ F8 hotkey ready")
#     else:
#         root.after(100, register_f8)  

# if not config.mobile_mode:
#     import threading
#     def start_hotkey_listener():
#         global hide_function, debug_frame_global, main_frame_global,hide_button_global
#         if not config.mobile_mode:
#             keyboard.add_hotkey('f6' ,toggle_clickthrough,args=(hide_function, debug_frame_global, main_frame_global,hide_button_global))
        
#             keyboard.wait()  # Keeps the listener alive
            
          
#     listener_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
#     listener_thread.start()
#     if not config.mobile_mode:
#         threading.Thread(target=lambda: (config.OCR.wait(), register_f8()), daemon=True).start()
class PlayerFrame:
    """
    Refactor of create_player_frame(root, player) into a class.

    - Instantiate with (parent, player)
    - Call .build() to construct everything
    - All frames that have `outer` as parent are isolated into their own methods:
        * _build_name_bar()
        * _build_overview()
        * _build_heroes()
        * _build_history()

    NOTE:
    - This assumes you still have these globals/functions available exactly like before:
      s, SCALE, fonttk, image_loader, make_circle, SpriteSheetAnimator,
      NAMEPLATES (list), random, Image, ImageTk, MANUAL_DEBUG, bTest, etc.
    - I kept your logic and layout, but removed the UI dict and inlined the numbers.
    """

    def __init__(self, parent: SuperFrame, player: Player, x, y):
        self.x = x
        self.y = y
        self.superframe = parent
        self.player = player
        self.db = DB
        self.overview_frame = 130
        self.stat_frame_height = 112 #112
        self.player_frame_width = 380
        self.hero_stats_offset = self.stat_frame_height - 112
        self.icon_frame_height = self.stat_frame_height - 22
        self.icon_image_size = self.stat_frame_height - 34
        # root frame for this player card (the "outer")
        self.outer = None

        # cached/derived data used by multiple sections
        self.ov = None
        self.roles = []
        self.matches = []
        self.fov_heroes = []
        self.top3 = []
        self.char_scores = []
        self.order = []
        self.total_time_played = 0
        self.used_herobgs = set()
        # random nameplate chosen for this player card
        self.nameplate = None

    # ---------------------------
    # Public build entry
    # ---------------------------
    def build(self):
        
        #self._pull_player_data()
        
        self._build_outer()

        # All frames that have `outer` as parent:
        self._build_name_bar()
        self._build_overview_new()
        self._build_heroes_new()
        self._build_match_history()
        #self._build_history()
        #self._finishing_touches()
        return self.outer

    # ---------------------------
    # Small helpers
    # ---------------------------


    #Get coordinates of a widget relative to the root window

    # ---------------------------
    # Color rules (same logic)
    # ---------------------------
    
    def _get_foreground_color(self, label, value, flag=None):
        variable_colors_background = {
            "Matches": {"9999": "#2B2B2B"},
            "Win %": {"30": "#b34454", "45": "#cf9f00", "60": "#23ad58", "200": "#10b0eb"},
            "Kda": {"1": "#b34454", "3": "#cf9f00", "5": "#23ad58", "2222": "#10b0eb"},
            "Kd": {"1": "#b34454", "2": "#cf9f00", "4": "#23ad58", "200": "#10b0eb"},
            "Mvp %": {"5": "#b34454", "10": "#cf9f00", "35": "#23ad58", "200": "#10b0eb"},
            "MVPs": {"5": "#b34454", "10": "#cf9f00", "35": "#23ad58", "200": "#10b0eb"},
            "Final Hits": {"4": "#b34454", "8": "#cf9f00", "12": "#23ad58", "200": "#10b0eb"},
            "Dam/Min": {"800": "#b34454", "1300": "#cf9f00", "1600": "#23ad58", "4000": "#10b0eb"},
            "Damage": {"800": "#b34454", "1300": "#cf9f00", "1600": "#23ad58", "4000": "#10b0eb"},
            "Healing": {"800": "#b34454", "1300": "#cf9f00", "1600": "#23ad58", "4000": "#10b0eb"},
            "Usage": {"10": "#b34454", "20": "#cf9f00", "35": "#23ad58", "200": "#10b0eb"},
            "Healing2": {"800": "#b34454", "1300": "#cf9f00", "1600": "#23ad58", "4000": "#3ecbff"},
            "Kills": {"0": "#b34454", "10": "#cf9f00", "20": "#23ad58", "9899": "#10b0eb"},
            "AvgLife": {"0.5": "#b34454", "1.5": "#cf9f00", "2.5": "#23ad58", "9899": "#10b0eb"},
            "Assists": {"0": "#b34454", "3": "#cf9f00", "7": "#23ad58", "9899": "#10b0eb"},
            "Acc": {"0": "#b34454", "20": "#cf9f00", "45": "#23ad58", "9899": "#10b0eb"},
            "CritAcc": {"3": "#b34454", "6": "#cf9f00", "9": "#23ad58", "9899": "#10b0eb"},
            "LastKill": {"3": "#b34454", "6": "#cf9f00", "12": "#23ad58", "9899": "#10b0eb"},
            "Blocked": {"100": "#b34454", "900": "#cf9f00", "1800": "#23ad58", "99899": "#10b0eb"},
            "db": {"30": "#b34454", "60": "#cf9f00", "85": "#23ad58", "9899": "#10b0eb"},
            "Time": {"9999": "#2B2B2B"},
            "db_img": {"25": "db_red", "40": "db_yellow", "60": "db_neutral", "85": "db_green", "9899": "db_blue"},

        }

        try:
            label = str(label).strip()
            v_str = str(value).strip()
            if v_str.endswith("%"):
                v_str = v_str[:-1].strip()
            value_num = float(v_str)
            if label == "db_img":
                value_num = abs(value_num - 100)

            thr = variable_colors_background.get(label)
            if thr:
                for k in sorted(thr.keys(), key=lambda x: float(x)):
                    if value_num <= float(k):
                        return thr[k] if not flag else thr[k]

            return "#D5D9E4" if not flag else "#292929"
        except Exception as e:
            print("getForegroundColor error:", e, "label:", repr(label), "value:", repr(value))
            return "#D5D9E4" if not flag else "#171B20"

    # ---------------------------
    # Pull data once (same intent)
    # ---------------------------
    def _pull_player_data(self):
        p = self.player

        self.ov = getattr(p, "full_overview", None)
        if not self.ov:
            self.ov = getattr(p, "seasonal_overview", None)
        #self.roles = getattr(self.ov, "role_objs", []) or []
        self.matches = getattr(p, "matches", []) or []
        if not isinstance(self.matches, list):
            self.matches = []

        #fov = getattr(p, "full_overview", None)
        #self.fov_heroes = fov.heroes if fov and hasattr(fov, "heroes") else []
        self.TTSuperCondLight = 'TT Sprmlt N Trl Cnd Lt'
        self.TTSuperCondMedium = 'TT Sprmlt N Trl Cnd Md'
        self.TTSuperCondThin = 'TT Sprmlt N Trl Cnd Th'

        # top3 heroes
        #self.top3 = self._topn(getattr(p, "top_heroes", []) or [], 4)
        #self.char_scores = [getattr(h, "score", None) for h in self.top3]

        # total time
        # self.total_time_played = sum(
        #     h.time_played for h in getattr(p, "heroes", []) if hasattr(h, "time_played")
        # )
        #print(f"Total Time Played for {p.name}: {self.total_time_played}")

        # order by score desc (1-based indices)
        # self.order = [
        #     i
        #     for i, score in sorted(
        #         ((i + 1, score) for i, score in enumerate(self.char_scores) if score is not None),
        #         key=lambda x: x[1],
        #         reverse=True,
        #     )
        # ]

    # ---------------------------
    # OUTER
    # ---------------------------
    def _build_outer(self):
        
        self.superframe.createSuperFrameImage(img_key="Yellow Glow", x=self.x+214, y=self.y+745, anc="c")
        self.superframe.createSuperFrameImage(img_key="heroframe", x=self.x, y=self.y, anc="nw")

    
        
    # ---------------------------
    # OVERVIEW (outer -> ov + canvas)
    # ---------------------------
    def _build_overview_new(self):
        p = self.player.seasonal_overview
        if not p:
            return
        offx = 64
        offy = 186
        x = self.x + offx
        y = self.y + offy
        set = 24
        
        # Games Played Top
        
        self.superframe.createSuperFrameText(text="MATCHES", x=x+324, y=y-38, anchor="c", font=fonttk("Refrigerator Deluxe ExtraBold", 10, "normal", italic=False), fill="#8685B6")
        
        self.superframe.createSuperFrameText(text=str(round(p.matches_played,1)), x=x+300, y=y-38, anchor="e", font=fonttk("Refrigerator Deluxe ExtraBold", 14, "bold", italic=False), fill="#CDCEEB")
        
        # OV Stat Values
        
        
        
        self.superframe.createSuperFrameText(text=p.win_pct, x=x, y=y, anchor="c", font=fonttk("Refrigerator Deluxe", 20, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text=str(round(p.kd_ratio,2)), x=x+98, y=y, anchor="c", font=fonttk("Refrigerator Deluxe", 20, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text=p.mvp_pct, x=x+202, y=y, anchor="c", font=fonttk("Refrigerator Deluxe", 20, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text=str(round(p.kda_ratio,2)), x=x+301, y=y, anchor="c", font=fonttk("Refrigerator Deluxe", 20, "bold", italic=False), fill="#121225")
        
        # Ov Stat Labels
        
        self.superframe.createSuperFrameText(text="WIN RATE", x=x-2, y=y+set, anchor="c", font=fonttk("Refrigerator Deluxe", 9, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text="KD RATIO", x=x+98, y=y + set, anchor="c", font=fonttk("Refrigerator Deluxe", 9, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text="MVP RATE", x=x+201, y=y + set, anchor="c", font=fonttk("Refrigerator Deluxe", 9, "bold", italic=False), fill="#121225")
        
        self.superframe.createSuperFrameText(text="KDA RATIO", x=x+300, y=y + set, anchor="c", font=fonttk("Refrigerator Deluxe", 9, "bold", italic=False), fill="#121225")

        

    # ---------------------------
    # NAME BAR (outer -> name_bar + canvas)
    # ---------------------------
    def _build_name_bar(self):
        icon_string = "item_nameplate_" +self.player.Icon
        self.superframe.createSuperFrameImage(img_key=icon_string, x=self.x + 69, y=self.y + 71, anc="c")
        self.superframe.createSuperFrameText(text=self.player.Name, x=self.x + 120, y=self.y + 70, anchor="w", font=fonttk("Refrigerator Deluxe ExtraBold", 30, "bold", italic=False), fill="#FFFFFF")
        rank = self.player.best_rank
        if rank:
            self.superframe.createSuperFrameImage(img_key=rank, x=self.x + 312, y=self.y + 13, anc="nw")

    def _build_heroes_new(self):
        print()
        hli = list(self.player.Heroes.values())

        hero1: Hero | None = hli[0] if len(hli) > 0 else None
        hero2: Hero | None = hli[1] if len(hli) > 1 else None
        hero3: Hero | None = hli[2] if len(hli) > 2 else None
        heroes = [hero1, hero2, hero3]
        icon_position = [(5,456), (5, 610), (5, 766)]
        badge_offset = (27, 155)
        stats_xy = [(184, 540), (184, 695), (184, 850)]
        idx = 0
        for hero in heroes:
            icon_x, icon_y = icon_position[idx]
            stats_x, stats_y = stats_xy[idx]
            x = icon_x + self.x
            y = icon_y + self.y
            if hero is None:
                idx += 1
                continue
            proficiency = hero.ProficiencyLevel if hero else 0
            bAnimated, frame, badge, heroname, rank = self.proficiency_handler(hero.Name, int(proficiency))
            self.hero_animation = HeroImager(
                                        self.superframe,
                                        image_key=heroname,  # Passed directly to image_loader()
                                        x=x,
                                        y=y,
                                        anchor="nw",
                                        bAnimated=bAnimated,
                                        fps=24,
                                        loop=True,
                                        autoplay=True,
                                    )
            #hero_animate = self.superframe.createSuperFrameImage(img_key=heroname, x=x, y=y, anc="nw")
            if badge:
                x += badge_offset[0]
                y += badge_offset[1]
                self.superframe.createSuperFrameImage(img_key=f"badge_{str(badge)}", x=x, y=y, anc="c")
            idx += 1
            
            # Hero Stats
            
            
            x = self.x + 184
            y = self.y + 540
            
            # Stat Labels
            x = stats_x + self.x
            y = stats_y + self.y
            
            self.superframe.createSuperFrameText(text="WIN%", x=x, y=y+4, anchor="c", font=fonttk("Refrigerator Deluxe", 10, "bold", italic=False), fill="#121225")
            self.superframe.createSuperFrameImage(img_key="winrate", x=x, y=y+30, anc="c")
            
            self.superframe.createSuperFrameText(text="KD", x=x+65, y=y+4, anchor="c", font=fonttk("Refrigerator Deluxe", 10, "bold", italic=False), fill="#121225")

            self.superframe.createSuperFrameImage(img_key="kd", x=x+65, y=y+32, anc="c")
            
            self.superframe.createSuperFrameText(text="MVP%", x=x+133, y=y+4, anchor="c", font=fonttk("Refrigerator Deluxe", 10, "bold", italic=False), fill="#121225")

            self.superframe.createSuperFrameImage(img_key="mvp", x=x+131, y=y+30, anc="c")
            
            self.superframe.createSuperFrameText(text="GAMES", x=x+198, y=y+4, anchor="c", font=fonttk("Refrigerator Deluxe", 10, "bold", italic=False), fill="#121225")

            self.superframe.createSuperFrameImage(img_key="games", x=x+198, y=y+30, anc="c")
            
            # Stat Values
            set = 62
            self.superframe.createSuperFrameText(text=hero.Stats.win_pct, x=x, y=y+set, anchor="c", font=fonttk("Refrigerator Deluxe", 18, "bold", italic=False), fill="#5B5D6E")
            
            self.superframe.createSuperFrameText(text=str(round(hero.Stats.kd_ratio,2)), x=x+64, y=y+set, anchor="c", font=fonttk("Refrigerator Deluxe", 18, "bold", italic=False), fill="#5B5D6E")
            
            self.superframe.createSuperFrameText(text=hero.Stats.mvp_pct, x=x+133, y=y+set, anchor="c", font=fonttk("Refrigerator Deluxe", 18, "bold", italic=False), fill="#5B5D6E")
            
            self.superframe.createSuperFrameText(text=str(round(hero.Stats.matches_played,1)), x=x+198, y=y+set, anchor="c", font=fonttk("Refrigerator Deluxe", 18, "bold", italic=False), fill="#5B5D6E")
            
    def _build_match_history(self):
        offx = 8
        offy = 1026
        x = self.x + offx
        y = self.y + offy
        complete = 0
        
        for match in self.player.matches:
            row_img = "match_winF" if match.result == "win" else "match_lossF"
    
            self.superframe.createSuperFrameImage(img_key=row_img, x=x, y=y , anc="nw")

            y += 66
            complete += 1
            if complete >= 5:
                break      
            
    def proficiency_handler(self,hero, lv):
            # lv60 = 195/2 #AnimatedLord, Badge4, Gold
            # lv55 = 165/2 #AnimatedLord, Badge4, Gold
            # lv50 = 137.5/2 #AnimatedLord, Badge3, Gold
            # lv45 = 112.5/2 #Lord, Badge3, Gold
            # lv40 = 90/2 #Lord, Badge2, Gold
            # lv35 = 70/2 #Lord, Badge2, Purple
            # lv30 = 52.5/2 #Lord, Badge1, Purple
            # lv25 = 37/2 #Lord, Badge1
            # lv20 = 25/2 #Lord
            # lv15 = 15/2
            # lv10 = 7.5/2
            # lv5 = 2.5/2

            if lv > 55: #200:
                return True, "gold", 4, hero + "0", "Champion"
            elif lv > 50: #140:
                return True, "gold", 3, hero + "0", "Champion" 
            elif lv > 45: #100:    
                return False, "gold", 3, hero + "_l", "Guardian"
            elif lv > 40: #100:    
                return False, "gold", 2, hero + "_l", "Elite"
            elif lv > 35: #80:
                return False, "purp", 2, hero + "_l", "Warrior"
            elif lv > 30: #55:
                return False, 'purp', 1, hero + "_l", "Colonel"
            elif lv > 25: #35:
                return False, False, 1, hero + "_l", "Count"
            elif lv > 20: #25:
                return False, False, False, hero + "_l", "Lord"
            elif lv > 15: #15:
                return False, False, False, hero, "Centurion"
            elif lv > 10: #7.5:
                return False, False, False, hero, "Captain"
            elif lv > 5: #2.5:
                return False, False, False, hero, "Knight"
            else:
                return False, False, False, hero, "Agent"
            
    def proficiency_handlerAll(self,hours, hero):
            lv60 = 195 #AnimatedLord, Badge4, Gold
            lv55 = 165 #AnimatedLord, Badge4, Gold
            lv50 = 137.5 #AnimatedLord, Badge3, Gold
            lv45 = 112.5 #Lord, Badge3, Gold
            lv40 = 90 #Lord, Badge2, Gold
            lv35 = 70 #Lord, Badge2, Purple
            lv30 = 52.5 #Lord, Badge1, Purple
            lv25 = 37 #Lord, Badge1
            lv20 = 25 #Lord
            lv15 = 15
            lv10 = 7.5
            lv5 = 2.5

            if hours > lv55: #200:
                return True, "gold", 4, hero, "Champion"
            elif hours > lv50: #140:
                return True, "gold", 3, hero, "Champion" 
            elif hours > lv45: #100:    
                return False, "gold", 3, hero + "_l", "Guardian"
            elif hours > lv40: #100:    
                return False, "gold", 2, hero + "_l", "Elite"
            elif hours > lv35: #80:
                return False, "purp", 2, hero + "_l", "Warrior"
            elif hours > lv30: #55:
                return False, 'purp', 1, hero + "_l", "Colonel"
            elif hours > lv25: #35:
                return False, False, 1, hero + "_l", "Count"
            elif hours > lv20: #25:
                return False, False, False, hero + "_l", "Lord"
            elif hours > lv15: #15:
                return False, False, False, hero, "Centurion"
            elif hours > lv10: #7.5:
                return False, False, False, hero, "Captain"
            elif hours > lv5: #2.5:
                return False, False, False, hero, "Knight"
            else:
                return False, False, False, hero, "Agent"
    # ---------------------------

        #stat_names = config.load_ui_stats_config()
     #   stat_names_1 = stat_names[:2]
        #stat_names_2 = stat_names[3:7]
        #stats = self._buildStatTuple(hero, stat_names_1)
        #stats = ("Time",round(hero_timeH,1), False),("Usage", usage_pct, False)
        
        #mvp = hero.getHeroMvpPct()
        #avg_kills_match = hero.getHeroAvgKillsPerMatch()
        #killrate = hero.getHeroKillsPer10()

        #stats2 =   ("Mvp %", mvp, False),("Kills", hero.getHeroAvgKillsPerMatch(),self.db.stat_percentile(heroname, "kills_per_10", float(hero.getHeroKillsPer10()), min_samples=10)),("Deaths", hero.getHeroAvgDeathsPerMatch(),self.db.stat_percentile(heroname, "average_lifespan", float(hero.getHeroAvgLifespan()), min_samples=10)),(hero.string, int(round(hero.getHeroAvgDamagePerMatch() if role != "Strategist" else hero.getHeroAvgHealingPerMatch())), self.db.stat_percentile(heroname, f"{hero.string.lower()}_per_minute", float(hero.dpm), min_samples=10) if role != "Strategist" else self.db.stat_percentile(heroname, "healing_per_minute", float(hero.dpm), min_samples=10))
                      #("Assists", hero_obj.avg_assists_per_match,self.db.stat_percentile(hero, "assists_per_10", float(hero_obj.assists_per_10), min_samples=1)),(hero.string, int(round(hero.getHeroAvgDamagePerMatch() if role != "Strategist" else hero.getHeroAvgHealingPerMatch())), self.db.stat_percentile(hero, f"{hero.string.lower()}_per_minute", float(hero.dpm), min_samples=1) if role != "Strategist" else self.db.stat_percentile(hero, "healing_per_minute", float(hero.dpm), min_samples=1)),
                      #("Blocked", int(round(hero_obj.avg_damage_taken_per_match)), self.db.stat_percentile(hero, "total_damage_taken_per_minute", float(hero_obj.total_damage_taken_per_minute), min_samples=1)),
           

# ---------------------------
# Drop-in replacement usage
# ---------------------------
def create_player_frame(parent, player):
    return PlayerFrame(parent, player).build()

class App:
    def __init__(self, base_dpi_scale):
        self.base_dpi_scale = base_dpi_scale
        self._after_ids = set()
        # ---- ONE root for the life of the app ----
        self.root = create_root(self.base_dpi_scale)
        self.root.title("Capture Names")
        if not config.mobile_mode:
            loaded_paths, families = call_register_fonts(self.root)
        #list_fonts()
        self.root.configure(bg="#151426")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # ---- page holder ----
        self.page = None

        # ---- state that used to be globals ----
        self.fonts = {}
        self.font_scale = 1

        self.bhidden = False
        self.bdebug_menu = False
        self.bHide = False
        self.hotkey_f6_id = None
        self.hotkey_f7_id = None
        self.hotkey_f8_id = None
        self.hwnd = None

        self.var1 = tk.BooleanVar()
        self.var2 = tk.BooleanVar()
        self.var3 = tk.BooleanVar()
        self.var4 = tk.BooleanVar()
        
        self.indicator_label = None
        self.lock_btn = None

        # Account Config UI state
        self.account_var = None
        self.account_combo = None
        self.account_editor = None

        # You had these as globals; keep as app state
        self.global_debugflag = False

        # Monitor state. The saved display is used for both launcher and match UI.
        self.monitors = get_monitors() if not config.mobile_mode else []
        self.selected_monitor_index = load_monitor_selection(self.monitors)

        # show first page
        self.show_launcher_page()
    def force_geometry(self, w, h, x, y):
        # apply twice, one tick apart (this fixes intermittent Windows behavior)
        geo = f"{w}x{h}+{x}+{y}"
        self.root.geometry(geo)
        self.root.update_idletasks()
        self.root.geometry(geo)

    def refresh_monitors(self):
        if config.mobile_mode:
            self.monitors = []
            self.selected_monitor_index = 0
            return

        old_device = None
        if self.monitors and 0 <= self.selected_monitor_index < len(self.monitors):
            old_device = self.monitors[self.selected_monitor_index].get("device")

        self.monitors = get_monitors()
        if not self.monitors:
            self.selected_monitor_index = 0
            return

        if old_device:
            for i, mon in enumerate(self.monitors):
                if mon.get("device") == old_device:
                    self.selected_monitor_index = i
                    return

        self.selected_monitor_index = min(self.selected_monitor_index, len(self.monitors) - 1)

    def get_selected_monitor(self):
        if config.mobile_mode or not self.monitors:
            return {
                "index": 0,
                "device": "Primary",
                "left": 0,
                "top": 0,
                "right": self.root.winfo_screenwidth(),
                "bottom": self.root.winfo_screenheight(),
                "width": self.root.winfo_screenwidth(),
                "height": self.root.winfo_screenheight(),
                "primary": True,
            }

        self.selected_monitor_index = max(
            0, min(self.selected_monitor_index, len(self.monitors) - 1)
        )
        return self.monitors[self.selected_monitor_index]

    def get_launcher_position(self):
        mon = self.get_selected_monitor()
        # Preserve your original launcher placement, but relative to selected monitor.
        return mon["left"] + (mon["width"] // 2) + s(175), mon["top"]
    # =========================
    # Page Switching Helpers
    # =========================
    def clear_page(self):
        if self.page is not None:
            self.page.destroy()
            self.page = None

    def show_launcher_page(self):
        # Remove hotkeys registered by other pages if needed
        self.unregister_hotkeys()
        self.cancel_all_afters()
        self.clear_page()
        self.page = tk.Frame(self.root, bg="#151426")
        self.page.pack()

        self.build_launcher(self.page)

    def show_match_page(self, players):
        self.unregister_hotkeys()
        self.cancel_all_afters()
        self.clear_page()
        self.page = tk.Frame(self.root, bg="black")
        self.page.pack()

        self.build_match_overview(self.page, players)

    def unregister_hotkeys(self):
        if not config.mobile_mode:
            for hid in (self.hotkey_f7_id, self.hotkey_f8_id,self.hotkey_f6_id):
                if hid is not None:
                    try:
                        keyboard.remove_hotkey(hid)
                    except Exception:
                        pass
        self.hotkey_f7_id = None
        self.hotkey_f8_id = None
        self.hotkey_f6_id = None

    def after_tracked(self, ms, func):
        aid = self.root.after(ms, func)
        self._after_ids.add(aid)
        return aid

    def after_idle_tracked(self, func):
        aid = self.root.after_idle(func)
        self._after_ids.add(aid)
        return aid

    def cancel_all_afters(self):
        for aid in list(self._after_ids):
            try:
                self.root.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()
    # =========================
    # Launcher Page (refactor of show_launcher)
    # =========================
    def get_account_list(self, d):
        return list(d.keys()) if isinstance(d, dict) else []

    # =========================
    # Account config helpers
    # config.account_config_json is the PATH to the JSON file.
    # Expected format:
    # {
    #     "set": "ProfChloroform",
    #     "accounts": {
    #         "ProfChloroform": 1324925930
    #     }
    # }
    # =========================
    def load_account_config(self):
        data = config.account_config_json

        if not isinstance(data, dict):
            data = {}

        accounts = data.get("accounts")
        if not isinstance(accounts, dict):
            accounts = {}
            data["accounts"] = accounts

        # If the JSON is empty, keep the currently configured account available
        # so the combobox still has something useful to display.
        fallback_name = str(getattr(config, "USER_NAME", "") or "").strip()
        fallback_uid = getattr(config, "USER_UID", None)
        if not accounts and fallback_name and fallback_uid is not None:
            accounts[fallback_name] = fallback_uid

        selected = data.get("set")
        if selected not in accounts:
            selected = next(iter(accounts), "")
            data["set"] = selected

        return data

    def save_account_config(self, data):
        path = config.ap3
        folder = os.path.dirname(os.path.abspath(path))
        if folder:
            os.makedirs(folder, exist_ok=True)

        # Write atomically so the JSON is not left half-written if something
        # interrupts the save.
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, path)

    def apply_account_to_runtime(self, name, uid):
        # Keep the already-imported config module in sync immediately.
        config.USER_NAME = name
        config.USER_UID = uid

    def refresh_account_combo(self, preferred_name=None):
        if not getattr(self, "account_combo", None) or not getattr(self, "account_var", None):
            return

        try:
            if not self.account_combo.winfo_exists():
                return
        except tk.TclError:
            return

        data = self.load_account_config()
        accounts = data.get("accounts", {})
        names = self.get_account_list(accounts)
        self.account_combo["values"] = names

        selected = preferred_name if preferred_name in accounts else data.get("set", "")
        if selected not in accounts:
            selected = names[0] if names else ""

        self.account_var.set(selected)
        if selected in names:
            self.account_combo.current(names.index(selected))

    def account_selected(self, event=None):
        selected = self.account_var.get().strip() if self.account_var else ""
        if not selected:
            return

        data = self.load_account_config()
        accounts = data.get("accounts", {})
        if selected not in accounts:
            return

        data["set"] = selected
        self.save_account_config(data)
        self.apply_account_to_runtime(selected, accounts[selected])
        print(f"Active account: {selected} ({accounts[selected]})")

    def open_account_editor(self):
        from tkinter import ttk, messagebox

        # Only allow one account editor at a time.
        editor = getattr(self, "account_editor", None)
        if editor is not None:
            try:
                if editor.winfo_exists():
                    editor.lift()
                    editor.focus_force()
                    return
            except tk.TclError:
                pass

        data = self.load_account_config()
        accounts = data.setdefault("accounts", {})

        editor = tk.Toplevel(self.root)
        self.account_editor = editor
        editor.title("Add / Edit Account")
        editor.configure(bg="#151426")
        editor.resizable(False, False)
        editor.attributes("-topmost", True)

        try:
            editor.transient(self.root)
        except tk.TclError:
            pass

        selected_var = tk.StringVar(master=editor)
        name_var = tk.StringVar(master=editor)
        uid_var = tk.StringVar(master=editor)
        state = {"original_name": None}

        tk.Label(
            editor,
            text="Account",
            bg="#151426",
            fg="white",
            font=fonttk("Rajdhani", "bold", 10),
        ).grid(row=0, column=0, padx=s(10), pady=(s(10), s(5)), sticky="w")

        editor_combo = ttk.Combobox(
            editor,
            textvariable=selected_var,
            values=["<New Account>"] + self.get_account_list(accounts),
            state="readonly",
            width=25,
        )
        editor_combo.grid(row=0, column=1, padx=s(10), pady=(s(10), s(5)), sticky="ew")

        tk.Label(
            editor,
            text="Username",
            bg="#151426",
            fg="white",
            font=fonttk("Rajdhani", "bold", 10),
        ).grid(row=1, column=0, padx=s(10), pady=s(5), sticky="w")

        name_entry = tk.Entry(editor, textvariable=name_var, width=28)
        name_entry.grid(row=1, column=1, padx=s(10), pady=s(5), sticky="ew")

        tk.Label(
            editor,
            text="UID",
            bg="#151426",
            fg="white",
            font=fonttk("Rajdhani", "bold", 10),
        ).grid(row=2, column=0, padx=s(10), pady=s(5), sticky="w")

        uid_entry = tk.Entry(editor, textvariable=uid_var, width=28)
        uid_entry.grid(row=2, column=1, padx=s(10), pady=s(5), sticky="ew")

        def load_selected_account(event=None):
            chosen = selected_var.get()
            if chosen == "<New Account>":
                state["original_name"] = None
                name_var.set("")
                uid_var.set("")
                name_entry.focus_set()
                return

            if chosen in accounts:
                state["original_name"] = chosen
                name_var.set(chosen)
                uid_var.set(str(accounts[chosen]))

        def begin_new_account():
            selected_var.set("<New Account>")
            state["original_name"] = None
            name_var.set("")
            uid_var.set("")
            name_entry.focus_set()

        def save_account():
            nonlocal data, accounts

            new_name = name_var.get().strip()
            uid_text = uid_var.get().strip()

            if not new_name:
                messagebox.showerror("Invalid Account", "Username cannot be empty.", parent=editor)
                return

            try:
                uid = int(uid_text)
            except ValueError:
                messagebox.showerror("Invalid UID", "UID must be a whole number.", parent=editor)
                return

            if uid <= 0:
                messagebox.showerror("Invalid UID", "UID must be greater than zero.", parent=editor)
                return

            original_name = state["original_name"]
            active_name = data.get("set", "")

            # Editing an existing account.
            if original_name is not None:
                if original_name not in accounts:
                    messagebox.showerror(
                        "Account Missing",
                        "That account no longer exists in the JSON file.",
                        parent=editor,
                    )
                    return

                if new_name != original_name and new_name in accounts:
                    messagebox.showerror(
                        "Account Exists",
                        f'An account named "{new_name}" already exists.',
                        parent=editor,
                    )
                    return

                if new_name != original_name:
                    del accounts[original_name]
                accounts[new_name] = uid

                # Renaming the active account must also rename "set".
                if active_name == original_name:
                    data["set"] = new_name

            # Adding a new account.
            else:
                if new_name in accounts:
                    messagebox.showerror(
                        "Account Exists",
                        f'An account named "{new_name}" already exists.',
                        parent=editor,
                    )
                    return

                accounts[new_name] = uid

                # A newly-added account becomes the selected account.
                data["set"] = new_name

            self.save_account_config(data)

            active_name = data.get("set", "")
            if active_name in accounts:
                self.apply_account_to_runtime(active_name, accounts[active_name])

            # Update both dropdowns immediately without rebuilding Config UI.
            self.refresh_account_combo(preferred_name=active_name)
            editor_combo["values"] = ["<New Account>"] + self.get_account_list(accounts)
            selected_var.set(new_name)
            state["original_name"] = new_name

            messagebox.showinfo("Account Saved", f'Account "{new_name}" was saved.', parent=editor)

        editor_combo.bind("<<ComboboxSelected>>", load_selected_account)

        button_row = tk.Frame(editor, bg="#151426")
        button_row.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=s(10),
            pady=(s(8), s(10)),
            sticky="ew",
        )

        tk.Button(
            button_row,
            text="New",
            command=begin_new_account,
        ).pack(side="left", padx=(0, s(5)))

        tk.Button(
            button_row,
            text="Save",
            command=save_account,
        ).pack(side="left", padx=s(5))

        tk.Button(
            button_row,
            text="Close",
            command=editor.destroy,
        ).pack(side="right", padx=(s(5), 0))

        # Start by editing the account currently selected in the main combobox.
        current = ""
        if getattr(self, "account_var", None):
            current = self.account_var.get().strip()
        if current not in accounts:
            current = data.get("set", "")

        if current in accounts:
            selected_var.set(current)
            state["original_name"] = current
            name_var.set(current)
            uid_var.set(str(accounts[current]))
        else:
            begin_new_account()

        editor.columnconfigure(1, weight=1)
        editor.bind("<Return>", lambda event: save_account())
        name_entry.focus_set()

    def build_launcher(self, parent):
        # ----- your original top-of-function setup -----
        self.font_scale = 2 if config.mobile_mode else 1
        font_sizes = list(range(6, 70))
        self.fonts = {size: scale_font(self.font_scale, size) for size in font_sizes}
        
        self.bhidden = False
        self.bdebug_menu = False

        # Position launcher on the monitor selected in Config.
        self.refresh_monitors()
        x, y = self.get_launcher_position()
        self.bConfigUI = False

        # Register fonts
        #if not config.mobile_mode:
            #loaded_paths, families = call_register_fonts(self.root)

        # ----- build UI into parent (NOT root directly) -----
        title_bar2 = tk.Frame(parent, bg="#141420", relief="solid", width=s(230), height=s(17))
        title_bar2.pack(fill="x", side="top", ipady=3)
        title_bar2.pack_propagate(False)

        main = tk.Frame(parent, bg="#151426", relief="solid", height=s(70), width=s(230))
        main.pack(fill="x", padx=s(10), pady=s(5), side="bottom")

        deb = tk.Frame(parent, bg="#151426", relief="solid", height=s(30), width=s(230))

        lef = tk.Frame(deb, bg="#151426", relief="solid", height=s(30), width=s(230))
        #rig = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
        lef.pack(fill="x", side="top",expand=True)
        lef.pack_propagate(False)
        #rig.pack(fill="x", side="top")
        self.ui_config = tk.Frame(deb, bg="#151426", relief="solid", height=s(315), width=s(230))
        #ui_config.pack(fill="both", padx=0, pady=0, side="bottom")
        #ui_config.pack_forget()

        def show_ui_config():
            from tkinter import ttk
            self.bConfigUI = not self.bConfigUI
            
            if not self.bConfigUI:

                self.ui_config.destroy()
            else:
                self.ui_config = tk.Frame(deb, bg="#151426", relief="solid", height=s(315), width=s(230))
                stat_labels = ["Stat 1", "Stat 2", "Stat 3", "Stat A", "Stat B", "Stat C", "Stat D"]
                stat_list = config.load_ui_stats_config()


                FULL_LIST = [
                    "Games", "Time", "Usage", "Win %", "KD/KDA", "Mvp %", 
                    "Kills", "Deaths", "Assists", "Damage/Healing", "Blocked","Accuracy"
                
                ]

                # container
                self.ui_config.pack(fill="both", padx=0, pady=0, side="top")
                self.ui_config.pack_propagate(False)

                combo_vars = []
                combos = []

                # -------------------------
                # Monitor selection
                # -------------------------
                self.refresh_monitors()
                monitor_names = []
                for i, mon in enumerate(self.monitors):
                    primary = " (Primary)" if mon.get("primary") else ""
                    monitor_names.append(
                        f"Monitor {i + 1} - {mon['width']}x{mon['height']}{primary}"
                    )
                user_row = tk.Frame(self.ui_config, bg=self.ui_config.cget("bg"))
                user_row.pack(fill="x", padx=s(8), pady=(s(5), s(8)))

                # config.account_config_json is the JSON FILE PATH, not the loaded dict.
                account_data = self.load_account_config()
                accounts = account_data.get("accounts", {})
                names = self.get_account_list(accounts)
                setname = account_data.get("set", "")

                # Keep the StringVar on self. A local StringVar can be garbage
                # collected after show_ui_config() returns, which causes a
                # readonly ttk.Combobox to lose the displayed value.
                self.account_var = tk.StringVar(master=self.root, value=setname)

                tk.Label(
                    user_row,
                    text="Account",
                    bg=self.ui_config.cget("bg"),
                    fg="white",
                    font=fonttk("Rajdhani", "bold", 10),
                ).pack(side="left", padx=(0, s(8)))

                self.account_combo = ttk.Combobox(
                    user_row,
                    textvariable=self.account_var,
                    values=names,
                    state="readonly",
                    width=12,
                )
                self.account_combo.pack(side="left", fill="x", expand=True)

                # Force ttk to use the saved "set" account as its initial
                # selection, without requiring the user to click the dropdown.
                if setname in names:
                    self.account_combo.current(names.index(setname))

                self.account_combo.bind("<<ComboboxSelected>>", self.account_selected)

                account_butt = tk.Button(
                    user_row,
                    text="Add",
                    command=self.open_account_editor,
                )
                account_butt.pack(side="left", padx=(s(5), 0))
                monitor_row = tk.Frame(self.ui_config, bg=self.ui_config.cget("bg"))
                monitor_row.pack(fill="x", padx=s(8), pady=(s(5), s(8)))

                tk.Label(
                    monitor_row, 
                    text="Monitor",
                    bg=self.ui_config.cget("bg"),
                    fg="white",
                    font=fonttk("Rajdhani", "bold", 10),
                ).pack(side="left", padx=(0, s(8)))

                monitor_var = tk.StringVar()
                if monitor_names:
                    self.selected_monitor_index = max(
                        0, min(self.selected_monitor_index, len(monitor_names) - 1)
                    )
                    monitor_var.set(monitor_names[self.selected_monitor_index])
                else:
                    monitor_names = ["Primary Monitor"]
                    monitor_var.set(monitor_names[0])

                monitor_combo = ttk.Combobox(
                    monitor_row,
                    textvariable=monitor_var,
                    values=monitor_names,
                    state="readonly",
                    width=24,
                )
                monitor_combo.pack(side="left", fill="x", expand=True)

                def refresh_combobox_values(event=None):
                    # current selections across all 6 boxes
                    current_values = [var.get() for var in combo_vars]

                    for i, combo in enumerate(combos):
                        current_value = combo_vars[i].get()

                        # exclude values selected in OTHER boxes
                        used_by_others = {v for j, v in enumerate(current_values) if j != i and v}

                        allowed = [item for item in FULL_LIST if item not in used_by_others]

                        # make sure this combo keeps showing its own current value
                        if current_value and current_value not in allowed:
                            allowed.insert(0, current_value)

                        combo["values"] = allowed

                # build 6 dropdowns
                for i in range(len(stat_labels)):
                    label = stat_labels[i] if i < len(stat_labels) else f"Stat {i+1}" 
                    row = tk.Frame(self.ui_config, bg=self.ui_config.cget("bg"))
                    row.pack(fill="x", padx=s(8), pady=s(4))

                    tk.Label(
                        row,
                        text=label,
                        bg=self.ui_config.cget("bg"),
                        fg="white"
                    ).pack(side="left", padx=(0, s(8)))

                    var = tk.StringVar(value=stat_list[i])
                    combo = ttk.Combobox(
                        row,
                        textvariable=var,
                        state="readonly",
                        width=s(20)
                    )
                    combo.pack(side="left", fill="x", expand=True)

                    combo_vars.append(var)
                    combos.append(combo)

                    combo.bind("<<ComboboxSelected>>", refresh_combobox_values)

                def save_ui_config():
                    selected_stats = [var.get() for var in combo_vars]
                    config.save_ui_stats_config(selected_stats)   # adjust to your save function

                    if self.monitors:
                        selected = monitor_combo.current()
                        if selected >= 0:
                            self.selected_monitor_index = selected
                            save_monitor_selection(selected, self.monitors)

                    self.bConfigUI = False
                    self.ui_config.destroy()

                    # Move launcher immediately to the newly selected monitor.
                    self.root.update_idletasks()
                    lx, ly = self.get_launcher_position()
                    self.root.geometry(f"+{lx}+{ly}")

                sav = tk.Button(
                    self.ui_config,
                    bg="#FCD92E",
                    fg="#151426",
                    relief="flat",
                    command=save_ui_config,
                    cursor="hand2",
                    text="Save and Close",
                    font=fonttk("Rajdhani", "bold", 12)
                )
                sav.pack(pady=s(10))

                refresh_combobox_values()

            # sav = tk.Button(ui_config, bg="#FCD92E", fg="#151426", relief="flat", command=save_ui_config(), cursor="hand2",
            #                      text="Save and Close", font=fonttk("Rajdhani", 'bold', 12))
            # stat1 = ttk.Combobox(ui_config, values=stat_list, state="readonly")
            # ui_config.pack(fill="both", padx=0, pady=0, side="bottom")

            
        # set your vars (these globals can stay globals if you want, but this is cleaner)
        global global_random_ban, global_random_matchup, global_dex, global_debugmode
        global_debugmode = config.debug_mode

        self.var1.set(global_random_ban)
        self.var2.set(global_random_matchup)
        self.var3.set(global_dex)
        self.var4.set(global_debugmode)

        # ---- checkbox setup ----
        frame = lef
        self.global_debugflag = False
        if config.debug_mode:
            #
            
            
    
            #cb2 = tk.Checkbutton(lef, bg="#151426", fg="white", selectcolor="#151426",
                                #text="Random Matchup", font=fonttk(carbon, 10), variable=self.var2)
           # cb1.pack(anchor="w")
            #cb2.pack(anchor="w")
            self.global_debugflag = True

        #cb3 = tk.Checkbutton(frame, bg="#151426", fg="white", selectcolor="#151426",
                            # text="Use Classic Logic", font=fonttk(carbon, 10), variable=self.var3)
        cb4 = tk.Checkbutton(lef, bg="#151426", fg="white", selectcolor="#151426",
                             text="Enable Debug", font=fonttk(carbon, 10), variable=self.var4)
        #cb3.pack(anchor="w")
        cb4.pack(side= "right", anchor="c",expand=True,padx=(s(5),s(5))) 
        cb1 = tk.Button(lef, bg="#FCD92E", fg="#151426", relief="flat", command=show_ui_config,cursor="hand2",
                                 text="UI Config", font=fonttk("Rajdhani", 'normal', 12))
        cb1.pack(side="left",anchor="c",expand=True,padx=(s(30),s(5)))
        # ---- local funcs that need access to widgets ----
        def toggle_hide():
            self.bhidden = not self.bhidden
            if self.bhidden:
                if self.bdebug_menu:
                    deb.pack_forget()
                else:
                    main.pack_forget()
                hide_btn2.config(text="Show(F7)")
            else:
                if self.bdebug_menu:
                    deb.pack(fill="x", padx=0, pady=s(6), side="bottom")
                else:
                    main.pack(fill="x", padx=s(10), pady=s(5), side="bottom")
                hide_btn2.config(text="Hide(F7)")
            self.root.update_idletasks()
            #self.root.geometry("")

        def toggle_clickthrough_0():
            # keep your existing behavior here; just use self.* where needed
            global is_clickthrough
            if is_clickthrough:
                self.make_interactive()
                if self.indicator_label:
                    self.indicator_label.config(text="")
                    self.lock_btn.config(
                        text="Lock(F6)", fg="white"
                    )
            else:
                self.make_clickthrough()
                if self.indicator_label:
                    self.indicator_label.config(text="🔒", fg="red")
                    self.lock_btn.config(
                        text="Unlock(F6)", fg="#ffa0a0"
                    )
            is_clickthrough = not is_clickthrough

        def toggle_debug():
            # This is your existing toggle_debug logic,
            # but referencing self.var* and local widgets
            self.bdebug_menu = not self.bdebug_menu

            if self.bhidden:
                self.bhidden = False
                hide_btn2.config(text="Hide(F7)")

            if self.bdebug_menu:
                main.pack_forget()
                debug_btn.config(text="Back")

                config.dex = self.var3.get()
                config.debug_mode = self.var4.get()

                deb.pack(fill="none", padx=0, pady=s(6), side="bottom")
            else:
                config.dex = self.var3.get()
                config.debug_mode = self.var4.get()

                deb.pack_forget()
                debug_btn.config(text="Debug")
                main.pack(fill="x", padx=s(10), pady=s(5), side="bottom")

        def trigger1(flag, tvar_value):
            # This replaces "root.destroy() + call other GUI"
            #t = time.perf_counter()
            if flag:
                config.randomize_ban = True
            global is_clickthrough
            if is_clickthrough:
            
                self.toggle_clickthrough_0()    
            toggle_hide()
            initialize_hide_pass(None, None, None, None)

            # call your existing bridge function but with shared root

            self.on_f8_pressed(tvar_value)
            #print(f"Triggered F8 in {time.perf_counter() - t:.2f} seconds.")

        # ---- title bar buttons ----
        close_btn2 = tk.Button(
            title_bar2, command=lambda: close2(self.root),
            text="x", width=s(2), height=1, fg="white", relief="flat",
            bg="#141420", font=fonttk(exo, 12, 'normal'), cursor="hand2"
        )
        close_btn2.pack(side="right", padx=0)

        hide_btn2 = tk.Button(
            title_bar2, command=toggle_hide,
            text="Hide(F7)", relief="flat", fg="white", bg="#141420",
            font=fonttk(carbon, 10, 'normal'), cursor="hand2"
        )
        hide_btn2.pack(side="right", padx=1)

        debug_btn = None
        if config.debug_mode or config.debug_menu:
            debug_btn = tk.Button(
                title_bar2, command=toggle_debug,
                text="Debug", relief="flat", fg="#FCD92E", bg="#141420",
                font=fonttk(carbon, 10, 'normal'), cursor="hand2"
            )
            debug_btn.pack(side="right", padx=1)

        self.lock_btn = tk.Button(
            title_bar2, command=self.toggle_clickthrough_0,
            text="Lock(F6)", relief="flat", fg="white", bg="#141420",
            font=fonttk(carbon, 10, 'normal'), cursor="hand2"
        )
        self.lock_btn.pack(side="right", padx=1)

        self.indicator_label = tk.Label(
            title_bar2, text="", fg="white", bg="#141420", font=fonttk("Arial", 12)
        )
        self.indicator_label.pack(side="left", padx=0)

        # hotkey
        if not config.mobile_mode:
            self.hotkey_f7_id = keyboard.add_hotkey(
                "f7",
                lambda: self.root.after(0, toggle_hide)
            )
            self.hotkey_f6_id = keyboard.add_hotkey(
                "f6",
                lambda: self.root.after(0, self.toggle_clickthrough_0)
            )

            self.hotkey_f8_id = keyboard.add_hotkey('f8', lambda: self.root.after(0, lambda: trigger1(self.var1.get(),self.tvar.get())))

        # main button (your bans trigger)
        fra = tk.Frame(main, bg="#151426", relief="solid", height=s(33), width=s(210))
        fra.pack(side="top", expand=True)
        fra.pack_propagate(False)
        self.search = tk.Frame(main, bg="#151426", relief="solid", height=s(33), width=s(210))


        def search_by_name_toggle():
            print("Manual mode toggled:", self.var5.get())
            if self.var5.get():
                self.search.pack(side="bottom", fill="both",expand=True)
                entry.bind("<FocusIn>", clear_on_click)
                self.search.pack_propagate(False)
            else:
                self.search.pack_forget()
                self.var5.set(False)
                self.tvar.set('Name(s): "EyeingFlux, BicZilla"')
        

        button = tk.Button(
            fra,
            text="Bans F8", height=1, state="normal",
            relief="flat", bg="#FCD92E",
            font=fonttk("Rajdhani SemiBold", 'bold', 13),
            command=lambda: trigger1(self.var1.get(), self.tvar.get()),
            cursor="hand2"
        )
        self.var5 = tk.BooleanVar()
        man = tk.Checkbutton(
            fra, bg="#151426", fg="white", selectcolor="#151426",
            text="By Name", font=fonttk(rajdhani, 10,"normal"), variable=self.var5, command=search_by_name_toggle)
        man.pack(side="right", padx=(0, 0))
        # button2 = tk.Button(
        #     fra,
        #     text="Search", state="normal",
        #     relief="flat", bg="#FCD92E",
        #     font=fonttk("Rajdhani Medium", 'normal', 12),
        #     command=lambda: lookup(tvar.get()),
        #     cursor="hand2"
        # )
        self.tvar = tk.StringVar()
        self.tvar.set('Name(s): "EyeingFlux, BicZilla"')
        entry = tk.Entry(self.search, textvariable=self.tvar,  highlightthickness=1, highlightbackground="#FFFFFF", highlightcolor="#FCD92E",bg="#D8D4F8", width = s(28),fg="#151426", relief="solid", font=fonttk(rajdhani_medium, 'normal', 10), justify="left")

        button.pack(side="right",padx=(s(2),s(6)),expand=False)

        entry.pack(side="bottom",pady=(s(5),0),ipady=s(2),expand=False)
        # button2.pack(side="left",padx=(0,0),expand=False)
        def clear_on_click(event):
            event.widget.delete(0, tk.END)

        entry.bind("<FocusIn>", clear_on_click)
        close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
        close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))

        
        hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
        hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
        self.lock_btn.bind("<Enter>", lambda e: self.lock_btn.config(bg="#31314D"))
        self.lock_btn.bind("<Leave>", lambda e: self.lock_btn.config(bg="#141420"))
        def lookup(name):
            print("Looking up", name)
        button.config(state="normal", bg="#FCD92E", cursor="hand2")
        button.bind("<Enter>", lambda e, b=button: b.config(bg="#A18D25"))
        button.bind("<Leave>", lambda e, b=button: b.config(bg="#FCD92E"))

        # your hide init
        initialize_hide_pass(toggle_hide, deb, main, hide_btn2)

        self.root.update_idletasks()
        self.root.geometry("")              # <-- critical: reset to requested size
        self.root.update_idletasks()
        x, y = self.get_launcher_position()
        self.root.geometry(f"+{x}+{y}")     # restore position on selected monitor

        if not config.mobile_mode:
            try:
                self.hwnd = win32gui.FindWindow(None, self.root.title())
            except Exception:
                self.hwnd = None

    # =========================
    # Match Overview Page (refactor of show_gui)
    # =========================

    def setup_super_frame(self, parent):
        """
        Create the fixed logical 2560x1440 parent used to position PlayerFrames.

        PlayerFrame itself is intentionally left unchanged. Each PlayerFrame is
        instead given a small holder frame that is placed at an (x, y) offset
        inside this SuperFrame.
        """

        canvas = tk.Canvas(parent, relief="flat", borderwidth=0, highlightthickness=0, width=s(SUPER_FRAME_WIDTH), height=s(SUPER_FRAME_HEIGHT))
        canvas.pack(side="top", anchor="nw", fill="both", expand=True)
        canvas.pack_propagate(False)  # Remove window decorations

                        
        super_frame = SuperFrame(
            master=canvas,
            width=s(SUPER_FRAME_WIDTH),
            height=s(SUPER_FRAME_HEIGHT),
            
        )
        super_frame.pack(side="top",fill="both", expand=True)
        super_frame.createSuperFrameImage(img_key="bgDLSS4", anc="nw", x=0, y=0)


        # Keep the SuperFrame at its requested 2560x1440 logical size instead of
        # allowing its children to determine its dimensions.
        
        return super_frame


    def build_match_overview(self, parent, players):
        global NAMEPLATES
        NAMEPLATES = []

        self.root.title("Match Overview")
        self.stat_frame_height = 112# 145 #112
        self.player_frame_width = 380
        width = 2560
        he = 12 if SCALE != 1 else 0
        h = 1440
        w = 2560
        
        h = 1440

        # Use the selected monitor's virtual-desktop origin.
        self.root.overrideredirect(True)

        self.refresh_monitors()
        self.monitor = self.get_selected_monitor()

        self.x_m = self.monitor["left"]
        self.y_m = self.monitor["top"]

        w = 2560
        h = 1440

        self.force_geometry(w, h, self.x_m, self.y_m)

        self.after_idle_tracked(
            lambda: self.force_geometry(w, h, self.x_m, self.y_m)
        )
        self.after_tracked(
            30,
            lambda: self.force_geometry(w, h, self.x_m, self.y_m)
        )
        self.root.after(0, lambda: print("actual", self.root.winfo_x(), self.root.winfo_y()))
        self.root.configure(bg="black")

        title_bar = tk.Frame(parent, bg="#141420", relief="groove", height=s(30), width=s(width))
        title_bar.pack(fill="x", side="top", expand=True)

        player_frames = tk.Frame(parent, relief="flat", borderwidth=0, highlightthickness=0,bg="#141420")
        player_frames.pack(side="top", fill="both", padx=0, pady=0, expand=True)

        

        def toggle_hide():
            self.bHide = not self.bHide
            if self.bHide:
                player_frames.pack_forget()
                hide_btn.config(text="Show(F7)")
                self.root.update_idletasks()
                self.force_geometry(w, s(30), self.x_m, self.y_m)
            else:
                player_frames.pack(side="bottom", fill="both", expand=True)
                hide_btn.config(text="Hide(F7)")
                self.root.update_idletasks()
                self.force_geometry(w, h, self.x_m, self.y_m)

        def go_back_to_launcher():
            # Instead of destroying root, just go back
            self.show_launcher_page()

        close_btn = tk.Button(
            title_bar,
            command=go_back_to_launcher,  # <--- key change
            text="x", width=s(2), height=s(1),
            fg="white", relief="flat", bg="#141420",
            font=fonttk(exo, 12, 'normal'), cursor="hand2"
        )
        close_btn.pack(side="right", padx=0)

        hide_btn = tk.Button(
            title_bar, command=toggle_hide, text="Hide(F7)",
            relief="flat", fg="white", bg="#141420",
            font=fonttk(carbon, 10, 'normal'), cursor="hand2"
        )
        hide_btn.pack(side="right", padx=10)

        self.lock_btn = tk.Button(
            title_bar, command=self.toggle_clickthrough_0,
            text="Lock(F6)", relief="flat", fg="white", bg="#141420",
            font=fonttk(carbon, 10, 'normal'), cursor="hand2"
        )
        self.lock_btn.pack(side="right", padx=10)

        self.indicator_label = tk.Label(
            title_bar, text="", fg="white", bg="#141420", font=fonttk("Arial", 12)
        )
        self.indicator_label.pack(side="left", padx=0)

        if not config.mobile_mode:
           
            self.hotkey_f7_id = keyboard.add_hotkey(
                "f7",
                lambda: self.root.after(0, toggle_hide)
            )
            self.hotkey_f6_id = keyboard.add_hotkey(
                "f6",
                lambda: self.root.after(0, self.toggle_clickthrough_0)
            )

        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#d41c1c"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#141420"))


        hide_btn.bind("<Enter>", lambda e: hide_btn.config(bg="#31314D"))
        hide_btn.bind("<Leave>", lambda e: hide_btn.config(bg="#141420"))
        self.lock_btn.bind("<Enter>", lambda e: self.lock_btn.config(bg="#31314D"))
        self.lock_btn.bind("<Leave>", lambda e: self.lock_btn.config(bg="#141420"))
        # Your existing logic
        #top_player = max(players, key=lambda p: float(p.playermvp.strip('%')))
        #top_player.ace = True

        #rank_players(players)
        # for p in players:
        #     print(
        #         f"{p.best_rank}. {p.name}  | "
        #         f"Final={p.final_score:.3f}  "
        #         f"(Overall={p.overall_score:.3f}, {p.best_hero}(Best Char Score)={p.char1_score:.3f})"
        #     )
        t = time.perf_counter()
        from stats_db import StatsDB
        from stats_db_diff_queue import append_diff_jsonl
        global DB
        DB = StatsDB()

        # Build one fixed 2560x1440 coordinate space first. PlayerFrame is left
        # untouched; each instance receives a holder frame positioned relative
        # to this SuperFrame.
        self.super_frame = self.setup_super_frame(player_frames)
        self.player_frame_slots = []
        self.coordinates = {
                            "6": {
                                "1": (0, 10),
                                "2": (425, 10),
                                "3": (850, 10),
                                "4": (1275, 10),
                                "5": (1700, 10),
                                "6": (2125, 10),
                            },
                            "5": {
                                "1": (80, 10),
                                "2": (572, 10),
                                "3": (1064, 10),
                                "4": (1556, 10),
                                "5": (2048, 10),
                            },
                            "4": {
                                "1": (164, 10),
                                "2": (766, 10),
                                "3": (1368, 10),
                                "4": (1970, 10),
                            },
                            "3": {
                                "1": (286, 10),
                                "2": (1068, 10),
                                "3": (1848, 10),
                            },
                            "2": {
                                "1": (572, 10),
                                "2": (1556, 10),
                            },
                            "1": {
                                "1": (1168, 10),
                            },
                        }
        t = time.perf_counter()
        p_count = len(players)
        idx = 1
        for player in players:
            # Default placement preserves the old side-by-side layout, but the
            # values are now true offsets from the SuperFrame's top-left corner.
            # Change either value here later to freely position each PlayerFrame.
            x, y = self.coordinates.get(str(p_count), {}).get(str(idx), (0, 44))
            
            idx += 1
            PlayerFrame(self.super_frame, player, x, y).build()
            #create_player_frame(player_slot, player)
        print(f"Created player frames in {time.perf_counter() - t:.2f} seconds.")
        
        #self.super_frame.createSuperFrameImage(img_key="bg_clouds", anc="nw", x=0, y=0)
        
          # ./data/marvel_stats.db next to stats_db.py
        ops = DB.upsert_players(players)  # you must modify upsert_players to return ops
        DB.close()

        if config.bUseCloudSync:
            if not config.IS_ADMIN and ops:
                from stats_db_diff_queue import append_diff_jsonl

                append_diff_jsonl(
                    path=config.pending_diffs_path,
                    user_id=config.LOCAL_USERNAME,
                    cloud_etag_base=getattr(config, "cloud_master_etag", "unknown"),
                    ops=ops,
                )
        

        self.root.update_idletasks()

        if not config.mobile_mode:
            try:
                self.hwnd = win32gui.FindWindow(None, self.root.title())
            except Exception:
                self.hwnd = None
    
    # =========================
    # Bridge (refactor of on_f8_pressed)
    # =========================


    def on_f8_pressed(self, tvar_value):
        MATCH_PLAYERS = []
        print(f">> Script running. Press F8 to OCR names and check tracker.gg...")
        search_by_name = True if tvar_value and tvar_value != 'Name(s): "EyeingFlux, BicZilla"' else False
        initialize_hide_pass(None, None, None,None)
        
        #if search_by_name:
            #names = [name.strip() for name in tvar_value.split(",") if name.strip()]
            #if names[0] == "STATSDB":
                #print(">> STATSDB command detected. Fetching all player names from the database...")
                #from tracker_lookup import fetchNamesForDB
                #np=helpers.create_path("_1Names.txt", 'debug')

                #names = helpers.load_list(np)
                #fetchNamesForDB(names)
                #time.sleep(100000)
                #print(f">> Fetched {len(names)} names from the database and saved.")
                #return

            #print(f">> Searching for names: {names}")
        #elif MANUAL_DEBUG == 69:
                #names = ['BicZilla','EyeingFlux','BicZilla.']
                #from tracker_lookup import open_multiple_tracker_profiles
                #tracker_data = open_multiple_tracker_profiles(names)
                #save_json("_DEBUGTrackerGGJSON.json", tracker_data)
        # elif config.debug_mode:
            
        #     trackerdata = helpers.create_path("_2TrackerGGJSON.json", 'debug')
        #     tracker_data = helpers.load_json(trackerdata)
        #     names = list(tracker_data.keys())
        #     print(">> Loaded names from debug JSON.")
        #     if not config.randomize_ban:
        #         if not config.mobile_mode:
        #             np=helpers.create_path("_1Names.txt", 'debug')
        #             names = helpers.load_list(np)
        #             #names = CAPTURE(flag_debug=True)
        #             #if names:
        #                 #save_list_file(names,"_1Names.txt")
        #else:
            
        if bUseRivalsDataNames:
            if bLiveDebug:
                p = os.path.join(config.script_dir, "debug","LiveDebug.json")
                li = helpers.load_json(path=p)
                from RDMO import Match
                import tracker_trim
                MatchObject = Match(li)
                tracker_trim.getTrackerGG(MatchObject, bLiveDebug)
                MATCH_PLAYERS = []
                names = None
                for p in MatchObject.players:
                    if "*" in p.Name:
                        #print(f"Skipping {p.Name}: Private Account")
                        continue
                    MATCH_PLAYERS.append(p)
                #from tracker_trim import open_multiple_tracker_profiles
                #open_multiple_tracker_profiles(MatchObject)
                
            
            elif bTrackerDebug:
                import tracker_trim
                from tracker_trim_debug_helper import make_debug_live_match
                live_match_data = make_debug_live_match(bTrackerNames)
                from RDMO import Match
                matches = Match(live_match_data)
                tracker_trim.getTrackerGG(matches)
                MATCH_PLAYERS = []
                names = None
                for p in matches.players:
                    if "*" in p.Name:
                        #print(f"Skipping {p.Name}: Private Account")
                        continue
                    MATCH_PLAYERS.append(p)
                

            else:
                from RDMO import Match
                import tracker_trim
                if not True:
                    MATCH_PLAYERS = tracker_trim.main()
                    tracker_data = None
                    names = None
                else:
                    print(">> Fetching names via Live Match API..")
                    live_match_data = tracker_trim.getLive()
                    match = Match(live_match_data)
                    tracker_trim.getTrackerGG(match)
                    MATCH_PLAYERS = []
                    names = None
                    for p in match.players:
                        if "*" in p.Name:
                            #print(f"Skipping {p.Name}: Private Account")
                            continue
                        MATCH_PLAYERS.append(p)
                    
                    #print(names)
                    #if not names:
                        #print("No valid player data to display.")
                        #self.show_launcher_page()
                        #return False
                    #tracker_trim.getTrackerGG(MatchObject)
                    #MATCH_PLAYERS = []
                    #for p in MatchObject.players:
                        #if "*" in p.Name:
                            #print(f"Skipping {p.Name}: Private Account")
                            #continue
                        ##MATCH_PLAYERS.append(p)
                    
        else:
            print(">> Capturing names via OCR...")
            names = []
            #names = ['Razzerz', 'bk123456', 'Sour-']

        #print("\n🎯 Captured Player Names:")
        #for name in names:
            #print(f"- {name}")

        players = []
        if len(MATCH_PLAYERS) > 0:
            self.show_match_page(MATCH_PLAYERS)
        else:
            print(">> No valid player data to display.")
            self.show_launcher_page()  # Go back to launcher if no players
        return
        

    def toggle_clickthrough_0(self):
            # keep your existing behavior here; just use self.* where needed
        global is_clickthrough
        if is_clickthrough:
            self.make_interactive()
            if self.indicator_label:
                self.indicator_label.config(text="")
                self.lock_btn.config(
                    text="Lock(F6)", fg="white"
                )
                self.root.update_idletasks()
                #self.root.overrideredirect(True)
                
        else:
            self.make_clickthrough()
            if self.indicator_label:
                self.indicator_label.config(text="🔒", fg="red")
                self.lock_btn.config(
                    text="Unlock(F6)", fg="#ffa0a0"

                )
                self.root.update_idletasks()
                #self.root.overrideredirect(False)
                
        is_clickthrough = not is_clickthrough

    def toggle_lock(self,lock_button):
        current = lock_button.cget("text")

        print(current)
        lock_button.config(text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)")
        self.toggle_clickthrough()
            
    def make_clickthrough(self):
        global hwnd
        self.root.attributes("-topmost", False)

        self.root.lower()

        if not config.mobile_mode:
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style)
        #print("LOCKED")

    def make_interactive(self):
        global hwnd
        self.root.attributes("-topmost", True)
        if not config.mobile_mode:
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            style &= ~win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style)
        #print("UNLOCKED")

    def widget_exists(self,widget):
        try:
            return bool(widget.winfo_exists())
        except:
            return False

    def run(self):
        self.root.mainloop()



# ENTRY POINT:
def start_app():
    global icon_idx
    icon_idx =0
    app = App(BASE_DPI_SCALE)
    app.run()
        
