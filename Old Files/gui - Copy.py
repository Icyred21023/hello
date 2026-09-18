

import tkinter as tk
import config
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab,  ImageDraw, ImageChops
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

SHEETS_DIR = os.path.join(config.script_dir, "assets_match_hd")
CROP_CACHE_PATH = os.path.join(SHEETS_DIR, "_mastery_crop_cache.json")
import _Mastery_Sheet_Editor 
crop_cache = _Mastery_Sheet_Editor.load_crop_cache(CROP_CACHE_PATH) if os.path.exists(CROP_CACHE_PATH) else {}
bTest = True
bSpecialBG = False

def split_edges(total: int, parts: int) -> list[int]:
        base = total // parts
        rem = total % parts
        edges = [0]
        acc = 0
        for i in range(parts):
            acc += base + (1 if i < rem else 0)
            edges.append(acc)
        return edges

class SpriteSheetAnimator:
    def __init__(
        self,
        master,
        hero,
        animated=True,              # NEW
        sheet_path=None,            # for animated
        rows=10,
        cols=6,
        fps=24,
        scale=1,
        bg="#77789E",
        relief="sunken",
        borderwidth=1,
        size=None,
        bSubCrop=False,
        static_icon=None,           # NEW: for non-animated
        bSpecialBG=False,           # keep if you use it
    ):
        """
        animated:
          True  -> uses sprite sheet animation
          False -> renders a single static icon into the same canvas

        static_icon:
          Whatever key/path your createOnlyImage/_create_only_image uses.
        """
        SHEETS_DIR = os.path.join(config.script_dir, "assets_match_hd")

        self.master = master
        self.hero = hero
        self.animated = animated
        self.fps = fps
        self.delay_ms = int(1000 / fps) if fps else 0
        self.scale = scale
        self.rows = rows
        self.cols = cols
        self.size = size
        self.bSubCrop = bSubCrop
        self.running = False

        # --- your existing vars ---
        self.colors = ['blue', 'green', 'pink', 'purple', 'white']
        self.herobg = "heromasterybg_"

        # If you have crop_cache logic, keep it (only matters for animated sheets)
        sheet_key = self.hero + "_Master.png"
        if self.animated and sheet_key in crop_cache:
            prev = crop_cache[sheet_key]
            self.subcrop_x = int(prev["x0"])
            self.subcrop_y = int(prev["y0"])
            self.subcrop_w = int(prev["side"])
            self.subcrop_h = int(prev["side"])
            self.bSubCrop = True
            self.size = (s(104), s(104))

        # --- wrapper + canvas (same for both) ---
        icon_wrap = tk.Frame(master, width=s(104), height=s(104), bg=bg)
        icon_wrap.pack(side="left",pady=(0,0))
        icon_wrap.pack_propagate(False)

        self.canvas = tk.Canvas(
            icon_wrap,
            width=s(104),
            height=s(104),
            bg=bg,
            highlightthickness=0,
            bd=borderwidth,
            relief=relief
        )
        self.canvas.pack(fill="both",side ="bottom", expand=False)

        # center + offsets
        dx, dy = HERO_MASTERY_OFFSETS.get(self.hero, (0, 0))
        cx, cy = s(52), s(52)

        # optional special BG
        self.hero_bg_colored = None
        self.hero_bg_id = None
        if bSpecialBG:
            import random
            random_color = random.choice(self.colors)
            bg_name = self.herobg + random_color
            #self.hero_bg_colored = self.createOnlyImage(bg_name, size=(233, 104))
            self.hero_bg_id = self.canvas.create_image(s(52), s(52), image=self.hero_bg_colored, anchor="c")

        # ============================
        # STATIC MODE
        # ============================
        if not self.animated:
            # Load your normal hero icon and draw it onto canvas
            # Use your existing image loader (choose one that exists in this class)
            # If your loader returns a PIL.Image, convert to PhotoImage.
            # If it already returns PhotoImage, just use it.
            try:
                # OPTION A: if you have the same helper as outside:
                # pil = self._create_only_image(static_icon, (104, 104))  # but you likely don't in this class

                # OPTION B: if createOnlyImage returns ImageTk.PhotoImage directly:
                # img = self.createOnlyImage(static_icon, size=(s(104), s(104)))

                # safest: load PIL image first then convert (depends on your helpers)
                img_pil = self.createOnlyImagePIL(static_icon)  # <-- implement or swap to your real loader
                if self.size:
                    # if size is already scaled, don't s() twice. assume size is pixels.
                    w, h = self.size
                    img_pil = img_pil.resize((int(w), int(h)), Image.LANCZOS)
                elif scale != 1:
                    img_pil = img_pil.resize(
                        (int(img_pil.size[0] * scale), int(img_pil.size[1] * scale)),
                        Image.NEAREST
                    )

                self.static_img = ImageTk.PhotoImage(img_pil)
            except Exception:
                # fallback: try your other loader that already returns a PhotoImage
                self.static_img = self.createOnlyImage(static_icon, size=(s(104), s(104)))

            self.image_id = self.canvas.create_image(
                cx + s(dx), cy + s(dy),
                image=self.static_img,
                anchor="center"
            )

            #self.frame_overlay = self.createOnlyImage("gold_frame2", size=(s(128), s(128)))

            # self.frame_id = self.canvas.create_image(
            #     s(52), s(52),
            #     image=self.frame_overlay,
            #     anchor="center"
            # )

            self.frames = []
            self.index = 0
            return

        # ============================
        # ANIMATED MODE (your current logic)
        # ============================
        sheet, (sheet_w, sheet_h) = self.createOnlyImage1(sheet_path)

        xs = split_edges(sheet_w, cols)
        ys = split_edges(sheet_h, rows)

        frames = []
        for r in range(rows):
            for c in range(cols):
                x0, x1 = xs[c], xs[c + 1]
                y0, y1 = ys[r], ys[r + 1]

                if self.bSubCrop:
                    gx0 = x0 + self.subcrop_x
                    gy0 = y0 + self.subcrop_y
                    gx1 = gx0 + self.subcrop_w
                    gy1 = gy0 + self.subcrop_h
                    gx1 = min(gx1, x1)
                    gy1 = min(gy1, y1)
                    frame = sheet.crop((gx0, gy0, gx1, gy1))
                else:
                    frame = sheet.crop((x0, y0, x1, y1))

                if self.size:
                    # IMPORTANT: if self.size is already scaled by s(), don't s() again
                    w, h = self.size
                    frame = frame.resize((int(w), int(h)), Image.LANCZOS)
                elif scale != 1:
                    frame = frame.resize(
                        (int(frame.size[0] * scale), int(frame.size[1] * scale)),
                        Image.NEAREST
                    )

                frames.append(ImageTk.PhotoImage(frame))

        import random
        self.frames = frames
        self.index = random.randrange(len(self.frames)) if self.frames else 0

        if self.frames:
            self.image_id = self.canvas.create_image(
                cx + s(dx), cy + s(dy),
                image=self.frames[self.index],
                anchor="center"
            )

    def play(self):
        if not self.animated:
            return
        if not self.frames:
            return
        if self.running:
            return
        self.running = True
        self._tick()

    def stop(self):
        self.running = False

    def _tick(self):
        if not self.running:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.canvas.itemconfig(self.image_id, image=self.frames[self.index])
        self.canvas.after(self.delay_ms, self._tick)

            
            
    
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

def list_fonts():

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
              'Neue_Condensed_Bold.ttf', 'S.ttf','TTSCMD.ttf','Neue_Condensed_Medium.ttf',
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





if not config.mobile_mode:    
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

