

import tkinter as tk
import config
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab,  ImageDraw, ImageChops
import os
import random
import sys



import helpers
if not config.mobile_mode:
    from fonts_registry import register_ttf_private
#from main3 import HeroMatch
#import numpy as np
import config


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
    user32.SetProcessDPIAware()
    BASE_DPI = 96
    dpi = user32.GetDpiForSystem()


bTest = True
bSpecialBG = False
class SpriteSheetAnimator:
    def __init__(self, master, hero, sheet_path, rows, cols, fps=24, scale=0.45,
                 bg="#77789E", relief="sunken", borderwidth=1, size=None, bSubCrop=False):
        """
        size: tuple(w,h) target size for each frame after cropping (optional).
              If provided, overrides scale behavior.
        """
        self.colors = ['blue', 'green',  'pink', 'purple', 'white']
        self.herobg = "heromasterybg_"
        self.master = master
        self.fps = fps
        self.delay_ms = int(1000 / fps)
        self.scale = scale
        self.rows = rows
        self.hero = hero
        self.cols = cols
        self.size = size  # (w,h) optional

        # Fixed sub-crop inside each cell
        self.subcrop_x = 197
        self.subcrop_y = 119
        self.subcrop_w = 185
        self.subcrop_h = 185

        icon_wrap = tk.Frame(master, width=s(104), height=s(104), bg="#77789E")
        icon_wrap.pack(side="left")
        icon_wrap.pack_propagate(False)
        self.canvas = tk.Canvas(icon_wrap, width=s(104), height=s(104),
                        bg=bg, highlightthickness=0, bd=borderwidth, relief=relief)
        self.canvas.pack(fill="both", expand=False)
        self.canvas.pack_propagate(False)

        dx, dy = HERO_MASTERY_OFFSETS.get(self.hero, (0, 0))
        cx, cy = s(52), s(52)  # center of 104x104
        if bSpecialBG:
            random_color = random.choice(self.colors)
            bg_name = self.herobg + random_color
            self.hero_bg_colored = self.createOnlyImage(bg_name, size=(233, 104))
        
        # Load sheet and slice frames once
        sheet, (sheet_w, sheet_h) = self.createOnlyImage1(sheet_path)

        frame_w = sheet_w // cols
        frame_h = sheet_h // rows

        frames = []
        for r in range(rows):
            for c in range(cols):
                x0 = c * frame_w
                y0 = r * frame_h
                cell = sheet.crop((x0, y0, x0 + frame_w, y0 + frame_h))

                # ---- FIXED CROP INSIDE EACH CELL ----
                frame = cell
                if bSubCrop:
                    sx0 = self.subcrop_x
                    sy0 = self.subcrop_y
                    sx1 = sx0 + self.subcrop_w
                    sy1 = sy0 + self.subcrop_h

                    # Optional safety clamp if crop exceeds cell bounds
                    sx0 = max(0, min(sx0, cell.size[0]))
                    sy0 = max(0, min(sy0, cell.size[1]))
                    sx1 = max(0, min(sx1, cell.size[0]))
                    sy1 = max(0, min(sy1, cell.size[1]))

                    frame = cell.crop((sx0, sy0, sx1, sy1))
                # ------------------------------------

                # Resize rule:
                # - if explicit size provided => resize to that
                # - else scale factor
                if self.size:
                    frame = frame.resize(self.size, Image.LANCZOS)
                elif scale != 1:
                    frame = frame.resize(
                        (int(frame.size[0] * scale), int(frame.size[1] * scale)),
                        Image.NEAREST
                    )

                frames.append(ImageTk.PhotoImage(frame))

        self.frames = frames
        self.index = 0
        self.running = False

        # Keep a reference to prevent GC
        
        if self.frames:
            if bSpecialBG:
                self.hero_bg_id = self.canvas.create_image(s(104), 0, image = self.hero_bg_colored, anchor="ne")
            self.image_id = self.canvas.create_image(cx + s(dx), cy + s(dy),
                                         image=self.frames[0], anchor="center")
            
            

    def _tick(self):
        if not self.running or not self.frames:
            return
        
        
        
        self.canvas.itemconfigure(self.image_id, image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.master.after(self.delay_ms, self._tick)

    def play(self):
        if not self.running:
            self.running = True
            self._tick()

    def pause(self):
        self.running = False

    def createOnlyImage1(self,player_img, size=None):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False
        sheet = img_raw.copy()
        return sheet, sheet.size
        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            resized = resized.resize(s(size), Image.LANCZOS)

            img_raw = ImageTk.PhotoImage(resized)
        si = img_raw.size 
        return img_raw, si
    def createOnlyImage(self,player_img, size):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False

        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            resized = resized.resize(s(size), Image.LANCZOS)

        img = ImageTk.PhotoImage(resized)
        return img

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
                    "Wolverine":(0,-32)
                    }

HERO_SKINS_KEY = {"Adam Warlock":7,
                  "Angela":4,
                  "Black Panther":6,
                  "Black Widow":7,
                  "Blade":6,
                  "Bruce Banner":4,
                  "Captain America":7,
                  "Cloak & Dagger":5,
                    "Daredevil":4,
                    "Deadpool":3,
                    "Doctor Strange":6,
                    "Emma Frost":6,
                    "Gambit":3,
                    "Groot":6,
                    "Hawkeye":6,
                    "Hela":8,
                    "Human Torch":7,
                  "Invisible Woman":14,
                  "Iron Fist":6,
                  "Iron Man":6,
                  "Jeff The Land Shark":9,
                  "Loki":8,
                  "Luna Snow":8,
                    "Magik":8,
                    "Magneto":7,
                    "Mantis":7,
                    "Mister Fantastic":7,
                    "Moon Knight":6,
                    "Namor":8,
                    "Peni Parker":7,
                    "Phoenix":5,
                    "Psylocke":11,
                  "Rocket Raccoon":8,
                  "Rogue": 3,
                  "Scarlet Witch":11,
                  "Spider-Man":11,
                  "Squirrel Girl":5,
                    "Star-Lord":7,
                    "Storm":5,
                    "The Punisher":9,
                    "The Thing":9,
                    "Thor":8,
                    "Ultron":5,
                    "Venom":11,
                    "Winter Soldier":7,
                    "Wolverine":7}

SPECIAL_IMAGE_MAP = None
root = tk.Tk()
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

BASE_W, BASE_H = 2440, 1440  # whatever resolution you originally designed for
scale_x = screen_w / BASE_W
scale_y = screen_h / BASE_H
SCALE = min(scale_x, scale_y)  # preserve aspect ratio
root.destroy()
TARGET_DPI_SCALE = (SCALE * 96) / 72 

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

def list_fonts():

    families = sorted(set(tkFont.families(root)))
    weights = ["normal", "bold"]
    slants = ["roman", "italic"]

    for fam in families:
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
              'SairaCondensed-Medium.ttf','SairaCondensed-Bold.ttf','SairaCondensed-Regular.ttf','SairaCondensed-SemiBold.ttf','SairaCondensed-Thin.ttf',
              "Saira Thin Medium.ttf",'SairaExtraCondensed-Medium.ttf','SairaExtraCondensed-Bold.ttf','SairaExtraCondensed-Regular.ttf','SairaExtraCondensed-SemiBold.ttf','SairaExtraCondensed-Thin.ttf',
              'Saira_SemiCondensed-Medium.ttf','Saira_SemiCondensed-Black.ttf', 'Saira_SemiCondensed-Bold.ttf','Saira_SemiCondensed-ExtraBold.ttf','Saira_SemiCondensed-Medium.ttf','Saira_SemiCondensed-Regular.ttf', 'Saira_SemiCondensed-SemiBold.ttf','Saira_SemiCondensed-Thin.ttf',
              'Saira-Black.ttf','Saira-Bold.ttf','Saira-ExtraBold.ttf','Saira-Light.ttf','Saira-Medium.ttf','Saira-Regular.ttf','Saira-SemiBold.ttf','Saira-Thin.ttf',
              "Refrigerator-Deluxe-Bold.ttf","Refrigerator-Deluxe-Heavy.ttf", 'Refrigerator-Deluxe-Extrabold.ttf', 'Refrigerator-Deluxe.ttf','Refrigerator-Deluxe-Light.ttf',
              'KelsonSans.ttf','KelsonSansBold.ttf',
              "Exo Demi Bold.ttf","Exo Light.ttf",
              "CarbonRegular.ttf","CarbonBold Italic.ttf","CarbonRegular Italic.ttf",
              "Cairo Black.ttf","Cairo Bold.ttf",
              'TT_Supermolot_Neue_Bold.ttf','TT_Supermolot_Neue_Bold_Italic.ttf',
              'TT_Supermolot_Neue_DemiBold_Italic.ttf','TT_Supermolot_Neue_DemiBold.ttf',
              'TT_Supermolot_Neue_Medium.ttf','TT_Supermolot_Neue_Medium_Italic.ttf',
              'TT_Supermolot_Neue_Condensed_ExtraBold.ttf',
              'Neue_Condensed_Bold.ttf', 'S.ttf',
              'TT_Supermolot_Neue_Italic.ttf', 'TT_Supermolot_Neue_Regular.ttf']
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





    
from ocr_capture import capture_names as CAPTURE
from tracker_lookup import open_multiple_tracker_profiles
import json
import os

