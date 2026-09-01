

import tkinter as tk
import config
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab,  ImageDraw, ImageChops,ImageOps
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
bLiveDebug = False
bUseRivalsDataNames = True
if bUseRivalsDataNames:
    import curlRivals



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

class SpriteSheetAnimator:
    def __init__(
        self,
        master,
        hero,
        animated=True,              # NEW
        sheet_path=None,            # for animated
        rows=10,##
        cols=6,
        fps=24,
        badge=False,
        frame=False,
        scale=1,
        bg="#77789E",
        relief="sunken",
        borderwidth=1,
        size=None,
        bSubCrop=False,
        frame_height = 90,
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
        self.badge = badge
        self.frame = frame
        self.fps = fps
        self.delay_ms = int(1000 / fps) if fps else 0
        self.scale = scale
        self.rows = rows
        self.cols = cols
        self.size = size
        self.bSubCrop = bSubCrop
        self.running = False
        frame_height = frame_height if frame_height else 90
        # --- your existing vars ---
        self.colors = ['blue', 'green', 'pink', 'purple', 'white']
        self.herobg = "heromasterybg_"
        self.scaling_frame = int(frame_height / 90)
        self.image_sizeX = frame_height - 2
        self.image_sizeY = frame_height - 2
        # If you have crop_cache logic, keep it (only matters for animated sheets)
        sheet_key = self.hero + "_Master.png"
        if self.animated and sheet_key in crop_cache:
            prev = crop_cache[sheet_key]
            self.subcrop_x = int(prev["x0"])
            self.subcrop_y = int(prev["y0"])
            self.subcrop_w = int(prev["side"])
            self.subcrop_h = int(prev["side"])
            self.bSubCrop = True
            self.size = (s(frame_height), s(frame_height))

        # --- wrapper + canvas (same for both) ---
        icon_wrap = tk.Frame(master, width=s(frame_height), height=s(frame_height), bg=bg,padx=0, pady=0)
        icon_wrap.pack(side="bottom",anchor="sw",pady=(0,0),padx=(0,0))
        icon_wrap.pack_propagate(False)

        self.canvas = tk.Canvas(
            icon_wrap,
            width=s(frame_height-3),
            height=s((frame_height-3)),
            bg=bg,
            highlightthickness=0,
            bd=borderwidth,
            relief=relief
        )
        self.canvas.pack(fill="both",side ="bottom",anchor="sw", expand=False,padx=0, pady=0)
        self.canvas.pack_propagate(False)

        # center + offsets
        dx, dy = HERO_MASTERY_OFFSETS.get(self.hero, (0, 0))
        cx, cy = s(frame_height // 2), s(frame_height // 2)
        self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite")  # keep reference!
        self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")

        # optional special BG
        self.hero_bg_colored = None
        self.hero_bg_id = None
        if bSpecialBG:
            import random
            random_color = random.choice(self.colors)
            bg_name = self.herobg + random_color
            #self.hero_bg_colored = self.createOnlyImage(bg_name, size=(233, 104))

            self.hero_bg_id = self.canvas.create_image(s(frame_height // 2), s(frame_height // 2), image=self.hero_bg_colored, anchor="c")

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
                
                self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite", size=(frame_height-1, frame_height-1))  # keep reference!
                self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")
                self.static_img = self.createOnlyImage(static_icon, size=(self.image_sizeX, self.image_sizeY))
                if self.frame:
                    frame_ne = f"_prof_frame_{self.frame}4"
                    self.frame_ne_img = self.createOnlyImage(frame_ne, size=(s(190*self.scaling_frame), s(82*self.scaling_frame)))
                    self.frame_ne_id = self.canvas.create_image(s(frame_height), s(-1), tags=["frame"],image=self.frame_ne_img, anchor="ne")
                
                self.image_id = self.canvas.create_image(
                    cx + s(dx), cy + s(dy),
                    image=self.static_img,
                    anchor="center",
                    tags=["icon"]
                )

                if self.frame:
                    frame_sw = f"_prof_frame_{self.frame}12"
                    self.frame_sw_img = self.createOnlyImage(frame_sw, size=(s(190*self.scaling_frame), s(85*self.scaling_frame)))
                    self.frame_sw_id = self.canvas.create_image(s(0), s(frame_height-1), image=self.frame_sw_img, tags=["frame"],anchor="sw")

                if self.badge:
                    pass
                    
                    add = -2 if self.badge == 3 else 0
                    add = -4 if self.badge == 4 else add
                    
                    badge_name = f"_prof_badge{self.badge}"
                    self.badge_img = self.createOnlyImage(badge_name, bNearest=False, size=(s(37+add), s(37+add)))
                    self.badge_id = self.canvas.create_image(s(14), s(frame_height -13), image=self.badge_img, anchor="center")
                    #self.badge_id = self.canvas.create_image(s(14), s(13), image=self.badge_img, anchor="center")
                    
                self.canvas.tag_raise("frame", "icon")  # ensure frame is on top if it exists
                

                

                # img_pil = self.createOnlyImagePIL(static_icon)  # <-- implement or swap to your real loader
                # if self.size:
                #     # if size is already scaled, don't s() twice. assume size is pixels.
                #     w, h = self.size
                #     #img_pil = img_pil.resize((int(w), int(h)), Image.BICUBIC)
                # elif scale != 1:
                #     img_pil = img_pil.resize(
                #         (int(img_pil.size[0] * scale), int(img_pil.size[1] * scale)),
                #         Image.NEAREST
                #     )

                # self.static_img = ImageTk.PhotoImage(img_pil)
            except Exception:
                # fallback: try your other loader that already returns a PhotoImage
                self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite", size=(frame_height-1, frame_height-1))  # keep reference!
                self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")
                self.static_img = self.createOnlyImage(static_icon, size=(frame_height-2, frame_height-2))
            
            

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
                    frame = frame.resize((int(w), int(h)), Image.BICUBIC)
                elif scale != 1:
                    frame = frame.resize(
                        (int(frame.size[0] * scale), int(frame.size[1] * scale)),
                        Image.NEAREST
                    )

                frames.append(ImageTk.PhotoImage(frame))

        import random
        self.frames = frames
        self.index = random.randrange(len(self.frames)) if self.frames else 0

        if self.frame:
            frame_ne = f"_prof_frame_{self.frame}4"
            self.frame_ne_img = self.createOnlyImage(frame_ne, size=(s(190), s(82)))
            self.frame_ne_id = self.canvas.create_image(s(frame_height), s(-1), tags=["frame"], image=self.frame_ne_img, anchor="ne")
        

        if self.frames:
            self.image_id = self.canvas.create_image(
                cx + s(dx), cy + s(dy),
                image=self.frames[self.index],
                tags=["icon"],
                anchor="center"
            )
        if self.frame:
            frame_sw = f"_prof_frame_{self.frame}5"
            self.frame_sw_img = self.createOnlyImage(frame_sw, size=(s(190), s(85)))
            self.frame_sw_id = self.canvas.create_image(s(0), s(frame_height-1), tags=["frame"], image=self.frame_sw_img, anchor="sw")

        if self.badge:
            pass
            add = 0
            badge_name = f"_prof_badge{self.badge}"
            self.badge_img = self.createOnlyImage(badge_name, bNearest=False, size=(s(34+add), s(34+add)))
            self.badge_id = self.canvas.create_image(s(14), s(frame_height -14), image=self.badge_img, anchor="center")
        
        self.canvas.tag_raise("frame", "icon")  # ensure frame is on top if it exists
        

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
            resized = resized.resize(s(size), Image.BICUBIC)

            img_raw = ImageTk.PhotoImage(resized)
        si = img_raw.size 
        return img_raw, si
    def createOnlyImage(self,player_img, bNearest = False, size=None):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False

        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            if bNearest:
                resized = resized.resize(s(size), Image.NEAREST)
            else:
                resized = resized.resize(s(size), Image.BICUBIC)

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






    
    
import json
import os

#t= time.perf_counter()
#from player2 import Player2
from playerNEW import Hero, Player
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

    def __init__(self, parent, player: Player):
        
        self.parent = parent
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
        mask_glow = False,
        factor=0.5,
        tags = False,
        arh=None,
        x=0,
        y=0,
        mask=False,
        recolor=False,
    ):
        """
        Your original createCanvasImage converted to a method.
        Keeps the "canvas holds references" behavior.
        """
        def recolor_white(img, hex_color):
            """
            Replace white pixels with given hex color.
            Keeps transparency.
            """
            img = img.convert("RGBA")

            # Convert hex → RGB tuple
            hex_color = hex_color.lstrip("#")
            target = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            pixels = img.load()

            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]

                    # Only affect near-white pixels (tolerance helps antialiasing)
                    if r > 240 and g > 240 and b > 240 and a > 0:
                        pixels[x, y] = (*target, a)

            return img
        def apply_black_crops_mask(img, mask, flip=False, resize_mask=False):
            """
            img: already-loaded PIL image
            mask_path: path to black/white mask image
            black = erase, white = keep
            """
            img = img.convert("RGBA")
            mask = image_loader(mask)
            mask = mask.convert("RGBA")



            if resize_mask and mask.size != img.size:
                mask = mask.resize(img.size, Image.BICUBIC)
            if flip:
                mask = mask.transpose(Image.FLIP_LEFT_RIGHT)

            src_alpha = img.getchannel("A")

            # Mask channels
            r, g, b, a = mask.split()

            # Convert RGB to grayscale brightness
            gray = ImageOps.grayscale(mask)   # black=0, white=255

            # We want black areas to erase, so invert brightness:
            # black -> 255 erase strength
            # white -> 0 erase strength
            black_strength = ImageOps.invert(gray)

            # Transparent parts of mask should do nothing,
            # so multiply erase strength by mask alpha
            erase_strength = ImageChops.multiply(black_strength, a)

            # Invert erase strength to make a "keep" mask
            keep_mask = ImageOps.invert(erase_strength)

            # Apply to source alpha
            new_alpha = ImageChops.multiply(src_alpha, keep_mask)

            out = img.copy()
            out.putalpha(new_alpha)
            return out
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
        if recolor:
            img_raw = recolor_white(img_raw, recolor)

        if tint_alpha:
            img_raw = adjust_alpha(img_raw, factor=factor)  # light gray/white
        if mask:
            img_raw = img_raw.convert("RGBA")
            img_raw = make_circle(img_raw)

        if size:
            img_raw = img_raw.resize(self._s2(size), Image.BICUBIC)
        if mask_glow:
            if isinstance(mask_glow, tuple):
                bMask, bFlip = mask_glow
            else:
                bMask = mask_glow
                bFlip = False
            img_raw = apply_black_crops_mask(img_raw, "_GlowMask", flip=bFlip, resize_mask=True)
        img = ImageTk.PhotoImage(img_raw)

        if bg is not None:
            canvas.configure(bg=bg)
        if tags:
            item = canvas.create_image(s(x), s(y), anchor=anc, image=img, tags=tags, **arh)
        else:
            item = canvas.create_image(s(x), s(y), anchor=anc, image=img, **arh)

        # store tkinter image refs
        if not hasattr(canvas, "_images"):
            canvas._images = {}

        canvas._images[item] = img

        # store editable PIL image
        if not hasattr(canvas, "_pil_images"):
            canvas._pil_images = {}

        canvas._pil_images[item] = img_raw   # <--- THIS IS THE IMPORTANT ONE
        

        return item

    def _create_only_image(self, img_key, size):
        img_raw = image_loader(img_key)
        if not img_raw:
            return False

        if size:
            img_raw = img_raw.resize(self._s2(size), Image.BICUBIC)

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
        NAME_BANNER = "#24212B"  # was UI["outer"]["bg"]
        add = 12 if int(SCALE) != 1 else 0

        self.outer = tk.Frame(
            self.parent,
            width=s(self.player_frame_width),
            height=s(599) +s(self.overview_frame) + s((self.stat_frame_height * 3)) + add,
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
    def _build_overview(self):
        NAME_BANNER = "#24212B"

        overview_bar = tk.Frame(
            self.outer,
            bg="#171B20",
            width=s(self.player_frame_width),
            height=s(40),
            relief="raised",
            borderwidth=2,
        )
        overview_bar.pack(side="top", pady=(4, 0), fill="both")
        overview_bar.pack_propagate(False)

        overview_stats = tk.Frame(
            self.outer,
            bg="#171B20",
            width=s(self.player_frame_width),
            height=s(self.overview_frame),
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
            height=s(self.overview_frame),
            width=s(self.player_frame_width),
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
            ("Win%", winpct, self.db.overview_stat_percentile("win_pct", winpct, player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)))),
            ("Mvp%", mvppct, self.db.overview_stat_percentile("mvp_pct", mvppct, player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)))),
            ("Kd", kd_ov, self.db.overview_stat_percentile("kd_ratio", float(kd_ov), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)))),
            ("Kda", kda_ov, self.db.overview_stat_percentile("kda_ratio", float(kda_ov), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)))),
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



                
                
            y += 24

        # role usage (kept same logic)
        from playerNEW import Role
        roles: Role = self.roles
        if roles and len(roles) >= 1:
            gray_role = roles[0].role_name + "_G"
            self._create_canvas_image(ov_canvas, img_key=gray_role, size=(26, 26), bg=NAME_BANNER, x=260, y=1)

            t1 = roles[0].time_played
            t2 = roles[1].time_played if len(roles) > 1 else 0
            t3 = roles[2].time_played if len(roles) > 2 else 0
            denom = (t1 + t2 + t3) if (t1 + t2 + t3) else 1

            usage = roles[0].usage
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
            width=s(self.player_frame_width),
            height=s(35),
            relief="raised",
            borderwidth=2,
            padx=0,
            pady=0,
        )
        heroes_bar.pack(side="top", fill="both")
        heroes_bar.pack_propagate(False)

        heroes_bar_canvas = tk.Canvas(heroes_bar, height=s(35), highlightthickness=0)
        heroes_bar_canvas.pack(anchor="center", fill="x",padx=0, pady=0)

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
            s(4), s(4),
            text="Best Heroes",
            fill="#E0DAFA",
            font=fonttk("Refrigerator Deluxe ExtraBold", 18, "normal"),
            anchor="nw",
        )

        heroes_bar_canvas.create_text(
            s(self.player_frame_width - 8), s(6),
            text=self.player.seasons_string,
            fill="#B4B0DB",
            font=fonttk("Refrigerator Deluxe", 16, "bold"),
            anchor="ne",
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
            width=s(self.player_frame_width),
            height=s(36)+ s((self.stat_frame_height * 3)),
            relief="flat",
            borderwidth=0,
        )
        heroes_frame.pack(side="top", fill="both", padx=0, pady=0)
        heroes_frame.pack_propagate(False)

        heroes_bg_canvas = tk.Canvas(heroes_frame, height=s(82)+ s((self.stat_frame_height * 3)), width=s(380), highlightthickness=0,bg=NAME_BANNER)
        heroes_bg_canvas.pack(anchor="center", fill="both",pady=(s(2),0))
        heroes_bg_canvas.pack_propagate(False)
        self._create_canvas_image(
            heroes_bg_canvas,
            img_key="herobg3",
            anc="nw",
            size=(380, 36 + self.stat_frame_height * 3),
            bg=NAME_BANNER,
            x=0,
            y=0,
        )

        # Build hero cards in score order
        global bTest
        coun = 0
        self.active_hero: Hero = None
        for hero_obj in self.top3:

        # for idx1 in self.order:  # idx1 is 1..3
        #     coun += 1
        #     # kept in case you use it later
        #     # scfg = "#e2b52d" if coun == 1 else "#7f9ccf" if coun == 2 else "#d39a74"

        #     if idx1 == 0:
        #         continue

        #     i = idx1 - 1
        #     #from playerNEW import Hero
        #     hero_obj: Hero = None
        #     hero_obj = self._safe_at(self.top3, i, None)

            if hero_obj is None:
                continue
            self.active_hero = hero_obj

            hero = hero_obj.getHeroName()
            role = hero_obj.getHeroRole()




            # Lord/skin selection logic (same behavior)
            hero_icon = hero
            bAnimatedLord = False
            badge = False
            frame = False
            self.prof_rank = False
            

            if hero != "Unknown":
                if MANUAL_DEBUG != 1:
                    global icon_idx
                    bAnimatedLord = True
                    
                else:
                    bAnimatedLord = self.active_hero.bAnimated if hasattr(self.active_hero, "bAnimated") else False
                    frame = self.active_hero.Frame if hasattr(self.active_hero, "Frame") else False

                    badge = self.active_hero.Badge if hasattr(self.active_hero, "Badge") else False
                    hero_icon = self.active_hero.HeroIconName if hasattr(self.active_hero, "HeroIconName") else hero
                    self.prof_rank = self.active_hero.Proficiency_Rank if hasattr(self.active_hero, "Proficiency_Rank") else "Agent"
                    # time_played_h = hero_obj.time_played_All
                    # if time_played_h is False:

                    #     for h in self.fov_heroes:
                    #         if h.heroname == hero:
                    #             time_played_s = h.time_played
                    #             time_played_m = time_played_s / 60
                    #             time_played_h = time_played_m / 60
                    #             break

                    #     bAnimatedLord, frame, badge, hero_icon, self.prof_rank = self.proficiency_handler(time_played_h, hero)
                    # else:
                    #     bAnimatedLord, frame, badge, hero_icon, self.prof_rank = self.proficiency_handlerAll(time_played_h, hero)
            else:
                bAnimatedLord = False
                frame = False
                badge = False
                hero_icon = "Unknown"
                self.prof_rank = "Agent"

            badge = False if not config.bBadges else badge
            frame = False if not config.bFrames else frame
                            

            if not image_loader(hero_icon):
                hero_icon = hero
                if not image_loader(hero_icon):
                    print(f"Image not found for {hero_icon}, setting to Unknown")
                    hero_icon = "Unknown"

            
            
            # --- card container ---
            hero_bar = tk.Frame(
                heroes_bg_canvas,
                bg="#c8d9f9",
                width=s(self.player_frame_width),
                height=s(self.stat_frame_height),
                relief="raised",
                borderwidth=2,
                padx=0,
                pady=0,
            )
            hero_bar.pack(side="top", pady=(s(3), s(2)), fill="x")
            hero_bar.pack_propagate(False)
            

            hero_icon_frame2 = tk.Frame(
                hero_bar,
                bg="#c8d9f9",
                width=s(self.icon_frame_height),
                height=s(self.stat_frame_height),
                bd=0,
                #relief="solid",
                #highlightcolor="#3d3e5e",
                padx=0,
                pady=0)
            hero_icon_frame2.pack(side="left",fill="both",expand=True,anchor="w",padx=(s(0), s(0)), pady=(s(0), s(0)))
            hero_icon_frame2.pack_propagate(False)

            hero_icon_frame = tk.Frame(
                hero_icon_frame2,
                bg="#c8d9f9",
                width=s(self.icon_frame_height),
                height=s(self.icon_frame_height),
                bd=0,

                padx=0,
                pady=0)
            hero_icon_frame.pack(side="bottom",anchor="w",padx=(s(0), s(0)), pady=(s(0), s(0)), expand=False,fill='none')
            hero_icon_frame.pack_propagate(False)

            # icon (animated or static)
            # icon (animated or static)
            try:
                if bAnimatedLord:
                    sheee = hero + "_Master2"
                    anim = SpriteSheetAnimator(
                        master=hero_icon_frame,
                        hero=hero,
                        animated=True,
                        sheet_path=sheee,
                        rows=10,
                        badge=badge,
                        frame=frame,
                        cols=6,
                        fps=24,
                        bg="#3d3e5e",#"#595A88",
                        relief="sunken",
                        frame_height = self.icon_frame_height,
                        borderwidth=2,
                    )
                    anim.play()
                    hero_bar.hero_anim = anim
                    bTest += 1

                else:
                    anim = SpriteSheetAnimator(
                        master=hero_icon_frame,
                        hero=hero,
                        animated=False,
                        badge=badge,
                        frame=frame,
                        static_icon=hero_icon,   # <-- whatever you pass to _create_only_image()
                        bg="#3d3e5e",#"#595A88",
                        relief="sunken",
                        borderwidth=2,
                        frame_height = self.icon_frame_height,
                        size=(self.icon_image_size, self.icon_image_size),   # optional: force icon size
                    )
                    hero_bar.hero_anim = anim  # optional (just keeps a ref)

            except Exception as e:
                print("Error loading hero icon for", hero, e)
                anim = SpriteSheetAnimator(
                    master=hero_icon_frame,
                    hero=hero,
                    animated=False,
                    badge=badge,
                    frame=frame,
                    static_icon="Unknown",
                    bg="#3d3e5e",
                    relief="sunken",
                    borderwidth=2,
                    frame_height = self.icon_frame_height,
                    size=(self.icon_image_size, self.icon_image_size),
                )
                hero_bar.hero_anim = anim


            

            self._hero_stats(parent=hero_bar, hero=hero_obj, stats_frame_size=(290, self.stat_frame_height-2), top=hero_icon_frame2,
                              fonts = [(self.TTSuperCondMedium, 12, "normal"),("TTSupermolotNeueCond-Bd", 12, "bold")])

    def _hero_stats(self, parent=None, hero:Hero= None, top =None, label_orientation="vertical",stats_frame_size=(290, 110),  fonts = []):
    # stats canvas
        def split_int(total: int, parts: int) -> list[int]:
            if parts <= 0:
                raise ValueError("parts must be > 0")

            base = total // parts
            remainder = total % parts

            # Distribute remainder (+1) to the first `remainder` parts
            return [base + 1] * remainder + [base] * (parts - remainder)
        if not hero:
            print("Warning: hero is None in _hero_stats")
            return
        role = hero.getHeroRole()
        x, y = stats_frame_size
        hero_stats = tk.Canvas(
            parent,
            height=s(y),
            width=s(x),
            highlightthickness=0,
            bg="#77789E",
        )

        #canTags = ["text", "header", "bg", "games_group", "time_group","]
        hero_stats.pack(side="left", padx=(0, 0), pady=(0, 0), fill="both")

        hero_statstop = tk.Canvas(
            top,
            
            height=s(18),
            width=s(x),
            highlightthickness=0,
            bg="#9e9faf",
            #relief="solid",
            #borderwidth=2,
            #highlightcolor="#3d3e5e"

        )

        #canTags = ["text", "header", "bg", "games_group", "time_group","]
        hero_statstop.pack(side="left", fill="both", expand=True, padx=(0, 0), pady=(0, 0) )

        def apply_text_cutout_to_tag(canvas: tk.Canvas, tag: str, text: str, font_path: str, font_size: int):
            items = canvas.find_withtag(tag)
            if not items:
                return

            item = items[0]  # or loop if multiple
            x, y = map(int, canvas.coords(item))  # canvas placement point (anchor dependent!)

            # You MUST have the original PIL image used for this item
            pil_img = canvas._pil_images[item].copy()  # example storage dict

            font = ImageFont.truetype(font_path, font_size)

            # If your image is anchored "nw" and drawn at (x,y),
            # then the text position INSIDE the image is:
            text_xy = (20, 10)  # inside-image coords (you choose)

            out = punch_text_out_of_image(pil_img, text, text_xy, font)

            tk_img = ImageTk.PhotoImage(out)
            canvas.itemconfigure(item, image=tk_img)
            canvas._images[item] = tk_img  # keep ref alive


        bg = self._create_canvas_image(
            hero_stats,
            img_key="_SBg2",#"hero_stats_bg_new2",
            anc="ne",
            tags = "bg",
            size=(377, 144),
            bg=NAME_BANNER,
            x=x - s(self.hero_stats_offset),
            y=0,
        )

        ol = self._create_canvas_image(
            hero_stats,
            img_key="_SBg_Tile4",#"hero_stats_bg_new2",
            anc="ne",
            tags = "bg",
            size=(400, 152),
            bg=NAME_BANNER,
            x=x-s(7) - s(self.hero_stats_offset) ,
            y=0- s(4),
        )

       
        # hd = self._create_canvas_image(
        #     hero_stats,
        #     img_key="_SBanner_Small2",
        #     anc="center",
        #     tags = "header",
        #     size=(168, 33),
        #     bg=NAME_BANNER,
        #     x=40,# - s(18),
        #     y=12,
        # )
        scaled_x = 168 * int(self.stat_frame_height / 112)
        scaled_y = 33 * int(self.stat_frame_height / 112)
        hd = self._create_canvas_image(
            hero_statstop,
            img_key="_SBanner_Small2",
            anc="center",
            tags = "header",
            size=(scaled_x, scaled_y),
            
            x=s(40),# - s(18),
            y=s(12),
        )

        

        heroname = hero.getHeroName()
        
        short_name = HERO_SHORT_NAMES.get(heroname, heroname)
        #short_name = heroname
        #hero_name = hero_stats.create_text(s(x/2)-s(6),s(10),tags="header",text=heroname,fill="#FBFCFF",font=fonttk("Refrigerator Deluxe ExtraBold", 11, "bold"),anchor="c")
        hero_name = hero_statstop.create_text(s(21),s(4),tags="header",text=short_name,fill="#E2E3F7",font=fonttk("Refrigerator Deluxe ExtraBold", 12, "bold", italic=False),anchor="nw")#"#ece5ff"#"#ece5ff"
        _,_,use,_ = self._get_iterative_coordinates(hero_statstop, hero_name, padx=0, pady=0)
        m1,n1,m2,n2 = hero_statstop.bbox(hero_name)
        flip = (x/2 - use) + x/2 
        # r = self._create_canvas_image(
        #     hero_statstop,
        #     tint_alpha=False,
        #     img_key=f"{role}_2",
        #     anc="center",
        #     tags = "header",
        #     size=(20, 20),
        #     bg=NAME_BANNER,
        #     x= m2/SCALE + 15,
        #     y=13,
        # )

        #xc = m2/SCALE + 15
        #print(f"{short_name}: {xc}")
        role_y = s(13) if role in ["Strategist"] else s(13)
        role_x = s(96) if role in ["Strategist"] else s(97)
        role_x += self.hero_stats_offset

        
        
        r = self._create_canvas_image(
            hero_statstop,
            tint_alpha=False,
            img_key=f"{role}_2",
            anc="center",
            tags = ["header", "role"],
            size=(20, 20),
            bg=NAME_BANNER,
            x= role_x,
            y=role_y,
            recolor="#c7bfdb",
        )
        prof = hero.Frame if hasattr(hero, "Frame") else False
        prof_fx = f"_prof_frame_{prof}_fx" if prof else False
        
        if prof_fx:
            self._create_canvas_image(
            hero_statstop,
            tint_alpha=False,
            img_key=prof_fx,
            anc="center",
            tags = "fx",
            size=(60, 56),
            bg=NAME_BANNER,
            x= s(93-18),
            y=s(39-4),
            #recolor="#ebe4ff",
        )
            
            self._create_canvas_image(
            hero_stats,
            tint_alpha=False,
            img_key=prof_fx,
            anc="center",
            tags = "fx",
            size=(60, 56),
            bg=NAME_BANNER,
            x= s(-17),
            y=s(39-4),
            #recolor="#ebe4ff",
        )
        

        # _______Final HEADER position adjustment_______#
        #hero_statstop.move('header',s(-18), -1)

        hero_statstop.move('header',s(-18), s(-4))
        hero_statstop.lift('role')
 


        self.fg_l = "#434A5A"
        self.fg_v = "#262836"

        self.RIGHT_MOST = 0
        self.FINAL_RIGHT_MOST = False
        self.FIRST_TEXT = False
        y = 41
        x = -5

        matches_played = hero.getHeroMatchesPlayed()
        hero_timeH = hero.getHeroTimePlayed() / 3600
        usage_pct = hero.getHeroUsagePct()
        stat_names = config.load_ui_stats_config()
        stat_names_1 = stat_names[:2]
        stat_names_2 = stat_names[3:7]
        stats = self._buildStatTuple(hero, stat_names_1)
        #stats = ("Time",round(hero_timeH,1), False),("Usage", usage_pct, False)
        
        #mvp = hero.getHeroMvpPct()
        #avg_kills_match = hero.getHeroAvgKillsPerMatch()
        #killrate = hero.getHeroKillsPer10()

        #stats2 =   ("Mvp %", mvp, False),("Kills", hero.getHeroAvgKillsPerMatch(),self.db.stat_percentile(heroname, "kills_per_10", float(hero.getHeroKillsPer10()), min_samples=10)),("Deaths", hero.getHeroAvgDeathsPerMatch(),self.db.stat_percentile(heroname, "average_lifespan", float(hero.getHeroAvgLifespan()), min_samples=10)),(hero.string, int(round(hero.getHeroAvgDamagePerMatch() if role != "Strategist" else hero.getHeroAvgHealingPerMatch())), self.db.stat_percentile(heroname, f"{hero.string.lower()}_per_minute", float(hero.dpm), min_samples=10) if role != "Strategist" else self.db.stat_percentile(heroname, "healing_per_minute", float(hero.dpm), min_samples=10))
                      #("Assists", hero_obj.avg_assists_per_match,self.db.stat_percentile(hero, "assists_per_10", float(hero_obj.assists_per_10), min_samples=1)),(hero.string, int(round(hero.getHeroAvgDamagePerMatch() if role != "Strategist" else hero.getHeroAvgHealingPerMatch())), self.db.stat_percentile(hero, f"{hero.string.lower()}_per_minute", float(hero.dpm), min_samples=1) if role != "Strategist" else self.db.stat_percentile(hero, "healing_per_minute", float(hero.dpm), min_samples=1)),
                      #("Blocked", int(round(hero_obj.avg_damage_taken_per_match)), self.db.stat_percentile(hero, "total_damage_taken_per_minute", float(hero_obj.total_damage_taken_per_minute), min_samples=1)),
        stats2 = self._buildStatTuple(hero, stat_names_2)  
        inde = 0            
        for label, value, percentile in stats:
            #print(f"{short_name} - Placed {label} at x={x}, y={y}")
            label = label.lower().strip().replace(" %", "")
            
            self._buildGFX_StatLabelValue(
                canvas=hero_stats,
                label=label,
                value=value,
                x=x,
                index = inde,
                y=y,
                scale=1.15
                )
            x1, y1, x2, y2 = hero_stats.bbox(label)
            #print(f"GROUP: {label}, x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}")
            inde += 1
            #y = y2/SCALE + y - 35
            y += 44
            
        hero_stats.move('GFX',s(7), s(18))
        

        xtare = 113 #Old layout
        ytare = 43 - 16 #Old layout

        xtare = 120
        ytare = 43 - 18

        #__Game Average Stat Builder__
        idex = 0
        for label, value, percentile in stats2:
            self._buildGFX_AverageStatLabelValue(
                canvas=hero_stats,
                label=label.strip().replace(" %", ""),
                value=value,
                x=xtare,
                y=ytare,
                index = idex,
                scale=1.1,
                percentile=percentile
            )
            xtare += 46
            idex += 1