def score_player(player):
    # ======================
    # Overall stats
    # ======================
    ov = getattr(player, "seasonal_overview", None)
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
    
    for hero in player.top_heroes:

        
        hero1 = getattr(hero, "heroname", "Unknown")
        if hero1 == "Unknown" or hero1 == "Null":
            continue
        mvp = getattr(hero, f"total_mvp", 0.0)
        win1_raw = norm_pct2(to_float_pct(getattr(hero, f"win_pct", 0.0)), baseline=75)
        kd1_raw  = norm_kd(to_float_ratio(getattr(hero, f"kd_ratio", 0.0)))
        

        char1_games = int(to_float_ratio(getattr(hero, f"matches_played", 0)))
        mvp_pctt = (mvp/char1_games)*100 if char1_games >0 else 0.0
        mvp1_raw = norm_pct2(to_float_pct(mvp_pctt), baseline=75)
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

    def __init__(self, parent, player):
        
        self.parent = parent
        self.player = player
        self.db = DB

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
        self._pull_player_data()
        self._build_outer()

        # All frames that have `outer` as parent:
        self._build_name_bar()
        self._build_overview()
        self._build_heroes()
        self._build_history()

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

    def _create_canvas_image(
        self,
        canvas,
        img_key,
        anc="nw",
        size=None,
        bg=None,
        tint_alpha=False,
        tags = False,
        arh=None,
        x=0,
        y=0,
        mask=False,
    ):
        """
        Your original createCanvasImage converted to a method.
        Keeps the "canvas holds references" behavior.
        """
        def adjust_alpha(img_rgba, factor=1.0):
            img_rgba = img_rgba.convert("RGBA")
            r, g, b, a = img_rgba.split()

            # scale alpha
            a = a.point(lambda px: int(px * factor))

            img_rgba.putalpha(a)
            return img_rgba
        if arh is None:
            arh = {}

        img_raw = image_loader(img_key)

        if not img_raw:
            return False
        if tint_alpha:
            img_raw = adjust_alpha(img_raw, factor=0.85)  # light gray/white
        if mask:
            img_raw = img_raw.convert("RGBA")
            img_raw = make_circle(img_raw)

        if size:
            img_raw = img_raw.resize(self._s2(size), Image.LANCZOS)

        img = ImageTk.PhotoImage(img_raw)

        if bg is not None:
            canvas.configure(bg=bg)
        if tags:
            canvas.create_image(s(x), s(y), anchor=anc, image=img, tags=tags, **arh)
        else:
            canvas.create_image(s(x), s(y), anchor=anc, image=img, **arh)

        if not hasattr(canvas, "_images"):
            canvas._images = []
        canvas._images.append(img)

        return True

    def _create_only_image(self, img_key, size):
        img_raw = image_loader(img_key)
        if not img_raw:
            return False

        if size:
            img_raw = img_raw.resize(self._s2(size), Image.LANCZOS)

        return ImageTk.PhotoImage(img_raw)


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

        self.ov = getattr(p, "seasonal_overview", None) or getattr(p, "full_overview", None)
        self.roles = getattr(p, "roles", []) or []
        self.matches = getattr(p, "matches", []) or []
        if not isinstance(self.matches, list):
            self.matches = []

        fov = getattr(p, "full_overview", None)
        self.fov_heroes = fov.heroes if fov and hasattr(fov, "heroes") else []
        self.TTSuperCondLight = 'TT Sprmlt N Trl Cnd Lt'
        self.TTSuperCondMedium = 'TT Sprmlt N Trl Cnd Md'
        self.TTSuperCondThin = 'TT Sprmlt N Trl Cnd Th'

        # top3 heroes
        self.top3 = self._topn(getattr(p, "top_heroes", []) or [], 3)
        self.char_scores = [getattr(h, "score", None) for h in self.top3]

        # total time
        self.total_time_played = sum(
            h.time_played for h in getattr(p, "heroes", []) if hasattr(h, "time_played")
        )
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
        NAME_BANNER = "#24212B"  # was UI["outer"]["bg"]
        add = 12 if int(SCALE) != 1 else 0

        self.outer = tk.Frame(
            self.parent,
            width=s(380),
            height=s(1040) + add,
            bg=NAME_BANNER,
            borderwidth=1,
            relief="flat",
        )
        self.outer.pack(side="left", fill="both")
        self.outer.pack_propagate(False)

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

    # ---------------------------
    # OVERVIEW (outer -> overview_bar + overview_stats)
    # ---------------------------
    def _build_overview(self):
        NAME_BANNER = "#24212B"

        overview_bar = tk.Frame(
            self.outer,
            bg="#171B20",
            width=s(380),
            height=s(40),
            relief="raised",
            borderwidth=2,
        )
        overview_bar.pack(side="top", pady=(4, 0), fill="both")
        overview_bar.pack_propagate(False)

        overview_stats = tk.Frame(
            self.outer,
            bg="#171B20",
            width=s(380),
            height=s(125),
            relief="groove",
            borderwidth=2,
        )
        overview_stats.pack(side="top", fill="both")
        overview_stats.pack_propagate(False)

        # --- top strip canvas ---
        t_canvas = tk.Canvas(overview_bar, height=s(44 - 2), highlightthickness=0)
        t_canvas.pack(anchor="center", fill="x")

        self._create_canvas_image(
            t_canvas,
            img_key="overviewbg",
            anc="ne",
            size=(530, 59),
            bg="#1C2127",
            x=516,
            y=0,
        )

        ranking = getattr(self.player, "ranking", 999)
        imggg = None
        if ranking == 1:
            imggg, sizex, sizey = "MVP2", 58, 24
        elif ranking == 2:
            imggg, sizex, sizey = "SVP", 48, 23

        if ranking <= 3:
            self._create_canvas_image(
                t_canvas,
                img_key=f"{ranking}_banner",
                anc="ne",
                size=(166, 42),
                bg="#1C2127",
                x=150,
                y=0,
            )

        overfg = "#252438" if ranking <= 3 else "#ECEBFF"
        oss = round(getattr(self.player, "overall_score", 0), 3)

        t_canvas.create_text(
            s(12),
            s(6),
            text="Overview",
            fill=overfg,
            font=fonttk("Refrigerator Deluxe ExtraBold", 19, "normal"),
            anchor="nw",
        )
        t_canvas.create_text(
            s(270),
            s(6),
            text=oss,
            fill="#EBEAFF",
            font=fonttk("Refrigerator Deluxe ExtraBold", 19, "normal"),
            anchor="nw",
        )

        self._create_canvas_image(
            t_canvas,
            img_key=getattr(self.player, "best_rank", "Unknown"),
            anc="c",
            size=(46, 46),
            bg="#1C2127",
            x=353,
            y=20,
        )

        if imggg:
            self._create_canvas_image(
                t_canvas,
                img_key=imggg,
                size=(sizex, sizey),
                bg="#1C2127",
                x=175,
                y=8,
            )

        # --- overview stats block canvas ---
        ov_canvas = tk.Canvas(
            overview_stats,
            height=s(125),
            width=s(380),
            highlightthickness=0,
        )
        ov_canvas.pack(anchor="center", fill="both")

        self._create_canvas_image(
            ov_canvas,
            img_key="ov",
            anc="c",
            size=(398, 125),
            bg="#171B20",
            x=190,
            y=62,
        )

        ov = self.ov

        kd_ov = round(self._safe_attr(ov, "kd_ratio", 0), 2)
        kda_ov = round(self._safe_attr(ov, "kda_ratio", 0), 2)
        mvppct = self._safe_attr(ov, "mvp_pct", "0%")

        winpct = self._safe_attr(ov, "win_pct", "0%")

        stats_overview = [
            ("Matches", self._safe_attr(ov, "matches_played", 0), False),
            ("Win%", winpct, self.db.overview_stat_percentile("win_pct", winpct)),
            ("Mvp%", mvppct, self.db.overview_stat_percentile("mvp_pct", mvppct)),
            ("Kd", kd_ov, self.db.overview_stat_percentile("kd_ratio",float(kd_ov))),
            ("Kda", kda_ov, self.db.overview_stat_percentile("kda_ratio", float(kda_ov))),
        ]

        x, x2, y = 8, 95, 2
        for label, value, pctile in stats_overview:
            ov_canvas.create_text(
                s(x),
                s(y),
                text=label,
                fill="#2B2B2B",
                font=fonttk("Rajdhani", 14, "normal"),
                anchor="nw",
            )
            fgg = self._get_foreground_color(label, value, True)
            sval = ov_canvas.create_text(
                s(x2),
                s(y),
                text=value,
                fill=fgg,
                font=fonttk("Rajdhani Bold", 14, "normal"),
                anchor="nw",
            )
            if pctile:
                p = f"{round(pctile,1)}%" if pctile < 100 else f"100%"
                db_img = self._get_foreground_color("db_img", p, True)
                # lbl = tk.Label(
                #     ov_canvas,
                #     text=f"{p}",
                #     font=fonttk("Saira Condensed Medium", 8, "italic"),
                #     relief="sunken",
                #     bd=1
                # )

                # ov_canvas.create_window(
                #     s(x2 + 50),
                #     s(y)+4,
                #     window=lbl,
                #     anchor="nw"
                # )
                pct_overlay = 53
                xnew, ynew, xnew_before, ynew_before = self._get_iterative_coordinates(ov_canvas, sval, padx=12, pady=3)
                ynew = s(y) + 5
                tid = ov_canvas.create_text(
                    s(xnew),
                    s(ynew),
                    text=f"{p}",
                    fill="#353535",
                    font=fonttk("Rajdhani Medium", 9, "underline", italic=True),
                    anchor="nw",
                )
                xnew2, ynew2, xnew_before, ynew_before = self._get_iterative_coordinates(ov_canvas, tid, padx=5, pady=2)
                self._create_canvas_image(
                    ov_canvas,
                    img_key=db_img,
                    anc="nw",
                    size=(12, 9),
                    bg="#171B20",
                    x=xnew2,
                    y=ynew+2,
                )
                pct_overlay = 53 if xnew2 - xnew < 45 else 60
                size = (54, 15) if pct_overlay == 53 else (63, 15)
                pct_img = f"_pct{pct_overlay}"

                #print(f"Placing pct image at x={xnew - 3}, y={ynew - 2}, pct: {p}, img: {pct_img}")
                self._create_canvas_image(
                    ov_canvas,
                    img_key=pct_img,
                    anc="nw",
                    size=size,
                    bg="#FFFFFF",
                    x=xnew - 3,
                    y=ynew - 1,
                    tint_alpha=True,
                )


                # tid = ov_canvas.create_text(
                #     s(x2 + 50),
                #     s(y)+3,
                #     text=f"{p}",
                #     fill="#353535",
                #     font=fonttk("Rajdhani", 10, "underline"),
                #     anchor="nw",
                # )
                # self._create_canvas_image(
                #     ov_canvas,
                #     img_key=db_img,
                #     anc="nw",
                #     size=(12, 9),
                #     bg="#171B20",
                #     x=x2 + 50 + 25,
                #     y=y + 5,
                # )

                
                
            y += 24

        # role usage (kept same logic)
        roles = self.roles
        if roles and len(roles) >= 1:
            gray_role = roles[0].role_name + "_G"
            self._create_canvas_image(ov_canvas, img_key=gray_role, size=(26, 26), bg=NAME_BANNER, x=260, y=1)

            t1 = roles[0].time_played
            t2 = roles[1].time_played if len(roles) > 1 else 0
            t3 = roles[2].time_played if len(roles) > 2 else 0
            denom = (t1 + t2 + t3) if (t1 + t2 + t3) else 1

            usage = str(int((t1 / denom) * 100)) + " %"
            fgg = self._get_foreground_color("Win %", usage, True)

            ov_canvas.create_text(
                s(300), s(6),
                text=roles[0].role_name,
                fill="#2B2B2B",
                font=fonttk("Rajdhani", 12, "normal"),
                anchor="nw",
            )
            ov_canvas.create_text(
                s(320), s(36),
                text=usage,
                fill=fgg,
                font=fonttk("Rajdhani SemiBold", 12, "normal"),
                anchor="nw",
            )
            ov_canvas.create_text(
                s(270), s(36),
                text="Usage",
                fill="#2B2B2B",
                font=fonttk("Rajdhani", 12, "normal"),
                anchor="nw",
            )

            if len(roles) > 1:
                gray_role = roles[1].role_name + "_G"
                self._create_canvas_image(ov_canvas, img_key=gray_role, size=(26, 26), bg=NAME_BANNER, x=260, y=60)

                usage2 = str(int((t2 / denom) * 100)) + " %"
                fgg2 = self._get_foreground_color("Win %", usage2, True)

                ov_canvas.create_text(
                    s(300), s(65),
                    text=roles[1].role_name,
                    fill="#2B2B2B",
                    font=fonttk("Rajdhani", 12, "normal"),
                    anchor="nw",
                )
                ov_canvas.create_text(
                    s(320), s(94),
                    text=usage2,
                    fill=fgg2,
                    font=fonttk("Rajdhani SemiBold", 12, "normal"),
                    anchor="nw",
                )
                ov_canvas.create_text(
                    s(270), s(94),
                    text="Usage",
                    fill="#2B2B2B",
                    font=fonttk("Rajdhani", 12, "normal"),
                    anchor="nw",
                )

    # ---------------------------
    # HEROES (outer -> heroes_bar + heroes_frame + hero cards)
    # ---------------------------
    def _build_heroes(self):
        NAME_BANNER = "#24212B"

        heroes_bar = tk.Frame(
            self.outer,
            bg="#4A5172",
            width=s(380),
            height=s(35),
            relief="raised",
            borderwidth=2,
        )
        heroes_bar.pack(side="top", fill="both")
        heroes_bar.pack_propagate(False)

        heroes_bar_canvas = tk.Canvas(heroes_bar, height=s(35), highlightthickness=0)
        heroes_bar_canvas.pack(anchor="center", fill="x")

        self._create_canvas_image(
            heroes_bar_canvas,
            img_key="hero_banner2",
            anc="sw",
            size=(380, 82),
            bg="#4A5172",
            x=0,
            y=50,
        )

        heroes_bar_canvas.create_text(
            s(10), s(6),
            text="Best Heroes",
            fill="#E0DAFA",
            font=fonttk("Refrigerator Deluxe ExtraBold", 18, "normal"),
            anchor="nw",
        )

        if getattr(self.player, "bPrivate", False):
            heroes_bar_canvas.create_text(
                s(185), s(6),
                text="Private Account",
                fill="#FFE702",
                font=fonttk("Refrigerator Deluxe ExtraBold", 18, "normal"),
                anchor="nw",
            )

        heroes_frame = tk.Frame(
            self.outer,
            bg=NAME_BANNER,
            width=s(380),
            height=s(372),
            relief="flat",
            borderwidth=0,
        )
        heroes_frame.pack(side="top", fill="both")
        heroes_frame.pack_propagate(False)
        # while True:
        #     num = random.randint(1, 7)
        #     if num ==6:
        #         continue
        #     if num not in USED_HERO_BGS:
        #         hero_banner_bg = f"career ({num})"
        #         USED_HERO_BGS.append(num)
        #         break
        heroes_bg_canvas = tk.Canvas(heroes_frame, height=s(418), width=s(380), highlightthickness=0,bg=NAME_BANNER)
        heroes_bg_canvas.pack(anchor="center", fill="both",pady=(2,0))
        heroes_bg_canvas.pack_propagate(False)
        self._create_canvas_image(
            heroes_bg_canvas,
            img_key="herobg3",
            anc="nw",
            size=(380, 372),
            bg=NAME_BANNER,
            x=0,
            y=0,
        )
        # img = self._create_only_image(hero_banner_bg, (330, 794))
        # #img = self._create_only_image("herobg3", (330, 358))
        # img_bg = tk.Label(heroes_frame, image=img, bg=NAME_BANNER)
        # img_bg.image = img
        # img_bg.place(x=0, y=0, relwidth=1, relheight=1)

        # Build hero cards in score order
        global bTest
        coun = 0
        for idx1 in self.order:  # idx1 is 1..3
            coun += 1
            # kept in case you use it later
            # scfg = "#e2b52d" if coun == 1 else "#7f9ccf" if coun == 2 else "#d39a74"

            if idx1 == 0:
                continue

            i = idx1 - 1
            hero_obj = self._safe_at(self.top3, i, None)
            if hero_obj is None:
                continue
            killrate = getattr(hero_obj, "kills_per_10", 0)
            role = getattr(hero_obj, "role", "")
            hero = getattr(hero_obj, "heroname", "Unknown")
            hero_time = getattr(hero_obj, "time_played", 0)
            denom = self.total_time_played if self.total_time_played else 1
            usage_pct = str(int(hero_time / denom * 100)) + "%"

            matches_played = round(getattr(hero_obj, "matches_played", 0), 1)
            winpct = getattr(hero_obj, "win_pct", "0%")
            mvp = getattr(hero_obj, "mvp_pct", "0%")
            dpm = getattr(hero_obj, "damage_per_minute", 0)
            kd = round(getattr(hero_obj, "kd_ratio", 0), 2)
            
            matching = next(
                (h for h in self.fov_heroes 
                if h.heroname == hero),
                None
            )
            if matching:
                total_hero_time = matching.time_played
                total_hero_time_h = total_hero_time / 3600
            else:
                total_hero_time_h = False
            #pct = db.stat_percentile(hero, "kd_ratio", float(kd), min_samples=4)
            #print(f"{self.player.name}'s {hero} KD {kd} is {pct}%")


            score = self.char_scores[i]
            score = round(score, 3) if score is not None else 0

            string = "Damage" if role != "Strategist" else "Healing"
            kdstring = "Kd"

            # Lord/skin selection logic (same behavior)
            hero_icon = hero
            bAnimatedLord = False
            border_color = "#222222"
            border_thick = 0

            if hero != "Unknown":
                if MANUAL_DEBUG != 1:
                    global icon_idx
                    bAnimatedLord = True
                else:
                    for h in self.fov_heroes:
                        if h.heroname == hero:
                            time_played_s = h.time_played
                            time_played_m = time_played_s / 60
                            time_played_h = time_played_m / 60
                            #print(f"{self.player.name} - {hero} time played: {time_played_h:.2f} hours")

                            if time_played_h > 60:
                                bAnimatedLord = True
                                border_color = "#E79E18"
                                border_thick = 2
                            elif time_played_h > 10:
                                hero_icon = hero + "_l"
                                bAnimatedLord = False
                                border_color = "#b963ff"
                                border_thick = 2
                            else:
                                hero_icon = hero
                            break

            if not image_loader(hero_icon):
                hero_icon = hero
                if not image_loader(hero_icon):
                    print(f"Image not found for {hero_icon}, setting to Unknown")
                    hero_icon = "Unknown"

            # --- card container ---
            hero_bar = tk.Frame(
                heroes_bg_canvas,
                bg="#c8d9f9",
                width=s(380),
                height=s(112),
                relief="raised",
                borderwidth=2,
            )
            hero_bar.pack(side="top", pady=(3, 2), fill="x")
            hero_bar.pack_propagate(False)

            # icon (animated or static)
            # icon (animated or static)
            try:
                if bAnimatedLord:
                    sheee = hero + "_Master2"
                    anim = SpriteSheetAnimator(
                        master=hero_bar,
                        hero=hero,
                        animated=True,
                        sheet_path=sheee,
                        rows=10,
                        cols=6,
                        fps=24,
                        bg="#595A88",
                        relief="sunken",
                        borderwidth=2,
                    )
                    anim.play()
                    hero_bar.hero_anim = anim
                    bTest += 1

                else:
                    anim = SpriteSheetAnimator(
                        master=hero_bar,
                        hero=hero,
                        animated=False,
                        static_icon=hero_icon,   # <-- whatever you pass to _create_only_image()
                        bg="#595A88",
                        relief="sunken",
                        borderwidth=2,
                        size=(s(104), s(104)),   # optional: force icon size
                    )
                    hero_bar.hero_anim = anim  # optional (just keeps a ref)

            except Exception as e:
                print("Error loading hero icon for", hero, e)
                anim = SpriteSheetAnimator(
                    master=hero_bar,
                    hero=hero,
                    animated=False,
                    static_icon="Unknown",
                    bg="#595A88",
                    relief="sunken",
                    borderwidth=2,
                    size=(s(104), s(104)),
                )
                hero_bar.hero_anim = anim

                        # stats = [
            #     ("Matches", int(matches_played)),
            #     ("Usage", usage_pct),
            #     (string, dpm),
            #     (kdstring, kd),
            #     ("Mvp%", mvp),
            #     ("Win%", winpct),
            #     ("K/10min", killrate)
            # ]

            stats = [
                        ("Games",matches_played, False),
                        ("Usage", usage_pct, False),
                        ("Time", str(int(round(total_hero_time_h)))+'h', False),
                        ("Win %", winpct, False),
                        ("Mvp %", mvp, False),

                        ("AvgLife", hero_obj.average_lifespan, self.db.stat_percentile(hero, "average_lifespan", float(hero_obj.average_lifespan), min_samples=1)),
                        (kdstring, round(kd,1),self.db.stat_percentile(hero, "kd_ratio", float(kd), min_samples=1)),
                        ("Kills", killrate,self.db.stat_percentile(hero, "kills_per_10", float(killrate), min_samples=1)),
                        
                        
                        (string, dpm, self.db.stat_percentile(hero, f"{string.lower()}_per_minute", float(dpm), min_samples=1) if role != "Strategist" else self.db.stat_percentile(hero, "healing_per_minute", float(dpm), min_samples=1)),
                        ("Blocked", hero_obj.total_damage_taken_per_minute, self.db.stat_percentile(hero, "total_damage_taken_per_minute", float(hero_obj.total_damage_taken_per_minute), min_samples=1)),
                        
                        
                        #("Assists", hero_obj.assists_per_10),
                        #("Acc", hero_obj.accuracy),
                        #("CritAcc", hero_obj.headshot_accuracy),
                        ("LastKill", hero_obj.last_kills_per_10, False),



                        ]
            
            stats1 = [
                        ("Games",matches_played, False),
                        ("Time", round(total_hero_time_h,1), False),
                        ("Win %", winpct, False),
            ]

            stats2 = [("Kills", hero_obj.avg_kills_per_match,self.db.stat_percentile(hero, "kills_per_10", float(killrate), min_samples=1)),
                      ("Deaths", hero_obj.avg_deaths_per_match,self.db.stat_percentile(hero, "average_lifespan", float(hero_obj.average_lifespan), min_samples=1)),
                      #("Assists", hero_obj.avg_assists_per_match,self.db.stat_percentile(hero, "assists_per_10", float(hero_obj.assists_per_10), min_samples=1)),
                      (string, int(round(hero_obj.avg_damage_per_match if role != "Strategist" else hero_obj.avg_healing_per_match)), self.db.stat_percentile(hero, f"{string.lower()}_per_minute", float(dpm), min_samples=1) if role != "Strategist" else self.db.stat_percentile(hero, "healing_per_minute", float(dpm), min_samples=1)),
                      #("Blocked", int(round(hero_obj.avg_damage_taken_per_match)), self.db.stat_percentile(hero, "total_damage_taken_per_minute", float(hero_obj.total_damage_taken_per_minute), min_samples=1)),
                      ]

            stats3 = [
                        
                        ("Mvp %", mvp, False),
                        #("Usage", usage_pct, False),
                        (kdstring, round(kd,1),self.db.stat_percentile(hero, "kd_ratio", float(kd), min_samples=1)),

            ]
            

            self._hero_stats(parent=hero_bar, hero=hero_obj, stats_frame_size=(s(270), s(110)), 
                             stats=[stats1, stats2,stats3], fonts = [(self.TTSuperCondMedium, 12, "normal"),("TTSupermolotNeueCond-Bd", 12, "bold")])
            
    def _hero_stats(self, parent=None, hero=None, label_orientation="vertical",stats_frame_size=(s(270), s(110)), stats=[], fonts = []):
    # stats canvas
        def split_int(total: int, parts: int) -> list[int]:
            if parts <= 0:
                raise ValueError("parts must be > 0")

            base = total // parts
            remainder = total % parts

            # Distribute remainder (+1) to the first `remainder` parts
            return [base + 1] * remainder + [base] * (parts - remainder)
        
        role = getattr(hero, "role", "")
        x, y = stats_frame_size
        hero_stats = tk.Canvas(
            parent,
            height=y,
            width=x,
            highlightthickness=0,
            bg="#77789E",
        )

        #canTags = ["text", "header", "bg", "games_group", "time_group","]
        hero_stats.pack(side="left", padx=(0, 0), pady=(0, 0), fill="both")

        bg = self._create_canvas_image(
            hero_stats,
            img_key="hero_stats_bg_new2",
            anc="ne",
            tags = "bg",
            size=(377, 144),
            bg=NAME_BANNER,
            x=x,
            y=0,
        )
        hdr = self._create_canvas_image(
            hero_stats,
            img_key="hero_stats_header_right2",
            anc="nw",
            tint_alpha=False,
            tags = "header",
            size=(92, 20),
            bg=NAME_BANNER,
            x=s(x)/2 + s(34) +s(22),#- s(18),
            y=0,
        )

        hdl = self._create_canvas_image(
            hero_stats,
            img_key="hero_stats_header_left2",
            anc="ne",
            tint_alpha=False,
            tags = "header",
            size=(92, 20),
            bg=NAME_BANNER,
            x=s(x)/2 - s(33) + s(12),# - s(18),
            y=0,
        )

        hd = self._create_canvas_image(
            hero_stats,
            img_key="hero_stats_header_small",
            anc="center",
            tags = "header",
            size=(116, 22),
            bg=NAME_BANNER,
            x=s(x)/2,# - s(18),
            y=s(10),
        )

        

        
        heroname = getattr(hero, "heroname", "Unknown")

        hero_name = hero_stats.create_text(s(x/2)-s(6),s(10),tags="header",text=heroname,fill="#FBFCFF",font=fonttk("Refrigerator Deluxe ExtraBold", 11, "bold"),anchor="c")
        _,_,use,_ = self._get_iterative_coordinates(hero_stats, hero_name, padx=0, pady=0)
        flip = (s(x)/2 - use) + s(x)/2 
        r = self._create_canvas_image(
            hero_stats,
            tint_alpha=True,
            img_key=f"{role}_2",
            anc="center",
            tags = "header",
            size=(20, 20),
            bg=NAME_BANNER,
            x= flip, #s(use) - s(10),#s(x)/2 - s(),
            y=s(10),
        )
        left = hero_stats.create_text(s(x/2)-s(90)+s(6),s(10),tags="header",text="Usage",fill="#E9EDFF",font=fonttk("Refrigerator Deluxe ExtraBold", 9, "bold"),anchor="c")
        right = hero_stats.create_text(s(x/2)+s(90)+s(8),s(10),tags="header",text="Per Game Stats",fill="#E9EDFF",font=fonttk("Refrigerator Deluxe ExtraBold", 9, "bold"),anchor="c")

        # _______Final HEADER position adjustment_______#
        hero_stats.move('header',s(-18), 0)
        items_per_col = 5

        rows = 2
        count = 0
        #group_per_col = 5
        #rows = 2
        #row1, row2 = split_int(num_items, rows)
        #horizontal_offset = int(x/row1)
        #vert_offset = int(y/items_per_col) - 1
        font1 = fonts[0]
        font2 = fonts[1]
        font_name_1, font_size_1, font_weight_1 = font1
        font_name_2, font_size_2, font_weight_2 = font2
        font1 = [("TTSupermolotNeueCond-Md", 8, "normal")]#[("Nunito Sans 10pt Condensed Medium", 8, "normal")]
        font2 = [("Refrigerator Deluxe Heavy", 13, "normal")]
        fg_l = "#4A5264"
        fg_v = "#3B3E55"
        self.fg_l = "#434A5A"
        self.fg_v = "#262836"
        starting_x = 4
        starting_y = 2
        stage_2 = 0
        self.RIGHT_MOST = 0
        self.FINAL_RIGHT_MOST = False
        self.FIRST_TEXT = False
        y_start = 18
        x_start = -3
        sep_h = "seperator_horizontal2"
        sep_v = "seperator_vertical2"
        horizontal_sep_size = (64,2)
        vertical_sep_size = (2, 34)
        hsep_y = s(49)
        for label, value, percentile in stats[0]:
        #         la = tk.Label(
        #         hero_stats,
        #         bg="#9badce",
        #         text = label,
        #         font=fonttk(font_name_1, font_size_1, font_weight_1),
        #     relief ="sunken",
        #     borderwidth=1
        # )
            #hero_stats.create_window(s(current_x), s(current_y), window = la, anchor="nw")
            icon_label = label.lower().strip().replace(" %", "")
            icon = self._create_canvas_image(
                hero_stats,
                img_key=icon_label,
                anc="nw",
                size=(27, 27),
                tags=label,
                bg=NAME_BANNER,
                x=s(x_start)+2,
                y=s(y_start)+1,
            )
            # l = hero_stats.create_text(x_start+s(27),s(y_start)+1,text=label if label != "Win %" else "Win",tags=label,fill=self.fg_l,font=fonttk(font1[0][0],font1[0][1],font1[0][2]),anchor="nw")
           
            # x2, y2, x1, y1 = self._get_iterative_coordinates(hero_stats, l, padx=-3, pady=0)
            
            sep = self._create_canvas_image(
                hero_stats,
                img_key=sep_h,
                anc="nw",
                size=(32, 1),
                bg=NAME_BANNER,
                x=s(x_start)+s(20),
                y=hsep_y,
            )
            if label == "Games":
                #self.FIRST_TEXT = l
                sepv = self._create_canvas_image(
                    hero_stats,
                    img_key=sep_v,
                    anc="nw",
                    size=(2, 45),
                    bg=NAME_BANNER,
                    x=s(64),
                    y=s(y_start)+s(38),
                )
            self._setLabelValue_CanvasText1(hero_stats, lab=label, val=value, x=x_start+s(27), y=y_start+1, font1=("TTSupermolotNeueCond-Md", 8, "normal"), font2=("Refrigerator Deluxe Heavy", 13, "normal"), fills=[self.fg_l,self.fg_v], tag=label, anc="sw")
                #print(sep_h,sep)
            y_start += s(31)
            hsep_y += s(31)

            # fg_c = self._get_foreground_color(label, value, True)
            # check = str(value)
            
            # #value = str(value)
            # if "%" in check:
            #     value = check.replace("%", "")

            #     st = hero_stats.create_text(s(x1)-2,s(y2)-5,text=value,tags=label,fill=self.fg_v,font=fonttk(font2[0][0],font2[0][1],font2[0][2]),anchor="nw")
            #     x4, y4, x3, y3 = self._get_iterative_coordinates(hero_stats, st, padx=0, pady=0)

            #     hero_stats.create_text(s(x4),s(y4)-1,text="%",tags=label,fill=self.fg_l,font=fonttk("Refrigerator Deluxe ExtraBold",8,"normal"),anchor="sw")
            # else:
                
            #     vstring1, vstring2 = self.splitValue_PctOrDec(value)
            #     sw_offset = s(20)
            #     print(f"Value: {value}\n\tx:'{s(x1)-2}'\n\ty:'{s(y2)-5}'\n__________________________\n")

            #     st = hero_stats.create_text(s(x1)-2,s(y2)-5 + sw_offset,text=vstring1,tags=label,fill=self.fg_v,font=fonttk(font2[0][0],font2[0][1],font2[0][2]),anchor="sw")
            #     x4, y4, x3, y3 = self._get_iterative_coordinates(hero_stats, st, padx=0, pady=0)
            #     st = hero_stats.create_text(s(x4)-1,s(y2)-5 + sw_offset - 1,text=vstring2,tags=label,fill=self.fg_v,font=fonttk("Refrigerator Deluxe ExtraBold",8,"normal"),anchor="sw")
            # if label == "Time":
            #     strp = "HR" 
            #     x2, y2, x1, y1 = self._get_iterative_coordinates(hero_stats, st, padx=0, pady=0)
            #     hero_stats.create_text(s(x2),s(y2),text=strp,tags=label,fill=self.fg_l,font=fonttk("Refrigerator Deluxe ExtraBold",7,"normal"),anchor="sw")
            # y_start += s(31)


        xtare = s(86)
        ytare = s(78)

        #__Game Average Stat Builder__
        for label, value, percentile in stats[1]:
            
            xtare = self.build_avg_stat_ui(hero_stats, xtare, ytare, label, value, percentile)
        #__KD MVP Etc.__
        for label, value, percentile in stats[2]:
            self.build_stat_uibundle1(hero_stats, label, value, percentile)
        hero_stats.move('mvp', s(73)-s(6)+s(95), s(25)-s(25))
        t = stats[2][1][0].lower()
        print(t)
        hero_stats.move(t, s(130)-s(6)+s(95), s(25)-s(25))
        #hero_stats.move('mvp', s(181)-s(6), s(21)-s(23))
        #hero_stats.move('kd', s(236)-s(24), s(21)-s(23))

    