#t= time.perf_counter()
from player2 import Player2
from playerNEW import Player
#print("player2 import:", time.perf_counter() - t)

import helpers

#t = time.perf_counter()
import random
#print("random import:", time.perf_counter() - t)

#t = time.perf_counter()
from collections import Counter
#print("collections import:", time.perf_counter() - t)

import re
def on_f8_pressed(r):
    
    print(">> Script running. Press F8 to OCR names and check tracker.gg...")
    
    

    if config.debug_mode:
        #all_data = local_all_data
        trackerdata = helpers.create_path("_2TrackerGGJSON.json", 'debug')
        tracker_data = helpers.load_json(trackerdata)
        names = list(tracker_data.keys())
        print(">> Loaded names from debug JSON.")
        #names = ['ukenichi', 'TexasMiler','kalluto', 'Roundest Boi', 'ltzvenuss']
        if not config.randomize_ban:
            #print("First 6")
            if not config.mobile_mode:
                names = CAPTURE(flag_debug=True)

        else:
            print("Random 6")
            #all_keys = list(local_all_data.keys())
            #names = random.sample(all_keys, min(6, len(all_keys)))
        
    else:
        print(">> Capturing names via OCR...")
        names = CAPTURE()

    print("\n🎯 Captured Player Names:")
    for name in names:
        print(f"- {name}")
    import time
    #print("\n🔎 Tracker.gg Profile URLs:")
    players = []
    
    
    
    if not config.debug_mode:
        tracker_data = open_multiple_tracker_profiles(names)
    
    #save_json("_1MarvelRivalsApiJSON.json",all_data)
        save_json("_2TrackerGGJSON.json",tracker_data)
        #all_data = open_multiple_tracker_profiles(names)
        #print(all_data)
    #else:
        #tracker_data = open_multiple_tracker_profiles(names)
        #save_json("_2TrackerGGJSON.json",tracker_data)
        #tracker_data = helpers.load_json(helpers.create_path("_2TrackerGGJSON.json", 'debug'))
   
    
    if tracker_data:
        
        for name in tracker_data:
            data = tracker_data[name]
            if data is False:
                print(f"Skipping {name}: No Data Found")
                continue
            if not data:
                print(f"Skipping {name}: No Data Found")
                continue
            if "errors" in data:
                print(f"Skipping {name}: Private Account")
                continue
            if len(data["data"]["segments"]) < 3:
                print(f"Skipping {name}, no current season data found.")
                continue
            p = Player2(name, data)
            players.append(p)
            #ban_scoring[name] = p.result
        #b = helpers.create_path("_1Best_Bans_Heros.json", 'debug')
        #helpers.save_json(b, ban_scoring)

    if players:
        show_gui(players,r)

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
        
def create_player_frame(root, player):
    imggg = None
    
    bAnimatedLord = False
    if player.hero1 not in CACHED_IMGS:
        if "Deadpool" not in player.hero1:

            player.hero1 = "Question"
    if player.hero2 not in CACHED_IMGS:
        if "Deadpool" not in player.hero2:
            player.hero2 = "Question"
        variable_colors = {
        "Matches": { "9999": "#D5D9E4"},
        "Win %": { "30": "#bf868f",
                     '45': "#d6c73e",
                     '60': "#5de791",
                     '200': "#3ecbff" },
        "KDA Ratio": { "1": "#bf868f",
                 "3": "#d6c73e",
                 "5": "#5de791",
                 '2222': "#3ecbff"},
        "KD Ratio": { "1": "#bf868f",
                "2": "#d6c73e",
                "4": "#5de791",
                '200': "#3ecbff"},
        "MVP %": { "5": "#bf868f",
                     "10": "#d6c73e",
                     "35": "#5de791",
                     '200': "#3ecbff" },
        "Final Hits": { "4": "#bf868f",
                     "8": "#d6c73e",
                     "12": "#5de791",
                     '200': "#3ecbff" },
        "Damage/Min": { "800": "#bf868f",
                     "1300": "#d6c73e",
                     "1600": "#5de791",
                     '4000': "#3ecbff" },
        "Healing/Min": { "800": "#bf868f",
                     "1300": "#d6c73e",
                     "1600": "#5de791",
                     '4000': "#3ecbff" }
                    }
    
    variable_colors_background = {
        "Matches": { "9999": "#2B2B2B"},
        "Win %": { "30": "#b34454",
                     '45': "#cf9f00",
                     '60': "#23ad58",
                     '200': "#10b0eb" },
        "KDA Ratio": { "1": "#b34454",
                 "3": "#cf9f00",
                 "5": "#23ad58",
                 '2222': "#10b0eb"},
        "KD Ratio": { "1": "#b34454",
                "2": "#cf9f00",
                "4": "#23ad58",
                '200': "#10b0eb"},
        "MVP %": { "5": "#b34454",
                     "10": "#cf9f00",
                     "35": "#23ad58",
                     '200': "#10b0eb" },
        "MVPs": { "5": "#b34454",
                     "10": "#cf9f00",
                     "35": "#23ad58",
                     '200': "#10b0eb" },
        "Final Hits": { "4": "#b34454",
                     "8": "#cf9f00",
                     "12": "#23ad58",
                     '200': "#10b0eb" },
        "Damage/Min": { "800": "#b34454",
                     "1300": "#cf9f00",
                     "1600": "#23ad58",
                     '4000': "#10b0eb" },
        "Damage": { "800": "#b34454",
                     "1300": "#cf9f00",
                     "1600": "#23ad58",
                     '4000': "#10b0eb" },
        "Healing/Min": { "800": "#b34454",
                     "1300": "#cf9f00",
                     "1600": "#23ad58",
                     '4000': "#3ecbff" },
        "Heals": { "800": "#b34454",
                     "1300": "#cf9f00",
                     "1600": "#23ad58",
                     '4000': "#3ecbff" }}
        


                     
    
        
    def createImage(frame, player_img, size, bg, arh, param):
        img_raw = image_loader(player_img)
        if img_raw:
            #resized = img_raw.copy()
            resized = img_raw.resize(s(size), Image.LANCZOS)
            #resized.thumbnail(size)  # Resize to 32x32
            img = ImageTk.PhotoImage(resized)
            label = tk.Label(frame,bg=bg, image=img, **arh)
            label.image = img  # Prevent garbage collection
            label.pack(**param)
            return label
        else:
            return False
        

    def createCanvasImage(canvas, img_key,anc='nw', size=None,bg=None, arh=None,x=-23,y=-15, mask=False):
        """
        Draw a single background image on the given canvas,
        resized to `size`, anchored at top-left.
        """
        global NAMEPLATES
        if arh is None:
            arh = {}
        
            
        img_raw = image_loader(img_key)
        if not img_raw:
            return False
        
        if mask:
            img_raw = img_raw.convert("RGBA")
            img_raw = make_circle(img_raw)

        # Resize image to desired size
        resized = img_raw.resize(s(size), Image.LANCZOS)
        

        img = ImageTk.PhotoImage(resized)

        # Optional: set canvas background
        canvas.configure(bg=bg)
        
        # Draw at top-left corner
        canvas.create_image(s(x), s(y), anchor=anc,image=img, **arh)

        # Keep reference – use a list so you can add more later if needed
        if not hasattr(canvas, "_images"):
            canvas._images = []
        canvas._images.append(img)

        return canvas
    def handleDeadpool(hero_name):
        if "Deadpool" in hero_name:
            return "Deadpool"
        return hero_name
            
    def createOnlyImage(player_img, size):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False

        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            resized = resized.resize(s(size), Image.LANCZOS)

        img = ImageTk.PhotoImage(resized)
        return img
        # Outer container (already in your code)
    # Outer container
    add = 0
    if int(SCALE) != 1:
        add = 12
    NAME_BANNER = "#24212B"

    # MAIN OUTER FRAME              580 + add
    outer = tk.Frame(root, width=s(330), height=(s(1030)+add), bg=NAME_BANNER, borderwidth=1, relief='flat')
    outer.pack(side="left", fill="both")
    outer.pack_propagate(False)  # Prevent auto-resizing
    # ---------------------------
    # 1. Name Bar (with MVP + peak rank)
    # ---------------------------

    while True:
        num = random.randint(1, 161)
        nameplate = f"1 ({num})"
        if nameplate not in NAMEPLATES:
            NAMEPLATES.append(nameplate)
            break
    # Name Bar                ---- 60 + 44 + 125 = 229
    name_bar = tk.Frame(outer, bg=NAME_BANNER, height=s(60), relief='raised', borderwidth=3)
    name_bar.pack(side='top', fill="x",padx=(1,0))

    name_bar.pack_propagate(False)    
    

    canvas = tk.Canvas(name_bar, highlightthickness=0)
    canvas.pack(anchor="center", fill="both")

    # Assume your banner art is "grad" in image_map, and the desired size is 330x60
    createCanvasImage(
        canvas,
        img_key=nameplate,      # or "grad.png", depending on your keys
        size=(402, 91),
        bg=NAME_BANNER,
        
        x= -23,
        y= -15
)
    canvas.create_text(s(6),s(44), text=player.name, fill="white", font=fonttk(refrig_heavy, 23, 'bold'), anchor="sw")

    overfg = "#D0CFE2"
    # ---------------------------
    # Overview Bar (dark background)  -----------     44 + 125
    # ---------------------------
    overview_bar = tk.Frame(outer, bg="#171B20", width=s(330), height=s(44), relief='raised', borderwidth=2)
    overview_bar.pack(side='top', pady=(4,0), fill="both")
    overview_bar.pack_propagate(False)  # Prevent auto-resizing
    overview_stats = tk.Frame(outer, bg="#171B20", width=s(330), height=s(125),relief='groove', borderwidth=2)
    overview_stats.pack(side='top', fill="both")
    overview_stats.pack_propagate(False)  # Prevent auto-resizing

    t_canvas = tk.Canvas(overview_bar, height=s(42), highlightthickness=0)
    t_canvas.pack(anchor="center", fill="x")
    createCanvasImage(
        t_canvas,
        img_key="overviewbg", 
        anc='ne',     # or "grad.png", depending on your keys
        size=(530, 59),
        bg="#1C2127",
        
        x=486,
        y=0
)
    ranking = player.ranking
    if player.ranking == 1:
        imggg = "MVP2"
        sizex = 58
        sizey = 24
    elif player.ranking == 2:
        imggg = "SVP"
        sizex = 48
        sizey = 23
    if ranking <= 3:
        imgggg = str(ranking) + "_banner"
        createCanvasImage(
            t_canvas,
            img_key=imgggg, 
            anc='ne',     # or "grad.png", depending on your keys
            size=(166, 42),
            bg="#1C2127",
            
            x= 120,
            y= 0
        )
        
    if player.ranking <=3:
        
        overfg = "#252438"
    else:
        overfg = "#ECEBFF"
    oss = round(player.overall_score,3)
    t_canvas.create_text(s(12),s(6), text="Overview", fill=overfg, font=fonttk("Refrigerator Deluxe ExtraBold", 19, "normal"), anchor="nw")
    t_canvas.create_text(s(220),s(6), text=oss, fill="#EBEAFF", font=fonttk("Refrigerator Deluxe ExtraBold", 19, "normal"), anchor="nw")
    createCanvasImage(
        t_canvas,
        img_key=player.rank,
        anc='c',      # or "grad.png", depending on your keys
        size=(46, 46),
        bg="#1C2127",
        
        x=303,
        y=20
)
    
