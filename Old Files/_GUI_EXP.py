import tkinter as tk
from PIL import Image, ImageTk
import helpers
import os
import config
TRANSPARENT = "#000000"
ui_folder = os.path.join(config.script_dir, "assets_exp")
exp_map = {}
for filename in os.listdir(ui_folder):
    if filename.lower().endswith(".png"):
        key = os.path.splitext(filename)[0]
        path = os.path.join(ui_folder, filename)
        exp_map[key] = Image.open(path)  # Store PIL images instead

class HeroCard(tk.Frame):
    def __init__(self, parent, name, title, level, **kwargs):
        super().__init__(parent, bg=TRANSPARENT, bd=0, highlightthickness=0, **kwargs)

        img_raw = exp_map.get("border") or exp_map.get("border.png")
        if not img_raw:
            raise RuntimeError("border.png not found in exp_map")

        self.img_w, self.img_h = img_raw.size
        self.border_img = ImageTk.PhotoImage(img_raw)

        self.canvas = tk.Canvas(
            self,
            width=self.img_w,
            height=self.img_h,
            bg=TRANSPARENT,
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack()  # no padding

        self.canvas.create_image(0, 0, anchor="nw", image=self.border_img)

        self.canvas.create_text(
            10, 15, anchor="w",
            text=str(level),
            font=("Segoe UI", 12, "bold"),
            fill="white",
        )

        self.canvas.create_text(
            60, 15, anchor="w",
            text=name,
            font=("Segoe UI", 14, "bold"),
            fill="white",
        )

        self.canvas.create_text(
            self.img_w - 10, self.img_h - 10, anchor="e",
            text=title,
            font=("Segoe UI", 11),
            fill="#ffd7aa",
        )

def createImage(frame, player_img, size, bg, arh, param):
    img_raw = exp_map.get(player_img) or exp_map.get("Default")
    if img_raw:
        #resized = img_raw.copy()
        resized = img_raw.resize(size, Image.LANCZOS)
        #resized.thumbnail(size)  # Resize to 32x32
        img = ImageTk.PhotoImage(resized)
        label = tk.Label(frame,bg=bg, image=img, **arh)
        label.image = img  # Prevent garbage collection
        label.pack(**param)
        return label
    else:
        return False
def createWindow(rt):
    f = tk.Frame(rt,width=224, height=56,    bg=TRANSPARENT)
    f.pack(expand=True, fill="both")
    label = createImage(
        f,
        "story",
        (224, 56),
        "#000000",
        {"highlightcolor": "black"},
        {"side": "right", "padx": 0}
    )
if __name__ == "__main__":
    root = tk.Tk()
    root.configure(width=300, height=200)
    root.config(bg=TRANSPARENT)
    root.wm_attributes("-transparentcolor", TRANSPARENT)
    root.attributes("-topmost", True)
    createWindow(root)
    #card = HeroCard(root, "omgimGOOPING", "Chrono-Explorer", 67)
    #card.pack()  # no padx/pady

    root.mainloop()