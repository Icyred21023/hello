"""
Sprite Sheet Cropper (square 1:1 crop locked)
--------------------------------------------
Iterates over PNG sprite sheets in a directory (endswith "_master.png").

For each sheet:
  1) Slices all frames using ROWS/COLS grid (integer-perfect edges).
  2) Shows the FIRST frame in a Tkinter GUI.
  3) User draws/moves a SQUARE crop box (locked 1:1).
  4) On confirm, applies same square crop to ALL frames,
     rebuilds a clean sheet, saves it, repeats next.

Requirements:
  pip install pillow
"""

import os
import sys
import tkinter as tk
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
from PIL import Image, ImageTk
import config
import json

# ========= USER SETTINGS =========
TRIM_WIDTH_MAP = {
    3584: 3582,   # cut 2 px from the RIGHT
}
EDITOR_DIR = os.path.join(config.script_dir, "_Mastery_Sheet_Editor")
SHEETS_DIR = os.path.join(EDITOR_DIR, "Raw Sheets")
VECTOR_SVG = os.path.join(EDITOR_DIR, "svg.svg")
VECTOR_WIDTH = 322
VECTOR_HEIGHT = 368
print(SHEETS_DIR)
FILENAME_SUFFIX = "_MasterJ.png"

ROWS = 10
COLS = 6

ODD_GRID_SHIFT_X = -1   # left
ODD_GRID_SHIFT_Y = +1   # down

OUTPUT_SUFFIX = "2"

