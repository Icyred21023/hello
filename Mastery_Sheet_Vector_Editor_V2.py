"""
Mastery Sprite Sheet Vector Mask Editor
---------------------------------------
Walks hero folders under SHEETS_DIR, processes every PNG in each folder,
and rebuilds each image as the same 6-column x 10-row sprite sheet after
clipping every frame with the same fixed SVG vector mask.

Workflow for each PNG:
  1) Resolve the hero from the containing folder using config.HERO_KEYS.
  2) Slice the sheet into ROWS x COLS using integer-perfect edges.
  3) Show the first frame with the SVG mask overlaid.
  4) Move the fixed-size vector with the arrow keys (1 source pixel per keypress).
  5) Confirm the position.
  6) Apply the same vector position to all frames.
  7) Zero all RGBA pixels fully outside the mask.
  8) Rebuild the sheet at the ORIGINAL sheet dimensions.
  9) Save to OUTPUTS_DIR as: <hero_name><file_idx_in_folder>.png

Requirements:
    pip install pillow resvg_py

SVG notes:
  - Export the Illustrator clipping path as SVG with a TRANSPARENT background.
  - The clipping shape itself should have a solid fill.
  - VECTOR_WIDTH / VECTOR_HEIGHT are the final mask dimensions in source pixels.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tkinter as tk
from typing import Dict, Iterator, List, Optional, Tuple, Union

from PIL import Image, ImageChops, ImageFilter, ImageTk

import config


# ============================================================
# USER SETTINGS
# ============================================================

EDITOR_DIR = os.path.join(config.script_dir, "_Mastery_Sheet_Editor")
SHEETS_DIR = os.path.join(EDITOR_DIR, "Raw Sheets")
OUTPUTS_DIR = os.path.join(EDITOR_DIR, "Outputs")

VECTOR_SVG = os.path.join(EDITOR_DIR, "svg.svg")
VECTOR_WIDTH = 322
VECTOR_HEIGHT = 368

ROWS = 10
COLS = 6

# Output names are: hero_name + file index + .png
# 0 -> HeroName0.png, HeroName1.png, ...
# 1 -> HeroName1.png, HeroName2.png, ...
FILE_INDEX_START = 0

CANVAS_MAX = 720

# New cache lives directly in EDITOR_DIR, not Raw Sheets.
POSITION_CACHE_PATH = os.path.join(EDITOR_DIR, "_mastery_vector_position_cache.json")

# Lossless PNG compression. 9 is slowest/smallest and does NOT alter pixels.
PNG_COMPRESS_LEVEL = 9
PNG_OPTIMIZE = True

RESULT_QUIT = "QUIT"


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def natural_sort_key(value: str):
    """Sort names like 1.png, 2.png, 10.png in numeric order."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", value)]


def relative_cache_key(path: str) -> str:
    """Stable cache key relative to Raw Sheets."""
    return os.path.relpath(path, SHEETS_DIR).replace("\\", "/")


# ============================================================
# POSITION CACHE
# ============================================================

def load_position_cache(path: str) -> Dict[str, Dict[str, int]]:
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        out: Dict[str, Dict[str, int]] = {}
        if isinstance(data, dict):
            for key, value in data.items():
                if (
                    isinstance(value, dict)
                    and "x" in value
                    and "y" in value
                ):
                    out[str(key)] = {
                        "x": int(value["x"]),
                        "y": int(value["y"]),
                    }
        return out

    except Exception as exc:
        print(f"WARNING: Could not load position cache: {exc}")
        return {}


def save_position_cache(path: str, cache: Dict[str, Dict[str, int]]) -> None:
    ensure_dir(os.path.dirname(path))
    tmp = path + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)

    os.replace(tmp, path)


# ============================================================
# HERO / FOLDER DISCOVERY
# ============================================================