#     createCanvasImage(
#         t_canvas,
#         img_key=player._roleName,      # or "grad.png", depending on your keys
#         size=(32, 32),
#         bg=NAME_BANNER,
#         
#         x = 282,
#         y=2
# )
    
    ov_canvas = tk.Canvas(overview_stats, height=s(125), width=s(330), highlightthickness=0)
    ov_canvas.pack(anchor="center", fill="both")

    createCanvasImage(
        ov_canvas,
        img_key="ov",
              anc='c',      # or "grad.png", depending on your keys
        size=(398, 125),
        bg="#171B20",
        
        x=165,
        y=62
)
    if imggg:
        createCanvasImage(
            t_canvas,
            img_key=imggg,      # or "grad.png", depending on your keys
            size=(sizex, sizey),
            bg="#1C2127",
            
            x= 125,
            y= 8
    )
    

    def getSpecialBGColors(label):
        if label in ["Matches"]:
            return "#B3BBE0"
        elif label in ['Win %', 'MVP %']:
            return "#C4CAEA"
        elif label in ['KDA Ratio']:
            return  '#CFD6E9'
        else:
            return '#D9DFED'

    def getForegroundColor(label, value, flag=None):
        try:
            if '%' in label:
                value = value.strip('%')
            value = float(value)

            for item in variable_colors_background:
                if item == label:
                    thr = variable_colors_background[item]
                    for keys in thr:
                        compare = float(keys)
                        if value <= compare:
                            return thr[keys] if not flag else variable_colors_background[item][keys]
                        
            return '#D5D9E4' if not flag else "#292929"
        except Exception as e:
            return '#D5D9E4' if not flag else '#171B20'
    
    def getPadxValue(label, value):
        if label in ["Matches", 'Win Pct', 'MVP Pct']:
            return 6
        else:
            return 12
        
                    
    
    # ---------------------------
    # Stats split into 2 columns
    # ---------------------------
    

    stats = [
        ("Matches", player._matches_played),
        ("Win %", player._matches_won_pct),
        ("MVP %", player._mvpPct),
        ("KD Ratio", player._kd),
        ("KDA Ratio", player._kda)
        
    ]
    x = 8
    x2 = 110
    y = 2
    # place in 2-column grid
    for i, (label, value) in enumerate(stats):
        ov_canvas.create_text(s(x),s(y), text=label, fill="#2B2B2B", font=fonttk("Rajdhani", 14, 'normal'), anchor="nw")
        fgg = getForegroundColor(label, value, True)
        
        ov_canvas.create_text(s(x2),s(y), text=value, fill=fgg, font=fonttk("Rajdhani Bold", 14, 'normal'), anchor="nw")
        y += 24

    gray_role = player._roleName + "_G"
    createCanvasImage(
        ov_canvas,
        img_key=gray_role,      # or "grad.png", depending on your keys
        size=(26, 26),
        bg=NAME_BANNER,
        
        x = 190,
        y=1
)
    usage = str(player._roleUsagePct) + " %"
    fgg  = getForegroundColor("Win %", usage, True)
    ov_canvas.create_text(s(230),s(6), text=player._roleName, fill="#2B2B2B", font=fonttk("Rajdhani", 12, 'normal'), anchor="nw")
    ov_canvas.create_text(s(250),s(36), text=usage, fill=fgg, font=fonttk("Rajdhani SemiBold", 12, 'normal'), anchor="nw")
    ov_canvas.create_text(s(200),s(36), text='Usage', fill="#2B2B2B", font=fonttk("Rajdhani", 12, 'normal'), anchor="nw")
    if player._role2Name:
        gray_role = player._role2Name + "_G"
        createCanvasImage(
            ov_canvas,
            img_key=gray_role,      # or "grad.png", depending on your keys
            size=(26, 26),
            bg=NAME_BANNER,
            
            x = 190,
            y=60
    )
        usage = str(player._role2UsagePct) + " %"
        fgg  = getForegroundColor("Win %", usage, True)
        ov_canvas.create_text(s(230),s(65), text=player._role2Name, fill="#2B2B2B", font=fonttk("Rajdhani", 12, 'normal'), anchor="nw")
        ov_canvas.create_text(s(250),s(94), text=usage, fill=fgg, font=fonttk("Rajdhani SemiBold", 12, 'normal'), anchor="nw")
        ov_canvas.create_text(s(200),s(94), text='Usage', fill="#2B2B2B", font=fonttk("Rajdhani", 12, 'normal'), anchor="nw")


    heroes_bar = tk.Frame(outer, bg="#4A5172", width=s(330), height=s(45), relief='raised', borderwidth=2)
    heroes_bar.pack(side='top', fill="both")
    heroes_bar.pack_propagate(False)  # Prevent auto-resizing
    heroes_bar_canvas = tk.Canvas(heroes_bar, height=s(45), highlightthickness=0)
    heroes_bar_canvas.pack(anchor="center", fill="x")
    createCanvasImage(
        heroes_bar_canvas,
        img_key="hero_banner2",
        anc='sw',
        size=(330, 71),
        bg="#4A5172",
             
        
        x=0,
        y=50
              )
    heroes_bar_canvas.create_text(s(15),s(8), text="Best Heroes", fill="#D9D5E9", font=fonttk("Refrigerator Deluxe ExtraBold", 18, "normal"), anchor="nw")
    if player.bPrivate:
        heroes_bar_canvas.create_text(s(185),s(8), text="Private Account", fill="#FFE702", font=fonttk("Refrigerator Deluxe ExtraBold", 18, "normal"), anchor="nw")
              # or "grad.png", depending on your keys
    
    heroes_frame = tk.Frame(outer, bg=NAME_BANNER, width=s(330), height=s(358), relief='flat', borderwidth=0)   
    heroes_frame.pack(side='top', fill="both")
    heroes_frame.pack_propagate(False)  # Prevent auto-resizing

    img = createOnlyImage("herobg3", (330, 358))
    img_bg = tk.Label(heroes_frame, image=img, bg=NAME_BANNER)
    img_bg.image = img  # Prevent garbage collection
    img_bg.place(x=0, y=0, relwidth=1, relheight=1)

    x = 0
    y = 2
    text_x = 0
    text_y = 0
    heros = 0
    
    if player.hero1 != "Null":
        heros += 1
    if player.hero2 != "Null":
        heros += 1
    if player.hero3 != "Null":
        heros += 1
    char_scores = [
        getattr(player, "score_hero1"),
        getattr(player, "score_hero2"),
        getattr(player, "score_hero3"),
    ]

    order = [
        i for i, score in
        sorted(
            ((i + 1, score) for i, score in enumerate(char_scores) if score is not None),
            key=lambda x: x[1],
            reverse=True
        )
    ]
    coun = 0
    for i in order:
        coun += 1
        if coun == 1:
            scfg = "#e2b52d"
        elif coun == 2:
            scfg = "#7f9ccf"
        else:
            scfg = "#d39a74"
        xxx = 5
        yyy = 2
        if i == 0:
            continue
        idx = ''
        if i == 3:
            idx = 2
        role = getattr(player, f"_role{idx}Name")
        hero = getattr(player, f"hero{i}")

        #Deapool fix
        #hero = handleDeadpool(hero)

        matches = getattr(player, f"matches_played{i}")
        winpct = getattr(player, f"win_pct{i}")
        string = getattr(player, f"string{i}")
        mvp = getattr(player, f"mvp{i}")
        dpm = getattr(player, f"dpm{i}")
        kdstring = getattr(player, f"kdstring{i}")
        kd = getattr(player, f"kd{i}")
        score = char_scores[i-1]
        score = round(score,3)

        #hero_canvas = tk.Canvas(heroes_canvas, width=s(323), height=s(113), relief='raised', borderwidth=3)
        stats = [
            ("Matches", int(matches)),
            (string, dpm),
            (kdstring, kd),
            
            ("MVP %", mvp),
            ("Win %", winpct)
            
            ]
        lord = "_l"

        global bTest
        bLord = False
        ran = random.randint(1,1000)
        if ran > 100 and ran <= 300:
            hero_icon = hero + lord
        elif "Deadpool" in hero:
            print("Deadpool detected, using base icon.")
            hero_icon = hero
        elif ran <= 100:
            bLord = True
            skin_count = HERO_SKINS_KEY[hero]
            ran = random.randint(1,skin_count)
            hero_icon = f"{hero} ({ran})"
        else:
            hero_icon = hero
        
        if not image_loader(hero_icon):
            hero_icon = hero
            if not image_loader(hero_icon):
                print(f'Image not found for {hero_icon}, setting to Unknown')
                hero_icon = 'Unknown'
        
        hero_bar = tk.Frame(heroes_frame, bg="#77789E", width=s(328), height=s(110), relief='raised', borderwidth=2)
        hero_bar.pack(side='top', pady=(2,2), fill="x")
        hero_bar.pack_propagate(False)  # Prevent auto-resizing
        # hero_icon_frame = tk.Frame(hero_bar, bg="#2E2F41", width=s(105), height=s(105), relief='flat', borderwidth=0)
        # hero_icon_frame.pack(side='left', padx=(0,0), pady=(0,0))
        # hero_icon_frame.pack_propagate(False)  # Prevent auto-resizing
        try:
            if bLord:
                ran = random.randint(1,100)
                if ran <= 50:
                    bAnimatedLord = True
            if bTest:
                bAnimatedLord = True
            if bAnimatedLord:
                
                    
                    sheee = hero + "_Master"
                    anim = SpriteSheetAnimator(
                    master=hero_bar,
                    hero=hero,
                    sheet_path=sheee,   # <- now this should point to sprite sheet png
                    rows=10,
                    cols=6,
                    fps=24,
                    #size=s((104, 104)),     # uses your scaling func
                    bg="#77789E",
                    relief="sunken",
                    borderwidth=1
                )
                    #anim.canvas.pack(side='left', padx=(0,0), pady=(0,0))
                    anim.play()

                    # IMPORTANT: store reference somewhere that lives as long as the GUI
                    hero_bar.hero_anim = anim
                    
                    bTest += 1
                
            else:
                hero_img = createOnlyImage(hero_icon, (104, 104))
                hero_icon_label = tk.Label(hero_bar, image=hero_img, bg="#77789E",relief='sunken', borderwidth=2)
                hero_icon_label.image = hero_img  # Prevent garbage collection
                hero_icon_label.pack(side='left', padx=(0,0), pady=(0,0))
        except Exception as e:
            print("Error loading animated lord for", hero, e)
            hero_img = createOnlyImage("Unknown", (104, 104))
            hero_icon_label = tk.Label(hero_bar, image=hero_img, bg="#77789E",relief='sunken', borderwidth=2)
            hero_icon_label.image = hero_img  # Prevent garbage collection
            hero_icon_label.pack(side='left', padx=(0,0), pady=(0,0))

        hero_stats = tk.Canvas(hero_bar, height=s(106), width=s(220), highlightthickness=0, bg="#77789E")
        hero_stats.pack(side='left', padx=(0,0), pady=(0,0), fill="both")
        createCanvasImage(
            hero_stats,
            img_key="hero_stat_bg",
                anc='ne',
            size=(336, 106),
            bg=NAME_BANNER,
            
            x=220,
            y=0
                )
        role = role + "_G"
        createCanvasImage(
            hero_stats,
            img_key=role,
            size=(30, 30),
            
            x=150,
            y=24)
        char = min(len(hero), 7)
        
        #char = max(char, 4, 10)   
        coord = (100 - (char * 12)) + 100 
        if len(hero) >= 13:
            ssize = 11
        else:
            ssize = 14
        hero_stats.create_text(s(167),s(10), text=hero, fill="#2B2B2B", font=fonttk("Refrigerator Deluxe ExtraBold", ssize, 'normal'), anchor="c")
        hero_stats.create_text(s(164),s(94), text=score, fill="#2B2B2B", font=fonttk("Refrigerator Deluxe ExtraBold", 13, 'normal'), anchor="c")
        if hero == player.best_hero:
            createCanvasImage(
                hero_stats,
                img_key="MVP2",      # or "grad.png", depending on your keys
                size=(49, 21),
                bg="#1C2127",
                
                x= 138,
                y= 60
        )
        for i, (label, value) in enumerate(stats):
                
            fg_color = getForegroundColor(label, value)
            if fg_color == "#2B2B2B":
                fg_color = "#2B2B2B"
            hero_stats.create_text(s(xxx),s(yyy), text=label, fill="#2B2B2B", font=fonttk("Rajdhani", 12, 'normal'), anchor="nw")
            hero_stats.create_text(s(xxx+80),s(yyy), text=value, fill=fg_color, font=fonttk("Rajdhani", 12, 'bold'), anchor="nw")
            yyy += 21


        # Match History # Match History # Match History # Match History # Match History # Match History 
        # Match History # Match History # Match History # Match History # Match History # Match History 
        # Match History # Match History # Match History # Match History # Match History # Match History # Match History 
        # Match History v# Match History 

    matches = player.match_history
    

    if not isinstance(matches, list) or len(matches) == 0:
        matches = []
    history_frame = tk.Frame(outer, bg=NAME_BANNER, width=s(330), height=(s(84)*len(matches)), relief='flat', borderwidth=0)   
    history_frame.pack(side='top', fill="both",pady=(10,0))
    history_frame.pack_propagate(False)  # Prevent auto-resizing

    # historybg = createOnlyImage("historybg", size=(1720, 800), img_map=ui_img_map)
    # history_label = tk.Label(history_frame, image=historybg, bg="#77789E",relief='flat', borderwidth=0)
    # history_label.image = historybg  # Prevent garbage collection
    # history_label.place(x=0, y=0, relwidth=1, relheight=1)
    amt = 0
    for match in matches:
        if amt >7:
            break
        amt += 1
        winner_id = match["metadata"]["winningTeamId"]
        scores = match["metadata"]["scores"]
        metadata = match["segments"][0]["metadata"]
        stats = match["segments"][0]["stats"]
        result = metadata['result']
        mvp_str = metadata['isMvp']
        
        svp_str = metadata['isSvp']
        heroes = metadata['heroes']
        kills = stats['kills']['value']
        deaths = stats['deaths']['value']
        assists = stats['assists']['value']
        #damage = round(stats['totalHeroDamage']['value'])
        
        if mvp_str:
            mvp_string = "MVP2"
            saa = 48
        elif svp_str:
            mvp_string = "SVP"
            saa = 42
        else:
            mvp_string = None

        if result == "win":
            player_teamid = winner_id
            bg = "#26393C"
            outline = "#5DE48E"
            pic = "winbg"
        else:
            player_teamid = 1 if winner_id == 0 else 0
            bg = "#40272D"
            outline = "#DD475C"
            pic = "losebg"

        match_frame = tk.Frame(history_frame, bg=outline, width=s(326), height=s(42), relief='raised', borderwidth=1)
        match_frame.pack(side='top',anchor='c', pady=(4,4), padx=(4,4), fill="both")
        match_frame.pack_propagate(False)  # Prevent auto-resizing
        match_canvas = tk.Canvas(match_frame, height=s(42), width=s(326), highlightthickness=0, bg=bg)
        match_canvas.pack(anchor="center", fill="both")
        match_canvas.pack_propagate(False)  # Prevent auto-resizing
        createCanvasImage(
            match_canvas,
            img_key=pic,
            anc='nw', 
            size=(326, 77),
            bg=bg,
            
            x=0,
            y=0
                )
        if mvp_string:
            createCanvasImage(
                match_canvas,
                img_key=mvp_string,
                anc='center',
                size=(saa, 20),
                bg=bg,
                
                x=28,
                y=22)
        one = (36, 36)
        plus = 36
        x = 75
        y = 21
        match_canvas.create_text(s(70),s(10), text="Score", fill="#71C0EE", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="c")

        match_canvas.create_text(s(69),s(30), text=f"{scores[0]}:{scores[1]}", fill="#D5D9E4", font=fonttk("Rajdhani Bold", 12, 'normal'), anchor="c")
        x+=45
        count = 0
        for hero in heroes:
            if count > 2:
                break
            count += 1
            hero_name = hero['name']
            #hero_name = handleDeadpool(hero_name)
            createCanvasImage(
                match_canvas,
                img_key=hero_name,
                anc='center',
                size=one,
                
                x=x,
                y=y,mask=True)
            x += plus
            one = (24, 24)
            plus = 30
        if len(heroes) < 1:
            hero_name = "Unknown"
            createCanvasImage(
                match_canvas,
                img_key=hero_name,
                anc='center',
                size=one,
                
                x=x,
                y=y,mask=True)
        icons = {'match_kill': kills, 'match_death': deaths, 'match_assist': assists}
        x = 205
        for icon , value in icons.items():
            createCanvasImage(
                match_canvas,
                img_key=icon,
                anc='nw',
                size=(22, 22),
                
                x=x,
                y=0)
            
            match_canvas.create_text(s(x+9),s(30), text=value, fill="#D5D9E4", font=fonttk("Rajdhani Bold", 12, 'normal'), anchor="c")
            
            x += 40
        
        def new():
            for match in matches:
                if amt >4:
                    break
                amt += 1
                winner_id = match["metadata"]["winningTeamId"]
                scores = match["metadata"]["scores"]
                metadata = match["segments"][0]["metadata"]
                stats = match["segments"][0]["stats"]
                result = metadata['result']
                mvp_str = metadata['isMvp']
                
                svp_str = metadata['isSvp']
                heroes = metadata['heroes']
                kills = stats['kills']['value']
                deaths = stats['deaths']['value']
                assists = stats['assists']['value']
                #damage = round(stats['totalHeroDamage']['value'])
                
                if mvp_str:
                    mvp_string = "MVP2"
                    saa = 48
                elif svp_str:
                    mvp_string = "SVP"
                    saa = 42
                else:
                    mvp_string = None

                if result == "win":
                    player_teamid = winner_id
                    bg = "#26393C"
                    outline = "#5DE48E"
                    pic = "winbg"
                    pic = "winbg5_dark"
                    size = (326, 77)
                    size = (328, 43)
                elif result == "loss":
                    player_teamid = 1 if winner_id == 0 else 0
                    bg = "#40272D"
                    outline = "#DD475C"
                    pic = "losebg"
                    pic = "lossbg5_dark"
                    size = (326, 77)
                    size = (343, 44)
                elif result == "tie":
                    player_teamid = winner_id
                    bg = "#3C3C3C"
                    outline = "#AAAAAA"
                    pic = "tiebg"
                    pic = "tiebg5_dark"
                    size = (326, 77)
                    size = (343, 44)

                #match_frame = tk.Frame(history_frame, bg=outline, width=s(326), height=s(45), relief='raised', borderwidth=2)
                #match_frame.pack(side='top',anchor='c', pady=(5,5), padx=(4,4), fill="both")
                bg =NAME_BANNER
                match_frame = tk.Frame(history_frame, bg=NAME_BANNER, width=s(326), height=s(44), relief='flat', borderwidth=0)
                match_frame.pack(side='top',anchor='c', pady=(2,2), padx=(0,0), fill="both")
                match_frame.pack_propagate(False)  # Prevent auto-resizing
                #match_canvas = tk.Canvas(match_frame, height=s(45), width=s(326), highlightthickness=0, bg='#24212B')
                #match_canvas.pack(anchor="center", fill="both")
                match_canvas = tk.Canvas(match_frame, height=s(45), width=s(326), highlightthickness=0, bg='#24212B')
                match_canvas.pack(anchor="center", fill="both")
                match_canvas.pack_propagate(False)  # Prevent auto-resizing
                createCanvasImage(
                    match_canvas,
                    img_key=pic,
                    anc='nw', 
                    size=size,
                    bg=bg,
                    
                    x=0,
                    y=0
                        )
                if mvp_string:
                    createCanvasImage(
                        match_canvas,
                        img_key=mvp_string,
                        anc='center',
                        size=(saa, 20),
                        bg=bg,
                        
                        x=28,
                        y=22)
                one = (36, 36)
                plus = 36
                x = 75
                y = 21
                match_canvas.create_text(s(70),s(10), text="Score", fill="#71C0EE", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="c")

                match_canvas.create_text(s(69),s(30), text=f"{scores[0]}:{scores[1]}", fill="#D5D9E4", font=fonttk("Rajdhani Bold", 12, 'normal'), anchor="c")
                x+=45
                count = 0
                if len(heroes) < 1:
                    hero_name = "Unknown"
                    createCanvasImage(
                        match_canvas,
                        img_key=hero_name,
                        anc='center',
                        size=one,
                        
                        x=x,
                        y=y,mask=True)
                else:
                    for hero in heroes:
                        if count > 2:
                            break
                        count += 1
                        hero_name = hero['name']
                        createCanvasImage(
                            match_canvas,
                            img_key=hero_name,
                            anc='center',
                            size=one,
                            
                            x=x,
                            y=y,mask=True)
                        x += plus
                        one = (24, 24)
                        plus = 30
                

                icons = {'match_kill': kills, 'match_death': deaths, 'match_assist': assists}
                x = 205
                for icon , value in icons.items():
                    createCanvasImage(
                        match_canvas,
                        img_key=icon,
                        anc='nw',
                        size=(22, 22),
                        
                        x=x,
                        y=0)
                    
                    match_canvas.create_text(s(x+9),s(30), text=value, fill="#D5D9E4", font=fonttk("Rajdhani Bold", 12, 'normal'), anchor="c")
                    
                    x += 40





        




        heroes = match["segments"][0]["metadata"]['heroes']















        
    def evenolder():
        #OOOOLDD
        heroes_canvas = tk.Canvas(heroes_frame, height=s(358), width=s(330), highlightthickness=0)
        heroes_canvas.pack(anchor="center", fill="both")
        

        createCanvasImage(
            heroes_canvas,
            img_key="herobg3",
            size=(330, 358),
            bg=NAME_BANNER,
            
            x=0,
            y=0
                )
        
        
        x = 0
        y = 2
        text_x = 0
        text_y = 0
        heros = 0
        xxx = 115
        yyy = 2
        if player.hero1 != "Null":
            heros += 1
        if player.hero2 != "Null":
            heros += 1
        if player.hero3 != "Null":
            heros += 1
        for i in range(1,heros+1):
            if i == 0:
                continue
            idx = ''
            if i == 3:
                idx = 2
            role = getattr(player, f"_role{idx}Name")
            hero = getattr(player, f"hero{i}")
            matches = getattr(player, f"matches_played{i}")
            winpct = getattr(player, f"win_pct{i}")
            string = getattr(player, f"string{i}")
            mvp = getattr(player, f"mvp{i}")
            dpm = getattr(player, f"dpm{i}")
            kdstring = getattr(player, f"kdstring{i}")
            kd = getattr(player, f"kd{i}")

            #hero_canvas = tk.Canvas(heroes_canvas, width=s(323), height=s(113), relief='raised', borderwidth=3)
            stats = [
                ("Matches", matches),
                (string, dpm),
                (kdstring, kd),
                
                ("MVP %", mvp),
                ("Win %", winpct)
                
                ]
            createCanvasImage(
                heroes_canvas,
                img_key="hero_row",
                size=(326, 109),
                bg=NAME_BANNER,
                
                x=x+2,
                y=y
                    )
            #hero_icon = tk.Canvas(heroes_canvas, width=s(108), height=s(108), highlightthickness=0, relief='raised', borderwidth=2)
            createCanvasImage(
                heroes_canvas,
                img_key=hero,
                size=(106, 106),
                
                x=x+3,
                y=y+2)
            
            createCanvasImage(
                heroes_canvas,
                img_key=role,
                size=(32, 32),
                
                x=280,
                y=y+40)
            #hero_canvas.create_window(0, 0, anchor="nw", window=hero_icon)
            #heroes_canvas.create_window(x+1, y+5, anchor="nw", window=hero_canvas)
            y += 114
            
            for i, (label, value) in enumerate(stats):
                
                fg_color = getForegroundColor(label, value)
                if fg_color == "#2B2B2B":
                    fg_color = "#D6CCEC"
                heroes_canvas.create_text(xxx,yyy, text=label, fill="#D6CCEC", font=fonttk("Rajdhani SemiBold", 12, 'normal'), anchor="nw")
                heroes_canvas.create_text(xxx+50,yyy, text=value, fill=fg_color, font=fonttk("Rajdhani", 12, 'bold'), anchor="nw")
                yyy += 23
            # heroes_canvas.create_text(text_x+150,text_y+5, text=f"Matches", fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")
            # heroes_canvas.create_text(text_x+170,text_y+5, text=matches, fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")
            # heroes_canvas.create_text(text_x+150,text_y+35, text=f"Win %", fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")
            # heroes_canvas.create_text(text_x+170,text_y+35, text=winpct, fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")
            # heroes_canvas.create_text(text_x+150,text_y+65, text=f"MVPs", fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")
            # heroes_canvas.create_text(text_x+170,text_y+65, text=mvp, fill="#2B2B2B", font=fonttk("Rajdhani Medium", 12, 'normal'), anchor="nw")



        

    return outer
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