CANVAS_MAX = 720
MIN_CROP_SIZE = 8
CROP_CACHE_PATH = os.path.join(SHEETS_DIR, "_mastery_crop_cache.json")
PRESERVE_FRAME_SIZE = True
CONFIRM_ALL = "CONFIRM_ALL"
def snap_to_nearest_multiple(n: int, m: int) -> int:
    if m <= 0:
        return n
    lo = (n // m) * m
    hi = lo + m
    # choose nearest, tie → smaller (crop bias)
    return lo if (n - lo) <= (hi - n) else hi


def normalize_sheet_to_grid_end(img, rows: int, cols: int):
    """
    FINAL normalization rule:
      X axis → crop or pad on RIGHT
      Y axis → ALWAYS crop on BOTTOM
    """
    from PIL import Image

    w, h = img.size

    target_w = snap_to_nearest_multiple(w, cols)
    target_h = snap_to_nearest_multiple(h, rows)

    # --- X AXIS ---
    if target_w < w:
        img = img.crop((0, 0, target_w, h))
        
    elif target_w > w:
        out = Image.new("RGBA", (target_w, h), (0, 0, 0, 0))
        out.paste(img, (0, 0))
        img = out
        

    # --- Y AXIS (ALWAYS CROP) ---
    if target_h < img.size[1]:
        img = img.crop((0, 0, img.size[0], target_h))
    elif target_h > img.size[1]:
        diff = target_h - img.size[1]
        img = img.crop((0, 0, img.size[0], img.size[1] - diff))
        # even if target_h > h → DO NOTHING
        # (never pad vertically)
        pass

    return img

# ================================
def maybe_trim_rebuilt_sheet(img: Image.Image, trim_map: dict[int, int]) -> Image.Image:
    """
    If img.width matches a key in trim_map, crop RIGHT edge so width becomes trim_map[width].
    Keeps height unchanged.
    """
    w, h = img.size
    if w not in trim_map:
        return img

    new_w = int(trim_map[w])
    if new_w <= 0 or new_w >= w:
        return img  # safety: don't expand or zero it out

    # Crop off the RIGHT-most pixels
    return img.crop((0, 0, new_w, h))


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_crop_cache(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = {}
        for k, v in data.items():
            if isinstance(v, dict) and all(x in v for x in ("x0", "y0", "side")):
                out[k] = {"x0": int(v["x0"]), "y0": int(v["y0"]), "side": int(v["side"])}
        return out
    except Exception:
        return {}


def save_crop_cache(path: str, cache: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp, path)


def list_sheets(folder: str) -> List[str]:
    allowed = [
        "Jubilee"
        
    ]

    out = []
    for name in os.listdir(folder):
        lname = name.lower()
        

        if not lname.endswith(FILENAME_SUFFIX):
            print(f"  -> Skipped {lname}.")
            if not lname.endswith("jubilee_master.png"):
                continue
            out.append(os.path.join(folder, name))

        if not any(key in lname for key in allowed):
            print(f"  -> Skipped {lname} (not in allowed list).")
            continue

        out.append(os.path.join(folder, name))

    out.sort()
    return out


def split_edges(total: int, parts: int) -> List[int]:
    """
    Return edges [0..total] split into `parts` segments,
    distributing remainder pixels deterministically.
    """
    base = total // parts
    rem = total % parts
    edges = [0]
    acc = 0
    for i in range(parts):
        acc += base + (1 if i < rem else 0)
        edges.append(acc)
    return edges


def slice_frames(sheet: Image.Image, rows: int, cols: int) -> Tuple[List[Image.Image], List[int], List[int]]:
    """
    Slice frames using integer-perfect edges (NO floats),
    returns (frames, xs, ys) so rebuild uses same grid.
    """
    w, h = sheet.size
    print(f"Sheet size: {w}x{h}, rows: {rows}, cols: {cols}")

    xs = split_edges(w, cols)
    ys = split_edges(h, rows)

    frames = []
    for r in range(rows):
        for c in range(cols):
            x0, x1 = xs[c], xs[c + 1]
            y0, y1 = ys[r], ys[r + 1]
            frames.append(sheet.crop((x0, y0, x1, y1)))

    return frames, xs, ys


def _paste_rgba_clipped(dst: Image.Image, src: Image.Image, x: int, y: int) -> None:
    dw, dh = dst.size
    sw, sh = src.size

    dx0, dy0 = x, y
    dx1, dy1 = x + sw, y + sh

    clip_dx0 = max(0, dx0)
    clip_dy0 = max(0, dy0)
    clip_dx1 = min(dw, dx1)
    clip_dy1 = min(dh, dy1)

    if clip_dx0 >= clip_dx1 or clip_dy0 >= clip_dy1:
        return

    sx0 = clip_dx0 - dx0
    sy0 = clip_dy0 - dy0
    sx1 = sx0 + (clip_dx1 - clip_dx0)
    sy1 = sy0 + (clip_dy1 - clip_dy0)

    patch = src.crop((sx0, sy0, sx1, sy1))
    dst.paste(patch, (clip_dx0, clip_dy0))  # <-- NO MASK


def rebuild_sheet(frames: List[Image.Image], rows: int, cols: int, xs: List[int], ys: List[int],
                 shift_x: int = 0, shift_y: int = 0) -> Image.Image:
    if not frames:
        raise ValueError("No frames to rebuild.")

    out_w = xs[-1]
    out_h = ys[-1]
    out = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))

    i = 0
    for r in range(rows):
        for c in range(cols):
            px = xs[c] + shift_x
            py = ys[r] + shift_y
            _paste_rgba_clipped(out, frames[i], px, py)
            i += 1

    return out


@dataclass
class CropRect:
    x0: int
    y0: int
    x1: int
    y1: int

    def normalized(self) -> "CropRect":
        a, b = sorted((self.x0, self.x1))
        c, d = sorted((self.y0, self.y1))
        return CropRect(a, c, b, d)

    def width(self) -> int:
        r = self.normalized()
        return r.x1 - r.x0

    def height(self) -> int:
        r = self.normalized()
        return r.y1 - r.y0

    def as_tuple(self) -> Tuple[int, int, int, int]:
        r = self.normalized()
        return (r.x0, r.y0, r.x1, r.y1)