def get_hero_name(folder_name: str) -> str:
    """
    Resolve a hero folder through config.HERO_KEYS.

    The direct form requested is:
        config.HERO_KEYS[folder_name]["name"]

    This helper also tolerates HERO_KEYS using integer keys or differently-cased
    string keys, which is useful when folder names come from the filesystem.
    """
    hero_keys = config.HERO_KEYS

    # Exact string key first.
    if folder_name in hero_keys:
        return str(hero_keys[folder_name]["name"])

    # Numeric folder name with integer dictionary keys.
    if folder_name.isdigit():
        int_key = int(folder_name)
        if int_key in hero_keys:
            return str(hero_keys[int_key]["name"])

    # Final case-insensitive string comparison.
    folder_lower = folder_name.lower()
    for key, value in hero_keys.items():
        if str(key).lower() == folder_lower:
            return str(value["name"])

    raise KeyError(folder_name)


def walk_sheet_folders(root: str) -> Iterator[Tuple[str, str, str, List[str]]]:
    """
    Walk all folders beneath SHEETS_DIR.

    Yields:
        (folder_path, folder_name, hero_name, sorted_png_paths)

    A folder is only yielded if it contains PNG files and its folder name can
    be resolved through config.HERO_KEYS.
    """
    for current_root, dirs, files in os.walk(root):
        dirs.sort(key=natural_sort_key)

        png_names = [name for name in files if name.lower().endswith(".png")]
        if not png_names:
            continue

        png_names.sort(key=natural_sort_key)
        folder_name = os.path.basename(os.path.normpath(current_root))

        try:
            hero_name = get_hero_name(folder_name)
        except (KeyError, TypeError):
            print(
                f"  -> Skipping folder '{current_root}': "
                f"'{folder_name}' was not found in config.HERO_KEYS."
            )
            continue

        png_paths = [os.path.join(current_root, name) for name in png_names]
        yield current_root, folder_name, hero_name, png_paths


# ============================================================
# SPRITE SHEET GRID
# ============================================================

def split_edges(total: int, parts: int) -> List[int]:
    """
    Return integer edges [0..total] split into `parts` segments.
    Remainder pixels are distributed deterministically from the beginning.

    This lets us rebuild to the exact original sheet dimensions even when
    width/height are not perfectly divisible by COLS/ROWS.
    """
    base = total // parts
    rem = total % parts

    edges = [0]
    acc = 0

    for i in range(parts):
        acc += base + (1 if i < rem else 0)
        edges.append(acc)

    return edges


def slice_frames(
    sheet: Image.Image,
    rows: int,
    cols: int,
) -> Tuple[List[Image.Image], List[int], List[int]]:
    w, h = sheet.size
    print(f"    Sheet size: {w}x{h} | grid: {cols} cols x {rows} rows")

    xs = split_edges(w, cols)
    ys = split_edges(h, rows)

    frames: List[Image.Image] = []

    for r in range(rows):
        for c in range(cols):
            x0, x1 = xs[c], xs[c + 1]
            y0, y1 = ys[r], ys[r + 1]
            frames.append(sheet.crop((x0, y0, x1, y1)))

    return frames, xs, ys


def rebuild_sheet(
    frames: List[Image.Image],
    rows: int,
    cols: int,
    xs: List[int],
    ys: List[int],
) -> Image.Image:
    """Rebuild at exactly xs[-1] x ys[-1] with no resampling."""
    expected = rows * cols
    if len(frames) != expected:
        raise ValueError(f"Expected {expected} frames, got {len(frames)}")

    out = Image.new("RGBA", (xs[-1], ys[-1]), (0, 0, 0, 0))

    i = 0
    for r in range(rows):
        for c in range(cols):
            # The edited frame is already exactly the cell size, so this is a
            # straight pixel paste with zero resizing/resampling.
            out.paste(frames[i], (xs[c], ys[r]))
            i += 1

    return out


# ============================================================
# SVG MASK
# ============================================================

