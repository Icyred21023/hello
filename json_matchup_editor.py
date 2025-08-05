import os
import json
import tkinter as tk
from tkinter import ttk, Scrollbar, Canvas
from PIL import Image, ImageTk, ImageOps

# === Config ===
script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "type_matchup.json")
IMAGE_FOLDER = os.path.join(script_dir, "assets_characters")

# === Load Character Data ===
class Character:
    def __init__(self, data):
        self.name = data.get("name")
        self.role = data.get("role")
        self.counterPicks = data.get("counterPicks", [])
        self.data = data

def load_characters(filename):
    with open(filename, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    return {name: Character(data) for name, data in raw_data.items()}, raw_data

characters, data = load_characters(matchup_path)

# === Load PNG Icons ===
def load_image_map(names):
    image_map = {}
    for name in names:
        path = os.path.join(IMAGE_FOLDER, f"{name}.png")
        if os.path.exists(path):
            img = Image.open(path)
            img = ImageOps.expand(img, border=2, fill="black")
            img.thumbnail((96, 96))
            image_map[name] = ImageTk.PhotoImage(img)
    return image_map

# === GUI ===
root = tk.Tk()
root.title("Type Matchup Editor")
root.geometry("1920x1080")
root.configure(bg="#1E1E1E")

image_map = load_image_map(characters.keys())

# === Left Frame: Character Grid ===
left_frame = tk.Frame(root, width=640, bg="#1E1E1E")
left_frame.pack(side="left", fill="y")

canvas = Canvas(left_frame, bg="#1E1E1E", highlightthickness=0)
scrollbar = Scrollbar(left_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#1E1E1E")

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

def _on_mousewheel(event, widget):
    widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind_all("<MouseWheel>", lambda e: _on_mousewheel(e, canvas) if e.widget in scrollable_frame.winfo_children() else None)

# === Right Frame ===
right_frame = tk.Frame(root, bg="#2C2C2C")
right_frame.pack(side="right", fill="both", expand=True)

info_canvas = Canvas(right_frame, width=480, bg="#2C2C2C", highlightthickness=0)
info_scroll = Scrollbar(right_frame, orient="vertical", command=info_canvas.yview)
info_frame = tk.Frame(info_canvas, bg="#2C2C2C")

info_canvas.create_window((0, 0), window=info_frame, anchor="nw")
info_canvas.configure(yscrollcommand=info_scroll.set)
info_canvas.pack(side="left", fill="y")
info_scroll.pack(side="left", fill="y")

info_frame.bind("<Configure>", lambda e: info_canvas.configure(scrollregion=info_canvas.bbox("all")))
info_canvas.bind_all("<MouseWheel>", lambda e: _on_mousewheel(e, info_canvas) if e.widget in info_frame.winfo_children() else None)

detail_frame = tk.Frame(right_frame, bg="#2C2C2C")
detail_frame.pack(side="right", fill="both", expand=True)

selected_character = tk.StringVar()

# === Functions ===
def display_characters_by_role(parent, characters_dict, columns=3, icon_size=(96, 96), on_click=None):
    roles = ["Duelist", "Vanguard", "Strategist"]
    row = 0
    col = 0
    for role in roles:
        role_chars = [c for c in characters_dict.values() if c.role == role]
        for char in role_chars:
            name_label = tk.Label(parent, text=char.name, fg="white", bg="#1E1E1E")
            name_label.grid(row=row, column=col, padx=5, pady=(5, 0))

            img = image_map.get(char.name)
            if img:
                btn = tk.Button(parent, image=img, command=lambda n=char.name: on_click(n), bg="#1E1E1E", relief="flat")
                btn.grid(row=row + 1, column=col, padx=5, pady=(0, 10))

            col += 1
            if col >= columns:
                col = 0
                row += 2
# Track hovered slider
hovered_slider_var = {"var": None}

def bind_slider_scroll(widget, var):
    def on_enter(event):
        hovered_slider_var["var"] = var
    def on_leave(event):
        hovered_slider_var["var"] = None
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

def _on_mousewheel(event):
    var = hovered_slider_var.get("var")
    if var:
        # Scroll slider only
        delta = -1 if event.delta > 0 else 1
        current = var.get()
        new_val = max(0, min(10, current + delta))
        var.set(new_val)
        return "break"  # 🚫 prevent scrolling canvas
    else:
        # Scroll whichever canvas is hovered
        if event.widget in scrollable_frame.winfo_children():
            scroll_target = canvas
        elif event.widget in info_frame.winfo_children():
            scroll_target = info_canvas
        else:
            return
        scroll_target.yview_scroll(int(-1 * (event.delta / 120)), "units")



def show_counterpicks(name):
    selected_character.set(name)

    for widget in info_frame.winfo_children():
        widget.destroy()
    for widget in detail_frame.winfo_children():
        widget.destroy()

    tk.Label(info_frame, text="CounterPicks", font=("Arial", 14, "bold"), bg="#2C2C2C", fg="white").pack(anchor="w", pady=10, padx=10)

    char_obj = characters[name]
    counter_names = [cp["name"] for cp in char_obj.counterPicks]

    def remove_counter(n):
        char_obj.counterPicks = [cp for cp in char_obj.counterPicks if cp["name"] != n]
        show_counterpicks(name)

    for cp in char_obj.counterPicks:
        row_frame = tk.Frame(info_frame, bg="#2C2C2C")
        row_frame.pack(anchor="w", pady=5, fill="x", padx=10)

        img = image_map.get(cp["name"])
        if img:
            btn = tk.Button(row_frame, image=img, command=lambda n=cp["name"]: remove_counter(n), relief="flat", bg="#2C2C2C")
            btn.grid(row=0, column=0, sticky="w")

        tk.Label(row_frame, text=cp["name"], fg="white", bg="#2C2C2C").grid(row=0, column=1, sticky="w", padx=5)
        scale_var = tk.DoubleVar(value=5)
        scale = ttk.Scale(row_frame, from_=0, to=10, orient="horizontal", length=80, variable=scale_var)
        scale.grid(row=0, column=2, sticky="e")
        val_label = tk.Label(row_frame, textvariable=scale_var, fg="white", bg="#2C2C2C")
        val_label.grid(row=0, column=3, padx=5)

        bind_slider_scroll(row_frame, scale_var)

    unused = {k: v for k, v in characters.items() if k not in counter_names and k != name}

    def add_counter(n):
        char_obj.counterPicks.append({"name": n, "role": characters[n].role, "description": ""})
        show_counterpicks(name)

    display_characters_by_role(detail_frame, unused, columns=6, icon_size=(64, 64), on_click=add_counter)

# === Populate left frame with all characters ===
display_characters_by_role(scrollable_frame, characters, columns=3, icon_size=(96, 96), on_click=show_counterpicks)
root.bind_all("<MouseWheel>", _on_mousewheel)
root.mainloop()
