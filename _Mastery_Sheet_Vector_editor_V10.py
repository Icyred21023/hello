"""
Mastery Sprite Sheet Vector Mask Editor
---------------------------------------
Walks hero folders under SHEETS_DIR, processes every PNG in each folder,
and rebuilds each image as the same 6-column x 10-row sprite sheet after
clipping every frame with the same fixed SVG vector mask.

Workflow for each PNG:
  1) Resolve the hero from the containing folder using config.HERO_KEYS.
  2) Floor-divide the sheet into equal cells and discard right/bottom remainder pixels.
  3) Show the first cell against the locked hero frame and SVG mask.
  4) Arrows move the cell; the wheel scales the hero frame and vector together.
  5) Confirm the position.
  6) Apply the same vector position to all frames.
  7) Extract a NEW frame exactly the size of the scaled SVG canvas.
  8) Pixels outside the source frame remain transparent; pixels outside the SVG path are deleted.
  9) Rebuild a compact 6x10 sheet from those fixed-size extracted frames.
 10) Save to OUTPUTS_DIR as: <hero_name><file_idx_in_folder>.png

Requirements:
    pip install pillow resvg_py

SVG notes:
  - Export the Illustrator clipping path as SVG with a TRANSPARENT background.
  - The clipping shape itself should have a solid fill.
  - SVG intrinsic canvas dimensions define its native mask size.
  - SVG and hero frame start scaled to half the native cell dimensions.
  - Camera zoom affects display only; crop coordinates remain source pixels.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import tkinter as tk
from typing import Dict, Iterator, List, Optional, Tuple, Union

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

import config

VECTOR_EDITOR_BUILD = "2026-10-28-cell-relative-v11"


# ============================================================
# USER SETTINGS
# ============================================================

EDITOR_DIR = os.path.join(config.script_dir, "_Mastery_Sheet_Editor")
SHEETS_DIR = os.path.join(EDITOR_DIR, "Final Attempt Raws")
OUTPUTS_DIR = os.path.join(EDITOR_DIR, "Final Attempt Outputs")

VECTOR_SVG = os.path.join(EDITOR_DIR, "svg.svg")
VECTOR_PREVIEW_PNG = os.path.join(EDITOR_DIR, "heroframe_editor.png")
VECTOR_ANCHOR = (0, 908.0)  # SVG TOP-LEFT relative to native hero frame top-left.

ROWS = 10
COLS = 6

# Output names are: hero_name + file index + .png
# 0 -> HeroName0.png, HeroName1.png, ...
# 1 -> HeroName1.png, HeroName2.png, ...
FILE_INDEX_START = 0

CANVAS_MAX = 1200
CELL_TO_VECTOR_RATIO = 2.0  # Cell is approximately twice the SVG size.
PREVIEW_ZOOM = 1  # Camera zoom only; never affects export coordinates.
# Wheel steps change SVG width by one native pixel (Shift: five).
VECTOR_WHEEL_UNIT_STEP = 1
VECTOR_WHEEL_SHIFT_UNIT_STEP = 5
VECTOR_MIN_SCALE_MULTIPLIER = 0.10
VECTOR_MAX_SCALE_MULTIPLIER = 5.00

# New cache lives directly in EDITOR_DIR, not Raw Sheets.
POSITION_CACHE_PATH = os.path.join(EDITOR_DIR, "_mastery_vector_position_cache_v11_cell_relative.json")

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

def load_position_cache(path: str) -> Dict[str, Dict[str, Union[int, float]]]:
    """
    Load cached vector placement.

    Older cache files containing only x/y remain valid; their manual scale
    defaults to 1.0 (automatic half-cell size). The v11 cache uses this baseline.
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        out: Dict[str, Dict[str, Union[int, float]]] = {}
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
                        "scale": float(value.get("scale", 1.0)),
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
def _round_positive_half_up(value: float) -> int:
    """Round a non-negative value conventionally: .5 always rounds upward."""
    return int(math.floor(float(value) + 0.5))


def resize_mask_to_ratio_units(base_mask: Image.Image, ratio_units: int) -> Image.Image:
    """Scale from the native SVG canvas, preserving its aspect ratio."""
    width = max(1, int(ratio_units))
    height = max(1, _round_positive_half_up(width * base_mask.height / base_mask.width))
    size = (width, height)
    return base_mask.copy() if base_mask.size == size else base_mask.resize(size, Image.Resampling.LANCZOS)


def automatic_vector_units(mask, cell_size):
    """Fit SVG within half the cell, retaining the SVG aspect ratio."""
    fw, fh = cell_size
    scale = min(fw / (CELL_TO_VECTOR_RATIO * mask.width),
                fh / (CELL_TO_VECTOR_RATIO * mask.height))
    return max(1, _round_positive_half_up(mask.width * scale))