def load_svg_mask(svg_path: str, width: int, height: int) -> Image.Image:
    """
    Rasterize the Illustrator SVG into an 8-bit alpha mask.

    resvg_py is preferred. CairoSVG is accepted as a fallback if already
    installed. Only the mask is rasterized/resized; source sprite pixels are
    never resized by this function.
    """
    if width <= 0 or height <= 0:
        raise ValueError("VECTOR_WIDTH and VECTOR_HEIGHT must be > 0")

    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG mask not found: {svg_path}")

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_string = f.read()

    png_bytes: Optional[bytes] = None

    try:
        import resvg_py
        png_bytes = resvg_py.svg_to_bytes(svg_string=svg_string)
    except ImportError:
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(
                bytestring=svg_string.encode("utf-8"),
                output_width=width,
                output_height=height,
            )
        except ImportError as exc:
            raise RuntimeError(
                "No SVG renderer is installed. Run: pip install resvg_py"
            ) from exc

    rendered = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # If resvg rendered at the SVG's intrinsic dimensions, resize ONLY the
    # mask artwork to the desired source-pixel dimensions.
    if rendered.size != (width, height):
        rendered = rendered.resize((width, height), Image.Resampling.LANCZOS)

    # Illustrator SVG artboards are normally transparent. The path's alpha is
    # the clipping mask: 255 = keep, 0 = delete.
    mask = rendered.getchannel("A")

    if mask.getbbox() is None:
        raise RuntimeError(
            "The SVG rendered fully transparent. Ensure the Illustrator path "
            "has a solid fill before exporting the SVG."
        )

    return mask


