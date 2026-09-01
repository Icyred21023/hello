from __future__ import annotations
import os
import tkinter as tk
import config
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab,  ImageDraw, ImageChops,ImageOps,ImageFont

import os
import random
from typing import Any, Literal
import sys
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




WIDTH = 480
REGIONS = {
            "Name Bar": (WIDTH,80),
            "Overview Banner": (WIDTH,40),
            "Overview": (WIDTH, 180),
            "Hero Banner": (WIDTH, 35),
            "Hero": (WIDTH, 112),
            "Match History Banner": (WIDTH, 35),
            "Match": (WIDTH,38)
            }
OUTER = (0,0)

HEIGHT = 0
for item in REGIONS:
    w1,h1 = REGIONS[item]
    if item in ["Hero","Match"]:
        h1 = h1 * 4 if item == "Hero" else h1
        h1 = h1 * 8 if item =="Match" else h1
    HEIGHT += h1
OUTER = (WIDTH,HEIGHT)
print("HAIHSIJSIAJS\n\n\n")
print(HEIGHT)



if not config.mobile_mode:
    
    import win32gui
    import win32con
    # import win32api
    # import win32process
    # import win32com.client
    # import ctypes
    import keyboard

    import ctypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    def get_dpi():
        try:
            return user32.GetDpiForSystem()
        except AttributeError:
            hdc = user32.GetDC(0)
            try:
                return gdi32.GetDeviceCaps(hdc,88)
            finally:
                user32.ReleaseDC(0,hdc)
    user32.SetProcessDPIAware()
    BASE_DPI = 96
    
    dpi = get_dpi()

SHEETS_DIR = os.path.join(config.script_dir, "assets_match_hd")
CROP_CACHE_PATH = os.path.join(SHEETS_DIR, "_mastery_crop_cache.json")
import _Mastery_Sheet_Editor 
crop_cache = _Mastery_Sheet_Editor.load_crop_cache(CROP_CACHE_PATH) if os.path.exists(CROP_CACHE_PATH) else {}
bTest = True
bSpecialBG = False
#from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageChops

def punch_text_out_of_image(
    img_rgba: Image,
    text: str,
    xy: "tuple[int, int]",
    font: ImageFont.FreeTypeFont,
    fill: int = 255,
    text_anchor: str = "lt",
) -> Image:
    """
    Returns a new RGBA image where alpha is cleared (transparent)
    ONLY where the text is drawn.
    """
    img = img_rgba.convert("RGBA")
    w, h = img.size

    # 1) Build a text mask (white text on black background)
    text_mask = img.new("L", (w, h), 0)
    d = ImageDraw.Draw(text_mask)
    d.text(xy, text, fill=fill, font=font, anchor=text_anchor)

    # 2) Subtract text mask from existing alpha
    r, g, b, a = img.split()
    new_a = ImageChops.subtract(a, text_mask)  # alpha reduced where text is
    img.putalpha(new_a)
    return img
def split_edges(total: int, parts: int) -> "list[int]":
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
SCALE = 1  # preserve aspect ratio
root.destroy()
TARGET_DPI_SCALE = (SCALE * 96) / 72 

print(SCALE)
if config.mobile_mode:
   
    SCALE =1
    print(SCALE)
def s(v):
    if isinstance(v, (tuple, list)):
        return tuple(int(x * SCALE) for x in v)
    return int(v * SCALE)

def create_root(scale=None):
    if scale:
        s = 1
    else:
        s = 1
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
refrig_bold = 'Refrigerator Deluxe Bold' # Bold
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





#if not config.mobile_mode:    
    #from ocr_capture import capture_names as CAPTURE
    #from tracker_lookup import open_multiple_tracker_profiles
import json
import os

#t= time.perf_counter()
#from player2 import Player2
#from playerNEW import Hero, Player
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

from RDMO import Player, Hero
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
from typing import Union, Literal
import fGui_Ui




    # ---------------------------