def scaled_vector_units(base_units, multiplier):
    low = max(1, round(base_units * VECTOR_MIN_SCALE_MULTIPLIER))
    high = max(low, round(base_units * VECTOR_MAX_SCALE_MULTIPLIER))
    return clamp(_round_positive_half_up(base_units * float(multiplier)), low, high)


def load_preview_cell(sheet_path):
    """Decode once, detach only cell 0, and release the full sheet before GUI."""
    with Image.open(sheet_path) as source:
        size = source.size
        xs, ys = split_edges(size[0], COLS), split_edges(size[1], ROWS)
        with source.crop((0, 0, xs[1], ys[1])) as cell:
            first = cell.convert("RGBA")
    return first, size


def crop_sheet_after_confirmation(sheet_path, original_size, mask, x, y):
    """Reopen only on confirmation; process one cell at a time into output."""
    xs = split_edges(original_size[0], COLS)
    ys = split_edges(original_size[1], ROWS)
    output = Image.new("RGBA", (mask.width * COLS, mask.height * ROWS))
    try:
        with Image.open(sheet_path) as source:
            if source.size != original_size:
                raise RuntimeError("Sheet dimensions changed during placement; reopen it.")
            for row in range(ROWS):
                for col in range(COLS):
                    with source.crop((xs[col], ys[row], xs[col+1], ys[row+1])) as raw:
                        with raw.convert("RGBA") as cell:
                            with extract_frame_through_vector(cell, mask, x, y) as edited:
                                output.paste(edited, (col * mask.width, row * mask.height))
        return output
    except Exception:
        output.close()
        raise


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
    if parts <= 0:
        raise ValueError("parts must be greater than zero.")

    if total < parts:
        raise ValueError(
            f"Cannot split {total} pixels into {parts} non-empty cells."
        )

    base = total // parts
    return [i * base for i in range(parts + 1)]


def slice_frames(
    sheet: Image.Image,
    rows: int,
    cols: int,
) -> Tuple[List[Image.Image], List[int], List[int]]:
    w, h = sheet.size
    print(f"    Sheet size: {w}x{h} | grid: {cols} cols x {rows} rows")

    xs = split_edges(w, cols)
    ys = split_edges(h, rows)

    cell_w = xs[1] - xs[0]
    cell_h = ys[1] - ys[0]
    used_w = cell_w * cols
    used_h = cell_h * rows
    discarded_right = w - used_w
    discarded_bottom = h - used_h

    print(
        f"    Fixed cell size: {cell_w}x{cell_h} | "
        f"used grid: {used_w}x{used_h} | "
        f"discarding right={discarded_right}px, bottom={discarded_bottom}px"
    )

    frames: List[Image.Image] = []

    for r in range(rows):
        for c in range(cols):
            x0, x1 = xs[c], xs[c + 1]
            y0, y1 = ys[r], ys[r + 1]
            frames.append(sheet.crop((x0, y0, x1, y1)))

    return frames, xs, ys


def rebuild_fixed_frame_sheet(
    frames: List[Image.Image],
    rows: int,
    cols: int,
) -> Image.Image:
    """
    Rebuild a compact sprite sheet from equally-sized edited frames.

    Each edited frame is the exact scaled SVG canvas size, so the resulting
    sheet is simply:
        width  = frame_width  * cols
        height = frame_height * rows

    No sprite pixels are resized or resampled here.
    """
    expected = rows * cols
    if len(frames) != expected:
        raise ValueError(f"Expected {expected} frames, got {len(frames)}")

    if not frames:
        raise ValueError("No frames to rebuild.")

    frame_w, frame_h = frames[0].size

    for idx, frame in enumerate(frames):
        if frame.size != (frame_w, frame_h):
            raise ValueError(
                f"Edited frame {idx} has size {frame.size}; expected {(frame_w, frame_h)}"
            )

    out = Image.new(
        "RGBA",
        (frame_w * cols, frame_h * rows),
        (0, 0, 0, 0),
    )

    i = 0
    for r in range(rows):
        for c in range(cols):
            out.paste(frames[i], (c * frame_w, r * frame_h))
            i += 1

    return out


# ============================================================
# SVG MASK
# ============================================================

def _inject_svg_mask_style(svg_string: str) -> str:
    """
    Force exported SVG geometry to render as an opaque white mask while
    leaving empty artboard/padding transparent.

    This is intentionally used only as a fallback. Illustrator can export a
    perfectly valid path whose visual appearance comes from a stroke, class,
    group opacity, or other styling that an SVG renderer may interpret as
    transparent. For clipping, we care about the PATH GEOMETRY, not its
    Illustrator paint styling.
    """
    style = r"""
<style type="text/css">
  svg { background: transparent !important; }
  g, path, polygon, rect, circle, ellipse, polyline {
    visibility: visible !important;
    opacity: 1 !important;
  }
  path, polygon, rect, circle, ellipse {
    fill: #ffffff !important;
    fill-opacity: 1 !important;
    stroke: none !important;
  }
</style>
"""

    # Put the override directly inside the root <svg> element.
    out, count = re.subn(
        r"(<svg\b[^>]*>)",
        lambda m: m.group(1) + style,
        svg_string,
        count=1,
        flags=re.IGNORECASE,
    )
    if count == 0:
        raise RuntimeError("Could not find the root <svg> element.")
    return out