def placement_bounds(
    frame_size: Tuple[int, int],
    mask_size: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    """
    Valid placement range.

    If the mask is smaller than the frame, it remains fully inside the frame.
    If the mask is larger, negative coordinates are allowed so it can cover
    the complete frame.
    """
    fw, fh = frame_size
    mw, mh = mask_size

    min_x = min(0, fw - mw)
    max_x = max(0, fw - mw)
    min_y = min(0, fh - mh)
    max_y = max(0, fh - mh)

    return min_x, max_x, min_y, max_y


def clamp_mask_position(
    frame_size: Tuple[int, int],
    mask_size: Tuple[int, int],
    x: int,
    y: int,
) -> Tuple[int, int]:
    min_x, max_x, min_y, max_y = placement_bounds(frame_size, mask_size)
    return clamp(int(x), min_x, max_x), clamp(int(y), min_y, max_y)


def make_full_frame_mask(
    frame_size: Tuple[int, int],
    vector_mask: Image.Image,
    x: int,
    y: int,
) -> Image.Image:
    """Place the fixed vector mask into a full-frame L image."""
    full_mask = Image.new("L", frame_size, 0)
    # Pillow clips correctly when x/y are negative or extend beyond an edge.
    full_mask.paste(vector_mask, (int(x), int(y)))
    return full_mask


def apply_vector_mask(
    frame: Image.Image,
    vector_mask: Image.Image,
    x: int,
    y: int,
) -> Image.Image:
    """
    Clip one frame without resampling any sprite pixels.

    - RGB values of retained pixels remain unchanged.
    - Existing source alpha is multiplied by SVG alpha.
    - Every pixel whose resulting alpha is exactly 0 is rewritten to
      (0, 0, 0, 0), removing hidden RGB data outside the mask.
    """
    frame = frame.convert("RGBA")
    full_mask = make_full_frame_mask(frame.size, vector_mask, x, y)

    r, g, b, original_alpha = frame.split()
    new_alpha = ImageChops.multiply(original_alpha, full_mask)

    # Binary nonzero map used ONLY to clear hidden RGB where final alpha == 0.
    # Any retained or anti-aliased boundary pixel keeps its original RGB.
    nonzero = new_alpha.point(lambda p: 255 if p else 0)
    zero = Image.new("L", frame.size, 0)

    r = Image.composite(r, zero, nonzero)
    g = Image.composite(g, zero, nonzero)
    b = Image.composite(b, zero, nonzero)

    return Image.merge("RGBA", (r, g, b, new_alpha))


# ============================================================
# PLACEMENT GUI
# ============================================================

class VectorPlacementGUI(tk.Tk):
    """
    Shows frame 0 and the real fixed-size SVG mask.

    Keyboard:
        Left / Right / Up / Down -> move exactly 1 SOURCE pixel
        Enter                      -> confirm
        Escape                     -> skip
    """

    def __init__(
        self,
        frame_img: Image.Image,
        vector_mask: Image.Image,
        title: str,
        initial_position: Optional[Tuple[int, int]] = None,
    ):
        super().__init__()

        self.title(title)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

        self.frame_img = frame_img.convert("RGBA")
        self.vector_mask = vector_mask.convert("L")

        self.fw, self.fh = self.frame_img.size
        self.mw, self.mh = self.vector_mask.size

        if initial_position is None:
            x = (self.fw - self.mw) // 2
            y = (self.fh - self.mh) // 2
        else:
            x, y = initial_position

        self.x, self.y = clamp_mask_position(
            self.frame_img.size,
            self.vector_mask.size,
            x,
            y,
        )

        self.result: Optional[Union[Tuple[int, int], str]] = None

        self.display_scale = min(
            CANVAS_MAX / self.fw,
            CANVAS_MAX / self.fh,
            1.0,
        )

        self.disp_w = max(1, int(round(self.fw * self.display_scale)))
        self.disp_h = max(1, int(round(self.fh * self.display_scale)))

        self.canvas = tk.Canvas(
            self,
            width=self.disp_w,
            height=self.disp_h,
            highlightthickness=1,
        )
        self.canvas.grid(row=0, column=0, columnspan=5, padx=8, pady=(8, 4))

        self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.tk_preview: Optional[ImageTk.PhotoImage] = None

        self.position_var = tk.StringVar()
        self.position_label = tk.Label(
            self,
            textvariable=self.position_var,
            font=("TkDefaultFont", 10, "bold"),
        )
        self.position_label.grid(row=1, column=0, columnspan=5, pady=(4, 2))

        instruction = (
            "Arrow keys = move vector 1 px     Enter = Confirm     Esc = Skip"
        )
        tk.Label(self, text=instruction).grid(
            row=2,
            column=0,
            columnspan=5,
            padx=8,
            pady=(0, 8),
        )

        self.btn_center = tk.Button(
            self,
            text="Center",
            command=self.on_center,
            takefocus=False,
        )
        self.btn_confirm = tk.Button(
            self,
            text="Confirm",
            command=self.on_confirm,
            takefocus=False,
        )
        self.btn_skip = tk.Button(
            self,
            text="Skip sheet",
            command=self.on_skip,
            takefocus=False,
        )
        self.btn_quit = tk.Button(
            self,
            text="Quit",
            command=self.on_quit,
            takefocus=False,
        )

        self.btn_center.grid(row=3, column=0, padx=4, pady=(0, 8))
        self.btn_confirm.grid(row=3, column=1, padx=4, pady=(0, 8))
        self.btn_skip.grid(row=3, column=2, padx=4, pady=(0, 8))
        self.btn_quit.grid(row=3, column=3, padx=4, pady=(0, 8))

        # Bind on the root so the arrows continue working even if a widget is
        # clicked. Every event moves in ORIGINAL frame pixels, not display px.
        self.bind("<Left>", lambda event: self.move_mask(-1, 0))
        self.bind("<Right>", lambda event: self.move_mask(1, 0))
        self.bind("<Up>", lambda event: self.move_mask(0, -1))
        self.bind("<Down>", lambda event: self.move_mask(0, 1))
        self.bind("<Return>", lambda event: self.on_confirm())
        self.bind("<Escape>", lambda event: self.on_skip())

        self._update_preview()
        self.after(100, self.focus_force)

    def _update_preview(self) -> None:
        full_mask = make_full_frame_mask(
            self.frame_img.size,
            self.vector_mask,
            self.x,
            self.y,
        )

        # Preview only: darken everything that will be clipped.
        outside = ImageChops.invert(full_mask)
        shade_alpha = outside.point(lambda p: (p * 145) // 255)

        shade = Image.new("RGBA", self.frame_img.size, (0, 0, 0, 0))
        shade.putalpha(shade_alpha)
        preview = Image.alpha_composite(self.frame_img, shade)

        # Preview only: bright outline around the actual vector path.
        # No part of this outline is written into the output image.
        expanded = full_mask.filter(ImageFilter.MaxFilter(5))
        contracted = full_mask.filter(ImageFilter.MinFilter(5))
        outline_alpha = ImageChops.subtract(expanded, contracted)

        outline = Image.new("RGBA", self.frame_img.size, (255, 230, 0, 0))
        outline.putalpha(outline_alpha)
        preview = Image.alpha_composite(preview, outline)

        if preview.size != (self.disp_w, self.disp_h):
            preview = preview.resize(
                (self.disp_w, self.disp_h),
                Image.Resampling.LANCZOS,
            )

        self.tk_preview = ImageTk.PhotoImage(preview)
        self.canvas.itemconfigure(self.canvas_image_id, image=self.tk_preview)

        self.position_var.set(
            f"Vector position: x={self.x}, y={self.y}   |   "
            f"mask={self.mw}x{self.mh}   frame={self.fw}x{self.fh}"
        )

    def move_mask(self, dx: int, dy: int) -> None:
        nx, ny = clamp_mask_position(
            self.frame_img.size,
            self.vector_mask.size,
            self.x + dx,
            self.y + dy,
        )

        if nx == self.x and ny == self.y:
            return

        self.x = nx
        self.y = ny
        self._update_preview()

    def on_center(self) -> None:
        self.x, self.y = clamp_mask_position(
            self.frame_img.size,
            self.vector_mask.size,
            (self.fw - self.mw) // 2,
            (self.fh - self.mh) // 2,
        )
        self._update_preview()
        self.focus_force()

    def on_confirm(self) -> None:
        self.result = (self.x, self.y)
        self.destroy()

    def on_skip(self) -> None:
        self.result = None
        self.destroy()

    def on_quit(self) -> None:
        self.result = RESULT_QUIT
        self.destroy()


# ============================================================
# MAIN PROCESSING
# ============================================================

def process_sheet(
    sheet_path: str,
    hero_name: str,
    file_idx_in_folder: int,
    vector_mask: Image.Image,
    position_cache: Dict[str, Dict[str, int]],
    initial_position: Optional[Tuple[int, int]],
) -> Tuple[Optional[Tuple[int, int]], bool]:
    """
    Returns:
        (confirmed_position_or_None, quit_requested)
    """
    sheet_key = relative_cache_key(sheet_path)
    sheet_name = os.path.basename(sheet_path)

    print(f"    Loading: {sheet_name}")

    with Image.open(sheet_path) as source:
        sheet = source.convert("RGBA")

    original_size = sheet.size
    frames, xs, ys = slice_frames(sheet, ROWS, COLS)

    if len(frames) != ROWS * COLS:
        print("    -> Incorrect frame count; skipping.")
        return None, False

    first = frames[0]

    # Exact per-sheet cache wins. Otherwise inherit the previous confirmed
    # position from the same folder so the next sheet starts nearby.
    cached = position_cache.get(sheet_key)
    if cached is not None:
        starting_position = (int(cached["x"]), int(cached["y"]))
    else:
        starting_position = initial_position

    gui = VectorPlacementGUI(
        first,
        vector_mask,
        title=f"{hero_name} | {sheet_name}",
        initial_position=starting_position,
    )
    gui.mainloop()

    result = gui.result

    if result == RESULT_QUIT:
        return None, True

    if result is None:
        print("    -> Skipped.")
        return None, False

    mask_x, mask_y = result

    position_cache[sheet_key] = {
        "x": int(mask_x),
        "y": int(mask_y),
    }
    save_position_cache(POSITION_CACHE_PATH, position_cache)

    print(f"    -> Applying vector at x={mask_x}, y={mask_y} to {len(frames)} frames...")

    edited_frames = [
        apply_vector_mask(frame, vector_mask, mask_x, mask_y)
        for frame in frames
    ]

    rebuilt = rebuild_sheet(edited_frames, ROWS, COLS, xs, ys)

    if rebuilt.size != original_size:
        raise RuntimeError(
            f"Rebuilt size changed unexpectedly: {original_size} -> {rebuilt.size}"
        )

    output_index = file_idx_in_folder + FILE_INDEX_START
    output_name = f"{hero_name}{output_index}.png"
    output_path = os.path.join(OUTPUTS_DIR, output_name)

    rebuilt.save(
        output_path,
        format="PNG",
        optimize=PNG_OPTIMIZE,
        compress_level=PNG_COMPRESS_LEVEL,
    )

    print(f"    -> Saved: {output_path}")
    print(f"       size: {rebuilt.size}")

    return (mask_x, mask_y), False


def main() -> None:
    if ROWS <= 0 or COLS <= 0:
        raise SystemExit("ROWS and COLS must both be > 0")

    if not os.path.isdir(SHEETS_DIR):
        raise SystemExit(f"Raw sheet directory does not exist: {SHEETS_DIR}")

    ensure_dir(EDITOR_DIR)
    ensure_dir(OUTPUTS_DIR)

    print("PYTHON:", sys.executable)
    print("EDITOR_DIR:", EDITOR_DIR)
    print("SHEETS_DIR:", SHEETS_DIR)
    print("OUTPUTS_DIR:", OUTPUTS_DIR)
    print("VECTOR_SVG:", VECTOR_SVG)
    print(f"VECTOR SIZE: {VECTOR_WIDTH}x{VECTOR_HEIGHT}")
    print(f"GRID: {COLS} columns x {ROWS} rows")
    print("----")

    vector_mask = load_svg_mask(VECTOR_SVG, VECTOR_WIDTH, VECTOR_HEIGHT)
    print("Loaded SVG vector mask:", vector_mask.size)

    position_cache = load_position_cache(POSITION_CACHE_PATH)
    print("Loaded cached sheet positions:", len(position_cache))
    print("----")

    folders = list(walk_sheet_folders(SHEETS_DIR))

    if not folders:
        print("No hero folders containing PNGs were found.")
        return

    total_sheets = sum(len(png_paths) for _, _, _, png_paths in folders)
    print(f"Hero folders found: {len(folders)}")
    print(f"PNG sheets found: {total_sheets}")
    print("----")

    global_sheet_idx = 0

    for folder_idx, (folder_path, folder_name, hero_name, png_paths) in enumerate(folders, start=1):
        print(
            f"[{folder_idx}/{len(folders)}] HERO FOLDER: {folder_name} "
            f"-> {hero_name} ({len(png_paths)} PNGs)"
        )
        print("  PATH:", folder_path)

        # Start subsequent sheets in this hero folder at the position confirmed
        # on the previous sheet. Exact per-sheet cache still overrides this.
        last_confirmed_position: Optional[Tuple[int, int]] = None

        for file_idx_in_folder, sheet_path in enumerate(png_paths):
            global_sheet_idx += 1
            print(
                f"  [{global_sheet_idx}/{total_sheets}] "
                f"folder index={file_idx_in_folder + FILE_INDEX_START}"
            )

            confirmed_position, quit_requested = process_sheet(
                sheet_path=sheet_path,
                hero_name=hero_name,
                file_idx_in_folder=file_idx_in_folder,
                vector_mask=vector_mask,
                position_cache=position_cache,
                initial_position=last_confirmed_position,
            )

            if quit_requested:
                print("Quit requested. Exiting.")
                return

            if confirmed_position is not None:
                last_confirmed_position = confirmed_position

        print("----")

    print("Finished processing all sheets.")


if __name__ == "__main__":
    main()
