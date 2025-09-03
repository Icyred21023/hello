
import colorsys
import tkinter as tk
from tkinter import font, _default_root
import tkinter.font as tkFont
from PIL import ImageTk, Image, ImageGrab, ImageColor
import os
import sys
import time
from fonts_registry import register_ttf_private
from main3 import HeroMatch
import numpy as np
import config
import hashlib, colorsys
if not config.mobile_mode:
    
    import win32gui
    import win32con
    import win32api
    import win32process
    import win32com.client
    import ctypes
    import keyboard
font_families = set()
hide_function, debug_frame_global, main_frame_global, hide_button_global = None, None, None, None

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

fonts_list = ["Rajdhani.ttf","Rajdhani Medium.ttf","Rajdhani Bold.ttf","Saira Semi Condensed Medium.ttf","Saira Thin Medium.ttf","Refrigerator Deluxe Bold.ttf","Refrigerator Deluxe Heavy.ttf","Exo Demi Bold.ttf","Exo Light.ttf","CarbonRegular.ttf","CarbonBold Italic.ttf","CarbonRegular Italic.ttf"]
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

def fonttk(family, *args, size=None, weight="normal",
           italic=False, underline=False, overstrike=False):
    """
    Build a Tk font tuple from flexible args.

    Positional forms supported:
      fonttk("Rajdhani", "bold", 12)
      fonttk("Rajdhani", 12, "bold")
      fonttk("Rajdhani", 12)
      fonttk("Rajdhani", "bold")

    Or keyword:
      fonttk("Rajdhani", weight="bold", size=12, italic=True)
    """
    # Parse flexible positional args (weight/size in any order)
    if args:
        if len(args) == 1:
            a = args[0]
            if isinstance(a, str):
                weight = a
            else:
                size = a
        elif len(args) >= 2:
            a, b = args[0], args[1]
            if isinstance(a, str):
                weight, size = a, b
            elif isinstance(b, str):
                size, weight = a, b
            else:
                size = a  # ignore extras

    if size is None:
        size = 12

    # Normalize weight to Tk's 'normal' or 'bold'
    w = (str(weight).lower() if isinstance(weight, str) else weight)
    weight_map = {
        "regular": "normal", "normal": "normal", "book": "normal",
        "light": "normal", "thin": "normal", "medium": "normal",
        "demi": "bold", "demibold": "bold", "semibold": "bold",
        "bold": "bold", "heavy": "bold", "black": "bold", "extrabold": "bold",
    }
    if isinstance(w, (int, float)):  # numeric weight → CSS-like
        w = "bold" if w >= 600 else "normal"
    w = weight_map.get(w, "bold" if w in ("700", "800", "900") else "normal")

    styles = []
    if w == "bold":
        styles.append("bold")
    if italic:
        styles.append("italic")
    if underline:
        styles.append("underline")
    if overstrike:
        styles.append("overstrike")

    # Return a tuple Tk understands: (family, size, *styles)
    return (family, int(size), *styles)



_registered_fonts = set()
def call_register_fonts(root: tk.Tk, fonts_list=fonts_list):
    """Load TTFs privately for this process and refresh Tk once.
    Returns (loaded_paths, available_families_set)."""
    print("Registering fonts...")
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
            print(f"Font file already registed: {font_file}")
            continue

        try:
            ok = register_ttf_private(path)  # should return True if OS accepted the font
            if ok:
                _registered_fonts.add(path)
                loaded.append(path)
                num = len(loaded)
                print(f"{num}: {font_file} registered.")
        except Exception as e:
            print(f"Error loading font {font_file}: {e}")

    # Refresh Tk’s font list once after batch
    if loaded:
        root.update_idletasks()

    families = set(tkFont.families(root))
    return loaded, families

lock = None
bhidden = False
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

def handle_f10():
    global main, var2, trigger2_func, root, is_clickthrough, indicator_label
    try:

        if is_clickthrough:
                    make_interactive()
                    is_clickthrough = False
                    if indicator_label:
                        indicator_label.config(text="", bg="#1C2026")
                        indicator_label.update_idletasks()

        if main and main.winfo_ismapped() and root and root.winfo_exists():
            # Schedule both actions in the Tkinter main thread
            root.after(0, lambda: (root.destroy(), trigger2_func(var2.get())))
    except Exception as e:
        print(f"F10 error: {e}")

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
    print("Click-through ENABLED")