def score_player(player):
    # ======================
    # Overall stats
    # ======================

    kda_raw = norm_kda(to_float_ratio(getattr(player, "_kda", 0.0)))
    kd_raw  = norm_kd(to_float_ratio(getattr(player, "_kd", 0.0)))
    win_raw = norm_pct2(to_float_pct(getattr(player, "_matches_won_pct", 0.0)), baseline=75)
    mvp_raw = norm_pct2(to_float_pct(getattr(player, "_mvpPct", 0.0)), baseline=60)

    overall_games = int(to_float_ratio(getattr(player, "_matches_played", 0)))

    

    # Trust overall stats fully around 100 games
    kda_n = apply_games_confidence(kda_raw, overall_games, full_conf_games=20)
    kd_n  = apply_games_confidence(kd_raw,  overall_games, full_conf_games=20)
    win_n = apply_games_confidence(win_raw, overall_games, full_conf_games=20)
    mvp_n = apply_games_confidence(mvp_raw, overall_games, full_conf_games=20)

    # Overall score weighting
    # KDA = 25%, KD = 30%, Win% = 30%, MVP% = 15%
    overall_score = (
        0.05 * kda_n +
        0.5 * kd_n +
        0.10 * win_n +
        0.35 * mvp_n
    )

    # ======================
    # Best character stats (char1)
    # ======================
    best = 0
    best_name = "Unknown"
    for i in range(1, 4):
        hero1 = getattr(player, f"hero{i}", "Unknown")
        if hero1 == "Unknown" or hero1 == "Null":
            continue
        win1_raw = norm_pct2(to_float_pct(getattr(player, f"win_pct{i}", 0.0)), baseline=75)
        kd1_raw  = norm_kd(to_float_ratio(getattr(player, f"kd{i}", 0.0)))
        mvp1_raw = norm_pct2(to_float_pct(getattr(player, f"mvp{i}", 0.0)), baseline=75)

        char1_games = int(to_float_ratio(getattr(player, f"matches_played{i}", 0)))
        # Char1 has fewer games, so full trust around 40 games
        win1_n = apply_games_confidence(win1_raw, char1_games, full_conf_games=20)
        kd1_n  = apply_games_confidence(kd1_raw,  char1_games, full_conf_games=20)
        mvp1_n = apply_games_confidence(mvp1_raw, char1_games, full_conf_games=20)

        # Char1 score: emphasize win% and KD
        # Win% = 45%, KD = 40%, MVP% = 15%
        char1_score = (
            0.10 * win1_n +
            0.55 * kd1_n +
            0.35 * mvp1_n
        )
        setattr(player, f"score_hero{i}", char1_score)
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