#######################################################################################
    def _buildGFX_StatLabelValue(self, canvas: tk.Canvas, scale: int = 1, index:int = None, label: str = None, value=None, percentile=None, x=0, y=0):
        # Create label text
        #icon_label = label.lower().strip().replace(" %", "")
        #icon_label = icon_label + '2'
        pct = None
        sizev = int(round(14*scale))
        sizel = int(round(9*scale))
        sizes = int(round(8*scale))
        fgv = "#262836"
        fgl = "#546280"
        font1 = ("Refrigerator Deluxe Heavy", 8, "normal")#[("Nunito Sans 10pt Condensed Medium", 8, "normal")]
        font2 = ("Refrigerator Deluxe Heavy", 14, "normal")
        px = 42 if "win" in label.lower() else 42
        icon = self._create_canvas_image(
            canvas=canvas,
            img_key=label,
            anc="sw",
            size=(px*scale, px*scale),
            tags=[label,"GFX"],
            bg=NAME_BANNER,
            x=x,
            y=y,
        )


        x1,y1,x2,y2 = canvas.bbox(icon)
        x2 += 8
        #y2 += 3
        x = x2/SCALE - 3 * scale
        y = y2/SCALE - 4 * scale
        #v = canvas.create_text(x2 - 1*scale,y2 - 6 * scale,text=value if label != "Win %" else "WIN",tags=label,fill=self.fg_v,font=fonttk("Refrigerator Deluxe Heavy", 16, "normal"),anchor="sw")
        if isinstance(value, str) and value.endswith("%"):
            value = value.replace("%", "")
            pct = '%'
        st = canvas.create_text(s(x), s(y), text=value, tags=[label,"GFX"], fill=fgv, font=fonttk("Refrigerator Deluxe Heavy", sizev, "normal"), anchor="sw")
        x1, y1, x2, y2 = canvas.bbox(st)
        if pct:
            canvas.create_text(s(x2), s(y-1), text=pct, tags=[label,"GFX",f"{label}%"], fill=fgv, font=fonttk("Refrigerator Deluxe Heavy", sizev-3, "normal"), anchor="sw")
        if label == "time":
                
                strp = "HR"

                canvas.create_text(x2, s(y) - 2 * scale, text=strp, tags=[label,"GFX"], fill=fgl, font=fonttk("Refrigerator Deluxe ExtraBold", sizes, "normal"), anchor="sw")
        x = x

        # if index in [0,1]:
        #     icon = self._create_canvas_image(
        #     canvas=canvas,
        #     img_key="_gfx_sep",
        #     anc="c",
        #     size=(58*scale, 4*scale),
        #     tags=[label,"GFX"],
        #     bg=NAME_BANNER,
        #     x=x +4,
        #     y=y + 2,
        # )
        y = y - int(round(18 * scale))
        l = canvas.create_text(s(x), s(y), text=label.upper() if label != "Win %" else "WIN", tags=[label,"GFX"], fill=fgl, font=fonttk("Refrigerator Deluxe ExtraBold", sizel, "bold"), anchor="sw")

    def _buildGFX_AverageStatLabelValue(self, canvas: tk.Canvas, scale: int = 1, label: str = None, value=None, index:int=None, percentile=None, x=0, y=0):
        # Create label text
        #icon_label = label.lower().strip().replace(" %", "")
        #icon_label = icon_label + '2'
        sizev = int(round(13*scale))
        sizel = 10#int(round(9*scale))
        sizes = int(round(8*scale))

        ui_value, ui_value_2 = self._convertValue_AverageStat(value, label)
        # avg_match = (self.hero_time_s/60) / self.hero_matches_played  if self.hero_time_s else 0
        # if "%" not in str(value):
        #     value = round(10 / avg_match * value,1) if avg_match else value
        font_pct = "TTSupermolotNeueCond-Bd"
        font_pct = "TTSupermolotNeueCond-Bd"
        fgv = "#303242"
        fgvorig = "#303242"
        fgl = "#5A6988"
        fgl2 = "#43465C"
        font1 = ("Refrigerator Deluxe Heavy", 8, "normal")#[("Nunito Sans 10pt Condensed Medium", 8, "normal")]
        font2 = ("Refrigerator Deluxe Heavy", 14, "normal")
        glow = False
        gstr = None
        if percentile:
            percentile = round(int(percentile),0) if percentile > 20 else round(float(percentile),1)
            if percentile < 5:
                glow = "P"
                gstr = "purple"
            elif percentile < 15:
                glow = "B"
                gstr = "blue"
            elif percentile < 35:
                glow = "G"
                gstr = "green"
            elif percentile < 55:
                glow = None
                gstr = None
            elif percentile < 75:
                glow = "Y"
                gstr = "yellow"
            else:
                glow = "R"
                gstr = "red"
        img_key = label.lower().strip().replace(" %", "")
        icon = self._create_canvas_image(
            canvas=canvas,
            img_key=img_key,
            anc="c",
            size=(34*scale, 34*scale),
            tags=[label,"avg"],
            bg=NAME_BANNER,
            x=x,
            y=y,
        )


        x1,y1,x2,y2 = canvas.bbox(icon)
        c1, c2 = canvas.coords(icon)

        #print(f"AVERAGE ICON BBOX for {label.upper()}:\na:{x1}, \nb:{y1}, \nc:{x2}, \nd:{y2}\n\nCOORDS:\nc1:{c1}, \nc2:{c2}\n____________\n")
        #x = x2 - 3 * scale

        # y = y2 + 7 * scale OLD LAYOUT
        y = y2/SCALE + 29 * scale
        #fg = self._get_foreground_color(label, value)
        #v = canvas.create_text(x2 - 1*scale,y2 - 6 * scale,text=value if label != "Win %" else "WIN",tags=label,fill=self.fg_v,font=fonttk("Refrigerator Deluxe Heavy", 16, "normal"),anchor="sw")
        st = canvas.create_text(s(x), s(y-2), text=ui_value, tags=[label,"avg"], fill=fgvorig, font=fonttk("Refrigerator Deluxe Heavy", sizev, "normal"), anchor="c")
        a1, b1, a2, b2 = canvas.bbox(st)
        topx = x+1
        topy = y+18
        if glow:
            glow_img_key = f"_Glow{glow}"
            if index == 0:
                bMask = (True, True)
            elif index == 3:
                bMask = (True, False)
            else:
                bMask = False

            glow_icon = self._create_canvas_image(
                canvas=canvas,
                img_key=glow_img_key,
                anc="c",
                tint_alpha=True,

                mask_glow=bMask,
                factor=0.75,
                size=(42*scale,17*scale),
                tags=[label,"avg"],
                bg=NAME_BANNER,
                x=x+1,
                y=y+18,
            )
        st2 = canvas.create_text(a2, s(y), text=ui_value_2, tags=[label,"avg"], fill=fgvorig, font=fonttk("Refrigerator Deluxe Heavy", sizev-2, "normal"), anchor="c")

        x = x
        #y = y1 - int(round(5*scale)) OLD LAYOUT
        y = y2/SCALE + int(round(6*scale)) -3
        l = canvas.create_text(s(x), s(y), text=label.upper() if label != "Win %" else "WIN", tags=[label,"avg"], fill=fgl, font=fonttk("Refrigerator Deluxe ExtraBold", sizel, "normal"), anchor="c")

        if percentile is not False and percentile is not None:
            #percentile = round(int(percentile),0) if percentile > 20 else round(float(percentile),1)
            if percentile == 0:
                glow_img_key = f"_top1_c"
                bMask = True if label.lower() == "damage" or label.lower() == "healing" else False
                glow_icon = self._create_canvas_image(
                    canvas=canvas,
                    img_key=glow_img_key,
                    anc="c",
                    tint_alpha=False,
                    mask_glow=bMask,
                    
                    factor=0.75,
                    size=(42*scale,19*scale),
                    tags=[label,"avg"],
                    bg=NAME_BANNER,
                    x=topx,
                    y=topy,
                )
            else:
                percentile = f"{percentile}%" if percentile != "N/A" else "N/A"
                #p = canvas.create_text(s(x+6), s(y+42), text=percentile, tags=[label,"avg"], fill=fgl2, font=fonttk("Refrigerator Deluxe ExtraBold", sizel-2, "bold", italic=False), anchor="c")
                p = canvas.create_text(s(x+6), s(y+43+3), text=percentile, tags=[label,"avg"], fill=fgl2, font=fonttk("Refrigerator Deluxe ExtraBold", sizel-2, "bold", italic=False), anchor="c")
                q,w,e,r = canvas.bbox(p)
                p_icon = self._create_canvas_image(
                    canvas=canvas,
                    img_key=f"db_{gstr}",
                    anc="c",
                    size=(10*scale, 7*scale),
                    tags=[label,"avg"],
                    bg=NAME_BANNER,
                    x=x-13,
                    y=y+42+3,
                )
                t,y = canvas.coords(p)
            #print(f"Percentile bbox for {label.upper()}:\na:{q}, \nb:{w}, \nc:{e}, \nd:{r}\n\nCOORDS:\nt:{t}, \ny:{y}\n____________\n")

                
        

        #print(f"Icon coords for {label}:\na:{a}, \nb:{b}, \nc:{c}, \nd:{d}\n____________\n")
        
        #self._setLabelValue_CanvasText1(parent, lab=label, val=value, x=x, y=y, font1=font1, font2=font2,fills=fills, tag=tag, anc=anc)

    def _buildStatTuple(self, hero: Hero, stat_names: list[str]):
        stats = []
        seconds = hero.getHeroTimePlayed()
        for stat_label in stat_names:
            if stat_label == "Games":
                stat_value = round(hero.getHeroMatchesPlayed(), 1)
                stat_db = False
            elif stat_label == "Time":
                stat_value = round(hero.getHeroTimePlayed() / 3600, 1)
                stat_db = False
            elif stat_label == "Usage":
                stat_value = hero.getHeroUsagePct()
                stat_db = False
            elif stat_label == "Win %":
                stat_value = hero.getHeroWinPct()
                db_value = hero.win_pct_raw
                stat_db = self.db.stat_percentile(hero.getHeroName(), "win_pct", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "Mvp %":
                stat_value = hero.getHeroMvpPct()
                db_value = hero.mvp_pct_raw
                stat_db = self.db.stat_percentile(hero.getHeroName(), "mvp_pct", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "Kills":
                stat_value, db_value = hero.getHeroStatMatchAvg(hero.kills)
                stat_db = self.db.stat_percentile(hero.getHeroName(), "kills_per_10", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "Deaths":
                stat_value, db_value = hero.getHeroStatMatchAvg(hero.deaths)
                stat_db = self.db.stat_percentile(hero.getHeroName(), "average_lifespan", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), direction="asc", min_samples=10, sec = seconds)
            elif stat_label == "Assists":
                stat_value, db_value = hero.getHeroStatMatchAvg(hero.assists)
                stat_db = self.db.stat_percentile(hero.getHeroName(), "assists_per_10", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "Blocked":
                stat_value, db_value = hero.getHeroStatMatchAvg(hero.total_damage_taken)
                stat_db = self.db.stat_percentile(hero.getHeroName(), "total_damage_taken_per_minute", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "Accuracy":
                stat_value = hero.getHeroAccuracy()
                if stat_value == "N/A":
                    stat_db = False
                else:
                    db = stat_value.strip("%") if isinstance(stat_value, str) else stat_value
                    stat_db = self.db.stat_percentile(hero.getHeroName(), "accuracy_pct", float(db), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
            elif stat_label == "KD/KDA":
                stat_value = round(hero.getHeroKDRatio() if hero.getHeroRole() != "Strategist" else hero.getHeroKDARatio(), 2)
                db_value = hero.kd_ratio if hero.getHeroRole() != "Strategist" else hero.kda_ratio
                stat_db = self.db.stat_percentile(hero.getHeroName(), "kd_ratio" if hero.getHeroRole() != "Strategist" else "kda_ratio", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
                stat_label = "Kd" if hero.getHeroRole() != "Strategist" else "Kda"
            elif stat_label == "Damage/Healing":
                stat_value, db_value = hero.getHeroStatMatchAvg(hero.total_damage) if hero.getHeroRole() != "Strategist" else hero.getHeroStatMatchAvg(hero.total_healing)
                stat_db = self.db.stat_percentile(hero.getHeroName(), f"{hero.string.lower()}_per_minute", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds) if hero.getHeroRole() != "Strategist" else self.db.stat_percentile(hero.getHeroName(), "healing_per_minute", float(db_value), player_name=getattr(self.player, "name", getattr(self.player, "player_name", None)), min_samples=10, sec = seconds)
                stat_label = hero.string
            else:
                stat_value = "N/A"
                stat_db = False
            stat_tuple = (stat_label, stat_value, stat_db)
            stats.append(stat_tuple)
        return tuple(stats)
    
    def _convertValue_AverageStat(self, value: str | int = "NAN", label: str = "NaN", pct=""):
        if label.upper() == "MVP":
            return value, pct
        elif label.upper() == "WIN":
            return value, pct
        elif label.upper() in ["GAMES", "USAGE",'ACCURACY','KD','KDA','TIME']:
            return value, pct
        #avg_match = self.active_hero.avg_match_duration_minutes if self.active_hero else 0
        #value = round(float(10 / avg_match * value),1) if avg_match else value
        if label.upper() == "DAMAGE" or label.upper() == "HEALING":
            value = str(round(float(value/1000),1)) + "K" if value > 999 else value
        


        return value, pct
            

    # ---------------------------
    # HISTORY (outer -> history_frame + rows)
    # ---------------------------
    from playerNEW import Match
    def _build_history(self, match: Match = None):
        NAME_BANNER = "#24212B"

        matches = self.matches
        history_h = s(38) * len(matches)

        history_frame = tk.Frame(
            self.outer,
            bg=NAME_BANNER,
            width=s(self.player_frame_width),
            height=history_h,
            relief="flat",
            borderwidth=0,
        )
        history_frame.pack(side="top", fill="both", pady=(s(10), 0))
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
            rank = match.rank
            tier = match.rank_tier
            rank_d = match.rank_delta

            if mvp_str:
                mvp_string = "mvp108"
            elif svp_str:
                mvp_string= "svp108"
            else:
                mvp_string = None

            if result == "win":
                bg, outline, pic, fg = "#26393C", "#5DE48E", "winbg", "#6DC5FF"# "#_mh_winS3"
            elif result == "tie":
                bg, outline, pic, fg = "#272C40", "#96bfff", "tiebg", "#78beff"#"_mh_drawS3"
            elif result == "disconnected":
                bg, outline, pic, fg = "#40272D", "#DADADA", "disconnectbg", "#BBBBBB"#"_mh_disconnectS3"
            elif result == "loss":
                bg, outline, pic, fg = "#40272D", "#DD475C", "losebg", "#FF8D6A"#"_mh_lossS3"
            else:
                bg, outline, pic, fg = "#5A5A5A", "#E6E6E6", "disconnectbg", "#BBBBBB"#"_mh_lossS3"
            match_frame = tk.Frame(
                history_frame,
                bg=outline,
                width=s(375),
                height=s(38),
                relief="raised",
                borderwidth=1,
            )
            match_frame.pack(side="top", anchor="c", pady=(s(5), s(4)), padx=(s(4), s(4)), fill="both")
            match_frame.pack_propagate(False)

            match_canvas = tk.Canvas(
                match_frame,
                height=s(38),
                width=s(375),
                highlightthickness=0,
                bg=bg,
            )
            match_canvas.pack(anchor="center", fill="both")
            match_canvas.pack_propagate(False)

            self._create_canvas_image(match_canvas, img_key=pic, anc="nw", size=(381, 82), bg=bg, x=-8, y=0) #size=(368, 37)

            if mvp_string:
                self._create_canvas_image(
                    match_canvas,
                    img_key=mvp_string,
                    anc="center",
                    size=(52, 52),
                    bg=bg,
                    x=28,
                    y=15,
                )

            one = (30, 30)
            one_frame = (33, 33)
            plus = 28
            x = 60
            y = 18

            match_canvas.create_text(
                s(92), s(11),
                text="Score",
                tags="score_text",
                fill="#D1DAFF",
                font=fonttk("Roboto SemiBold", 8, "normal"),
                anchor="c",
            )
            match_canvas.create_text(
                s(82), s(25),
                text=f"{scores[0]}",
                tags="score_text",
                fill="#8FADFF",
                font=fonttk("Roboto Bold", 12, "bold"),
                anchor="c",
            )

            match_canvas.create_text(
                s(92), s(24),
                text=":",
                fill="#FFFFFF",
                tags="score_text",
                font=fonttk("Roboto Bold", 12, "bold"),
                anchor="c",
            )
            match_canvas.create_text(
                s(101), s(25),
                text=f"{scores[1]}",
                fill="#FF8D6A",
                tags="score_text",
                font=fonttk("Roboto Bold", 12, "bold"),
                anchor="c",
            )
            match_canvas.move("score_text", -19, 1)
            x += 50
            count = 0
            for hero in heroes:
                if count > 2:
                    break
                count += 1
                self._create_canvas_image(match_canvas, img_key="_mh_heroframe3", anc="center", size=one_frame, x=x, y=y)
                self._create_canvas_image(match_canvas, img_key=hero, anc="center", size=one, x=x, y=y, mask=True)
                x += plus
                one = (20, 20)
                one_frame = (22, 22)
                plus = 22

            if len(heroes) < 1:
                self._create_canvas_image(match_canvas, img_key="_mh_heroframe3", anc="center", size=one_frame, x=x, y=y)
                self._create_canvas_image(match_canvas, img_key="Unknown", anc="center", size=one, x=x, y=y, mask=True)


            x = 346
            self._create_canvas_image(match_canvas, img_key=f"{rank}2", anc="center", size=(37,37), x=x-1, y=18)
            

            match_canvas.create_text(
                    s(x + 12),
                    s(30),
                    text=rank_d if result in ["loss","disconnect", "tie"] else f"+{rank_d}",
                    fill=fg,
                    font=fonttk("Roboto SemiCondensed Medium", 7, "normal", italic=True),
                    anchor="c",
                )
            f = RANK_FG.get(rank.lower(), "#B1C7F7")
            match_canvas.create_text(
                    s(x + 15),
                    s(7),
                    text=tier,
                    fill=f,
                    font=fonttk("Roboto SemiCondensed Medium", 8, "normal", italic=False),
                    anchor="c",
                )
            icons = {"match_kill": kills, "match_death": deaths, "match_assist": assists}

            x = 203
            for icon, value in icons.items():
                self._create_canvas_image(match_canvas, img_key=icon, anc="nw", size=(22, 22), x=x, y=0)
                match_canvas.create_text(
                    s(x + 9),
                    s(28),
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
    def build_match_overview(self, parent, players):
        global NAMEPLATES
        NAMEPLATES = []

        self.root.title("Match Overview")
        self.stat_frame_height = 112# 145 #112
        self.player_frame_width = 380
        width = len(players) * s(self.player_frame_width)
        he = 12 if SCALE != 1 else 0
        h = s(1040) + he
        w = s(len(players) * self.player_frame_width)
        
        h = s(724) + s((self.stat_frame_height*3)) + (12 if SCALE != 1 else 0)

        # Use the selected monitor's virtual-desktop origin.
        self.refresh_monitors()
        monitor = self.get_selected_monitor()
        x = monitor["left"]
        y = monitor["top"]

        self.force_geometry(w, h, x, y)

        # also re-apply on idle (handles the intermittent "stays put" case)
        self.after_idle_tracked(lambda: self.force_geometry(w, h, x, y))
        self.after_tracked(30, lambda: self.force_geometry(w, h, x, y))
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
                self.force_geometry(w, s(30), x, y)
            else:
                player_frames.pack(side="bottom", fill="both", expand=True)
                hide_btn.config(text="Hide(F7)")
                self.root.update_idletasks()
                self.force_geometry(w, h, x, y)

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
        t = time.perf_counter()
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
                from tracker_lookup import open_multiple_tracker_profiles
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
            
            if bUseRivalsDataNames:
                if bLiveDebug:
                    p = os.path.join(config.script_dir, "debug","LiveDebug.json")
                    li = helpers.load_json(path=p)
                    from RDMO import Match
                    MatchObject = Match(li)
                    from tracker_trim import open_multiple_tracker_profiles
                    open_multiple_tracker_profiles(MatchObject)
                    return
                
                    
                else:
                    import curlRivals
                    print(">> Fetching names via Live Match API..")
                    MatchObject = curlRivals.main()
                    names = [player.Name for player in MatchObject.Players]
                    print(names)
                    if not names:
                        print("No valid player data to display.")
                        self.show_launcher_page()
                        return False
            else:
                print(">> Capturing names via OCR...")
                names = []
            #names = ['Razzerz', 'bk123456', 'Sour-']

        print("\n🎯 Captured Player Names:")
        for name in names:
            print(f"- {name}")

        players = []
        
        if search_by_name and names:
            print(">> Fetching stats for manually entered names...")
            from tracker_lookup import open_multiple_tracker_profiles

            tracker_data = open_multiple_tracker_profiles(names)
            print(f"Fetched tracker.gg data in {time.perf_counter() - t:.2f} seconds.")
            save_json("_ByNamesTrackerGGJSON.json", tracker_data)
        elif not config.debug_mode and MANUAL_DEBUG != 69:
            if names:
                from tracker_lookup import open_multiple_tracker_profiles
                tracker_data = open_multiple_tracker_profiles(names)
                
                save_json("_2TrackerGGJSON.json", tracker_data)
                save_list_file(names,"_1Names.txt")
        elif config.debug_mode and MANUAL_DEBUG == 0:
            from tracker_lookup import open_multiple_tracker_profiles
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
        