def make_interactive():
    global hwnd
    if not config.mobile_mode:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    print("Click-through DISABLED")

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
        return "#FF1919"
    
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
    
    
def show_suggestion_gui(results, image_map,map, blue_dict,red_dict):
    global bhidden, indicator_label
    blue_result, suggest_result, alt_result, red_result = results
    origs_score = round(blue_result.total_score,1)
    origs_stat_score = round(blue_result.stats_score,1)
    origs_teamup_score = round(blue_result.teamup_score,1)
    new_scores  = round(suggest_result.total_score,1)
    new_stat_scores = round(suggest_result.stats_score,1)
    new_teamup_scores = round(suggest_result.teamup_score,1)
    alt_scores   = round(alt_result.total_score,1)
    alt_stat_scores = round(alt_result.stats_score,1)
    alt_teamup_scores = round(alt_result.teamup_score,1)
    
    red_scores1 = round(red_result.total_score,1)
    red_scores2 = round(red_result.total_score2,1)
    red_scores3 = round(red_result.total_score3,1)
    red_stat_scores = round(red_result.stats_score,1)
    red_stat_scores2 = round(red_result.stats_score2,1)
    red_stat_scores3 = round(red_result.stats_score3,1)
    red_teamup_scores = round(red_result.teamup_score,1)
    
    teamup_image_map = create_teamup_image_map(os.path.join(os.path.dirname(__file__), "teamup_icons"))
    return_data = {}
    bhidden = False
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    x = (screen_width // 2) - 700
    root.geometry(f"+{x}+0")
    root.withdraw()

    win = tk.Toplevel(root)
    win.title("")
    def go_back():
        blue = []
        red = []
        for i in range(1, 7):
            b_member = getattr(blue_result, str(i))
            r_member = getattr(red_result, str(i))
        #     s = b_member.suggestion
        #     if not s:
        #         s = b_member.character
        #         name = s.name
        #     else:
        #         name = s.original if s else member.character.name
        #     blue.append(HeroMatch(name, name, 10, False))
        #     name = r_member.character.name
        #     red.append(HeroMatch(name, name, 10, False))
        # return_data["teams"] = (blue, red)
        root.destroy()



    def toggle_hide(debug_frame= None, m=None, btn2=None):
        global bhidden
        if  m and btn2:
            main_frame = m
            hide_btn2 = btn2
        bhidden = not bhidden
        if bhidden:

            main_frame.pack_forget()
            hide_btn2.config(text="Show")
            
        else:
            main_frame.pack(padx=0, pady=0)
            hide_btn2.config(text="Hide")
        win.update_idletasks()
        

    win.overrideredirect(True)
    title_bar2 = tk.Frame(win, bg="#13151A", relief="solid", width=1135,height=17)
    title_bar2.pack(fill="x", side="top",ipady=3)
    title_bar2.pack_propagate(False)
    close_btn2 = tk.Button(title_bar2, command=lambda: close3(root),text="x", width=2,height=1,fg="white", relief="flat",bg="#141420", font=fonttk(exo, 12, 'bold'), cursor="hand2")
    close_btn2.pack(side="right", padx=0)
    hide_btn2 = tk.Button(title_bar2, command=lambda: toggle_hide(None,main_frame,hide_btn2),text="Hide", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 12, 'normal'), cursor="hand2")
    hide_btn2.pack(side="right", padx=10)
    back = tk.Button(title_bar2, command=go_back,text="Back", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 12, 'normal'), cursor="hand2")
    back.pack(side="right", padx=10)
    global lock
    lock = tk.Button(title_bar2, command=lambda: toggle_clickthrough(toggle_hide, None, main_frame, hide_btn2),text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon_italic, 8, 'normal'), cursor="hand2")
    lock.pack(side="right", padx=10)

    indicator_label = tk.Label(title_bar2, text="", fg="white", bg="#13151A", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)
    close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
    close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))

    hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
    hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
    back.bind("<Enter>", lambda e: back.config(bg="#31314D"))
    back.bind("<Leave>", lambda e: back.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    
    win.geometry(f"+{x}+0")
    win.title("Team Suggestion Comparison")
    win.configure(bg="#1C2026")
    win.attributes("-topmost", True)
    win.grab_set()
    
    def get_image(name):
        img_obj = image_map.get(name)
        if not img_obj:
            img_obj = image_map.get("Default")
        if img_obj:
            resized = img_obj.copy()
            resized.thumbnail((128, 128))
            return ImageTk.PhotoImage(resized)
        return None
    
    def add_teamup_icons(parent_frame, teamups, icon_color):
        

        bg = parent_frame.cget("bg")
        bd_color = adjust_color(parent_frame, parent_frame.cget("bg"), 0.4)
        li_color = adjust_color(parent_frame, parent_frame.cget("bg"), 1.2)
        fr  = tk.Frame(parent_frame, width=60,height=1,bg=parent_frame.cget("bg"))
        fr.pack(side="top",padx=0,pady=0,expand=False)
        fr.pack_propagate(False)
        #tk.Label(fr,bg=parent_frame.cget("bg"), text='Team',fg=bg).pack(side='top')
        grid_host = tk.Frame(parent_frame, bg=parent_frame.cget("bg")
                            #highlightthickness=3,
                    )
        grid_host.pack(side="bottom",fill='both', expand=True,padx=0, pady=0)
        if not teamups:
            return
        
        # teamups: list of (tid, teamup_name) but we color by teamup_name
        for i, (_tid, teamup_name) in enumerate(teamups):
            row, col = i % 2, i // 2
            tkimg = get_teamup_tkimage(
                teamup_name, 
                icon_name=teamup_name, 
                image_map=teamup_image_map
            )
            
            
            lbl = tk.Label(grid_host, bg=bg, image=tkimg, bd=0,highlightthickness=0,padx=0,pady=0)
                            #highlightthickness=3,)
            lbl.image = tkimg
            lbl.pack(side='top', anchor="center",padx=0, pady=0,expand=True)

    def add_teamup_icons2(parent_frame, teamups):
        

        if not teamups:
            grid_host = tk.Frame(parent_frame, width=60,height=1, bg=parent_frame.cget("bg"))
            grid_host.pack(side="left")
            grid_host.pack_propagate(False)
            bg = grid_host.cget("bg")
            return
        grid_host = tk.Frame(parent_frame, bg=parent_frame.cget("bg"))
        grid_host.pack(side="left")
        bg = grid_host.cget("bg")
        # teamups: list of (tid, teamup_name) but we color by teamup_name
        for i, (_tid, teamup_name) in enumerate(teamups):
            row, col = i % 2, i // 2
            tkimg = get_teamup_tkimage(
                teamup_name, 
                icon_name=teamup_name, 
                image_map=teamup_image_map
            )
            lbl = tk.Label(grid_host, bg=bg, image=tkimg)
            lbl.image = tkimg
            lbl.grid(row=row, column=col, padx=2, pady=2, sticky="w")

    
        
    def adjust_color(widget, color, factor=0.8):
        """
        Darken/lighten a Tk color relative to a widget's color parser.
        factor < 1.0 -> darker
        factor > 1.0 -> lighter
        """
        # convert to normalized RGB
        r, g, b = [v/65535 for v in widget.winfo_rgb(color)]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        l = max(0, min(1, l * factor))
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    
        # 1) flat recolor that preserves original alpha
    def recolor_icon_flat(pil_img, hex_color):
        r, g, b = ImageColor.getrgb(hex_color)
        pil_img = pil_img.convert("RGBA")
        a = pil_img.split()[-1]
        colored = Image.new("RGBA", pil_img.size, (r, g, b, 0))
        colored.putalpha(a)
        return colored

    # 2) deterministic color per tid (palette or hash)
    TEAMUP_COLORS = {
    # optional fixed picks for important names:
    "Arcane Order": "#53B5FF",
    "Chilling Assault": "#47D1C2",
    "Dimensional Shortcut": "#FF8A5B",
    "Duality Dance": "#F2C94C",
    "Ever-Burning Bond": "#F58A1F",   # orange flame
    "Gamma Monstro": "#49A674",       # green
    "Operation Microchip": "#4A90E2", # steel blue
    "Rocket Network": "#F4762D",      # bright orange
    "Stark Protocol": "#E64A5F",      # pink/red
    
    "Fantastic Four": "#3AB8E7",      # light blue
    "Jeff-Nado": "#47A6DB",           # medium blue
    "Planet X Pals": "#7ED321",       # lime green
    "Symbiote Shenanigans": "#A0B4BF",# grayish blue
    
    "Fastball Special": "#F9D54C",    # yellow/gold
    "Lunar Force": "#8A7DBE",         # violet
    "Primal Flame": "#E84C3D",        # red/orange
    "Vibrant Vitality": "#8CC152",    # bright green
    
    "First Steps": "#F27935",         # orange
    "Mental Projection": "#4BC9F0",   # cyan/light teal
    "Ragnarok Rebirth": "#3DC2A7",    # turquoise
    "Stars Aligned": "#5A7DFF", 
    "Blank": "#594940",    # indigo blue
}

    
    def color_for_teamup(teamup_name: str) -> str:
        """Deterministic color for a teamup name."""
        if teamup_name in TEAMUP_COLORS:
            return TEAMUP_COLORS[teamup_name]
        

        # stable hash → hue
        h = int(hashlib.md5(teamup_name.encode("utf-8")).hexdigest(), 16)
        hue = (h % 360) / 360.0
        s, v = 0.65, 0.95  # pleasant saturation/value
        r, g, b = colorsys.hsv_to_rgb(hue, s, v)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def recolor_icon_flat(pil_img, hex_color):
        pil_img = pil_img.convert("RGBA")
        a = pil_img.split()[-1]
        color = Image.new("RGBA", pil_img.size, ImageColor.getrgb(hex_color) + (0,))
        color.putalpha(a)
        return color

    _tk_cache = {}

    def get_teamup_tkimage(teamup_name: str, icon_name: str, image_map: dict, size=(42,42)):
        """
        teamup_name -> color, icon_name -> which PNG in image_map to tint.
        image_map[icon_name] should be a PIL.Image original.
        """
        key = (teamup_name, icon_name, size)
        if key not in _tk_cache:
            base_pil = image_map[icon_name]
            tint = recolor_icon_flat(base_pil, color_for_teamup(teamup_name))
            if size:
                tint = tint.resize(size, Image.LANCZOS)
            _tk_cache[key] = ImageTk.PhotoImage(tint)
        return _tk_cache[key]
    
    def makeTeamColumn(team_colors):
        icon, score, bg_color, light = team_colors
        bd_color = adjust_color(main_frame, bg_color, 0.5)
        frame = tk.Frame(main_frame, bg=bg_color, padx=0, pady=0)
        title = tk.Frame(frame, bg=icon, padx=0,highlightbackground=bd_color,
                    highlightcolor=bd_color,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="sunken")
        title.pack(side="top", fill="both",expand=True,pady=(0,0))
        return frame, title 
    
    def makeEntryRow(parent_frame, bg_color):
        bd_color = adjust_color(parent_frame, parent_frame.cget("bg"), 0.5)
        row = tk.Frame(parent_frame, bg=bg_color,
                    highlightbackground=bd_color,
                    highlightcolor=bd_color,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="raised")
        row.pack(fill="x", pady=0,padx = 0)
        char = tk.Frame(row, bg=bg_color)
        char.pack(side='left', pady=0,padx = 0)
        teamups = tk.Frame(row, bg=bg_color,padx=0)
        teamups.pack(side='left', fill='y',pady=0,padx = 0)
        score = tk.Frame(row, bg=bg_color,padx=0)
        score.pack(side='left', fill='both',pady=0,padx = 0,expand=True,anchor='center')
        #score_title=tk.Frame(score, bg=bg_color)
        #score_title.pack(side='top', pady=0,padx = 0)
        frames = [row, char, teamups, score]
        
        
        return frames
    
    def makeEntryRow2(parent_frame, bg_color):
        row = tk.Frame(parent_frame, bg=bg_color)
        row.pack(fill="x", pady=0,padx = 0)
        return row
    
    def makeCharacterBox(parent_row, img, icon_color):
        bd_color = adjust_color(parent_row, parent_row.cget("bg"), 0.75)
        bd3_color = adjust_color(parent_row, parent_row.cget("bg"), 0.6)
        bd2_color = adjust_color(parent_row, parent_row.cget("bg"), 0.5)
        outer = tk.Label(parent_row, width=124, height=124,image=img, bg=bd3_color, 
                            highlightthickness=1,
                            highlightcolor=bd_color,
                            highlightbackground=bd_color,
                    borderwidth=2,
                    bd=2,
                    relief="sunken")
        outer.pack(side="left",anchor='c',padx=1)
        #outer.pack_propagate(False)
        parent_row.image = img
        return outer
    
    def makeCharacterBox2(parent_row, img, icon_color):
        bd_color = adjust_color(parent_row, parent_row.cget("bg"), 0.4)
        outer = tk.Label(parent_row, width=124, height=124,image=img, bg=icon_color, 
                            #highlightthickness=3,
                    highlightthickness=2,
                    highlightcolor=bd_color,
                    highlightbackground=bd_color, 
                    borderwidth=1,
                    bd=1,
                    relief="sunken")
        outer.pack(side="left",anchor='c',padx=(8,0),fill='both')
        #outer.pack_propagate(False)
        parent_row.image = img
        return outer
    
    def makeCounterLabel(row, score, bg_color,flag=False):
        bg_med = row.cget("bg")
        bg_darker = adjust_color(row, bg_med, 0.75)
        darker = adjust_color(row, bg_color, 0.5)
        #if flag:
            #tk.Label(row, text="Score", fg='white', bg=bg_color,
                 #font=("Saira Thin Medium", fonts[16], "normal")).pack(side='top',padx=10)
        scolor = change_color(score)
        la = tk.Label(row, text=f"{score:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=bg_color,
                 font=("CarbonRegular Italic", fonts[16], "normal"))
        la.pack(side='left',anchor='center',ipadx=2,padx=5,expand=True)
        return
    
    def makeCounterLabel2(row, score, bg_color):
        scolor = change_color(score)
        tk.Label(row, text=f"{score:+}", highlightthickness=2,
                 highlightbackground=bord_color, fg=scolor, bg=bg_color,
                 font=("Saira Thin Medium", fonts[16], "normal")).pack(side="left", padx=(0,10))
        return
    
    def makeScoreFrames(parent_column, team_colors):
        icon_color, score_color, bg_color, stats_color = team_colors
        bd_color = adjust_color(parent_column, bg_color, 0.5)
        team_stats = tk.Frame(parent_column, bg=bg_color)#highlightbackground=bd_color,
                    #highlightcolor=bd_color,
                    #highlightthickness=1,
                    #borderwidth=2,
                    #bd=2,
                    #relief="sunken")
        team_stats.pack(fill="x",padx = 0,pady=0)

        #Stats
        bd_color2 = adjust_color(parent_column, stats_color, 0.85)
        stat = tk.Frame(team_stats, bg=stats_color,highlightbackground=bd_color,
                    highlightcolor=bd_color2,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="raised")
        stat.pack(fill="x",anchor='n', side="top",expand=False)
        #add_seperator(stat, ["bottom"],None,(5,0))
        #Stat scores - Original
        stsc = tk.Frame(team_stats, bg=bg_color,highlightbackground=bd_color,
                    highlightcolor=bd_color,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="raised")
        stsc.pack(fill="x",side="top",expand=True)
        
        #teamups - Original Score
        tu = tk.Frame(team_stats, bg=bg_color,highlightbackground=bd_color,
                    highlightcolor=bd_color,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="raised")
        tu.pack(fill="x",side="top",expand=True)
        #add_seperator(tu_orig, ["bottom"])

        #total - Original Score
        bd_color = adjust_color(parent_column, icon_color, 0.5)
        tot = tk.Frame(team_stats, bg=icon_color,highlightbackground=bd_color,
                    highlightcolor="#fcd601",#bd_color,
                    highlightthickness=1,
                    borderwidth=2,
                    bd=2,
                    relief="raised")
        tot.pack(fill="x", side="top", ipady=8,expand=True)
        return [team_stats, stat, stsc, tu, tot]
    
    def makeScoreFrameLabels(frames, scores, team_colors, red=False):
        if not red:
            team_stats, stat, stsc, tu, tot = frames
            icon_color, score_color, bg_color, stats_color = team_colors
            score, teamup_score, stat_score = scores
            bg_med = stsc.cget("bg")
            bg_darker = adjust_color(stsc, bg_color, 0.75)
            darker = adjust_color(stsc, bg_color, 0.5)
            tk.Label(stsc, text="Stats Score: ", font=("Saira Thin Medium", fonts[16], "normal"), fg="white", bg=bg_color).pack(side="left",padx=(10,0))
            scolor = change_color(stat_score)
            tk.Label(stsc, text=f"{stat_score:+}",  relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="right", padx=20)
            bg_med = tu.cget("bg")
            bg_darker = adjust_color(tu, bg_color, 0.75)
            darker = adjust_color(tu, bg_color, 0.5)
            tk.Label(tu, text="Teamups Score: ", font=("Saira Thin Medium", fonts[16], "normal"), fg="white", bg=bg_color).pack(side="left",padx=(10,0))
            scolor = change_color(teamup_score)
            tk.Label(tu, text=f"{teamup_score:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="right", padx=20)
            bg_med = tot.cget("bg")
            bg_darker = adjust_color(tot, icon_color, 0.75)
            darker = adjust_color(tot, bg_color, 0.5)
            tk.Label(tot, text="Total Score: ", font=("Rajdhani", fonts[24], "bold"), fg=yellow, bg=icon_color).pack(side="left",padx=(10,0))
            scolor = change_color(score)
            #scolor = adjust_color(tot, scolor, 0.8)
            tk.Label(tot, text=f"{score:+}", relief='raised',bd=2,borderwidth=2,highlightthickness=2,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=bg_color,
                        font=("CarbonBold Italic", fonts[22], "bold", "roman")).pack(side="right", padx=15)
            
            return
        else:
            team_stats, stat, stsc, tu, tot = frames
            icon_color, score_color, bg_color, stats_color = team_colors
            scores1, scores2, scores3, teamup_scores, stat_scores, stat_scores2, stat_scores3 = scores

            bg_med = stsc.cget("bg")
            bg_darker = adjust_color(stsc, bg_color, 0.75)

            tk.Label(stsc, text="Stats Scores:", font=("Saira Thin Medium", fonts[16], "normal"), fg="white", bg=bg_color).pack(side="left",padx=(10,0))
            scolor = change_color(stat_scores3)
            tk.Label(stsc, text=f"{stat_scores3:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="right", padx=5,expand=True)
            scolor = change_color(stat_scores2)
            tk.Label(stsc, text=f"{stat_scores2:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="right", padx=5,expand=True)
            scolor = change_color(stat_scores)
            tk.Label(stsc, text=f"{stat_scores:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="right", padx=5,expand=True)
            bg_med = tu.cget("bg")
            bg_darker = adjust_color(tu, bg_color, 0.75)
            tk.Label(tu, text="Teamups Score:", font=("Saira Thin Medium", fonts[16], "normal"), fg="white", bg=bg_color).pack(side="left",padx=(10,0))
            scolor = change_color(teamup_scores)
            tk.Label(tu, text=f"{teamup_scores:+}", relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=score_color,
                        font=("CarbonRegular", fonts[18], "normal")).pack(side="left", padx=5,expand=True)
            bg_med = tot.cget("bg")
            bg_darker = adjust_color(tot, icon_color, 0.75)
            tk.Label(tot, text="Total Scores:", font=("Rajdhani", fonts[24], "bold"), fg=yellow, bg=icon_color).pack(side="left",padx=(10,0))
            scolor = change_color(scores3)
            #scolor = adjust_color(tot, scolor, 0.8)
            tk.Label(tot, text=f"{scores3:+}", relief='raised',bd=2,borderwidth=2,highlightthickness=2,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=bg_color,
                        font=("CarbonBold Italic", fonts[22], "bold", "roman")).pack(side="right", padx=5)
            scolor = change_color(scores2)
            #scolor = adjust_color(tot, scolor, 0.8)
            tk.Label(tot, text=f"{scores2:+}", relief='raised',bd=2,borderwidth=2,highlightthickness=2,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=bg_color,
                        font=("CarbonBold Italic", fonts[22], "bold", "roman")).pack(side="right", padx=5)
            scolor = change_color(scores1)
            #scolor = adjust_color(tot, scolor, 0.8)
            tk.Label(tot, text=f"{scores1:+}", relief='raised',bd=2,borderwidth=2,highlightthickness=2,
                 highlightbackground=bg_darker, highlightcolor=bg_darker, fg=scolor, bg=bg_color,
                        font=("CarbonBold Italic", fonts[22], "bold", "roman")).pack(side="right", padx=5)

    main_frame = tk.Frame(win, bg="#1C2026")
    main_frame.pack(padx=0, pady=0,fill="both", expand=True)
    light_blue = "#456093" 
    dark_blue = "#2C334B"
    orig_icon = "#263557"
    suggest_dark = "#354569"
    suggest_blue = "#6D9EC2"
    alt_dark = "#2A4A32"
    alt_light = "#579967"
    light_red = "#A15444"
    dark_red = "#6B382E"
    bord_color = "#1C2026"
    blue_score = "#456093"
    suggest_score = "#465C8C"
    green_score = "#41734D"
    red_score = "#854539"

    orig_dark = "#2A3552"
    orig_med = "#2E4069"
    orig_counter = "#2F3A59"
    orig_tu_stat = "#31416E"
    origbg = "#283559"
    origtot = "#3E5685"
    origstats = "#456093"
    newbg = "#556FA8"
    altbg = "#4A8258"
    redbg = "#A15445"
    yellow = "#FFC90E"

    orig_stats_color = origstats
    orig_bg_color = '#405891'
    orig_icon_color = orig_icon
    orig_score_color = orig_counter
    orig_stat_number_color = orig_bg_color
    orig_tu_stat_score_color = orig_tu_stat

    orig_stats_color = '#6B8DC7'
    orig_bg_color = '#455E9C'
    orig_icon_color = '#30416B'
    orig_score_color = '#364B7C'
    orig_tu_stat_score_color = orig_score_color

    new_stats_color = "#6B8BA6"
    new_bg_color = "#456587"
    new_icon_color = "#2E4359"
    new_score_color = "#3B5673"
    new_stat_number_color = new_bg_color
    new_tu_stat_score_color = new_score_color

    alt_stats_color = "#6EA676"
    alt_bg_color = "#41734D"
    alt_icon_color = "#2A4A32"
    alt_score_color = "#345C3D"
    alt_stat_number_color = alt_bg_color
    alt_tu_stat_score_color = alt_score_color

    red_stats_color = "#DE8776"
    red_bg_color = "#A35546"
    red_icon_color = "#703B2F"
    red_score_color = "#854539"
    red_stat_number_color = red_bg_color
    red_tu_stat_score_color = red_score_color

    orig_colors = [orig_icon_color, orig_score_color, orig_bg_color, orig_stats_color]
    new_colors = [new_icon_color, new_score_color, new_bg_color, new_stats_color]
    alt_colors = [alt_icon_color, alt_score_color, alt_bg_color, alt_stats_color]
    red_colors = [red_icon_color, red_score_color, red_bg_color, red_stats_color]

    original_frame, original_title = makeTeamColumn(orig_colors)
    suggestion_frame, sug_title = makeTeamColumn(new_colors)
    alt_frame, alt_title = makeTeamColumn(alt_colors)
    red_frame, red_title = makeTeamColumn(red_colors)

    initialize_hide_pass(toggle_hide, None, main_frame,hide_btn2)

    original_frame.grid(row=0, column=0, sticky="nw")
    suggestion_frame.grid(row=0, column=1, sticky="nw")
    alt_frame.grid(row=0, column=2, sticky="nw")
    red_frame.grid(row=0, column=3, sticky="nw")

    if config.dex:
        string = "Dexerto Counters"
    else:
        string = "Best Replacements"

    def add_seperator(parent, sides, befor=None,tupple=False):
        for side in sides:
            fill = "x" if side in ("top", "bottom") else "y"
            y = 10 if side in ("top", "bottom") else 0
            x = 10 if side in ("left", "right") else 0
            if tupple:
                y = tupple
            
            strip = tk.Frame(parent, bg=adjust_color(parent, parent.cget("bg"), 0.4), height=2)
            strip.pack(side=side, fill=fill,expand=True, anchor="s", pady=y, padx=x, before=befor)

    

    tk.Label(original_title, text="Current Team", font=("Rajdhani", fonts[22], "bold"), fg="white", bg=orig_dark).pack(fill="both",expand=True)
    tk.Label(sug_title, text=string, font=("Rajdhani", fonts[22], "bold"), fg="white", bg=new_icon_color).pack(fill="both",expand=True)
    tk.Label(alt_title, text="Alternate Team", font=("Rajdhani", fonts[22], "bold"), fg="white", bg=alt_icon_color).pack(fill="both",expand=True)
    tk.Label(red_title, text="Enemy Team", font=("Rajdhani", fonts[22], "bold"), fg="white", bg=red_icon_color).pack(fill="both",expand=True)
    score_totals_list = []
    
    

    for i in range(1, 7):
        # Blue column (col 1)
        if i == 6:
            tup = (5,0)
        else:
            tup = False
        b_member = getattr(blue_result, str(i))
        s_member = getattr(suggest_result, str(i))
        a_member = getattr(alt_result, str(i))
        r_member = getattr(red_result, str(i))

        orig_name = b_member.name
        orig_score = b_member.matchup_score
        orig_teamups = b_member.teamup_names
        new_teamups = s_member.teamup_names
        alt_teamups = a_member.teamup_names
        red_teamups = r_member.teamup_names
        new_name = s_member.name
        new_score = s_member.matchup_score
        alt_name = a_member.name
        alt_score = a_member.matchup_score
        red_name = r_member.name
        red_score1 = r_member.matchup_score
        red_score2 = r_member.matchup_score2
        red_score3 = r_member.matchup_score3
        
        
        frames = makeEntryRow(original_frame, orig_bg_color)
        # === Column 1: Original Blue ===
        #row_orig = tk.Frame(original_frame, bg=orig_med)
        #row_orig.pack(fill="x", pady=0,padx = 0)
        row_orig, char_orig, teamups_orig, score_orig = frames

        bd_color = adjust_color(row_orig, row_orig.cget("bg"), 0.4)
        orig_img = get_image(orig_name)
        key = "orig"
        if orig_img:
            
            outer = makeCharacterBox(char_orig, orig_img, orig_icon_color)
                                                                                                    

        
        add_teamup_icons(teamups_orig,orig_teamups,orig_icon_color)
        makeCounterLabel(score_orig, orig_score, orig_score_color)
                                                                                                   
        frames = makeEntryRow(suggestion_frame, new_bg_color)
        
        row_sugg, char_sugg, teamups_sugg, score_sugg = frames
        if s_member:
           
            sugg_img = get_image(new_name)
            if sugg_img:
                outer = makeCharacterBox(char_sugg, sugg_img, new_icon_color)
                                                                                    
            
            add_teamup_icons(teamups_sugg,new_teamups,new_icon_color)
            makeCounterLabel(score_sugg, new_score, new_score_color)
            # Suggestion score
                                                                                    
            

        else:
            # No replacement or replacement == original — reserve space
            spacer = tk.Frame(row_sugg, width=130 + 8, height=130 + 22, bg=new_bg_color)
            #spacer.pack_propagate(False)
            spacer.pack(side="left",pady=0,fill='both')
            
            add_teamup_icons(row_sugg,new_teamups,new_icon_color)
            # Suggestion score
            scolor = change_color(new_score)
            tk.Label(row_sugg, text=f"{new_score:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=new_score_color,
                     font=("Courier New", fonts[16], "bold")).pack(side="left", padx=(0,10))
            
            
        alt = a_member
        frames = makeEntryRow(alt_frame, alt_bg_color)
        row_alt, char_alt, teamups_alt, score_alt = frames                                                                                                    # row_alt = tk.Frame(alt_frame, bg=alt_bg_color)
                                                                                                            # row_alt.pack(fill="x", pady= 0,padx=0)
        if alt:
            alt_img = get_image(alt_name)
            if alt_img:
                outer = makeCharacterBox(char_alt, alt_img, alt_icon_color)
                                                                                                                        
                row_alt.image = alt_img
            
            add_teamup_icons(teamups_alt,alt_teamups,alt_icon_color)
            makeCounterLabel(score_alt, alt_score, alt_score_color)
                                                                                                                       
           ## add_seperator(row_alt, ["bottom"],outer,tup)
        else:
            tk.Label(row_alt, text="No alt", fg="white", bg=alt_bg_color).pack()

        # === Column 4: Red Team ===
        frames = makeEntryRow(red_frame, red_bg_color)
        red_row, char_red, teamups_red, score_red = frames                                                                                                            # red_row = tk.Frame(red_frame, bg=red_bg_color)
                                                                                                                    # red_row.pack(fill="x", pady=0, padx=0)

        red_img = get_image(red_name)
        if red_img:
            outer = makeCharacterBox(char_red, red_img, red_icon_color)
                                                                                                                    
            #outer.pack_propagate(False)
            red_row.image = red_img
        
        add_teamup_icons(teamups_red,red_teamups,red_icon_color)
        
                                                                                                        # scolor = "white"
                                                                                                        # scolor = change_color(red_score1)
       # add_seperator(red_row, ["bottom"],outer,tup)
        
        makeCounterLabel(score_red, red_score1, red_score_color,True)
        makeCounterLabel(score_red, red_score2, red_score_color)
        makeCounterLabel(score_red, red_score3, red_score_color)
                                                                                                                                    
        
        red_scores1 = round(red_scores1,1)
        red_scores2= round(red_scores2,1)
        red_scores3= round(red_scores3,1)
        alt_scores= round(alt_scores,1)
        new_scores=round(new_scores,1)
        origs_score= round(origs_score,1)

        
        

    orig_frames = makeScoreFrames(original_frame, orig_colors)
    orig_team_stats, stat_orig, stsc_orig, tu_orig, tot_orig = orig_frames
    orig_score_list = [origs_score, origs_teamup_score, origs_stat_score]
    makeScoreFrameLabels(orig_frames, orig_score_list, orig_colors)                                                                                                                # orig_team_stats = tk.Frame(original_frame, bg=orig_med)
                                                                                                                    
    new_frames = makeScoreFrames(suggestion_frame, new_colors)
    new_team_stats, stat_new, stsc_new, tu_new, tot_new = new_frames
    new_score_list = [new_scores, new_teamup_scores, new_stat_scores]
    makeScoreFrameLabels(new_frames, new_score_list, new_colors)

                                                                                                                                   
    alt_frames = makeScoreFrames(alt_frame, alt_colors)
    alt_team_stats, stat_alt, stsc_alt, tu_alt, tot_alt = alt_frames
    alt_score_list = [alt_scores, alt_teamup_scores, alt_stat_scores]
    makeScoreFrameLabels(alt_frames, alt_score_list, alt_colors)




    

                                                                                                                       
    red_frames = makeScoreFrames(red_frame, red_colors)
    red_team_stats, stat_red, stsc_red, tu_red, tot_red = red_frames
    red_score_list = [red_scores1,red_scores2,red_scores3, red_teamup_scores, red_stat_scores, red_stat_scores2, red_stat_scores3]
    makeScoreFrameLabels(red_frames, red_score_list, red_colors, True)

   
    
    def get_color(value, stat_type, thresholds):
        t = thresholds[stat_type]
        avg = t["avg"]
        tolerance = 0.005 * avg  # 5% of average
    
        # First: check if value is within ±5% of avg
        if abs(value - avg) <= tolerance:
            return "#ffffff"  # white
    
        # Then use original logic
        if value <= t["low_mid"]:
            return "#ff3c3c"  # red
        elif value <= avg:
            return "#FFa800"  # yellow
        elif value <= t["high_mid"]:
            return "#5de791"  # green
        else:
            return "#3ecbff"  # blue

    
    def build_color_thresholds(results):
        # results is an iterable of team objects
        stats = {"dps": [], "hps": [], "health": []}
    
        # Collect totals from each team
        for team in results:
            stats["dps"].append(team.dps)
            stats["hps"].append(team.hps)
            stats["health"].append(team.health)
    
        thresholds = {}
        for key, values in stats.items():
            min_v = min(values)
            max_v = max(values)
            avg = sum(values) / len(values)
            half_range = (max_v - min_v) / 2
    
            thresholds[key] = {
                "min": min_v,
                "max": max_v,
                "avg": avg,
                "low_mid": avg - 0.5 * half_range,
                "high_mid": avg + 0.5 * half_range
            }
    
        return thresholds

    
            
              

    
    

    def create_stat_frames(frame, color, num, back, bg2):
        

        # --- 3 columns on one row ---
        row = tk.Frame(frame, bg=back)
        row.pack(fill="x", side="top", pady=(2, 8))

        # make columns expand evenly
        for i in range(3):
            row.grid_columnconfigure(i, weight=1, uniform="stats")

        # pick team & colors
        index = 3 if color == "Red" else int(num) - 1
        teaam = results[index]
        dps, hps, health = teaam.dps, teaam.hps, teaam.health
        fg_dps   = get_color(dps,    "dps",    thresholds)
        fg_hps   = get_color(hps,    "hps",    thresholds)
        fg_health= get_color(health, "health", thresholds)

        # helper to build one column
        def make_col(col, label_txt, value, fg):
            cell = tk.Frame(row, bg=back)
            #bg_med = back
            bg_darker = adjust_color(row, back, 0.75)
            bg_lighter = adjust_color(row, bg2, 1.15)
            #bg2 = adjust_color(row, back, 0.75)
            cell.grid(row=0, column=col, padx=12, sticky="n")
            tk.Label(
                cell, text=label_txt, font=("Saira Thin Medium", fonts[15], "normal"),
                fg="white", bg=back
            ).pack()
            tk.Label(
                cell, text=value, font=("CarbonRegular Italic", fonts[16], "normal"),
                fg=fg, bg=bg_lighter, relief='sunken',bd=2,borderwidth=2,highlightthickness=1,
                 highlightbackground=bg_darker, highlightcolor=bg_darker,
                padx=6, pady=1
            ).pack(pady=(6, 0))

        # build the three columns
        make_col(0, "Dps:",    dps,    fg_dps)
        make_col(1, "Hps:",    hps,    fg_hps)
        make_col(2, "Health:", health, fg_health)        
    
    #  
    

                                                                                                    
    thresholds = build_color_thresholds(results)
    
    create_stat_frames(stat_orig,"Blue","1",orig_stats_color,orig_stat_number_color)
    create_stat_frames(stat_new,"Blue","2",new_stats_color,new_stat_number_color)
    create_stat_frames(stat_alt,"Blue","3",alt_stats_color,alt_stat_number_color)
    create_stat_frames(stat_red,"Red","1",red_stats_color,red_stat_number_color)
    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()
    win.update_idletasks()
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, win.title())
    #make_clickthrough()
    win.geometry("")
    root.mainloop()
    return return_data.get("teams")


def show_countdown():
    global indicator_label
    root = tk.Tk()
    root.title("Scoreboard Scan in...")
    root.configure(bg="#2C334B")
    root.overrideredirect(True)
    screen_width = root.winfo_screenwidth()
    x = screen_width // 2
    root.geometry(f"200x100+{x}+0")
    root.attributes("-topmost", True)
    indicator_label = tk.Label(root, text="", fg="white", bg="#2C334B", font=("Arial", fonts[8]))
    indicator_label.pack(anchor="w")
    labela = tk.Label(root, text="Hold\nTAB",bg="#2C334B", fg="yellow",font=("Lucida Console", fonts[14],"bold"))
    labela.pack(expand=True,anchor="center",pady=0)
    label = tk.Label(root, text="",bg="#2C334B", fg="white",font=("Arial", fonts[20],"bold"))
    label.pack(expand=True,pady=5)

    def update_countdown(i):
        if i > 0:
            if not is_clickthrough:
                toggle_clickthrough()
            label.config(text=str(i))
            root.update()
            root.after(1000, update_countdown, i - 1)
        else:
            if is_clickthrough:
                toggle_clickthrough()
            root.destroy()

    update_countdown(3)
    
    root.mainloop()

def get_image_from_map(image_map, base_name, full_name):
    variants = image_map.get(base_name, [])
    for variant in variants:
        if variant["name"] == full_name:
            return variant["image"]
    return image_map["Default"][0]["image"]  # fallback

def change_character_dropdown(match, image_map, label_widget):
    top = tk.Toplevel()
    top.attributes("-topmost", True)
    top.title("Change Character")
    top.grab_set()  # Make it modal

    tk.Label(top, text=f"Current: {match.name}").pack(pady=(10, 2))

    hero_names = sorted(image_map.keys())
    selected_hero = tk.StringVar(value=match.name)

    # Image preview area
    img_label = tk.Label(top)
    img_label.pack(pady=5)

    def update_image(*args):
        hero = selected_hero.get()
        img_obj = image_map.get(hero, image_map.get("Default"))
        if img_obj:
            preview = img_obj.copy()
            preview.thumbnail((128, 128))
            photo = ImageTk.PhotoImage(preview)
            img_label.configure(image=photo)
            img_label.image = photo
        else:
            img_label.configure(text="No image found", image="")

    selected_hero.trace_add("write", update_image)

    dropdown = tk.OptionMenu(top, selected_hero, *hero_names)
    dropdown.pack(pady=5)

    def submit():
        match.name = selected_hero.get()
        # Refresh the image in the original GUI
        new_img = image_map.get(match.name, image_map.get("Default")).copy()
        new_img.thumbnail((128, 128))
        new_photo = ImageTk.PhotoImage(new_img)
        label_widget.configure(image=new_photo)
        label_widget.image = new_photo
        top.destroy()

    tk.Button(top, text="OK", command=submit).pack(pady=(0, 10))

    update_image()
    top.wait_window()  # Block interaction with main window

def convert_color(value):
    mapping = {
        "#456093": "#2C334B",  # bg_c blue
        "#A15444": "#6B382E",  # bg_c red
    }
    return mapping.get(value, value)  # Return the mapped value, or original if not found

def change_character(match, image_map, label_widget,bg_c):
    import tkinter as tk
    from PIL import Image, ImageTk
    bg_dark = convert_color(bg_c)
    top = tk.Toplevel()
    top.configure(bg=bg_dark)
    top.attributes("-topmost", True)
    top.title("Change Character")
    top.grab_set()  # Make it modal
    topb = tk.Frame(top, bg=bg_dark)
    topb.pack( side="top")
    left = tk.Frame(topb, bg=bg_dark)
    left.pack(fill="y", padx=15,side="left")

    right = tk.Frame(topb, bg=bg_dark)
    if match.score >= 55:
        right.pack(fill="y",padx=15, side="right")

    tk.Label(left, fg="white",bg=bg_dark,text=f"Current: {match.name}",font=("Arial",12,"bold")).pack(pady=(10, 2), anchor="center")

    selected_hero = tk.StringVar(value=match.name)

    # Image preview area
    img_label = tk.Label(left,bg=bg_c,relief="raised")
    img_label.pack(pady=5, anchor="center")
    if match.score >= 55:
        tk.Label(right,fg="white",bg=bg_dark,text=f"Scanned:",font=("Arial",12,"bold"), anchor="s").pack(pady=(10, 2), anchor="s")
        img_label2 = tk.Label(right,bg=bg_c,relief="raised", anchor="s")
        img_label2.pack(pady=5, anchor="s")

    def update_image(*args):
        hero = selected_hero.get()
        img_obj = image_map.get(hero, image_map.get("Default"))
        if img_obj:
            preview = img_obj.copy()
            preview.thumbnail((128, 128))
            photo = ImageTk.PhotoImage(preview)
            img_label.configure(image=photo, bg = bg_c)
            img_label.image = photo
        else:
            img_label.configure(text="No image found", image="")
        if match.score >= 55:
            cropped = match.image
            cropped.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(cropped)
            
            img_label2.configure(image=img2, bg = bg_c)
            img_label2.image = img2

    selected_hero.trace_add("write", update_image)

    # --- 6x6 Icon Grid ---
    grid_frame = tk.Frame(top, bg=bg_dark)
    grid_frame.pack(pady=10)

    thumbnails = {}
    max_cols = 6
    row = col = 0

    for hero_name in sorted(image_map.keys()):
        if hero_name == "Unknown":
            continue
        img_obj = image_map[hero_name]
        if not img_obj:
            continue

        # Make 64x64 thumbnail
        thumb = img_obj.copy()
        thumb.thumbnail((64, 64))
        thumb_img = ImageTk.PhotoImage(thumb)
        thumbnails[hero_name] = thumb_img  # Prevent garbage collection

        def make_click_callback(name=hero_name):
            def callback():
                selected_hero.set(name)  # Triggers preview update
                submit()
            return callback

        btn = tk.Button(grid_frame, bg=bg_c, image=thumb_img, command=make_click_callback(), width=64, height=64)
        btn.grid(row=row, column=col, padx=3, pady=3)

        def on_enter(event, name=hero_name, button=btn):
            img_obj = image_map[name]
            thumb = img_obj.copy()
            thumb.thumbnail((64, 64))
            base_img = thumb.convert("RGBA")
            overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))
            combined = Image.alpha_composite(base_img, overlay)
            hover_img = ImageTk.PhotoImage(combined)

            button.configure(image=hover_img)
            button.image = hover_img  # prevent garbage collection

        def on_leave(event, name=hero_name, button=btn):
            img_obj = image_map[name]
            thumb = img_obj.copy()
            thumb.thumbnail((64, 64))
            normal_img = ImageTk.PhotoImage(thumb)

            button.configure(image=normal_img)
            button.image = normal_img  # prevent garbage collection
            

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        col += 1
        if col >= max_cols:
            col = 0
            row += 1


    def submit():
        match.name = selected_hero.get()
        match.fullname = match.name  # Update full name if needed
        # Refresh the image in the original GUI
        new_img = image_map.get(match.name, image_map.get("Default")).copy()
        new_img.thumbnail((128, 128))
        new_photo = ImageTk.PhotoImage(new_img)
        label_widget.configure(image=new_photo)
        label_widget.image = new_photo
        top.destroy()

    tk.Button(top, text="OK", command=submit).pack(pady=(0, 10))

    update_image()
    top.wait_window()  # Block interaction with main window

def show_team_comparison_gui(team1_matches, team2_matches,map):
    global indicator_label
    img2 = None
    cropped = None
    indicator_label = None
    root = tk.Tk()
    null = None
    screen_width = root.winfo_screenwidth()
    x = screen_width // 2
    root.geometry(f"+{x}+0")
    root.withdraw()  # Hide root window
    result = {"blue": [], "red": []}
    win = tk.Toplevel(root)
    win.geometry(f"+{x}+0")
    resultdict = {"blue": [], "red": []}
    result = {"blue": [], "red": []}
    win.title("Team Matchup Comparison")
    win.configure(bg="#1C2026")
    win.attributes("-topmost", True)
    win.grab_set()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    assets_folder = os.path.join(script_dir, "assets_characters")

    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead

    # Set layout frame
    main_frame = tk.Frame(win, bg="#1C2026")
    main_frame.pack(padx=10, pady=10)

    # Create team frames (left + center + right)
    left_frame = tk.Frame(main_frame, bg="#2C334B", padx=5, pady=5)
    left_frame.grid(row=0, column=0, sticky="n")
    center_frame = tk.Frame(main_frame, bg="#1C2026", padx=10)
    center_frame.grid(row=0, column=1, sticky="n")
    right_frame = tk.Frame(main_frame, bg="#6B382E", padx=5, pady=5)
    right_frame.grid(row=0, column=2, sticky="n")
    #indicator_label = tk.Label(center_frame, text="", fg="white", bg="#1C2026", font=("Arial", fonts[12]))
    #indicator_label.pack(side="top")
    # Team labels
    tk.Label(left_frame, text="Team 1", font=("Arial", fonts[14], "bold"), fg="white", bg="#2C334B").pack(fill=tk.X)
    tk.Label(right_frame, text="Team 2", font=("Arial", fonts[14], "bold"), fg="white", bg="#6B382E").pack(fill=tk.X)

    # Add player frames for each match
    def add_match_widget(frame, match, bg_color):
        outer = tk.Frame(frame, width=132, height=132, bg=bg_color, highlightthickness=2)
        outer.pack_propagate(False)
        outer.pack(pady=3)
        cropped = None
        img2 = None

        # Adjust border color if score > 50
        if match.score >= 55:
            outer.config(highlightbackground="yellow",highlightthickness= 4)
            cropped = match.image
            cropped.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(cropped)
            
        else:
            outer.config(highlightbackground="black")

        img_obj = get_image_from_map(map, match.name, match.fullname)
        resized = img_obj.copy()
        resized.thumbnail((128, 128))
        img = ImageTk.PhotoImage(resized)
        if cropped:
            resized2 = cropped.copy()
            resized2.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(resized2)
                
        

        if img:
            label = tk.Label(outer, image=img, bg=bg_color)
            label.image = img  # Prevent garbage collection
        else:
            label = tk.Label(outer, text=match.name, fg="white", bg=bg_color)
        
        label.pack()
        def on_click(event, match=match, label=label, bg=bg_color):
            change_character(match, image_map, label, bg)

        label.bind("<Button-1>", on_click)
        # Hover effect – store a darkened image to use on hover
        def create_overlay(image):
            # Ensure consistent image size and mode
            base = image.copy().convert("RGBA")
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 100))  # semi-transparent black
            combined = Image.alpha_composite(base, overlay)
            return ImageTk.PhotoImage(combined)

        def on_enter(event):
            hero = match.name
            #img_obj = image_map.get(hero, image_map.get("Default"))
            if cropped:
                resized = cropped.copy()
                resized = cropped.resize((128, 128), Image.LANCZOS)
                
            else:
                img_obj = get_image_from_map(map, match.name, match.fullname)
                resized = img_obj.copy()
                resized.thumbnail((128, 128))
            base_img = resized.convert("RGBA")
            overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))
            combined = Image.alpha_composite(base_img, overlay)
            hover_img = ImageTk.PhotoImage(combined)

            label.configure(image=hover_img)
            label.image = hover_img
            outer.config(bg="#2a2a2a")

        def on_leave(event):
            hero = match.name
            img_obj = get_image_from_map(map, match.name, match.fullname)
            resized = img_obj.copy()
            resized.thumbnail((128, 128))
            normal_img = ImageTk.PhotoImage(resized)

            label.configure(image=normal_img)
            label.image = normal_img
            outer.config(bg=bg_color)

        def on_click(event, match=match, label=label):
            change_character(match, image_map, label)

        label.bind("<Enter>", on_enter)
        label.bind("<Leave>", on_leave)

    # Populate both teams using iteration and single match
    for match in team1_matches:
        add_match_widget(left_frame, match, "#456093")

    for match in team2_matches:
        add_match_widget(right_frame, match, "#A15444")
    def on_save():
        resultdict["blue"] = [
    {"base_name": m.name, "full_name": m.fullname}
    for m in team1_matches
]
        resultdict["red"] = [
    {"base_name": m.name, "full_name": m.fullname}
    for m in team2_matches
]
        result["blue"] = [m.name for m in team1_matches]
        result["red"] = [m.name for m in team2_matches]
        win.destroy()
    # Save button in center frame
    save_btn = tk.Button(center_frame,fg="white", bg="#3B3B3B",text="Save", command=on_save,font=("Arial", fonts[12],"bold"), width=6,cursor="hand2")
    save_btn.pack(pady=100)
    a = tk.Label(center_frame,bg="#1C2026", text="Click Hero\nto change\nCharacter",fg="white",font=("Arial", fonts[12],"bold"), width=10)
    a.pack(pady=10)
    
    win.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, win.title())
    
    #make_clickthrough()
    
    win.wait_window()  # Block until win is destroyed
    root.destroy()     # Fully close hidden root window
    return result["blue"], result["red"], image_map, resultdict["blue"], resultdict["red"]
    return result["blue"], result["red"], image_map