def _render_svg_rgba_resvg(svg_string: str) -> Optional[Image.Image]:
    try:
        import resvg_py
    except ImportError:
        return None

    try:
        png_bytes = resvg_py.svg_to_bytes(svg_string=svg_string)
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception as exc:
        print(f"  -> resvg_py render failed: {exc}")
        return None


def _render_svg_rgba_cairo(
    svg_string: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[Image.Image]:
    try:
        import cairosvg
    except ImportError:
        return None

    try:
        png_bytes = cairosvg.svg2png(
            bytestring=svg_string.encode("utf-8"),
            output_width=width,
            output_height=height,
        )
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception as exc:
        print(f"  -> CairoSVG render failed: {exc}")
        return None


def _alpha_from_rendered_svg(
    rendered: Optional[Image.Image],
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[Image.Image]:
    if rendered is None:
        return None

    # Resize ONLY the rasterized VECTOR MASK canvas. Sprite pixels are never
    # resized. Transparent Illustrator artboard padding remains transparent.
    if width is not None and height is not None and rendered.size != (width, height):
        rendered = rendered.resize((width, height), Image.Resampling.LANCZOS)

    alpha = rendered.getchannel("A")
    if alpha.getbbox() is None:
        return None
    return alpha




def _geometry_only_svg(svg_string: str) -> tuple[str, int]:
    """
    Build a clean SVG containing only drawable geometry from the Illustrator SVG.

    This is a last-resort mask fallback for SVGs whose Illustrator appearance
    renders transparent because of classes, masks, clip paths, filters, hidden
    groups, or definitions. Transparent artboard padding is preserved by keeping
    the original viewBox.

    The geometry itself is forced to opaque white. Compound-path fill rules and
    transforms are preserved.
    """
    import copy
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(svg_string)
    except ET.ParseError as exc:
        raise RuntimeError(f"Could not parse SVG XML: {exc}") from exc

    def local(tag: str) -> str:
        return tag.rsplit('}', 1)[-1].lower()

    # Preserve the source coordinate system/artboard.
    view_box = root.attrib.get('viewBox') or root.attrib.get('viewbox')
    width_attr = root.attrib.get('width')
    height_attr = root.attrib.get('height')

    if not view_box:
        # If Illustrator omitted viewBox, use numeric width/height when possible.
        import re as _re
        def _num(v):
            if not v:
                return None
            m = _re.match(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))', str(v))
            return float(m.group(1)) if m else None
        w = _num(width_attr)
        h = _num(height_attr)
        if w and h:
            view_box = f"0 0 {w:g} {h:g}"

    attrs = {
        'xmlns': 'http://www.w3.org/2000/svg',
        'version': '1.1',
    }
    if view_box:
        attrs['viewBox'] = view_box
    if width_attr:
        attrs['width'] = width_attr
    if height_attr:
        attrs['height'] = height_attr

    out_root = ET.Element('svg', attrs)

    id_map = {}
    for el in root.iter():
        el_id = el.attrib.get('id')
        if el_id:
            id_map[el_id] = el

    drawable = {'path', 'polygon', 'rect', 'circle', 'ellipse', 'polyline'}
    container = {'svg', 'g', 'a', 'switch'}
    skip_normal = {'defs', 'metadata', 'title', 'desc', 'style', 'script',
                   'clippath', 'mask', 'pattern', 'lineargradient',
                   'radialgradient', 'filter', 'marker', 'symbol'}

    count = 0

    def combine_transform(parent_t: str, own_t: str) -> str:
        parent_t = (parent_t or '').strip()
        own_t = (own_t or '').strip()
        if parent_t and own_t:
            return parent_t + ' ' + own_t
        return parent_t or own_t

    def emit_shape(src, inherited_transform='', extra_transform=''):
        nonlocal count
        tag = local(src.tag)
        if tag not in drawable:
            return

        # Copy geometry attributes but discard appearance/visibility/mask attrs.
        blocked = {
            'style', 'class', 'fill', 'fill-opacity', 'stroke', 'stroke-width',
            'stroke-opacity', 'opacity', 'display', 'visibility', 'clip-path',
            'mask', 'filter', 'mix-blend-mode'
        }
        a = {}
        for k, v in src.attrib.items():
            lk = local(k)
            if lk in blocked or lk == 'id':
                continue
            a[lk] = v

        transform = combine_transform(inherited_transform, src.attrib.get('transform', ''))
        transform = combine_transform(transform, extra_transform)
        if transform:
            a['transform'] = transform

        a['fill'] = '#ffffff'
        a['fill-opacity'] = '1'
        a['opacity'] = '1'
        a['stroke'] = 'none'

        # Preserve compound-path hole semantics when Illustrator specified them.
        if 'fill-rule' in src.attrib:
            a['fill-rule'] = src.attrib['fill-rule']
        elif 'clip-rule' in src.attrib:
            a['fill-rule'] = src.attrib['clip-rule']

        ET.SubElement(out_root, tag, a)
        count += 1

    def walk(el, inherited_transform='', allow_defs=False, seen=None):
        if seen is None:
            seen = set()
        tag = local(el.tag)
        own_t = el.attrib.get('transform', '')
        current_t = combine_transform(inherited_transform, own_t)

        if tag in drawable:
            # current_t already includes the element transform, so pass only the
            # ancestor transform to emit_shape to avoid applying it twice.
            emit_shape(el, inherited_transform)
            return

        if tag == 'use':
            href = (el.attrib.get('href') or
                    el.attrib.get('{http://www.w3.org/1999/xlink}href') or '')
            ref_id = href[1:] if href.startswith('#') else None
            if ref_id and ref_id in id_map and ref_id not in seen:
                tx = el.attrib.get('x', '0')
                ty = el.attrib.get('y', '0')
                use_t = current_t
                try:
                    if float(tx) != 0 or float(ty) != 0:
                        use_t = combine_transform(use_t, f'translate({tx},{ty})')
                except Exception:
                    use_t = combine_transform(use_t, f'translate({tx},{ty})')
                walk(id_map[ref_id], use_t, True, seen | {ref_id})
            return

        if tag in skip_normal and not allow_defs:
            return

        # Recurse through ordinary groups/containers. For an explicitly resolved
        # symbol/defs target, allow traversal inside it.
        if tag in container or allow_defs or tag in {'symbol', 'defs', 'clippath', 'mask'}:
            for child in list(el):
                walk(child, current_t, allow_defs, seen)

    # First collect actual visible-tree geometry and resolved <use> references.
    for child in list(root):
        walk(child, '', False, set())

    # Some Illustrator exports put the only useful path inside defs/clipPath and
    # use CSS/masking to expose it. If nothing was found, salvage all geometry
    # from those definition containers while retaining their transforms.
    if count == 0:
        for child in list(root):
            if local(child.tag) in {'defs', 'clippath', 'mask', 'symbol'}:
                walk(child, '', True, set())

    return ET.tostring(out_root, encoding='unicode'), count


def load_svg_mask(svg_path: str) -> Image.Image:
    """
    Rasterize the Illustrator SVG into an 8-bit alpha clipping mask.

    Transparent padding around the path is valid and preserved. This function
    tries the Illustrator appearance first, then progressively ignores styling
    and finally rebuilds a geometry-only SVG so CSS/masks/defs cannot make the
    path disappear.
    """
    # Let the renderer use SVG width/height (or viewBox), without target resizing.
    width = height = None

    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG mask not found: {svg_path}")

    with open(svg_path, "r", encoding="utf-8-sig") as f:
        svg_string = f.read()

    attempts = []

    # PASS 1: Render exactly as Illustrator exported it.
    rendered = _render_svg_rgba_resvg(svg_string)
    mask = _alpha_from_rendered_svg(rendered, width, height)
    if mask is not None:
        print(f"  -> SVG mask loaded using Illustrator appearance. bbox={mask.getbbox()}")
        return mask
    attempts.append("resvg original")

    # PASS 2: Force normal SVG shape styling to opaque white.
    print("  -> SVG appearance rendered blank; forcing visible white geometry...")
    forced_svg = _inject_svg_mask_style(svg_string)
    rendered = _render_svg_rgba_resvg(forced_svg)
    mask = _alpha_from_rendered_svg(rendered, width, height)
    if mask is not None:
        print(f"  -> SVG mask loaded from forced styling. bbox={mask.getbbox()}")
        return mask
    attempts.append("resvg forced-style")

    # PASS 3/4: CairoSVG can parse some Illustrator exports differently.
    rendered = _render_svg_rgba_cairo(svg_string, width, height)
    mask = _alpha_from_rendered_svg(rendered, width, height)
    if mask is not None:
        print(f"  -> SVG mask loaded using CairoSVG. bbox={mask.getbbox()}")
        return mask
    attempts.append("cairo original")

    rendered = _render_svg_rgba_cairo(forced_svg, width, height)
    mask = _alpha_from_rendered_svg(rendered, width, height)
    if mask is not None:
        print(f"  -> SVG mask loaded using CairoSVG forced styling. bbox={mask.getbbox()}")
        return mask
    attempts.append("cairo forced-style")

    # PASS 5: Completely discard Illustrator paint/mask/CSS behavior and create
    # a new SVG using only the actual vector geometry + transforms.
    print("  -> Styled SVG still blank; extracting raw vector geometry...")
    geometry_svg, geometry_count = _geometry_only_svg(svg_string)
    print(f"  -> Geometry elements recovered: {geometry_count}")

    if geometry_count:
        rendered = _render_svg_rgba_resvg(geometry_svg)
        mask = _alpha_from_rendered_svg(rendered, width, height)
        if mask is not None:
            print(f"  -> SVG mask loaded from raw geometry via resvg. bbox={mask.getbbox()}")
            return mask
        attempts.append("resvg geometry-only")

        rendered = _render_svg_rgba_cairo(geometry_svg, width, height)
        mask = _alpha_from_rendered_svg(rendered, width, height)
        if mask is not None:
            print(f"  -> SVG mask loaded from raw geometry via CairoSVG. bbox={mask.getbbox()}")
            return mask
        attempts.append("cairo geometry-only")

    raise RuntimeError(
        "SVG mask could not be rasterized even after raw-geometry extraction. "
        f"Recovered geometry elements: {geometry_count}. Attempts: {', '.join(attempts)}. "
        "Transparent artboard padding is allowed. If geometry_count is 0, the "
        "file probably does not contain a normal SVG path/polygon/shape (for "
        "example it may be only an embedded image). Upload the actual svg.svg "
        "and I can adapt the loader to its exact Illustrator structure."
    )

def make_full_frame_mask(
    frame_size: Tuple[int, int],
    vector_mask: Image.Image,
    x: int,
    y: int,
) -> Image.Image:
    """Place the vector mask into a source-frame-sized L image.

    This is used only for preview shading. Pillow clips naturally when the
    vector extends outside the source frame.
    """
    full_mask = Image.new("L", frame_size, 0)
    full_mask.paste(vector_mask, (int(x), int(y)))
    return full_mask


def extract_frame_through_vector(
    source_frame: Image.Image,
    vector_mask: Image.Image,
    mask_x: int,
    mask_y: int,
) -> Image.Image:
    """
    Extract one NEW output frame whose canvas exactly matches vector_mask.

    mask_x / mask_y are the upper-left coordinates of the SVG canvas relative
    to the original source frame. The source sprite itself is never resized.

    If part of the SVG canvas extends beyond the source frame, those pixels are
    retained in the output canvas as transparent RGBA pixels. The SVG alpha is
    then multiplied by the source alpha, and fully clipped pixels have hidden
    RGB cleared to zero.
    """
    source_frame = source_frame.convert("RGBA")
    vector_mask = vector_mask.convert("L")

    src_w, src_h = source_frame.size
    mask_w, mask_h = vector_mask.size

    # The output canvas IS the SVG canvas.
    out = Image.new("RGBA", (mask_w, mask_h), (0, 0, 0, 0))

    # Find overlap between the source frame and the positioned SVG canvas.
    src_x0 = max(0, int(mask_x))
    src_y0 = max(0, int(mask_y))
    src_x1 = min(src_w, int(mask_x) + mask_w)
    src_y1 = min(src_h, int(mask_y) + mask_h)

    if src_x1 > src_x0 and src_y1 > src_y0:
        source_piece = source_frame.crop((src_x0, src_y0, src_x1, src_y1))

        # Translate source coordinates into SVG-canvas/output coordinates.
        dst_x = src_x0 - int(mask_x)
        dst_y = src_y0 - int(mask_y)
        out.paste(source_piece, (dst_x, dst_y))

    r, g, b, original_alpha = out.split()
    final_alpha = ImageChops.multiply(original_alpha, vector_mask)

    # Clear hidden RGB anywhere final alpha is zero. Retained / antialiased edge
    # pixels keep their original RGB values.
    nonzero = final_alpha.point(lambda p: 255 if p else 0)
    zero = Image.new("L", out.size, 0)

    r = Image.composite(r, zero, nonzero)
    g = Image.composite(g, zero, nonzero)
    b = Image.composite(b, zero, nonzero)

    return Image.merge("RGBA", (r, g, b, final_alpha))


# ============================================================
# PLACEMENT GUI
# ============================================================

class VectorPlacementGUI(tk.Tk):
    """A fixed-size sprite cell beneath a jointly scaled frame and SVG.

    World coordinates are source pixels. The vector center stays at (0, 0).
    VECTOR_ANCHOR locates the SVG top-left within the hero frame. Only the sprite's
    origin moves with the arrows. Confirmation converts this scene back to
    an integer crop origin relative to the original sprite cell.
    """

    def __init__(self, frame_img, vector_mask, vector_preview_img, title,
                 initial_position=None, initial_scale_multiplier=1.0):
        super().__init__()
        self.attributes("-fullscreen", True)
        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.frame_img = frame_img.convert("RGBA")
        self.fw, self.fh = self.frame_img.size
        if vector_preview_img is None:
            self.destroy()
            raise FileNotFoundError(f"Hero frame not found: {VECTOR_PREVIEW_PNG}")
        self.heroframe = vector_preview_img.convert("RGBA")
        self.base_vector_mask = vector_mask.convert("L").copy()
        self.base_ratio_units = automatic_vector_units(self.base_vector_mask, (self.fw, self.fh))
        self.min_ratio_units = max(1, round(self.base_ratio_units * VECTOR_MIN_SCALE_MULTIPLIER))
        self.max_ratio_units = max(self.min_ratio_units, round(self.base_ratio_units * VECTOR_MAX_SCALE_MULTIPLIER))
        self.ratio_units = clamp(_round_positive_half_up(self.base_ratio_units * initial_scale_multiplier),
                                 self.min_ratio_units, self.max_ratio_units)
        self._resize_vector()
        if initial_position is None:
            self.cell_x, self.cell_y = -self.fw / 2, -self.fh / 2
        else:
            self.cell_x = -self.mw / 2 - int(initial_position[0])
            self.cell_y = -self.mh / 2 - int(initial_position[1])
        self.result = None

        # Fixed camera zoom for all layers; source/crop coordinates stay native.
        self.display_scale = min(PREVIEW_ZOOM,
                                 max(200, min(CANVAS_MAX, self.winfo_screenwidth()-100)-80) / self.fw,
                                 max(200, min(CANVAS_MAX, self.winfo_screenheight()-240)-80) / self.fh)
        self.canvas = tk.Canvas(self, width=min(CANVAS_MAX, max(400, self.winfo_screenwidth() - 100)),
                                height=min(CANVAS_MAX, max(300, self.winfo_screenheight() - 240)),
                                background="#303030", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        horizontal = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        vertical = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        horizontal.grid(row=1, column=0, sticky="ew")
        vertical.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        self.position_var = tk.StringVar()
        tk.Label(self, textvariable=self.position_var).grid(row=2, column=0, columnspan=2)
        tk.Label(self, text="Arrows: move cell 1 px | Shift: 10 px | Wheel: scale frame + vector | Shift+Wheel: 5 px").grid(row=3, column=0, columnspan=2)
        tk.Label(self, text="Enter: confirm | Esc: skip | Scrollbars: inspect full frame after resizing").grid(row=4, column=0, columnspan=2)
        buttons = tk.Frame(self)
        buttons.grid(row=5, column=0, columnspan=2, pady=8)
        for label, command in (("Center cell", self.on_center), ("Reset size", self.on_reset_size),
                               ("Confirm", self.on_confirm), ("Skip sheet", self.on_skip), ("Quit", self.on_quit)):
            tk.Button(buttons, text=label, command=command, takefocus=False).pack(side="left", padx=5)
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            self.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self.move_cell(dx, dy))
            self.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self.move_cell(dx*10, dy*10))
        self.bind("<Return>", lambda e: self.on_confirm())
        self.bind("<Escape>", lambda e: self.on_skip())
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(event, self.on_mousewheel)
        self._update_preview()
        # Start near the SVG/cell overlap; the rest of the native frame scrolls.
        self.update_idletasks()
        left, top, right, bottom = (v * self.display_scale for v in self._scene_bounds())
        self.canvas.xview_moveto(max(0, (-self.canvas.winfo_width()/2 - left + 20) / (right-left+40)))
        self.canvas.yview_moveto(max(0, (-self.canvas.winfo_height()/2 - top + 20) / (bottom-top+40)))
        self.after(100, self.focus_force)

    def _resize_vector(self):
        self.vector_mask = resize_mask_to_ratio_units(self.base_vector_mask, self.ratio_units)
        self.mw, self.mh = self.vector_mask.size
        self.scale_multiplier = self.ratio_units / self.base_ratio_units

    def _frame_bounds(self):
        scale = self.mw / self.base_vector_mask.width
        x = -self.mw / 2 - VECTOR_ANCHOR[0] * scale
        y = -self.mh / 2 - VECTOR_ANCHOR[1] * scale
        return x, y, x + self.heroframe.width * scale, y + self.heroframe.height * scale

    def _scene_bounds(self):
        x0, y0, x1, y1 = self._frame_bounds()
        return (min(x0, -self.mw/2, self.cell_x), min(y0, -self.mh/2, self.cell_y),
                max(x1, self.mw/2, self.cell_x+self.fw), max(y1, self.mh/2, self.cell_y+self.fh))

    def crop_position(self):
        return (int(round(-self.mw/2 - self.cell_x)),
                int(round(-self.mh/2 - self.cell_y)))

    def _image(self, img, x, y, width, height):
        d = self.display_scale
        size = (max(1, round(width*d)), max(1, round(height*d)))
        resized = img if img.size == size else img.resize(size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized)
        self._photos.append(photo)
        self.canvas.create_image(x*d, y*d, image=photo, anchor="nw")

    def _update_preview(self):
        self.canvas.delete("all")
        self._photos = []
        d = self.display_scale
        x0, y0, x1, y1 = self._frame_bounds()
        self._image(self.heroframe, x0, y0, x1-x0, y1-y0)
        # Show retained sprite pixels normally; dim excluded pixels without
        # painting opaque black over transparent parts of the UI frame.
        x, y = self.crop_position()
        keep = make_full_frame_mask(self.frame_img.size, self.vector_mask, x, y)
        alpha = self.frame_img.getchannel("A")
        sprite = self.frame_img.copy()
        visibility = keep.point(lambda p: round(255 * 0.25 + p * 0.75))
        sprite.putalpha(ImageChops.multiply(alpha, visibility))
        self._image(sprite, self.cell_x, self.cell_y, self.fw, self.fh)
        # Outline actual SVG geometry, with the cyan box showing its canvas.
        edge = ImageChops.subtract(self.vector_mask.filter(ImageFilter.MaxFilter(5)),
                                   self.vector_mask.filter(ImageFilter.MinFilter(5)))
        outline = Image.new("RGBA", self.vector_mask.size, (255, 230, 0, 0))
        outline.putalpha(edge)
        self._image(outline, -self.mw/2, -self.mh/2, self.mw, self.mh)
        self.canvas.create_rectangle(-self.mw*d/2, -self.mh*d/2, self.mw*d/2, self.mh*d/2,
                                     outline="#00dcff")
        self.canvas.create_rectangle(self.cell_x*d, self.cell_y*d,
                                     (self.cell_x+self.fw)*d, (self.cell_y+self.fh)*d, outline="#dddddd")
        bounds = self._scene_bounds()
        self.canvas.configure(scrollregion=(bounds[0]*d-20, bounds[1]*d-20,
                                           bounds[2]*d+20, bounds[3]*d+20))
        self.position_var.set(f"Crop: ({x}, {y}) | Output: {self.mw} × {self.mh} | "
                              f"User scale: {self.scale_multiplier:.4f} | View: {self.display_scale:.0%} | Cell: {self.fw} × {self.fh}")

    def move_cell(self, dx, dy):
        self.cell_x += dx
        self.cell_y += dy
        self._update_preview()
        return "break"

    def set_ratio_units(self, units):
        self.ratio_units = clamp(int(units), self.min_ratio_units, self.max_ratio_units)
        self._resize_vector()
        # Cell origin and size stay fixed; frame and vector scale about (0, 0).
        self._update_preview()

    def on_mousewheel(self, event):
        delta = getattr(event, "delta", 0)
        direction = (1 if delta > 0 else -1) if delta else (1 if getattr(event, "num", None) == 4 else -1)
        step = VECTOR_WHEEL_SHIFT_UNIT_STEP if getattr(event, "state", 0) & 1 else VECTOR_WHEEL_UNIT_STEP
        self.set_ratio_units(self.ratio_units + direction * step)
        return "break"

    def on_reset_size(self):
        self.set_ratio_units(self.base_ratio_units)

    def on_center(self):
        self.cell_x, self.cell_y = -self.fw/2, -self.fh/2
        self._update_preview()

    def _close(self):
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(event)
        self.destroy()

    def on_confirm(self):
        x, y = self.crop_position()
        self.result = (x, y, float(self.scale_multiplier))
        self._close()

    def on_skip(self):
        self.result = None
        self._close()

    def on_quit(self):
        self.result = RESULT_QUIT
        self._close()