class PlayerFrame(tk.Canvas):
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

    def __init__(self, parent):
        self.parent = parent
        self.player = None

        canvas_width = 400
        canvas_height = 1200

        super().__init__(
            parent,
            width=canvas_width,
            height=canvas_height,
            highlightthickness=0,
            bd=0,
        )
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
        #self._build_name_bar()
        #self._build_overview()
        #self._build_heroes()
        #self._build_history()

        return self.outer

    # ---------------------------
    # Small helpers
    # ---------------------------
    def _s2(self, xy):
        """Your existing s(...) scaler expects tuples sometimes."""
        return s(xy)

    def _safe_attr(self, obj, attr, default=None):
        return getattr(obj, attr, default)

    def _safe_at(self, lst, idx, default=None):
        return lst[idx] if isinstance(lst, list) and 0 <= idx < len(lst) else default

    def _topn(self, lst, n):
        return lst[:n] if isinstance(lst, list) else []

    

    #Get coordinates of a widget relative to the root window
    def _get_iterative_coordinates(self, Frame: tk.Canvas = None, Widget: tk.Widget = None, padx: int = 0, pady: int = 0):
        """
        Frame = the canvas containing the widget
        Widget = the widget you want coordinates for
        padx, pady = optional padding to add around the widget's bbox (in pixels)
        """
        try:
            x1, y1, x2r, y2 = Frame.bbox(Widget)

            #pad = s(5)  # 5px (scaled)
            x_before = x1 - padx if x1 > padx else x1
            y_before = y1 - pady if y1 > pady else y1
            x_after = x2r + padx
            y_after = y2 + pady  # keep your current y logic (or use y1/y2 if you want)
            return x_after, y_after, x_before, y_before
        except Exception as e:
            print("get_iterative_coordinates error:", e)
            return None, None, None, None
        
    def _get_end_x_coord(self, Frame: tk.Canvas = None, Widget: tk.Widget = None):
        """
        Frame = the canvas containing the widget
        Widget = the widget you want coordinates for
        padx, pady = optional padding to add around the widget's bbox (in pixels)
        """
        try:
            x1, y1, x2r, y2 = Frame.bbox(Widget)

            
            return x2r
        except Exception as e:
            print("get_end_x_coord error:", e)
            return None

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
        self.roles = getattr(self.ov, "role_objs", []) or []
        self.matches = getattr(p, "matches", []) or []
        if not isinstance(self.matches, list):
            self.matches = []

        #fov = getattr(p, "full_overview", None)
        #self.fov_heroes = fov.heroes if fov and hasattr(fov, "heroes") else []
        self.TTSuperCondLight = 'TT Sprmlt N Trl Cnd Lt'
        self.TTSuperCondMedium = 'TT Sprmlt N Trl Cnd Md'
        self.TTSuperCondThin = 'TT Sprmlt N Trl Cnd Th'

        # top3 heroes
        self.top3 = self._topn(getattr(p, "top_heroes", []) or [], 4)
        self.char_scores = [getattr(h, "score", None) for h in self.top3]

        # total time
        # self.total_time_played = sum(
        #     h.time_played for h in getattr(p, "heroes", []) if hasattr(h, "time_played")
        # )
        #print(f"Total Time Played for {p.name}: {self.total_time_played}")

        # order by score desc (1-based indices)
        self.order = [
            i
            for i, score in sorted(
                ((i + 1, score) for i, score in enumerate(self.char_scores) if score is not None),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

    # ---------------------------
    # OUTER
    # ---------------------------
    def _build_outer(self):
        NAME_BANNER = "#24212B"
        add = 12 if int(SCALE) != 1 else 0

        outer_width = s(400)
        outer_height = (
            1200
        )

        # PlayerFrame is already the inherited tk.Canvas.
        self.configure(
            width=outer_width,
            height=outer_height,
            bg=NAME_BANNER,
        )
        self.pack(side="left", fill="both")

        # Build the outer SuperFrame directly on the inherited canvas.
        self.outer = fGui_Ui.SuperFrame(
            self,
            width=outer_width,
            height=outer_height,
            
            borderwidth=1,
            relief="flat",
        )
        self.outer.pack(fill="both")

        # Draw Placeholder through the SuperFrame image API.
        self.placeholder_image = self.outer.createSuperFrameImage(
            "outer",
            anc="nw",
            size=(outer_width, outer_height),
            x=0,
            y=0,
        )

    # ---------------------------
    # NAME BAR (outer -> name_bar + canvas)
    # ---------------------------
    def _build_name_bar(self):
        NAME_BANNER = "#24212B"

        # pick unique nameplate (same behavior)
        global NAMEPLATES
        while True:
            num = random.randint(1, 244)
            if num < 82:
                num = random.randint(1, 244)
            nameplate = f"1 ({num})"
            if nameplate not in NAMEPLATES:
                NAMEPLATES.append(nameplate)
                self.nameplate = nameplate
                break

        name_bar = tk.Frame(
            self.outer,
            bg=NAME_BANNER,
            height=s(60),
            relief="raised",
            borderwidth=3,
        )
        name_bar.pack(side="top", fill="x", padx=(1, 0))
        name_bar.pack_propagate(False)

        name_canvas = tk.Canvas(name_bar, highlightthickness=0)
        name_canvas.pack(anchor="center", fill="both")

        # banner image
        self._create_canvas_image(
            name_canvas,
            img_key=self.nameplate,
            size=(402, 91),
            bg=NAME_BANNER,
            x=-23,
            y=-15,
        )

        name_canvas.create_text(
            s(6),
            s(44),
            text=self.player.name,
            fill="white",
            font=fonttk(refrig_heavy, 23, "bold"),
            anchor="sw",
        )
    def proficiency_handler(self,hours, hero):
            lv60 = 195/2 #AnimatedLord, Badge4, Gold
            lv55 = 165/2 #AnimatedLord, Badge4, Gold
            lv50 = 137.5/2 #AnimatedLord, Badge3, Gold
            lv45 = 112.5/2 #Lord, Badge3, Gold
            lv40 = 90/2 #Lord, Badge2, Gold
            lv35 = 70/2 #Lord, Badge2, Purple
            lv30 = 52.5/2 #Lord, Badge1, Purple
            lv25 = 37/2 #Lord, Badge1
            lv20 = 25/2 #Lord
            lv15 = 15/2
            lv10 = 7.5/2
            lv5 = 2.5/2

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
    # OVERVIEW (outer -> overview_bar + overview_stats)
    # ---------------------------
    
    
# ---------------------------
# Drop-in replacement usage
# ---------------------------
def create_player_frame(parent):
    return PlayerFrame(parent).build()

class App:
    def __init__(self, base_dpi_scale):
        self.base_dpi_scale = 1
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

        # You had these as globals; keep as app state
        self.global_debugflag = False

        # show first page
        self.show_launcher_page()
    def force_geometry(self, w, h, x, y):
        # apply twice, one tick apart (this fixes intermittent Windows behavior)
        geo = f"{w}x{h}+{x}+{y}"
        self.root.geometry(geo)
        self.root.update_idletasks()
        self.root.geometry(geo)
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
        
    def show_beta_page(self):
        self.unregister_hotkeys()
        self.cancel_all_afters()
        self.clear_page()
        self.page = tk.Frame(self.root, bg="black")
        self.page.pack()

        self.build_beta(self.page)

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
    def build_launcher(self, parent):
        # ----- your original top-of-function setup -----
        self.font_scale = 2 if config.mobile_mode else 1
        font_sizes = list(range(6, 70))
        self.fonts = {size: scale_font(self.font_scale, size) for size in font_sizes}
        
        self.bhidden = False
        self.bdebug_menu = False

        # window position like your original
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width // 2) + s(175)
        y = 0
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
        self.ui_config = tk.Frame(deb, bg="#151426", relief="solid", height=s(250), width=s(230))
        #ui_config.pack(fill="both", padx=0, pady=0, side="bottom")
        #ui_config.pack_forget()

        def show_ui_config():
            from tkinter import ttk
            self.bConfigUI = not self.bConfigUI
            
            if not self.bConfigUI:

                self.ui_config.destroy()
            else:
                self.ui_config = tk.Frame(deb, bg="#151426", relief="solid", height=s(250), width=s(230))
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
                    self.bConfigUI = False
                    self.ui_config.destroy()

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
        self.root.geometry(f"+{x}+{y}")     # restore position after autosize

        if not config.mobile_mode:
            try:
                self.hwnd = win32gui.FindWindow(None, self.root.title())
            except Exception:
                self.hwnd = None

    # =========================
    # Match Overview Page (refactor of show_gui)
    # =========================
    
    def build_beta(self, parent):
      w = 400
      h= 1200
      self.force_geometry(w,h,0,0)
      self.after_idle_tracked(lambda: self.force_geometry(w, h, 0, 0))
      self.after_tracked(30, lambda: self.force_geometry(w, h, 0, 0))
      self.root.after(0, lambda: print("actual", self.root.winfo_x(), self.root.winfo_y()))
      self.root.configure(bg="black")
      
      title_bar = tk.Frame(parent, bg="#141420", relief="groove", height=s(30), width=s(400))
      title_bar.pack(fill="x", side="top", expand=True)

      player_frames = tk.Frame(parent, bg="#131523")
      player_frames.pack(side="bottom",fill="both", expand=True)
      pf = PlayerFrame(player_frames).build()
      pf.pack(side="left", padx=2)

      
    def build_match_overview(self, parent, players):
        global NAMEPLATES
        NAMEPLATES = []

        self.root.title("Match Overview")
        self.stat_frame_height = 112# 145 #112
        self.player_frame_width = 480
        width = len(players) * s(WIDTH)
        he = 12 if SCALE != 1 else 0
        _,h = OUTER



        h += he
        w = s(len(players) * WIDTH)
        
        #h = s(724) + s((self.stat_frame_height*4)) + (12 if SCALE != 1 else 0)

        screen_width = self.root.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 0

        self.force_geometry(w, h, 0, 0)

        # also re-apply on idle (handles the intermittent "stays put" case)
        self.after_idle_tracked(lambda: self.force_geometry(w, h, 0, 0))
        self.after_tracked(30, lambda: self.force_geometry(w, h, 0, 0))
        self.root.after(0, lambda: print("actual", self.root.winfo_x(), self.root.winfo_y()))
        self.root.configure(bg="black")
#START HERE
        title_bar = tk.Frame(parent, bg="#141420", relief="groove", height=s(30), width=s(width))
        title_bar.pack(fill="x", side="top", expand=True)

        player_frames = tk.Frame(parent, bg="#131523")
        player_frames.pack(side="bottom",fill="both", expand=True)

        

        def toggle_hide():
            self.bHide = not self.bHide
            if self.bHide:
                player_frames.pack_forget()
                hide_btn.config(text="Show(F7)")
                self.root.update_idletasks()
                self.force_geometry(w, s(30), 0, 0)
            else:
                player_frames.pack(side="bottom", fill="both", expand=True)
                hide_btn.config(text="Hide(F7)")
                self.root.update_idletasks()
                self.force_geometry(w, h, 0, 0)

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

        rank_players(players)
        for p in players:
            print(
                f"{p.best_rank}. {p.name}  | "
                f"Final={p.final_score:.3f}  "
                f"(Overall={p.overall_score:.3f}, {p.best_hero}(Best Char Score)={p.char1_score:.3f})"
            )
        t = time.perf_counter()
        from stats_db import StatsDB
        from stats_db_diff_queue import append_diff_jsonl
        global DB
        DB = StatsDB()
        for player in players:
            pf = PlayerFrame(player_frames, player).build()
            pf.pack(side="left", padx=2)
            #create_player_frame(player_frames, player)
        #print(f"Created player frames in {time.perf_counter() - t:.2f} seconds.")
        

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
        self.show_beta_page()
        return
        print(f">> Script running. Press F8 to OCR names and check tracker.gg...")
        search_by_name = True if tvar_value and tvar_value != 'Name(s): "EyeingFlux, BicZilla"' else False
        initialize_hide_pass(None, None, None,None)
        
        if search_by_name:
            names = [name.strip() for name in tvar_value.split(",") if name.strip()]
            if names[0] == "STATSDB":
                print(">> STATSDB command detected. Fetching all player names from the database...")
                from tracker_lookup import fetchNamesForDB
                np=helpers.create_path("_1Names.txt", 'debug')

                names = helpers.load_list(np)
                fetchNamesForDB(names)
                time.sleep(100000)
                print(f">> Fetched {len(names)} names from the database and saved.")
                return

            print(f">> Searching for names: {names}")
        elif MANUAL_DEBUG == 69:
                names = ['BicZilla','EyeingFlux','BicZilla.']
                tracker_data = open_multiple_tracker_profiles(names)
                save_json("_DEBUGTrackerGGJSON.json", tracker_data)
        elif config.debug_mode:
            
            trackerdata = helpers.create_path("_2TrackerGGJSON.json", 'debug')
            tracker_data = helpers.load_json(trackerdata)
            names = list(tracker_data.keys())
            print(">> Loaded names from debug JSON.")
            if not config.randomize_ban:
                if not config.mobile_mode:
                    np=helpers.create_path("_1Names.txt", 'debug')
                    names = helpers.load_list(np)
                    #names = CAPTURE(flag_debug=True)
                    #if names:
                        #save_list_file(names,"_1Names.txt")
        else:
            print(">> Capturing names via OCR...")
            names = CAPTURE()
            #names = ['Razzerz', 'bk123456', 'Sour-']

        print("\n🎯 Captured Player Names:")
        for name in names:
            print(f"- {name}")

        players = []
        
        if search_by_name and names:
            print(">> Fetching stats for manually entered names...")
            t = time.perf_counter()
            tracker_data = open_multiple_tracker_profiles(names)
            print(f"Fetched tracker.gg data in {time.perf_counter() - t:.2f} seconds.")
            save_json("_ByNamesTrackerGGJSON.json", tracker_data)
        elif not config.debug_mode and MANUAL_DEBUG != 69:
            if names:
                tracker_data = open_multiple_tracker_profiles(names)
                
                save_json("_2TrackerGGJSON.json", tracker_data)
                save_list_file(names,"_1Names.txt")
        elif config.debug_mode and MANUAL_DEBUG == 0:
            tracker_data = open_multiple_tracker_profiles(names)
            save_json("_2TrackerGGJSON.json", tracker_data)
            save_list_file(names,"_1Names.txt")
        if tracker_data:
            #tracker_data = transform_private_tracker_data(tracker_data)

            
            for name in tracker_data:
                data = tracker_data[name]
                if data is False or not data:
                    print(f"Skipping {name}: No Data Found")
                    continue
                if "errors" in data:
                    print(f"Skipping {name}: Private Account")
                    continue
                if len(data["data"]["segments"]) < 3:
                    print(f"Skipping {name}, no current season data found.")
                    continue
                
                p = Player(name, data)
                players.append(p)
            #print(f"Processed tracker.gg data in {time.perf_counter() - t:.2f} seconds.\n")

        if players:
            t = time.perf_counter()
            self.show_match_page(players)
            #print(f"Displayed match page in {time.perf_counter() - t:.2f} seconds.")
        else:
            print("No valid player data to display.")
            self.show_launcher_page()  # Go back to launcher if no players

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
    
if __name__ == "__main__":
    
    icon_idx =0
    app = App(BASE_DPI_SCALE)
    app.run()
        