def create_player_frame(root, player, image_map):
    if player.hero1 not in image_map:
        player.hero1 = "Question"
    if player.hero2 not in image_map:
        player.hero2 = "Question"
        
    def createImage(frame, player_img, size, bg, param):
        img_raw = image_map.get(player_img) or image_map.get("Default")
        if img_raw:
            resized = img_raw.copy()
            resized.thumbnail(size)  # Resize to 32x32
            img = ImageTk.PhotoImage(resized)
            label = tk.Label(frame,bg=bg, image=img)
            label.image = img  # Prevent garbage collection
            label.pack(**param)
            return label
        else:
            return False
    
    
    outer = tk.Frame(root, width=330, height=400, borderwidth=1, relief="flat")
    outer.pack(side="left", fill="x",padx=0, pady=0)
    #outer.pack_propagate(False)

    # Top bar: name + rank icon
    top_bar = tk.Frame(outer, bg="#2b2e41",height=65,relief='raised', borderwidth=3, bd=3)
    top_bar.pack(side='top',fill="both",expand=True)
    #top_bar.pack_propagate(False)
    
    

    
    name_label = tk.Label(top_bar, text=player.name,bg="#2b2e41", fg="#E4EAFF",font=fonttk(rajdhani_medium,20,'normal'),anchor="w")
    name_label.place(x=8, y=14)
    pack = {"side":"right", "padx":0,"pady":0,"anchor":'e'}
  
    rank_label = createImage(top_bar, player.rank,(72,72),"#2b2e41",pack)
    #rank_img_raw = image_map.get(player.rank) or image_map.get("Default")
    #if rank_img_raw:
       # resized = rank_img_raw.copy()
       # resized.thumbnail((72,72))  # Resize to 32x32
      #  rank_img = ImageTk.PhotoImage(resized)
       # rank_label = tk.Label(top_bar,bg="#2b2e41", image=rank_img)
        #rank_label.image = rank_img  # Prevent garbage collection
        #rank_label.pack(side="right", padx=0,anchor='e')
    
    mvp_icon = False
    if player.ace:
        mvp_label = createImage(top_bar, 'MVP2',(72,52),'#2b2e41',pack)
        #mvp_icon = image_map.get('MVP2') or image_map.get("Default")
    #if mvp_icon:
        #resized = mvp_icon.copy()
        #resized.thumbnail((72,52))
        #mvp_img = ImageTk.PhotoImage(resized)
        #mvp_label = tk.Label(top_bar,bg="#2b2e41",image=mvp_img)
        #mvp_label.image = mvp_img
        #mvp_label.pack(side='right', padx=0, anchor='e')
 
    #top_bar.image = rank_img

    # Main content split horizontally
    content = tk.Frame(outer)
    content.pack(fill="both", expand=True)

    # Left (hero images stacked)
    left_frame = tk.Frame(content, bg="#151426",width=150)
    left_frame.pack(side="left", fill="y")
    #left_frame.pack_propagate(False)
    
    left_frame_top = tk.Frame(left_frame,bg="#1c1b2d", height=150)
    left_frame_top.pack(side="top", fill="x",pady=(0,5))
    #left_frame_top.pack_propagate(False)
    
    hero1_label = createImage(left_frame_top, player.hero1, (136,136),'#1c1b2d',{'pady':0})
    #hero1_img = image_map.get(player.hero1, image_map.get("Default"))
    #resized = hero1_img.copy()
    #resized.thumbnail((136,136))
    #hero1_img = ImageTk.PhotoImage(resized)
    #hero1_label = tk.Label(left_frame_top, bg="#1c1b2d",image=hero1_img)
    #hero1_label.pack(pady=0)
   # left_frame_top.image1 = hero1_img
    
    left_frame_bot = tk.Frame(left_frame, bg="#1c1b2d",height=150)
    left_frame_bot.pack(side="bottom", fill="x",pady=(5,0))
    #left_frame_bot.pack_propagate(False)
    
    if player.hero2 == "None" or not player.hero2:
        pl2 = False
        player.hero2 = "Question"
    else:
        pl2 = True
        hero2_label = createImage(left_frame_bot, player.hero2, (136,136),'#1c1b2d',{'pady':0})

 #   hero2_img = image_map.get(player.hero2, image_map.get("Default"))