def show_gui(players,root):
    global indicator_label, bHide, NAMEPLATES
    NAMEPLATES = []
    
    #root = create_root()
    root.title("Match Overview")
    
    width = len(players) * s(330)
    he = 0
    if SCALE != 1:
        he = 12
    h = s(1000)+he
    screen_width = root.winfo_screenwidth()
    x = (screen_width - width) // 2
    y = 0
    root.geometry(f"{width}x{h}+0+{y}")
    root.configure(bg="black")
    root.overrideredirect(True)
    root.attributes("-topmost", True)  # Always on top
    
    # t = time.perf_counter()
    # image_map = {}
    # for filename in os.listdir(assets_chars):
    #     if filename.lower().endswith(".png"):
    #         key = os.path.splitext(filename)[0]
    #         path = os.path.join(assets_chars, filename)
    #         image_map[key] = Image.open(path)  # Store PIL images instead

    # nameplate_map = {}
    # for filename in os.listdir(assets_nameplates):
    #     if filename.lower().endswith(".png"):
    #         key = os.path.splitext(filename)[0]
    #         path = os.path.join(assets_nameplates, filename)
    #         nameplate_map[key] = Image.open(path)  # Store PIL images instead

    # ui_img_map = {}
    # for filename in os.listdir(assets_ui):
    #     if filename.lower().endswith(".png"):
    #         key = os.path.splitext(filename)[0]
    #         path = os.path.join(assets_ui, filename)
    #         ui_img_map[key] = Image.open(path)  # Store PIL images instead

    # special_hero_map = {}
    # for filename in os.listdir(assets_lords):
    #     if filename.lower().endswith(".png"):
    #         key = os.path.splitext(filename)[0]
    #         path = os.path.join(assets_lords, filename)
    #         special_hero_map[key] = Image.open(path)  # Store PIL images instead
    # print(f"OLD METHOD Loaded images in {time.perf_counter() - t:.2f} seconds.")
    global SPECIAL_IMAGE_MAP
    #SPECIAL_IMAGE_MAP = special_hero_map
    
    title_bar = tk.Frame(root, bg="#141420", relief="groove", height=s(30),width=s(width))
    title_bar.pack(fill="x", side="top",expand=True)
    #title_bar.pack_propagate(False)
    player_frames = tk.Frame(root, bg="#141420")
    player_frames.pack(side="bottom",fill="both", expand=True)
    close_btn = tk.Button(title_bar, command=lambda: close(root,script_dir),text="x", width=s(2),height=s(1),fg="white", relief="flat",bg="#141420", font=fonttk(exo, 12, 'normal' ), cursor="hand2")
    close_btn.pack(side="right", padx=0)
    hide_btn = tk.Button(title_bar, command=lambda: toggle_hide(),text="Hide(F7)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
    hide_btn.pack(side="right", padx=10)
    global lock
    lock = tk.Button(title_bar, command=toggle_clickthrough,text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
    lock.pack(side="right", padx=10)
    indicator_label = tk.Label(title_bar, text="", fg="white", bg="#141420", font=fonttk("Arial", 12))
    indicator_label.pack(side="left",padx=0)

    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#d41c1c"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#141420"))


    hide_btn.bind("<Enter>", lambda e: hide_btn.config(bg="#31314D"))
    hide_btn.bind("<Leave>", lambda e: hide_btn.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    top_player = max(players, key=lambda p: float(p.playermvp.strip('%')))
    def toggle_hide():
        global bHide
        
            
        
        bHide = not bHide
        if bHide:
            player_frames.pack_forget()
            hide_btn.config(text="Show(F7)")
            root.update_idletasks()
            current_height = root.winfo_height()
            hh = s(34)
            root.geometry(f"{width}x{hh}+{x}+{y}")
            
        else:
            
            player_frames.pack(side="bottom",fill="both", expand=True)
            
            hide_btn.config(text="Hide(F7)")
            root.update_idletasks()
            root.geometry(f"{width}x{h}+0+{y}")
        #keyboard.add_hotkey('f7', toggle_hide)
        

# Set their .ace to True
    top_player.ace = True
    rank_players(players)
    for p in players:
        print(
            f"{p.rank}. {p.name}  | "
            f"Final={p.final_score:.3f}  "
            f"(Overall={p.overall_score:.3f}, {p.best_hero}(Best Char Score)={p.char1_score:.3f})"
        )
    t   = time.perf_counter()
    for player in players:

        
        create_player_frame(player_frames, player)
        #create_player_frame2(root,player_frames, len(players),player, image_map, ui_img_map, nameplate_map)
    
    print(f"Created player frames in {time.perf_counter() - t:.2f} seconds.")
    root.update_idletasks()
    
    player_frames.pack_propagate(False)
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()

        #hotkey_id = keyboard.add_hotkey("f7", lambda: toggle_hide())
    #root.mainloop()
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


def show_launcher():
    global bhidden, bdebug_menu, indicator_label,main, var2, var1,root,cb1,cb2,cb3
    global fonts
    
    def list_fonts1():
        

        families = sorted(set(tkFont.families(root)))
        weights = ["normal", "bold"]
        slants = ["roman", "italic"]

        for fam in families:
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

    font_scale = 1
    #print(config.mobile_mode)
    if config.mobile_mode:
        font_scale = 2
        print(font_scale)
    font_sizes = list(range(6, 70))
    fonts = {size: scale_font(font_scale, size) for size in font_sizes}
    bhidden = False
    bdebug_menu = False
    root = create_root(BASE_DPI_SCALE)
    root.title("Capture Names")
    
    
    screen_width = root.winfo_screenwidth()
    x = (screen_width // 2)+175
    y = 0
    
    root.geometry(f"+{x}+{y}")
    root.attributes("-topmost", True)
    root.configure(bg="#151426")
    root.overrideredirect(True)
# Register Fonts !!!!!!
    if not config.mobile_mode:
        loaded_paths, families = call_register_fonts(root)
    # if len(loaded_paths) > 0:
    #     print(f"✅ Loaded {len(loaded_paths)} custom GUI fonts.")
    # list_fonts1()
    # fontsa = list(tkFont.families())
    # save_list_file(fontsa, "available_fonts.txt")
    # # Print them
    # #print(len(fontsa))
    # for f in fontsa[170:]:  # Limit output for brevity
    #     print(f)
    title_bar2 = tk.Frame(root, bg="#141420", relief="solid", width=230,height=17)
    title_bar2.pack(fill="x", side="top",ipady=3)
    title_bar2.pack_propagate(False)
    main = tk.Frame(root, bg="#151426", relief="solid", height=30, width=230)
    main.pack(fill="x", padx=10,pady=5, side="bottom")
    deb = tk.Frame(root, bg="#151426", relief="solid", height=30, width=230)
    lef = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
    rig = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
    lef.pack(fill="x", padx=0,pady=0, side="left")
    rig.pack(fill="x", padx=0,pady=0, side="right")
    var1 = tk.BooleanVar()
    var2 = tk.BooleanVar()
    var3 = tk.BooleanVar()
    var4 = tk.BooleanVar()
    global global_random_ban, global_random_matchup, global_dex, global_debugmode, global_debugflag
    global_debugmode = config.debug_mode
    var1.set(global_random_ban)
    var2.set(global_random_matchup)
    var3.set(global_dex)
    var4.set(global_debugmode)
    # Variables to hold checkbox states
    
    #if config.randomize_ban:
        #var1.set(True)
    #f config.randomize_matchup:
        #var2.set(True)

    # Create checkboxes on the 'deb' frame
    frame = lef
    global_debugflag = False
    if config.debug_mode:
        frame = rig
        cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=fonttk(carbon, 10),variable=var1)
        cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2, font=fonttk(carbon, 10))
        cb1.pack(anchor="w",padx=0)
        cb2.pack(anchor="w",padx=0)
        global_debugflag = True

    
    cb3 = tk.Checkbutton(frame, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3, font=fonttk(carbon, 10))
    cb4 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Enable Debug", variable=var4, font=fonttk(carbon, 10))
    #cb3 = tk.Checkbutton(deb, text="Option 3", variable=var3)

    # Pack them onto the frame
    
    cb3.pack(anchor="w",padx=0)
    cb4.pack(anchor="w",padx=0)
    #cb3.pack(anchor="w")
    def toggle_hide(debug_frame= None, m=None, btn2=None):
        global bhidden
        if m and btn2 and debug_frame:
            main = m
            hide_btn2 = btn2
            deb = debug_frame
        global bhidden, bdebug_menu
        bhidden = not bhidden
        if bhidden:
            if bdebug_menu:
                deb.pack_forget()
            else:
                main.pack_forget()
            hide_btn2.config(text="Show(F7)")
            
        else:
            if bdebug_menu:
                deb.pack(fill="x", padx=0,pady=6, side="bottom")
            else:
                main.pack(fill="x", padx=10,pady=5, side="bottom")
            
            hide_btn2.config(text="Hide(F7)")
        #keyboard.add_hotkey('f7', toggle_hide)
        root.update_idletasks()
        root.geometry("")
    def toggle_clickthrough_0():
        global is_clickthrough, indicator_label, lock, bhidden
        if is_clickthrough:

            make_interactive()
            if not bhidden:
                bhidden = not bhidden
                if bdebug_menu:
                    deb.pack(fill="x", padx=0,pady=6, side="bottom")
                else:
                    main.pack(fill="x", padx=10,pady=5, side="bottom")
            if indicator_label:
                indicator_label.config(text="")
                indicator_label.update_idletasks()
                indicator_label.update()
            if widget_exists(lock):
                
            
                current = lock.cget("text")

                
                
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
    def toggle_debug():
        import config
        global bdebug_menu,bhidden,global_random_matchup,global_random_ban,global_dex,global_debugmode,global_debugflag,cb1,cb2,cb3
        bdebug_menu = not bdebug_menu
        if bhidden:
            bhidden = False
            hide_btn2.config(text="Hide(F7)")
        if bdebug_menu:
            
            main.pack_forget()
            debug.config(text="Back")
            
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:

                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=fonttk(carbon, 10),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2, font=fonttk(carbon, 10))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3, font=fonttk(carbon, 10))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3, font=fonttk(carbon, 10))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            #print(f"Dexerto: {config.dex}")
            deb.pack(fill="x", padx=0,pady=6, side="bottom")
            
        else:
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:
                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=fonttk(carbon, 10),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2, font=fonttk(carbon, 10))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3, font=fonttk(carbon, 10))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3, font=fonttk(carbon, 10))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            #print(f"Dexerto: {config.dex}")
            deb.pack_forget()
            debug.config(text="Debug")
            main.pack(fill="x", padx=10,pady=5, side="bottom")

    close_btn2 = tk.Button(title_bar2, command=lambda: close2(root),text="x", width=2,height=1,fg="white", relief="flat",bg="#141420", font=fonttk(exo, 12, 'normal'), cursor="hand2")
    close_btn2.pack(side="right", padx=0)
    hide_btn2 = tk.Button(title_bar2, command=lambda: toggle_hide(deb, main, hide_btn2),text="Hide(F7)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
    hide_btn2.pack(side="right", padx=1)
    
    if config.debug_mode or config.debug_menu:
        debug = tk.Button(title_bar2, command=toggle_debug,text="Debug", relief="flat",fg="#FCD92E", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
        debug.pack(side="right", padx=1)
        debug.bind("<Enter>", lambda e: debug.config(bg="#31314D"))
        debug.bind("<Leave>", lambda e: debug.config(bg="#141420"))
    global lock
    lock = tk.Button(title_bar2, command=lambda: toggle_clickthrough(toggle_hide, deb, main, hide_btn2),text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
    lock.pack(side="right", padx=1)
    indicator_label = tk.Label(title_bar2, text="", fg="white", bg="#141420", font=fonttk("Arial", 12))
    indicator_label.pack(side="left",padx=0)
    close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
    close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))
    if not config.mobile_mode:
        hotkey_id = keyboard.add_hotkey("f7", lambda: toggle_hide(deb, main, hide_btn2))
    hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
    hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    si = "left"
    arr = {'text':"Bans [F8]", 'height':1, 'state':'disabled', 'relief':"flat", 'bg':"#8D8D8D",'font':fonttk("Rajdhani",'bold',13),'command':lambda: trigger1(var1.get())}
    wi = 88
    for i in range (1):
        fra = tk.Frame(main, bg="#151426", relief="solid", height=33, width=wi)
        fra.pack(side=si, expand=True)
        fra.pack_propagate(False)
        bu = tk.Button(fra, **arr)
        bu.pack()
        if i != 0:
            bu.bind("<Enter>", lambda e, b=bu: b.config(bg="#A18D25"))
            bu.bind("<Leave>", lambda e, b=bu: b.config(bg="#FCD92E"))
        si = "right"
        
        wi += 40
        if i == 0:
            button = bu


    button.config(state="normal", bg="#FCD92E", cursor="hand2")
    button.bind("<Enter>", lambda e, b=button: b.config(bg="#A18D25"))
    button.bind("<Leave>", lambda e, b=button: b.config(bg="#FCD92E"))

    #button = tk.Button(main,text="Bans [F8]", height=s(1, relief="flat", bg="#FCD92E",font=fonttk("Rajdhani Bold",'normal',12),command=lambda: trigger1(var1.get()), cursor="hand2")
    #button.pack(side="left",expand=True,ipady=0)
    # button.bind("<Enter>", lambda e: button.config(bg="#A18D25"))
    # button.bind("<Leave>", lambda e: button.config(bg="#FCD92E"))
    # button1 = tk.Button(main,text="Counters [F10]",height=s(1, relief="flat", bg="#FCD92E",font=fonttk("Rajdhani Bold",'normal',12),command=lambda: trigger22(var2.get()), cursor="hand2")
    # button1.pack(side="right",expand=True,ipady=0)
    # button.pack_propagate(False)
    # button1.pack_propagate(False)
    # #button.configure(font=fonttk("Cairo Black",'bold',12),height=s(1)
    # #button1.configure(font=fonttk("Cairo Black",'bold',12),height=s(1)
    # button1.bind("<Enter>", lambda e: button1.config(bg="#A18D25"))
    # button1.bind("<Leave>", lambda e: button1.config(bg="#FCD92E"))

    after_id = None  # Store enforce loop
    
    initialize_hide_pass(toggle_hide, deb, main,hide_btn2)

    # def force_focus():
    #     try:
    #         root.lift()
    #         root.focus_force()
    #         root.attributes('-topmost', True)
    #     except:
    #         pass
    #     nonlocal after_id
    #     after_id = root.after(1000, force_focus)

    def trigger(flag):
        if not config.mobile_mode:
            keyboard.remove_hotkey(hotkey_id)
        if flag:
            config.randomize_ban = True
        if after_id:
            root.after_cancel(after_id)
        #root.destroy()
        initialize_hide_pass(None, None, None,None)
        #on_trigger()

    def trigger1(flag):
        #if not config.mobile_mode:
            #keyboard.remove_hotkey(hotkey_id)
        if flag:
            config.randomize_ban = True
        #if after_id:
            #root.after_cancel(after_id)
        #root.destroy()
        initialize_hide_pass(None, None, None,None)
        title_bar2.pack_forget()
        deb.pack_forget()   
        main.pack_forget() 
        root.update_idletasks()
        root.geometry("")
        on_f8_pressed(root)

    
    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()
    
    trigger_func = trigger

   
    root.mainloop()   # keep the launcher window alive
    
        

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

class App:
    def __init__(self, base_dpi_scale):
        self.base_dpi_scale = base_dpi_scale
        self._after_ids = set()
        # ---- ONE root for the life of the app ----
        self.root = create_root(self.base_dpi_scale)
        self.root.title("Capture Names")
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
        x = (screen_width // 2) + 175
        y = 0
        

        # Register fonts
        if not config.mobile_mode:
            loaded_paths, families = call_register_fonts(self.root)

        # ----- build UI into parent (NOT root directly) -----
        title_bar2 = tk.Frame(parent, bg="#141420", relief="solid", width=230, height=17)
        title_bar2.pack(fill="x", side="top", ipady=3)
        title_bar2.pack_propagate(False)

        main = tk.Frame(parent, bg="#151426", relief="solid", height=30, width=230)
        main.pack(fill="x", padx=10, pady=5, side="bottom")

        deb = tk.Frame(parent, bg="#151426", relief="solid", height=30, width=230)
        lef = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
        rig = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
        lef.pack(fill="x", side="left")
        rig.pack(fill="x", side="right")

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
            frame = rig
            cb1 = tk.Checkbutton(lef, bg="#151426", fg="white", selectcolor="#151426",
                                text="Random Bans", font=fonttk(carbon, 10), variable=self.var1)
            cb2 = tk.Checkbutton(lef, bg="#151426", fg="white", selectcolor="#151426",
                                text="Random Matchup", font=fonttk(carbon, 10), variable=self.var2)
            cb1.pack(anchor="w")
            cb2.pack(anchor="w")
            self.global_debugflag = True

        cb3 = tk.Checkbutton(frame, bg="#151426", fg="white", selectcolor="#151426",
                             text="Use Classic Logic", font=fonttk(carbon, 10), variable=self.var3)
        cb4 = tk.Checkbutton(rig, bg="#151426", fg="white", selectcolor="#151426",
                             text="Enable Debug", font=fonttk(carbon, 10), variable=self.var4)
        cb3.pack(anchor="w")
        cb4.pack(anchor="w")

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
                    deb.pack(fill="x", padx=0, pady=6, side="bottom")
                else:
                    main.pack(fill="x", padx=10, pady=5, side="bottom")
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

                deb.pack(fill="none", padx=0, pady=6, side="bottom")
            else:
                config.dex = self.var3.get()
                config.debug_mode = self.var4.get()

                deb.pack_forget()
                debug_btn.config(text="Debug")
                main.pack(fill="x", padx=10, pady=5, side="bottom")

        def trigger1(flag):
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

            self.on_f8_pressed()
            #print(f"Triggered F8 in {time.perf_counter() - t:.2f} seconds.")

        # ---- title bar buttons ----
        close_btn2 = tk.Button(
            title_bar2, command=lambda: close2(self.root),
            text="x", width=2, height=1, fg="white", relief="flat",
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

            self.hotkey_f8_id = keyboard.add_hotkey('f8', lambda: self.root.after(0, lambda: trigger1(self.var1.get())))

        # main button (your bans trigger)
        fra = tk.Frame(main, bg="#151426", relief="solid", height=33, width=88)
        fra.pack(side="left", expand=True)
        fra.pack_propagate(False)

        button = tk.Button(
            fra,
            text="Bans [F8]", height=1, state="normal",
            relief="flat", bg="#FCD92E",
            font=fonttk("Rajdhani", 'bold', 13),
            command=lambda: trigger1(self.var1.get()),
            cursor="hand2"
        )
        button.pack()

        close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
        close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))


        hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
        hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
        self.lock_btn.bind("<Enter>", lambda e: self.lock_btn.config(bg="#31314D"))
        self.lock_btn.bind("<Leave>", lambda e: self.lock_btn.config(bg="#141420"))

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
    def build_match_overview(self, parent, players):
        global NAMEPLATES
        NAMEPLATES = []

        self.root.title("Match Overview")

        width = len(players) * s(330)
        he = 12 if SCALE != 1 else 0
        h = s(1030) + he
        w = s(len(players) * 330)
        h = s(1030) + (12 if SCALE != 1 else 0)

        screen_width = self.root.winfo_screenwidth()
        x = (screen_width - width) // 2
        y = 0

        self.force_geometry(w, h, 0, 0)

        # also re-apply on idle (handles the intermittent "stays put" case)
        self.after_idle_tracked(lambda: self.force_geometry(w, h, 0, 0))
        self.after_tracked(30, lambda: self.force_geometry(w, h, 0, 0))
        self.root.after(0, lambda: print("actual", self.root.winfo_x(), self.root.winfo_y()))
        self.root.configure(bg="black")

        title_bar = tk.Frame(parent, bg="#141420", relief="groove", height=s(30), width=s(width))
        title_bar.pack(fill="x", side="top", expand=True)

        player_frames = tk.Frame(parent, bg="#141420")
        player_frames.pack(side="bottom", fill="both", expand=True)

        

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
        top_player = max(players, key=lambda p: float(p.playermvp.strip('%')))
        top_player.ace = True

        rank_players(players)
        for p in players:
            print(
                f"{p.rank}. {p.name}  | "
                f"Final={p.final_score:.3f}  "
                f"(Overall={p.overall_score:.3f}, {p.best_hero}(Best Char Score)={p.char1_score:.3f})"
            )
        t = time.perf_counter()
        for player in players:
            create_player_frame(player_frames, player)
        print(f"Created player frames in {time.perf_counter() - t:.2f} seconds.")

        self.root.update_idletasks()

        if not config.mobile_mode:
            try:
                self.hwnd = win32gui.FindWindow(None, self.root.title())
            except Exception:
                self.hwnd = None
    
    # =========================
    # Bridge (refactor of on_f8_pressed)
    # =========================


    def on_f8_pressed(self):
        print(">> Script running. Press F8 to OCR names and check tracker.gg...")
        initialize_hide_pass(None, None, None,None)
        manual_debug = 1
        if manual_debug == 69:
                names = ['thanosplushie','DuckButtCut','Girtty','DrDubz']
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
        
        if not config.debug_mode and manual_debug != 69:
            if names:
                tracker_data = open_multiple_tracker_profiles(names)
                
                save_json("_2TrackerGGJSON.json", tracker_data)
                save_list_file(names,"_1Names.txt")
        elif config.debug_mode and manual_debug == 0:
            tracker_data = open_multiple_tracker_profiles(names)
            save_json("_2TrackerGGJSON.json", tracker_data)
            save_list_file(names,"_1Names.txt")
        if tracker_data:
            #tracker_data = transform_private_tracker_data(tracker_data)

            t = time.perf_counter()
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
                p = Player2(name, data)
                p = Player(name, data)
                players.append(p)
            print(f"Processed tracker.gg data in {time.perf_counter() - t:.2f} seconds.\n")

        if players:
            t = time.perf_counter()
            self.show_match_page(players)
            print(f"Displayed match page in {time.perf_counter() - t:.2f} seconds.")

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
    app = App(BASE_DPI_SCALE)
    app.run()
        