#######################################################################################

    def _setLabelValue_CanvasText1(
            self, 
            canvas: tk.Canvas, 
            lab: str = None, 
            val: Any | None = None, 
            x: int = 0, 
            y: int = 0, 
            font1: tuple = None, 
            font2: tuple = None,
            fills: list = None, 
            tag: str = None, 
            anc: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"] = ...,
        ):
        fam, siz, wei = font1
        fam2, siz2, wei2 = font2
        l = canvas.create_text(x , y ,text=lab if lab != "Win %" else "Win",tags=tag,fill=fills[0],font=fonttk(fam, siz, wei),anchor="nw")
        x2, y2, x1, y1 = self._get_iterative_coordinates(canvas, l, padx=s(-3), pady=0)
        

        vstring1, vstring2 = self.splitValue_PctOrDec(val)
        
        sw_offset = s(20) if anc == "sw" else s(0)

        #print(f"Value: {value}\n\tx:'{s(x1)-2}'\n\ty:'{s(y2)-5}'\n__________________________\n")

        st = canvas.create_text(s(x1)-s(2),s(y2)-s(5) + sw_offset,text=vstring1,tags=tag,fill=fills[1],font=fonttk(fam2, siz2, wei2),anchor=anc)
        x4, y4, x3, y3 = self._get_iterative_coordinates(canvas, st, padx=0, pady=0)
        st = canvas.create_text(s(x4),s(y2)-s(5) + sw_offset - 1,text=vstring2,tags=tag,fill=fills[1],font=fonttk("Refrigerator Deluxe ExtraBold",8,"normal"),anchor=anc)    
        if lab == "Time":

            strp = "HR" 
            x2, y2, x1, y1 = self._get_iterative_coordinates(canvas, st, padx=0, pady=0)
            canvas.create_text(s(x2),s(y2),text=strp,tags=lab,fill=fills[1],font=fonttk("Refrigerator Deluxe ExtraBold",7,"normal"),anchor=anc)
        

    def _setOnlyValue_CanvasText(
            self, 
            canvas: tk.Canvas, 
             
            val: Any | None = None, 
            x: int = 0, 
            y: int = 0, 
            font: tuple = None, 
            offset: tuple = (0,0),
            fill: str = "#2B2B2B", 
            tag: str = None, 
            anc: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"] = ...,
        ):
        fam, siz, wei = font
        x_offset, y_offset = offset
        val_1 , val_2 = self.splitValue_PctOrDec(val)
        st = canvas.create_text(s(x)+s(x_offset),s(y)+s(y_offset),text=val_1,tags=tag,fill=fill,font=fonttk(fam, siz, wei),anchor=anc)
        x2, y2, x1, y1 = self._get_iterative_coordinates(canvas, st, padx=0, pady=0)
        canvas.create_text(s(x1),s(y2),text=val_2,tags=tag,fill=fill,font=fonttk("Refrigerator Deluxe ExtraBold",8,"normal"),anchor=anc)

    def splitValue_PctOrDec(self,value):
        try:
            s = str(value).strip()

            # Handle percent
            percent = ''
            if s.endswith('%'):
                percent = '%'
                s = s[:-1]

            # Handle decimal
            if '.' in s:
                whole, decimal = s.split('.', 1)
                return whole, '.' + decimal + percent

            return s, percent
        except (ValueError, TypeError):
            return value, ''  # Return original value and empty percent if conversion fails
        

    def build_avg_stat_ui(self,p, x, y, label, value, percentile):
        icon = self._create_canvas_image(
                p,
                img_key=label.lower(),
                anc="center",
                size=(24, 24),
                tags=label,
                bg=NAME_BANNER,
                x=x,
                y=y+5,
            )
        ft_size = 12
        fg= self._get_foreground_color(label, value, True) if percentile is not False else self.fg_v
        if label.lower() in ['blocked', 'damage', 'healing']:
            ft_size = 10
        l = p.create_text(x,s(64),text=label,fill=self.fg_l,tags=label,font=fonttk("TTSupermolotNeueCond-Md", 8, "normal"),anchor="center")
        vsplit1, vsplit2 = self.splitValue_PctOrDec(value)
        multiplier = min(len(vsplit1),3) if vsplit2 != '' else 0
        xOffset = s(-5) + multiplier*s(2) if vsplit2 != '' else 0

        v = p.create_text(x+s(xOffset),s(100),text=vsplit1,tags=label,fill=fg,font=fonttk("Refrigerator Deluxe ExtraBold", ft_size, "normal"),anchor="center")
        x2, y2, x1, y1 = self._get_iterative_coordinates(p, v, padx=0, pady=0)
        p.create_text(s(x2)-1,s(y2)-s(1),text=vsplit2,tags=label,fill=fg,font=fonttk("Refrigerator Deluxe ExtraBold", 8, "normal"),anchor="sw")
        x += s(40)
        return x 
    
    def build_stat_uibundle1(self, parent: tk.Canvas,  label: str, value: str | int, pctile: float | bool):
        y_start = 25
        x_start = -3
        icon_label = label.lower().strip().replace(" %", "")
        icon = self._create_canvas_image(
            parent,
            img_key=icon_label,
            anc="nw",
            size=(27, 27),
            tags=icon_label,
            bg=NAME_BANNER,
            x=s(x_start),
            y=s(y_start),
        )
        
        l = parent.create_text(x_start+s(27),s(y_start)+1,text=label if label != "Mvp %" else "Mvp",tags=icon_label,fill=self.fg_l,font=fonttk("TTSupermolotNeueCond-Md", 8, "normal"),anchor="nw")
        
        x2, y2, x1, y1 = self._get_iterative_coordinates(parent, l, padx=-3, pady=0)

        
        check = str(value)
            
        #value = str(value)
        if "%" in check:
            value = check.replace("%", "")
            st = parent.create_text(s(x1)-2,s(y2)-5,text=value,tags=icon_label,fill=self.fg_v,font=fonttk("Refrigerator Deluxe Heavy", 13, "normal"),anchor="nw")
            x4, y4, x3, y3 = self._get_iterative_coordinates(parent, st, padx=0, pady=0)
            parent.create_text(s(x4),s(y4)-2,text="%",tags=icon_label,fill=self.fg_l,font=fonttk("Refrigerator Deluxe ExtraBold",8,"normal"),anchor="sw")
        else:
            st = parent.create_text(s(x1)-2,s(y2)-5,text=value,tags=icon_label,fill=self.fg_v,font=fonttk("Refrigerator Deluxe Heavy", 13, "normal"),anchor="nw")
        if label == "Time":
            strp = "HR" 
            x2, y2, x1, y1 = self._get_iterative_coordinates(parent, st, padx=0, pady=0)
            parent.create_text(s(x2),s(y2)-1,text=strp,tags=icon_label,fill=self.fg_l,font=fonttk("Refrigerator Deluxe ExtraBold",7,"normal"),anchor="sw")
        # fg_c = self._get_foreground_color(label, value, True)
        # st = parent.create_text(s(x1)-2,s(y2)-4,text=value,tags=icon_label,fill="#3B3E55",font=fonttk("Refrigerator Deluxe Heavy", 13, "normal"),anchor="nw")
        # if label == "Time":
        #     str = "HR" 
        #     x2, y2, x1, y1 = self._get_iterative_coordinates(parent, st, padx=0, pady=0)
        #     parent.create_text(s(x2),s(y2)-1,text=str,tags=icon_label,fill="#434760",font=fonttk("Refrigerator Deluxe ExtraBold",7,"normal"),anchor="sw")
            




    def _hero_stats_WORKING_UI(self, parent=None, hero=None, label_orientation="vertical",stats_frame_size=(s(270), s(110)), stats=[], fonts = []):
    # stats canvas
                    

            

        #     endx, endy, startx, starty = self._get_iterative_coordinates(hero_stats, st, padx=6, pady=0)
        #     if not self.FINAL_RIGHT_MOST:
        #         ending_x = self._get_end_x_coord(hero_stats, st)
        #         self.RIGHT_MOST = max(self.RIGHT_MOST, ending_x)
        #         if self.RIGHT_MOST == ending_x:
        #             self.VALUE = value
        #             self.LABEL = label
        #         print(f"Value: {value}, Ending X: {ending_x}, Current Right Most: {self.RIGHT_MOST}")
        #     if percentile:
        #         pct_overlay = 53
        #         p = f"{round(percentile,1)}%" if percentile < 10 else f"{int(round(percentile,0))}%"
        #         db_img = self._get_foreground_color("db_img", p, True)
                
        #         st_pct = hero_stats.create_text(s(endx),s(starting_y+3),text=p,fill="#313131",font=fonttk("TT Sprmlt N Trl Cnd", 8, "underline", italic=True),anchor="nw",tags="text")
        #         endx2, endy2, startx2, starty2 = self._get_iterative_coordinates(hero_stats, st_pct, padx=7, pady=0)

        #         #hero_stats.create_text(s(current_x+pct_padx),s(current_y+vert_offset-1),text=p,fill="#2B2B2B",font=fonttk("Saira Condensed Thin", 8, "italic"),anchor="nw",)
        #         self._create_canvas_image(
        #                 hero_stats,
        #                 img_key=db_img,
        #                 anc="ne",
        #                 tags="text",
        #                 size=(11, 8),
        #                 bg=NAME_BANNER,
        #                 x=endx2+5,
        #                 y=starting_y+4,
        #             )
        #         pct_overlay = 53 if endx2 - endx < 45 else 60
        #         #widt = (endx2 - 4) - (startx+3)
        #         widt = (endx2 + 11 - 5) - (endx - 6 + 2)
        #         #print(widt)
        #         #size = (54, 15) if pct_overlay == 53 else (63, 15)
        #         size = (widt, 15) if pct_overlay == 53 else (widt, 15)
        #         pct_img = f"_pct{pct_overlay}"
        #         self._create_canvas_image(
        #             hero_stats,
        #             img_key=pct_img,
        #             anc="nw",
        #             tags="text",
        #             size=size,
        #             bg="#FFFFFF",
        #             x=endx - 2,
        #             y=starting_y+1,
        #             tint_alpha=True,
        #         )
        #     count += 1

            
            

        #     if count == items_per_col:
        #         starting_x += endx + 55
        #         count = 0
        #         starting_y = 2
        #         stage_2 = 3
        #         if not self.FINAL_RIGHT_MOST:
        #             self.FINAL_RIGHT_MOST = self.RIGHT_MOST
        #             print(f"*------Label: {self.LABEL}, Value: {self.VALUE}, FINAL Right Most: {self.FINAL_RIGHT_MOST}")
        #     else:
        #         starting_y =y1-1 
        # w = self.FINAL_RIGHT_MOST + 1
        # gri = self._create_canvas_image(
        #                 hero_stats,
        #                 img_key="_hero_stats_grid_thin8",
        #                 anc="nw",
        #                 tags="grid",
        #                 size=(w, 104),
        #                 bg=NAME_BANNER,
        #                 x=1,
        #                 y=2,
        #             )
        # hero_stats.tag_lower("grid", "text")
        def split_int(total: int, parts: int) -> list[int]:
            if parts <= 0:
                raise ValueError("parts must be > 0")

            base = total // parts
            remainder = total % parts

            # Distribute remainder (+1) to the first `remainder` parts
            return [base + 1] * remainder + [base] * (parts - remainder)
        

        x, y = stats_frame_size
        hero_stats = tk.Canvas(
            parent,
            height=y,
            width=x,
            highlightthickness=0,
            bg="#77789E",
        )
        hero_stats.pack(side="left", padx=(0, 0), pady=(0, 0), fill="both")

        bg = self._create_canvas_image(
            hero_stats,
            img_key="hero_stat_bg",
            anc="ne",
            tags = "bg",
            size=(380, 126),
            bg=NAME_BANNER,
            x=270,
            y=0,
        )

        items_per_col = 5
        rows = 2
        count = 0
        #group_per_col = 5
        #rows = 2
        #row1, row2 = split_int(num_items, rows)
        #horizontal_offset = int(x/row1)
        #vert_offset = int(y/items_per_col) - 1
        font1 = fonts[0]
        font2 = fonts[1]
        font_name_1, font_size_1, font_weight_1 = font1
        font_name_2, font_size_2, font_weight_2 = font2
        starting_x = 4
        starting_y = 2
        stage_2 = 0
        self.RIGHT_MOST = 0
        self.FINAL_RIGHT_MOST = False
        self.FIRST_TEXT = False
        
        for label, value, percentile in stats:
        #         la = tk.Label(
        #         hero_stats,
        #         bg="#9badce",
        #         text = label,
        #         font=fonttk(font_name_1, font_size_1, font_weight_1),
        #     relief ="sunken",
        #     borderwidth=1
        # )
            #hero_stats.create_window(s(current_x), s(current_y), window = la, anchor="nw")
            
            l = hero_stats.create_text(s(starting_x),s(starting_y),text=label,fill="#2B2B2B",font=fonttk(font_name_1, font_size_1, font_weight_1),anchor="nw",tags="text")
            if not self.FIRST_TEXT:
                self.FIRST_TEXT = l
            x1, y1, x2, y2 = self._get_iterative_coordinates(hero_stats, l, padx=6, pady=3)

            fg_c = self._get_foreground_color(label, value, True)
            st = hero_stats.create_text(s(starting_x)+50+ stage_2,s(starting_y),text=value,fill=fg_c,font=fonttk(font_name_2, font_size_2, font_weight_2),anchor="nw",tags="text")
            endx, endy, startx, starty = self._get_iterative_coordinates(hero_stats, st, padx=6, pady=0)
            if not self.FINAL_RIGHT_MOST:
                ending_x = self._get_end_x_coord(hero_stats, st)
                self.RIGHT_MOST = max(self.RIGHT_MOST, ending_x)
                if self.RIGHT_MOST == ending_x:
                    self.VALUE = value
                    self.LABEL = label
                print(f"Value: {value}, Ending X: {ending_x}, Current Right Most: {self.RIGHT_MOST}")
            if percentile:
                pct_overlay = 53
                p = f"{round(percentile,1)}%" if percentile < 10 else f"{int(round(percentile,0))}%"
                db_img = self._get_foreground_color("db_img", p, True)
                
                st_pct = hero_stats.create_text(s(endx),s(starting_y+3),text=p,fill="#313131",font=fonttk("TT Sprmlt N Trl Cnd", 8, "underline", italic=True),anchor="nw",tags="text")
                endx2, endy2, startx2, starty2 = self._get_iterative_coordinates(hero_stats, st_pct, padx=7, pady=0)

                #hero_stats.create_text(s(current_x+pct_padx),s(current_y+vert_offset-1),text=p,fill="#2B2B2B",font=fonttk("Saira Condensed Thin", 8, "italic"),anchor="nw",)
                self._create_canvas_image(
                        hero_stats,
                        img_key=db_img,
                        anc="ne",
                        tags="text",
                        size=(11, 8),
                        bg=NAME_BANNER,
                        x=endx2+5,
                        y=starting_y+4,
                    )
                pct_overlay = 53 if endx2 - endx < 45 else 60
                #widt = (endx2 - 4) - (startx+3)
                widt = (endx2 + 11 - 5) - (endx - 6 + 2)
                #print(widt)
                #size = (54, 15) if pct_overlay == 53 else (63, 15)
                size = (widt, 15) if pct_overlay == 53 else (widt, 15)
                pct_img = f"_pct{pct_overlay}"
                self._create_canvas_image(
                    hero_stats,
                    img_key=pct_img,
                    anc="nw",
                    tags="text",
                    size=size,
                    bg="#FFFFFF",
                    x=endx - 2,
                    y=starting_y+1,
                    tint_alpha=True,
                )
            count += 1

            
            

            if count == items_per_col:
                starting_x += endx + 55
                count = 0
                starting_y = 2
                stage_2 = 3
                if not self.FINAL_RIGHT_MOST:
                    self.FINAL_RIGHT_MOST = self.RIGHT_MOST
                    print(f"*------Label: {self.LABEL}, Value: {self.VALUE}, FINAL Right Most: {self.FINAL_RIGHT_MOST}")
            else:
                starting_y =y1-1 
        w = self.FINAL_RIGHT_MOST + 1
        gri = self._create_canvas_image(
                        hero_stats,
                        img_key="_hero_stats_grid_thin8",
                        anc="nw",
                        tags="grid",
                        size=(w, 104),
                        bg=NAME_BANNER,
                        x=1,
                        y=2,
                    )
        hero_stats.tag_lower("grid", "text")

    def _hero_stats_under(self, parent=None, hero=None, stats_frame_size=(s(270), s(110)), stats=[], fonts = []):
    # stats canvas
        def split_int(total: int, parts: int) -> list[int]:
            if parts <= 0:
                raise ValueError("parts must be > 0")

            base = total // parts
            remainder = total % parts

            # Distribute remainder (+1) to the first `remainder` parts
            return [base + 1] * remainder + [base] * (parts - remainder)
        

        x, y = stats_frame_size
        hero_stats = tk.Canvas(
            parent,
            height=y,
            width=x,
            highlightthickness=0,
            bg="#77789E",
        )
        hero_stats.pack(side="left", padx=(0, 0), pady=(0, 0), fill="both")

        self._create_canvas_image(
            hero_stats,
            img_key="hero_stat_bg",
            anc="ne",
            size=(380, 126),
            bg=NAME_BANNER,
            x=270,
            y=0,
        )

        items_per_col = 6
        group_per_col = 3
        #rows = 2
        #row1, row2 = split_int(num_items, rows)
        #horizontal_offset = int(x/row1)
        vert_offset = int(y/items_per_col) - 1
        font1 = fonts[0]
        font2 = fonts[1]
        font_name_1, font_size_1, font_weight_1 = font1
        font_name_2, font_size_2, font_weight_2 = font2
        
        padding_x = 4
        padding_y = 1
        current_x = padding_x
        current_y = padding_y
        count = 0
        pct_padx = 32
        for label, value, percentile in stats:
        #         la = tk.Label(
        #         hero_stats,
        #         bg="#9badce",
        #         text = label,
        #         font=fonttk(font_name_1, font_size_1, font_weight_1),
        #     relief ="sunken",
        #     borderwidth=1
        # )
            #hero_stats.create_window(s(current_x), s(current_y), window = la, anchor="nw")
            
            hero_stats.create_text(s(current_x),s(current_y),text=label,fill="#2B2B2B",font=fonttk(font_name_1, font_size_1, font_weight_1),anchor="nw",)
            fg_c = self._get_foreground_color(label, value, True)
            st = hero_stats.create_text(s(current_x),s(current_y+vert_offset-3),text=value,fill=fg_c,font=fonttk(font_name_2, font_size_2, font_weight_2),anchor="nw",)
            if percentile:
                pct_overlay = 53
                p = f"{round(percentile,1)}%" if percentile < 100 else f"100%"
                db_img = self._get_foreground_color("db_img", p, True)
                endx, endy, startx, starty = self._get_iterative_coordinates(hero_stats, st, padx=6, pady=0)
                st_pct = hero_stats.create_text(s(endx),s(current_y+vert_offset+1),text=p,fill="#313131",font=fonttk("Rajdhani Medium", 8, "underline", italic=True),anchor="nw",)
                endx2, endy2, startx2, starty2 = self._get_iterative_coordinates(hero_stats, st_pct, padx=7, pady=0)

                #hero_stats.create_text(s(current_x+pct_padx),s(current_y+vert_offset-1),text=p,fill="#2B2B2B",font=fonttk("Saira Condensed Thin", 8, "italic"),anchor="nw",)
                self._create_canvas_image(
                        hero_stats,
                        img_key=db_img,
                        anc="ne",
                        size=(11, 8),
                        bg=NAME_BANNER,
                        x=endx2+5,
                        y=current_y+vert_offset+3,
                    )
                pct_overlay = 53 if endx2 - endx < 45 else 60
                #widt = (endx2 - 4) - (startx+3)
                widt = (endx2 + 11 - 5) - (endx - 6 + 2)
                #print(widt)
                #size = (54, 15) if pct_overlay == 53 else (63, 15)
                size = (widt, 15) if pct_overlay == 53 else (widt, 15)
                pct_img = f"_pct{pct_overlay}"
                self._create_canvas_image(
                    hero_stats,
                    img_key=pct_img,
                    anc="nw",
                    size=size,
                    bg="#FFFFFF",
                    x=endx - 2,
                    y=current_y+vert_offset-1,
                    tint_alpha=True,
                )
            count += 1

            
            

            if count == group_per_col or count == 6:
                if current_x > 60:
                    current_x += 15
                current_x += 66
                
                current_y = padding_y
                #pct_padx += 5
            else:
                current_y += vert_offset*2+3
                
        def gui_stats_horizontal_layout():
            items_per_col = 6
            group_per_col = 3
            #rows = 2
            #row1, row2 = split_int(num_items, rows)
            #horizontal_offset = int(x/row1)
            vert_offset = int(y/items_per_col) - 1
            font1 = fonts[0]
            font2 = fonts[1]
            font_name_1, font_size_1, font_weight_1 = font1
            font_name_2, font_size_2, font_weight_2 = font2
            
            padding_x = 10
            padding_y = 1
            current_x = padding_x
            current_y = padding_y
            count = 0
            pct_padx = 32
            for label, value, percentile in stats:
            #         la = tk.Label(
            #         hero_stats,
            #         bg="#9badce",
            #         text = label,
            #         font=fonttk(font_name_1, font_size_1, font_weight_1),
            #     relief ="sunken",
            #     borderwidth=1
            # )
                #hero_stats.create_window(s(current_x), s(current_y), window = la, anchor="nw")
                hero_stats.create_text(s(current_x),s(current_y),text=label,fill="#2B2B2B",font=fonttk(font_name_1, font_size_1, font_weight_1),anchor="nw",)
                fg_c = self._get_foreground_color(label, value, True)
                hero_stats.create_text(s(current_x),s(current_y+vert_offset-3),text=value,fill=fg_c,font=fonttk(font_name_2, font_size_2, font_weight_2),anchor="nw",)
                if percentile:
                    p = f"{round(percentile,1)}%" if percentile < 100 else f"100%"
                    db_img = self._get_foreground_color("db_img", p, True)
                    
                    hero_stats.create_text(s(current_x+pct_padx),s(current_y+vert_offset-1),text=p,fill="#2B2B2B",font=fonttk("Saira Condensed Thin", 8, "italic"),anchor="nw",)
                    self._create_canvas_image(
                            hero_stats,
                            img_key=db_img,
                            anc="ne",
                            size=(12, 9),
                            bg=NAME_BANNER,
                            x=current_x+pct_padx+37,
                            y=current_y+vert_offset+2,
                        )
                count += 1
                if count == group_per_col or count == 6:
                    current_x += 80
                    current_y = padding_y
                    #pct_padx += 5
                else:
                    current_y += vert_offset*2+3

        def gui_stats_horizontal_layout():
                    items_per_col = 5
                    #rows = 2
                    #row1, row2 = split_int(num_items, rows)
                    #horizontal_offset = int(x/row1)
                    vert_offset = int(y/items_per_col) - 1
                    font1 = fonts[0]
                    font2 = fonts[1]
                    font_name_1, font_size_1, font_weight_1 = font1
                    font_name_2, font_size_2, font_weight_2 = font2
                    
                    padding_x = 5
                    padding_y = 1
                    current_x = padding_x
                    current_y = padding_y
                    count = 0
                    pct_padx = 32
                    for label, value, percentile in stats:
                    #         la = tk.Label(
                    #         hero_stats,
                    #         bg="#9badce",
                    #         text = label,
                    #         font=fonttk(font_name_1, font_size_1, font_weight_1),
                    #     relief ="sunken",
                    #     borderwidth=1
                    # )
                        #hero_stats.create_window(s(current_x), s(current_y), window = la, anchor="nw")
                        hero_stats.create_text(s(current_x),s(current_y),text=label,fill="#2B2B2B",font=fonttk(font_name_1, font_size_1, font_weight_1),anchor="nw",)
                        fg_c = self._get_foreground_color(label, value, True)
                        hero_stats.create_text(s(current_x+58),s(current_y),text=value,fill=fg_c,font=fonttk(font_name_2, font_size_2, font_weight_2),anchor="nw",)
                        if percentile:
                            p = f"{round(percentile,1)}%" if percentile < 100 else f"100%"
                            db_img = self._get_foreground_color("db_img", p, True)
                            
                            hero_stats.create_text(s(current_x+58+pct_padx),s(current_y+2),text=p,fill="#2B2B2B",font=fonttk("Nunito Sans 10pt Condensed Medium", 8, "italic"),anchor="nw",)
                            self._create_canvas_image(
                                    hero_stats,
                                    img_key=db_img,
                                    anc="ne",
                                    size=(12, 9),
                                    bg=NAME_BANNER,
                                    x=current_x+58+pct_padx+40,
                                    y=current_y+4,
                                )
                        count += 1
                        if count == items_per_col or count == items_per_col *2:
                            current_x = padding_x + 130
                            current_y = padding_y
                            pct_padx += 5
                        else:
                            current_y += vert_offset







        # horizontal_offset = 
        # la = tk.Label(
        #     hero_stats,
        #     bg="#bccbe6",
        #     text = "Matches",
        #     font=fonttk("Refrigerator Deluxe", 11, "bold"),
        #     relief ="sunken",
        #     borderwidth=1
        # )
        # la2 = tk.Label(
        #     hero_stats,
        #     bg="#bccbe6",
        #     text = "Usage",
        #     font=fonttk("Refrigerator Deluxe", 11, "bold"),
        #     relief ="sunken",
        #     borderwidth=1
        # )

        # la3 = tk.Label(
        #     hero_stats,
        #     bg="#bccbe6",
        #     text = "Win %",
        #     font=fonttk("Refrigerator Deluxe", 11, "bold"),
        #     relief ="sunken",
        #     borderwidth=1
        # )

        # la4 = tk.Label(
        #     hero_stats,
        #     bg="#bccbe6",
        #     text = "Mvp %",
        #     font=fonttk("Refrigerator Deluxe", 11, "bold"),
        #     relief ="sunken",
        #     borderwidth=1
        # )


        
        
        # hero_stats.create_window(s(10), s(5), window = la, anchor="nw")
        # hero_stats.create_window(s(65), s(5), window = la2, anchor="nw")
        # hero_stats.create_window(s(110), s(5), window = la3, anchor="nw")
        # hero_stats.create_window(s(10), s(54), window = la4, anchor="nw")
        # usage = hero
        # fgm = self._get_foreground_color("Matches", matches_played)
        # fgu = self._get_foreground_color("Usage", usage_pct)
        # fgwin = self._get_foreground_color("Win %", winpct)
        # fgMvp = self._get_foreground_color("Mvp %", mvp)
        # hero_stats.create_text(s(65+30),s(30),text=usage_pct,fill=fgu,font=fonttk("Refrigerator Deluxe", 14, "bold"),anchor="ne",)
        # hero_stats.create_text(s(10+30),s(30),text=matches_played,fill=fgm,font=fonttk("Refrigerator Deluxe", 14, "bold"),anchor="ne",)

        # role_key = (role + "_G") if role else "Unknown"
        # self._create_canvas_image(hero_stats, img_key=role_key, size=(30, 30), x=200, y=24)

        # ssize = 11 if len(hero) >= 13 else 14
            # hero_stats.create_text(
            #     s(217),
            #     s(10),
            #     text=hero,
            #     fill="#2B2B2B",
            #     font=fonttk("Refrigerator Deluxe ExtraBold", ssize, "normal"),
            #     anchor="c",
            # )
            # hero_stats.create_text(
            #     s(214),
            #     s(94),
            #     text=score,
            #     fill="#2B2B2B",
            #     font=fonttk("Refrigerator Deluxe ExtraBold", 13, "normal"),
            #     anchor="c",
            # )

            # if hero == getattr(self.player, "best_hero", None):
            #     self._create_canvas_image(
            #         hero_stats,
            #         img_key="MVP2",
            #         size=(49, 21),
            #         bg="#1C2127",
            #         x=188,
            #         y=60,
            #     )

            # stats = [
            #     ("Matches", int(matches_played)),
            #     ("Usage", usage_pct),
            #     (string, dpm),
            #     (kdstring, kd),
            #     ("Mvp%", mvp),
            #     ("Win%", winpct),
            #     ("K/10min", killrate)
            # ]

            # xxx = 22
            # yyy = 10
            # yyy2 = 22
            # count = 0
            # for label, value in stats:
            #     if count in [3, 6]:
            #         yyy += 29
            #         yyy2 += 29
            #         xxx = 22
            #         count = 0

            #     fg_color = self._get_foreground_color(label, value)
            #     hero_stats.create_text(
            #         s(xxx),
            #         s(yyy),
            #         text=label,
            #         fill="#2B2B2B",
            #         font=fonttk("Refrigerator Deluxe", 11, "bold"),
            #         anchor="c",
            #     )
            #     hero_stats.create_text(
            #         s(xxx),
            #         s(yyy2),
            #         text=value,
            #         fill=fg_color,
            #         font=fonttk("Refrigerator Deluxe", 11, "bold"),
            #         anchor="c",
            #     )

            #     xxx += 43
            #     count += 1

    # ---------------------------
    # HISTORY (outer -> history_frame + rows)
    # ---------------------------
    def _build_history(self):
        NAME_BANNER = "#24212B"

        matches = self.matches
        history_h = s(35) * len(matches)

        history_frame = tk.Frame(
            self.outer,
            bg=NAME_BANNER,
            width=s(380),
            height=history_h,
            relief="flat",
            borderwidth=0,
        )
        history_frame.pack(side="top", fill="both", pady=(10, 0))
        history_frame.pack_propagate(False)

        amt = 0
        for match in matches:
            if amt > 7:  # max 8 rows
                break
            amt += 1

            scores = match.scores
            result = match.result
            mvp_str = match.isMvp
            svp_str = match.isSvp
            heroes = match.heroes_used
            kills = match.kills
            deaths = match.deaths
            assists = match.assists

            if mvp_str:
                mvp_string, saa = "MVP2", 48
            elif svp_str:
                mvp_string, saa = "SVP", 42
            else:
                mvp_string, saa = None, 0

            if result == "win":
                bg, outline, pic = "#26393C", "#5DE48E", "winbg"
            else:
                bg, outline, pic = "#40272D", "#DD475C", "losebg"

            match_frame = tk.Frame(
                history_frame,
                bg=outline,
                width=s(375),
                height=s(35),
                relief="raised",
                borderwidth=1,
            )
            match_frame.pack(side="top", anchor="c", pady=(4, 4), padx=(4, 4), fill="both")
            match_frame.pack_propagate(False)

            match_canvas = tk.Canvas(
                match_frame,
                height=s(35),
                width=s(375),
                highlightthickness=0,
                bg=bg,
            )
            match_canvas.pack(anchor="center", fill="both")
            match_canvas.pack_propagate(False)

            self._create_canvas_image(match_canvas, img_key=pic, anc="nw", size=(376, 77), bg=bg, x=0, y=0)

            if mvp_string:
                self._create_canvas_image(
                    match_canvas,
                    img_key=mvp_string,
                    anc="center",
                    size=(saa, 20),
                    bg=bg,
                    x=28,
                    y=22,
                )

            one = (30, 30)
            plus = 30
            x = 75
            y = 21

            match_canvas.create_text(
                s(70), s(10),
                text="Score",
                fill="#71C0EE",
                font=fonttk("Rajdhani Medium", 12, "normal"),
                anchor="c",
            )
            match_canvas.create_text(
                s(69), s(30),
                text=f"{scores[0]}:{scores[1]}",
                fill="#D5D9E4",
                font=fonttk("Rajdhani Bold", 12, "normal"),
                anchor="c",
            )

            x += 45
            count = 0
            for hero in heroes:
                if count > 2:
                    break
                count += 1
                self._create_canvas_image(match_canvas, img_key=hero, anc="center", size=one, x=x, y=y, mask=True)
                x += plus
                one = (20, 20)
                plus = 20

            if len(heroes) < 1:
                self._create_canvas_image(match_canvas, img_key="Unknown", anc="center", size=one, x=x, y=y, mask=True)

            icons = {"match_kill": kills, "match_death": deaths, "match_assist": assists}
            x = 205
            for icon, value in icons.items():
                self._create_canvas_image(match_canvas, img_key=icon, anc="nw", size=(22, 22), x=x, y=0)
                match_canvas.create_text(
                    s(x + 9),
                    s(30),
                    text=value,
                    fill="#D5D9E4",
                    font=fonttk("Rajdhani Bold", 12, "normal"),
                    anchor="c",
                )
                x += 40


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
        #if not config.mobile_mode:
            #loaded_paths, families = call_register_fonts(self.root)

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

            self.hotkey_f8_id = keyboard.add_hotkey('f8', lambda: self.root.after(0, lambda: trigger1(self.var1.get(),self.tvar.get())))

        # main button (your bans trigger)
        fra = tk.Frame(main, bg="#151426", relief="solid", height=33, width=210)
        fra.pack(side="left", expand=True)
        fra.pack_propagate(False)

        button = tk.Button(
            fra,
            text="Bans F8", height=1, state="normal",
            relief="flat", bg="#FCD92E",
            font=fonttk("Rajdhani Medium", 'normal', 12),
            command=lambda: trigger1(self.var1.get(), self.tvar.get()),
            cursor="hand2"
        )

        # button2 = tk.Button(
        #     fra,
        #     text="Search", state="normal",
        #     relief="flat", bg="#FCD92E",
        #     font=fonttk("Rajdhani Medium", 'normal', 12),
        #     command=lambda: lookup(tvar.get()),
        #     cursor="hand2"
        # )
        self.tvar = tk.StringVar()
        self.tvar.set("Search by Name(s)")
        entry = tk.Entry(fra, textvariable=self.tvar,  highlightthickness=1, highlightcolor="#FCD92E",bg="#C8C7D4", width = 15,fg="#151426", relief="flat", font=fonttk("Rajdhani", 'normal', 10), justify="center")
        
        button.pack(side="left",padx=(5,5),expand=True)
        
        entry.pack(side="left",ipady=5,expand=True)
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
    def build_match_overview(self, parent, players):
        global NAMEPLATES
        NAMEPLATES = []

        self.root.title("Match Overview")

        width = len(players) * s(380)
        he = 12 if SCALE != 1 else 0
        h = s(1040) + he
        w = s(len(players) * 380)
        h = s(1040) + (12 if SCALE != 1 else 0)

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
            PlayerFrame(player_frames, player).build()
            #create_player_frame(player_frames, player)
        print(f"Created player frames in {time.perf_counter() - t:.2f} seconds.")
        

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

        print(f">> Script running. Press F8 to OCR names and check tracker.gg...")
        search_by_name = True if tvar_value and tvar_value != "Search by Name(s)" else False
        initialize_hide_pass(None, None, None,None)
        
        if search_by_name:
            names = [name.strip() for name in tvar_value.split(",") if name.strip()]
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
            tracker_data = open_multiple_tracker_profiles(names)
        if not config.debug_mode and MANUAL_DEBUG != 69:
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
    global icon_idx
    icon_idx =0
    app = App(BASE_DPI_SCALE)
    app.run()
        