class SquareCropGUI(tk.Tk):
    def __init__(self, frame_img: Image.Image, title: str):
        super().__init__()
        self.title(title)
        self.resizable(False, False)

        self.frame_img = frame_img
        self.fw, self.fh = frame_img.size

        scale = min(CANVAS_MAX / self.fw, CANVAS_MAX / self.fh, 1.0)
        self.display_scale = scale
        disp_w = int(round(self.fw * scale))
        disp_h = int(round(self.fh * scale))

        self.disp_img = frame_img.resize((disp_w, disp_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(self.disp_img)

        self.canvas = tk.Canvas(self, width=disp_w, height=disp_h, highlightthickness=1)
        self.canvas.grid(row=0, column=0, columnspan=9, padx=8, pady=8)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        # Default square crop (centered)
        side = max(MIN_CROP_SIZE, min(self.fw, self.fh) - max(2, min(self.fw, self.fh) // 10))
        side = min(side, int(self.fw * 0.6), int(self.fh * 0.6))
        x0 = (self.fw - side) // 2
        y0 = (self.fh - side) // 2
        self.crop = CropRect(x0, y0, x0 + side, y0 + side)

        self.rect_id = None

        # controls
        self._make_controls()

        # dim overlay rectangles (4 regions)
        self.dim_ids = [
            self.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="black"),
            self.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="black"),
            self.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="black"),
            self.canvas.create_rectangle(0, 0, 0, 0, outline="", fill="black"),
        ]
        for rid in self.dim_ids:
            self.canvas.itemconfigure(rid, stipple="gray50")

        self._draw_rect()
        self.canvas.tag_raise(self.rect_id)

        # drag state
        self.drag_mode = None
        self.drag_start_disp = (0, 0)
        self.anchor_frame = (0, 0)
        self.crop_start = self.crop

        # mouse binds
        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)   # Windows
        self.canvas.bind("<Button-4>", self.on_mousewheel)     # Linux up
        self.canvas.bind("<Button-5>", self.on_mousewheel)     # Linux down

        self.result: Optional[Union[CropRect, str]] = None

    def _frame_to_disp(self, x: int, y: int) -> Tuple[int, int]:
        return (int(round(x * self.display_scale)), int(round(y * self.display_scale)))

    def _disp_to_frame(self, x: int, y: int) -> Tuple[int, int]:
        # IMPORTANT: floor-style mapping prevents 1px drift on odd sizes
        fx = int(x / self.display_scale)
        fy = int(y / self.display_scale)
        return clamp(fx, 0, self.fw), clamp(fy, 0, self.fh)

    def _update_dim_overlay(self):
        r = self.crop.normalized()
        sx0, sy0 = self._frame_to_disp(r.x0, r.y0)
        sx1, sy1 = self._frame_to_disp(r.x1, r.y1)

        cw = int(self.canvas.cget("width"))
        ch = int(self.canvas.cget("height"))

        top    = (0,    0,   cw,  sy0)
        left   = (0,   sy0,  sx0, sy1)
        right  = (sx1, sy0,  cw,  sy1)
        bottom = (0,   sy1,  cw,  ch)

        for rid, coords in zip(self.dim_ids, [top, left, right, bottom]):
            self.canvas.coords(rid, *coords)

        if self.rect_id is not None:
            self.canvas.tag_raise(self.rect_id)

    def _draw_rect(self):
        r = self.crop.normalized()
        sx0, sy0 = self._frame_to_disp(r.x0, r.y0)
        sx1, sy1 = self._frame_to_disp(r.x1, r.y1)
        if self.rect_id is None:
            self.rect_id = self.canvas.create_rectangle(sx0, sy0, sx1, sy1, outline="yellow", width=2)
        else:
            self.canvas.coords(self.rect_id, sx0, sy0, sx1, sy1)
        self._update_dim_overlay()
        self._sync_entries_from_crop()

    def _resize_square_by(self, delta: int):
        r = self.crop.normalized()
        side = r.width() + delta
        side = max(MIN_CROP_SIZE, side)
        side = min(side, self.fw, self.fh)

        cx = r.x0 + r.width() // 2
        cy = r.y0 + r.height() // 2

        x0 = clamp(cx - side // 2, 0, self.fw - side)
        y0 = clamp(cy - side // 2, 0, self.fh - side)

        self.crop = CropRect(x0, y0, x0 + side, y0 + side)
        self._draw_rect()

    def on_mousewheel(self, event):
        if hasattr(event, "delta") and event.delta:
            direction = 1 if event.delta > 0 else -1
        else:
            direction = 1 if event.num == 4 else -1

        step = 10 if (event.state & 0x0001) else 1
        self._resize_square_by(direction * step)

    def _point_in_rect_disp(self, x: int, y: int) -> bool:
        r = self.crop.normalized()
        sx0, sy0 = self._frame_to_disp(r.x0, r.y0)
        sx1, sy1 = self._frame_to_disp(r.x1, r.y1)
        return sx0 <= x <= sx1 and sy0 <= y <= sy1

    def _make_controls(self):
        tk.Label(self, text="x0").grid(row=1, column=0, sticky="e", padx=4)
        tk.Label(self, text="y0").grid(row=1, column=2, sticky="e", padx=4)
        tk.Label(self, text="side").grid(row=1, column=4, sticky="e", padx=4)

        self.var_x0 = tk.StringVar()
        self.var_y0 = tk.StringVar()
        self.var_side = tk.StringVar()

        self.ent_x0 = tk.Entry(self, width=8, textvariable=self.var_x0)
        self.ent_y0 = tk.Entry(self, width=8, textvariable=self.var_y0)
        self.ent_side = tk.Entry(self, width=8, textvariable=self.var_side)

        self.ent_x0.grid(row=1, column=1, padx=4, pady=2)
        self.ent_y0.grid(row=1, column=3, padx=4, pady=2)
        self.ent_side.grid(row=1, column=5, padx=4, pady=2)

        self.btn_center = tk.Button(self, text="Center", command=self.on_center)
        self.btn_full = tk.Button(self, text="Max square", command=self.on_max_square)
        self.btn_confirm = tk.Button(self, text="Confirm crop", command=self.on_confirm)
        self.btn_allow = tk.Button(self, text="Confirm All", command=self.on_confirm_all)
        self.btn_skip = tk.Button(self, text="Skip sheet", command=self.on_skip)
        self.btn_quit = tk.Button(self, text="Quit", command=self.on_quit)

        self.btn_center.grid(row=2, column=1, padx=4, pady=6)
        self.btn_full.grid(row=2, column=3, padx=4, pady=6)
        self.btn_confirm.grid(row=2, column=5, padx=4, pady=6)
        self.btn_allow.grid(row=2, column=6, padx=4, pady=6)
        self.btn_skip.grid(row=2, column=7, padx=4, pady=6)
        self.btn_quit.grid(row=2, column=8, padx=4, pady=6)

        for ent in (self.ent_x0, self.ent_y0, self.ent_side):
            ent.bind("<Return>", self.on_entry_apply)

        self._sync_entries_from_crop()

    def _sync_entries_from_crop(self):
        r = self.crop.normalized()
        self.var_x0.set(str(r.x0))
        self.var_y0.set(str(r.y0))
        self.var_side.set(str(r.width()))

    def on_entry_apply(self, event=None):
        try:
            x0 = int(self.var_x0.get())
            y0 = int(self.var_y0.get())
            side = int(self.var_side.get())
        except ValueError:
            return

        side = max(MIN_CROP_SIZE, side)
        side = min(side, self.fw, self.fh)

        x0 = clamp(x0, 0, self.fw - side)
        y0 = clamp(y0, 0, self.fh - side)

        self.crop = CropRect(x0, y0, x0 + side, y0 + side)
        self._draw_rect()

    def _make_square_from_drag(self, ax: int, ay: int, bx: int, by: int) -> CropRect:
        dx = bx - ax
        dy = by - ay
        side = max(abs(dx), abs(dy), MIN_CROP_SIZE)

        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1

        x1 = ax + sx * side
        y1 = ay + sy * side

        x0, _x1 = sorted((ax, x1))
        y0, _y1 = sorted((ay, y1))

        x0 = clamp(x0, 0, self.fw - side)
        y0 = clamp(y0, 0, self.fh - side)

        return CropRect(x0, y0, x0 + side, y0 + side)

    def on_down(self, event):
        self.drag_start_disp = (event.x, event.y)
        self.crop_start = self.crop

        if self._point_in_rect_disp(event.x, event.y):
            self.drag_mode = "move"
        else:
            self.drag_mode = "new"
            fx, fy = self._disp_to_frame(event.x, event.y)
            self.anchor_frame = (fx, fy)
            self.crop = self._make_square_from_drag(fx, fy, fx + MIN_CROP_SIZE, fy + MIN_CROP_SIZE)
            self._draw_rect()

    def on_drag(self, event):
        if self.drag_mode is None:
            return

        if self.drag_mode == "new":
            ax, ay = self.anchor_frame
            bx, by = self._disp_to_frame(event.x, event.y)
            self.crop = self._make_square_from_drag(ax, ay, bx, by)
            self._draw_rect()

        elif self.drag_mode == "move":
            dx_disp = event.x - self.drag_start_disp[0]
            dy_disp = event.y - self.drag_start_disp[1]
            dx = int(dx_disp / self.display_scale)
            dy = int(dy_disp / self.display_scale)

            r0 = self.crop_start.normalized()
            side = r0.width()

            nx0 = clamp(r0.x0 + dx, 0, self.fw - side)
            ny0 = clamp(r0.y0 + dy, 0, self.fh - side)

            self.crop = CropRect(nx0, ny0, nx0 + side, ny0 + side)
            self._draw_rect()

    def on_up(self, event):
        self.drag_mode = None

    def on_center(self):
        r = self.crop.normalized()
        side = r.width()
        x0 = (self.fw - side) // 2
        y0 = (self.fh - side) // 2
        self.crop = CropRect(x0, y0, x0 + side, y0 + side)
        self._draw_rect()

    def on_max_square(self):
        side = min(self.fw, self.fh)
        self.crop = CropRect(0, 0, side, side)
        self._draw_rect()

    def on_confirm(self):
        r = self.crop.normalized()
        if r.width() < MIN_CROP_SIZE:
            return
        self.result = r
        self.destroy()

    def on_confirm_all(self):
        r = self.crop.normalized()
        if r.width() < MIN_CROP_SIZE:
            return
        self.result = CONFIRM_ALL
        self.destroy()

    def on_skip(self):
        self.result = None
        self.destroy()

    def on_quit(self):
        self.result = "QUIT"
        self.destroy()


def main():
    sheets = list_sheets(SHEETS_DIR)
    auto_confirm_all = False

    if not sheets:
        print(f"No sheets found in: {SHEETS_DIR} (suffix={FILENAME_SUFFIX})")
        return

    crop_cache = load_crop_cache(CROP_CACHE_PATH) if os.path.exists(CROP_CACHE_PATH) else {}
    print("Loaded crop cache entries:", len(crop_cache))

    out_dir = SHEETS_DIR
    ensure_dir(out_dir)

    print("PYTHON:", sys.executable)
    print("Sheets found:", len(sheets))
    print("DIR:", SHEETS_DIR)
    print(f"GRID: {ROWS} rows x {COLS} cols")
    print("----")

    for idx, sheet_path in enumerate(sheets, start=1):
        sheet_key = os.path.basename(sheet_path)

        print(f"[{idx}/{len(sheets)}] Loading:", sheet_key)

        sheet = Image.open(sheet_path).convert("RGBA")

        frames, xs, ys = slice_frames(sheet, ROWS, COLS)
        if not frames:
            print("  -> No frames extracted; skipping.")
            continue

        first = frames[0]

        if not auto_confirm_all:
            gui = SquareCropGUI(first, title=f"Square Crop: {sheet_path}")

            prev = crop_cache.get(sheet_key)
            if prev:
                side = max(MIN_CROP_SIZE, int(prev["side"]))
                side = min(side, gui.fw, gui.fh)
                x0 = clamp(int(prev["x0"]), 0, gui.fw - side)
                y0 = clamp(int(prev["y0"]), 0, gui.fh - side)
                gui.crop = CropRect(x0, y0, x0 + side, y0 + side)
                gui._draw_rect()

            gui.mainloop()
            crop = gui.result

            if crop == CONFIRM_ALL:
                auto_confirm_all = True
                crop = gui.crop

        else:
            prev = crop_cache.get(sheet_key)
            if not prev:
                print("  -> No cached crop; skipping:", sheet_key)
                continue
            side = int(prev["side"])
            x0 = int(prev["x0"])
            y0 = int(prev["y0"])
            crop = CropRect(x0, y0, x0 + side, y0 + side)

        if crop == "QUIT":
            print("Quit requested. Exiting.")
            return

        if crop is None:
            print("  -> Skipped.")
            print("----")
            continue

        # save crop
        r = crop.normalized()
        crop_cache[sheet_key] = {"x0": r.x0, "y0": r.y0, "side": r.width()}
        save_crop_cache(CROP_CACHE_PATH, crop_cache)

        cx0, cy0, cx1, cy1 = r.as_tuple()

        if PRESERVE_FRAME_SIZE:
            orig_fw, orig_fh = frames[0].size
            cropped_frames = []
            for f in frames:
                c = f.crop((cx0, cy0, cx1, cy1))
                out_frame = Image.new("RGBA", (orig_fw, orig_fh), (0, 0, 0, 0))
                out_frame.paste(c, (cx0, cy0))  # <-- NO MASK


                cropped_frames.append(out_frame)
        else:
            cropped_frames = [f.crop((cx0, cy0, cx1, cy1)) for f in frames]

                # Detect odd cell size (the “frame dimension” you’re talking about)
        cell_w = frames[0].size[0]
        cell_h = frames[0].size[1]

        shift_x = 0
        shift_y = 0
        if (cell_w % 2) == 1 or (cell_h % 2) == 1:
            shift_x = ODD_GRID_SHIFT_X
            shift_y = ODD_GRID_SHIFT_Y

        rebuilt = rebuild_sheet(cropped_frames, ROWS, COLS, xs, ys, shift_x=shift_x, shift_y=shift_y)

# --- FIX: trim problematic widths (ex: 3584 -> 3582) ---
        # orig_size = rebuilt.size
        # rebuilt = maybe_trim_rebuilt_sheet(rebuilt, TRIM_WIDTH_MAP)
        orig_size = rebuilt.size
        rebuilt = normalize_sheet_to_grid_end(rebuilt, ROWS, COLS)
        if rebuilt.size != orig_size:
            print(f"  -> Normalized rebuilt size: {orig_size} -> {rebuilt.size}")
        # if rebuilt.size != orig_size:
        #     print(f"  -> Trimmed rebuilt sheet: {orig_size} -> {rebuilt.size}")
        # ------------------------------------------------------

        base_name = os.path.splitext(sheet_key)[0]
        out_path = os.path.join(out_dir, f"{base_name}{OUTPUT_SUFFIX}.png")
        rebuilt.save(out_path, optimize=True, compress_level=0)

        print("  -> Saved:", out_path, "size:", rebuilt.size)
        print("----")


if __name__ == "__main__":
    if ROWS <= 0 or COLS <= 0:
        raise SystemExit("Set ROWS and COLS at the top of the script.")
    main()