#    resized = hero2_img.copy()
 #   resized.thumbnail((136,136))
 #   hero2_img = ImageTk.PhotoImage(resized)
   # hero2_label = tk.Label(left_frame_bot,bg="#1c1b2d", image=hero2_img)
  #  hero2_label.pack(pady=0)
   # left_frame_bot.image = hero2_img

    # Right (text stacked)
    right_frame = tk.Frame(content, bg="#151426",width=180)
    right_frame.pack(side="right", fill="y")
    #right_frame.pack_propagate(False)
    
    right_frame_top = tk.Frame(right_frame, bg="#1c1b2d",height=150)
    right_frame_top.pack(side="top", pady=(0,5),fill="both",expand=True)
    #right_frame_top.pack_propagate(False)
    
    right_frame_topleft = tk.Frame(right_frame_top, bg="#1c1b2d",width=90)
    right_frame_topleft.pack(side="left",pady=5,padx=10,fill="both",expand=True)
   # right_frame_topleft.pack_propagate(False)
    
    right_frame_topr = tk.Frame(right_frame_top, bg="#1c1b2d",width=90)
    right_frame_topr.pack(side="right", fill="both",padx=10,expand=True,pady=5)
    #right_frame_topr.pack_propagate(False)
    
    right_frame_bot = tk.Frame(right_frame,bg="#1c1b2d", height=150)
    right_frame_bot.pack(side="bottom", fill="both",expand=True,pady=(5,0))
   # right_frame_bot.pack_propagate(False)
    
    right_frame_botl = tk.Frame(right_frame_bot,bg="#1c1b2d", width=90)
    right_frame_botl.pack(side="left", fill="both",padx=10,expand=True,pady=5)
    #right_frame_botl.pack_propagate(False)
    
    right_frame_botr = tk.Frame(right_frame_bot,bg="#1c1b2d", width=90)
    right_frame_botr.pack(side="right", fill="both",padx=10,expand=True,pady=5)
   # right_frame_botr.pack_propagate(False)
    
    kd1 = "white"
    title = "#BEBFE5"
    
    kd2 = "white"
    dpm1 = "white"
    dpm2 = "white"
    
    if int(float(player.kd1)) >= 3:
        kd1 = "#3ecbff"
    elif int(float(player.kd1))>=2:
        kd1 = "#5de791"
    elif int(float(player.kd1)) <1:
        kd1= "#bf868f"
    if pl2:
        if int(float(player.kd2)) >= 3:
            kd2 = "#3ecbff"
        elif int(float(player.kd2)) >=2:
            kd2 = "#5de791"
        elif int(float(player.kd2)) <1:
            kd2= "#bf868f"

    if int(float(player.dpm1)) >= 1500:
        dpm1 = "#3ecbff"
    elif int(float(player.dpm1))>=1100:
        dpm1 = "#5de791"
    elif int(float(player.dpm1)) <750:
        dpm1= "#bf868f"
    if pl2:
        if int(float(player.dpm2)) >= 1500:
            dpm2 = "#3ecbff"
        elif int(float(player.dpm2)) >=1100:
            dpm2 = "#5de791"
        elif int(float(player.dpm2)) <750:
            dpm2= "#bf868f"


    latitle= tk.Label(right_frame_topleft, text=f"KD",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11], "bold"))
    latitle.pack(pady=0,side='top')
    la= tk.Label(right_frame_topleft, text=f"{player.kd1}",fg=kd1,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
    la.pack(pady=0,side='top')
    latitle0= tk.Label(right_frame_topr, text=f"MVP %",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11], "bold"))
    latitle0.pack(pady=0,side='top')
    la0= tk.Label(right_frame_topr, text=f"{player.mvp1}",fg=kd1,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
    la0.pack(pady=0,side='top')
    la2= tk.Label(right_frame_topleft, text=f"{player.dpm1}",fg=dpm1,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
    la2.pack(pady=0,side='bottom')
    la2title= tk.Label(right_frame_topleft, text=f"{player.string1}",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
    la2title.pack(pady=0,side='bottom')
    
   # tk.Label(right_frame, text="Placeholder 1", font=("Calibri", fonts[4])).pack(pady=5)
    if pl2:
    #tk.Label(right_frame, text="Placeholder 2", font=("Calibri", fonts[4])).pack(pady=5)
        lbtitle= tk.Label(right_frame_botl, text=f"KD",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
        lbtitle.pack(pady=0,side='top')
        lb = tk.Label(right_frame_botl, text=f"{player.kd2}",fg=kd2,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
        lb.pack(pady=0,side='top')
        lbtitle0= tk.Label(right_frame_botr, text=f"MVP %",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
        lbtitle0.pack(pady=0,side='top')
        lb0 = tk.Label(right_frame_botr, text=f"{player.mvp2}",fg=kd2,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
        lb0.pack(pady=0,side='top')
        lb2= tk.Label(right_frame_botl, text=f"{player.dpm2}",fg=dpm2,bg="#1c1b2d", font=("Calibri", fonts[12],"bold"))
        lb2.pack(pady=0,side='bottom')
        lb2title= tk.Label(right_frame_botl, text=f"{player.string2}",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
        lb2title.pack(pady=0,side='bottom')
    
    #tk.Label(right_frame, text="Placeholder 3", font=("Calibri", fonts[4])).pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 4", font=("Calibri", fonts[4])).pack(pady=5)
    
    

    return outer

def show_gui(players):
    global indicator_label
    
    root = tk.Tk()
    root.title("Match Overview")
    width = len(players) * 330
    screen_width = root.winfo_screenwidth()
    x = (screen_width - width) // 2
    y = 0
    root.geometry(f"{width}x400+{x}+{y}")
    root.configure(bg="black")
    root.overrideredirect(True)
    root.attributes("-topmost", True)  # Always on top
    script_dir = os.path.dirname(os.path.abspath(__file__))

    assets_folder = os.path.join(script_dir, "assets")

    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead

    title_bar = tk.Frame(root, bg="#141420", relief="groove", height=30)
    title_bar.pack(fill="x", side="top")
    title_bar.pack_propagate(False)
    
    close_btn = tk.Button(title_bar, command=lambda: close(root,script_dir),text="X", width=2,height=1,fg="white", relief="flat",bg="#141420", font=("Lucida Console", fonts[16]), cursor="hand2")
    close_btn.pack(side="right", padx=0)
    hide_btn = tk.Button(title_bar, command=lambda: toggle_transparency(root,hide_btn),text="Hide", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[14]), cursor="hand2")
    hide_btn.pack(side="right", padx=10)
    global lock
    lock = tk.Button(title_bar, command=toggle_clickthrough,text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[8]), cursor="hand2")
    lock.pack(side="right", padx=10)
    indicator_label = tk.Label(title_bar, text="", fg="white", bg="#141420", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)

    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#d41c1c"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#141420"))


    hide_btn.bind("<Enter>", lambda e: hide_btn.config(bg="#31314D"))
    hide_btn.bind("<Leave>", lambda e: hide_btn.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    top_player = max(players, key=lambda p: float(p.playermvp.strip('%')))

# Set their .ace to True
    top_player.ace = True
    for player in players:
        
        create_player_frame(root, player, image_map)

    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()

    root.mainloop()
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

def close(root,script_dir):
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

def show_launcher(on_trigger,on_match):
    global bhidden, bdebug_menu, indicator_label,main, var2, var1, trigger_func,trigger2_func,root,cb1,cb2,cb3
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
    print(config.mobile_mode)
    if config.mobile_mode:
        font_scale = 2
        print(font_scale)
    font_sizes = list(range(6, 70))
    fonts = {size: scale_font(font_scale, size) for size in font_sizes}
    bhidden = False
    bdebug_menu = False
    root = tk.Tk()
    root.title("Capture Names")
    
    
    screen_width = root.winfo_screenwidth()
    x = (screen_width // 2)-50
    y = 0
    root.geometry(f"+{x}+{y}")
    root.attributes("-topmost", True)
    root.configure(bg="#151426")
    root.overrideredirect(True)
# Register Fonts !!!!!!
    loaded_paths, families = call_register_fonts(root)
    print(f"Loaded {len(loaded_paths)} custom fonts.")
    #list_fonts1()
    fontsa = list(tkFont.families())
    save_list_file(fontsa, "available_fonts.txt")
    # Print them
    #for f in fontsa:
     #   print(f)
    title_bar2 = tk.Frame(root, bg="#141420", relief="solid", width=250,height=17)
    title_bar2.pack(fill="x", side="top",ipady=3)
    title_bar2.pack_propagate(False)
    main = tk.Frame(root, bg="#151426", relief="solid", height=30, width=250)
    main.pack(fill="x", padx=10,pady=5, side="bottom")
    deb = tk.Frame(root, bg="#151426", relief="solid", height=30, width=250)
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
        cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Refrigerator Deluxe", fonts[10]),variable=var1)
        cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
        cb1.pack(anchor="w",padx=0)
        cb2.pack(anchor="w",padx=0)
        global_debugflag = True

    
    cb3 = tk.Checkbutton(frame, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
    cb4 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Enable Debug", variable=var4,font=("Calibri", fonts[10]))
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
            hide_btn2.config(text="Show")
            
        else:
            if bdebug_menu:
                deb.pack(fill="x", padx=0,pady=6, side="bottom")
            else:
                main.pack(fill="x", padx=10,pady=5, side="bottom")
            
            hide_btn2.config(text="Hide")
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
            hide_btn2.config(text="Hide")
        if bdebug_menu:
            
            main.pack_forget()
            debug.config(text="Back")
            
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:

                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Calibri", fonts[10]),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            print(f"Dexerto: {config.dex}")
            deb.pack(fill="x", padx=0,pady=6, side="bottom")
            
        else:
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:
                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Calibri", fonts[10]),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            print(f"Dexerto: {config.dex}")
            deb.pack_forget()
            debug.config(text="Debug")
            main.pack(fill="x", padx=10,pady=5, side="bottom")

    close_btn2 = tk.Button(title_bar2, command=lambda: close2(root),text="x", width=2,height=1,fg="white", relief="flat",bg="#141420", font=fonttk(exo, 12, 'normal'), cursor="hand2")
    close_btn2.pack(side="right", padx=0)
    hide_btn2 = tk.Button(title_bar2, command=lambda: toggle_hide(deb, main, hide_btn2),text="Hide", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 11, 'normal'), cursor="hand2")
    hide_btn2.pack(side="right", padx=3)
    
    if config.debug_mode or config.debug_menu:
        debug = tk.Button(title_bar2, command=toggle_debug,text="Debug", relief="flat",fg="#FCD92E", bg="#141420", font=fonttk(carbon, 11, 'normal'), cursor="hand2")
        debug.pack(side="right", padx=3)
        debug.bind("<Enter>", lambda e: debug.config(bg="#31314D"))
        debug.bind("<Leave>", lambda e: debug.config(bg="#141420"))
    global lock
    lock = tk.Button(title_bar2, command=lambda: toggle_clickthrough(toggle_hide, deb, main, hide_btn2),text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=fonttk(carbon, 10, 'normal'), cursor="hand2")
    lock.pack(side="right", padx=3)
    indicator_label = tk.Label(title_bar2, text="", fg="white", bg="#141420", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)
    close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
    close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))

    hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
    hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    


    button = tk.Button(main,text="Bans [F8]", height=1, relief="flat", bg="#FCD92E",font=fonttk(rajdhani_medium,'normal',12),command=lambda: trigger1(var1.get()), cursor="hand2")
    button.pack(side="left",padx=11)
    button.bind("<Enter>", lambda e: button.config(bg="#A18D25"))
    button.bind("<Leave>", lambda e: button.config(bg="#FCD92E"))
    button1 = tk.Button(main,text="Counters [F10]",height=0, relief="flat", bg="#FCD92E",font=fonttk(rajdhani_medium,'normal',12),command=lambda: trigger22(var2.get()), cursor="hand2")
    button1.pack(side="right",padx=11)
    button1.bind("<Enter>", lambda e: button1.config(bg="#A18D25"))
    button1.bind("<Leave>", lambda e: button1.config(bg="#FCD92E"))

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
        if flag:
            config.randomize_ban = True
        if after_id:
            root.after_cancel(after_id)
        #root.destroy()
        initialize_hide_pass(None, None, None,None)
        on_trigger()

    def trigger1(flag):
        if flag:
            config.randomize_ban = True
        if after_id:
            root.after_cancel(after_id)
        root.destroy()
        initialize_hide_pass(None, None, None,None)
        on_trigger()

    def trigger2(flag):
        if flag:
            config.randomize_matchup = True
        if after_id:
            root.after_cancel(after_id)
        initialize_hide_pass(None, None, None,None)
        #root.destroy()
        on_match()
    def trigger22(flag):
        if flag:
            config.randomize_matchup = True
        if after_id:
            root.after_cancel(after_id)
        initialize_hide_pass(None, None, None,None)
        root.destroy()
        on_match()
    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()
    trigger2_func = trigger2
    trigger_func = trigger

    root.mainloop()

def initialize_hide_pass(hide_func, debug_frame, main_frame,hide_btn):
    global hide_function, debug_frame_global, main_frame_global,hide_button_global
    hide_button_global = hide_btn
    hide_function = hide_func
    debug_frame_global = debug_frame
    main_frame_global = main_frame


if not config.mobile_mode:
    import threading
    def start_hotkey_listener():
        global hide_function, debug_frame_global, main_frame_global,hide_button_global
        keyboard.add_hotkey('f6' ,toggle_clickthrough,args=(hide_function, debug_frame_global, main_frame_global,hide_button_global))
        keyboard.wait()  # Keeps the listener alive

    listener_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    listener_thread.start()
    keyboard.add_hotkey('f8', handle_f8)

    keyboard.add_hotkey('f10', handle_f10)