# ============================================================
# MAIN PROCESSING
# ============================================================

def process_sheet(
    sheet_path: str,
    hero_name: str,
    file_idx_in_folder: int,
    vector_mask: Image.Image,
    vector_preview_img: Optional[Image.Image],
    position_cache: Dict[str, Dict[str, Union[int, float]]],
    initial_placement: Optional[Tuple[int, int, float]],
) -> Tuple[Optional[Tuple[int, int, float]], bool]:
    """
    Returns:
        ((confirmed_x, confirmed_y, manual_scale_multiplier) or None, quit_requested)
    """
    sheet_key = relative_cache_key(sheet_path)
    sheet_name = os.path.basename(sheet_path)

    print(f"    Loading: {sheet_name}")

    first, original_size = load_preview_cell(sheet_path)
    base_units = automatic_vector_units(vector_mask, first.size)
    print(f"    Preview cell: {first.size}; automatic SVG width: {base_units}px")

    cached = position_cache.get(sheet_key)
    if cached is not None:
        starting_position = (int(cached["x"]), int(cached["y"]))
        starting_scale_multiplier = float(cached.get("scale", 1.0))
    elif initial_placement is not None:
        starting_position = (int(initial_placement[0]), int(initial_placement[1]))
        starting_scale_multiplier = float(initial_placement[2])
    else:
        starting_position = None
        starting_scale_multiplier = 1.0

    gui = VectorPlacementGUI(
        first,
        vector_mask,
        vector_preview_img,
        title=f"{hero_name} | {sheet_name}",
        initial_position=starting_position,
        initial_scale_multiplier=2,
    )
    gui.mainloop()

    result = gui.result
    # Release preview buffers before reopening the large source sheet.
    gui.frame_img.close()
    first.close()
    del gui

    if result == RESULT_QUIT:
        return None, True

    if result is None:
        print("    -> Skipped.")
        return None, False

    mask_x, mask_y, manual_scale_multiplier = result

    # Recreate the final mask from the untouched native SVG mask.
    # The same sizing helper guarantees the exported mask matches the preview.
    final_vector_mask = resize_mask_to_ratio_units(
        vector_mask, scaled_vector_units(base_units, manual_scale_multiplier),
    )

    position_cache[sheet_key] = {
        "x": int(mask_x),
        "y": int(mask_y),
        "scale": float(manual_scale_multiplier),
    }
    save_position_cache(POSITION_CACHE_PATH, position_cache)

    print(
        f"    -> Applying vector at x={mask_x}, y={mask_y}, "
        f"manual scale={manual_scale_multiplier * 100:.2f}% "
        f"({final_vector_mask.width}x{final_vector_mask.height}) "
        f"to {ROWS * COLS} frames..."
    )

    rebuilt = crop_sheet_after_confirmation(
        sheet_path, original_size, final_vector_mask, mask_x, mask_y,
    )

    expected_output_size = (
        final_vector_mask.width * COLS,
        final_vector_mask.height * ROWS,
    )
    if rebuilt.size != expected_output_size:
        raise RuntimeError(
            f"Unexpected rebuilt size: {rebuilt.size}; expected {expected_output_size}"
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
    print(f"       original sheet: {original_size}")
    print(f"       native vector frame: {vector_mask.size}")
    print(f"       final output frame: {final_vector_mask.size}")
    print(f"       output sheet: {rebuilt.size}")

    rebuilt.close()
    final_vector_mask.close()
    return (mask_x, mask_y, manual_scale_multiplier), False


def main() -> None:
    print("Vector editor build:", VECTOR_EDITOR_BUILD)
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
    print("Preview: shared camera zoom; SVG starts at half-cell size; wheel scales frame + SVG")
    print(
        f"WHEEL RESIZE: {VECTOR_WHEEL_UNIT_STEP} ratio unit per notch | "
        f"Shift={VECTOR_WHEEL_SHIFT_UNIT_STEP} units"
    )
    print(f"GRID: {COLS} columns x {ROWS} rows")
    print("----")

    vector_mask = load_svg_mask(VECTOR_SVG)
    print("Loaded SVG vector mask:", vector_mask.size)

    if not os.path.exists(VECTOR_PREVIEW_PNG):
        raise FileNotFoundError(f"Hero frame not found: {VECTOR_PREVIEW_PNG}")
    with Image.open(VECTOR_PREVIEW_PNG) as image:
        vector_preview_img = image.convert("RGBA")
    print("Loaded hero frame:", VECTOR_PREVIEW_PNG, vector_preview_img.size)

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
        print(folder_name)
        #if folder_name not in ["1039"]:
#         if folder_name in [
#     "1065",  # Rogue
#     "1057",  # Deadpool
#     "1028",  # Ultron
#     "1051",  # Thing
#     "1050",  # Invis
#     "1040",  # Mister Fantastic
#     "1052",  # Iron Fist
#     "1030",  # Moon Knight
#     "1033",  # Black Widow
#     "1041",  # Winter
#     "1047",  # Jeff
#     "1046",  # Adam
#     "1045",  # Namor
#     "1015",  # Storm
#     "1027",  # Groot
#     "1037",  # Magneto
#     "1043",  # Star-Lord
#     "1036",  # Spider-Man
#     "1042",  # Peni
#     "1014",  # Punisher
#     "1023",  # Rocket
# ]:
            #continue
        # if folder_name not in ["1048"]:
        #     continue
        print(
            f"[{folder_idx}/{len(folders)}] HERO FOLDER: {folder_name} "
            f"-> {hero_name} ({len(png_paths)} PNGs)"
        )
        print("  PATH:", folder_path)

        # Subsequent sheets in a hero folder inherit both the previous position
        # and manual size multiplier. Exact per-sheet cache still wins.
        last_confirmed_placement: Optional[Tuple[int, int, float]] = None

        for file_idx_in_folder, sheet_path in enumerate(png_paths):
            global_sheet_idx += 1
            print(
                f"  [{global_sheet_idx}/{total_sheets}] "
                f"folder index={file_idx_in_folder + FILE_INDEX_START}"
            )

            confirmed_placement, quit_requested = process_sheet(
                sheet_path=sheet_path,
                hero_name=hero_name,
                file_idx_in_folder=file_idx_in_folder,
                vector_mask=vector_mask,
                vector_preview_img=vector_preview_img,
                position_cache=position_cache,
                initial_placement=last_confirmed_placement,
            )

            if quit_requested:
                print("Quit requested. Exiting.")
                return

            if confirmed_placement is not None:
                last_confirmed_placement = confirmed_placement

        print("----")

    print("Finished processing all sheets.")


if __name__ == "__main__":
    main()