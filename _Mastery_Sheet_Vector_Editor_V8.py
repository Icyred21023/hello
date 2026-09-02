"""
Mastery Sprite Sheet Vector Mask Editor
---------------------------------------
Walks hero folders under SHEETS_DIR, processes every PNG in each folder,
and rebuilds each image as the same 6-column x 10-row sprite sheet after
clipping every frame with the same fixed SVG vector mask.

Workflow for each PNG:
  1) Resolve the hero from the containing folder using config.HERO_KEYS.
  2) Floor-divide the sheet into equal cells and discard right/bottom remainder pixels.
  3) Show the first frame with the SVG mask overlaid.
  4) Move the fixed-size vector with the arrow keys (1 source pixel per keypress).
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
  - VECTOR_WIDTH / VECTOR_HEIGHT are the final mask dimensions in source pixels.
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

VECTOR_EDITOR_BUILD = "2026-09-01-floor-grid-crop-v8"


# ============================================================
# USER SETTINGS
# ============================================================

EDITOR_DIR = os.path.join(config.script_dir, "_Mastery_Sheet_Editor")
SHEETS_DIR = os.path.join(EDITOR_DIR, "Raw Sheets")
OUTPUTS_DIR = os.path.join(EDITOR_DIR, "Outputs")

VECTOR_SVG = os.path.join(EDITOR_DIR, "svg.svg")
VECTOR_WIDTH = 322
VECTOR_HEIGHT = 368
REFERENCE_FRAME_W = 600
REFERENCE_FRAME_H = 400

ROWS = 10
COLS = 6

# Output names are: hero_name + file index + .png
# 0 -> HeroName0.png, HeroName1.png, ...
# 1 -> HeroName1.png, HeroName2.png, ...
FILE_INDEX_START = 0

CANVAS_MAX = 720
PREVIEW_PADDING = 100  # source-frame pixels shown around every side in the placement preview

# Exact integer aspect-ratio sizing.
#
# VECTOR_WIDTH x VECTOR_HEIGHT is reduced to its smallest whole-number ratio.
# With 322x368 this is 7:8 because gcd(322, 368) == 46.
# Therefore EVERY valid vector/output size is an exact multiple of 7x8:
#   308x352, 315x360, 322x368, 329x376, ...
#
# The automatic frame-based scale is quantized to the nearest valid ratio step.
# The mouse wheel then moves one exact ratio step at a time.
VECTOR_RATIO_GCD = math.gcd(VECTOR_WIDTH, VECTOR_HEIGHT)
VECTOR_RATIO_W = VECTOR_WIDTH // VECTOR_RATIO_GCD
VECTOR_RATIO_H = VECTOR_HEIGHT // VECTOR_RATIO_GCD
VECTOR_REFERENCE_UNITS = VECTOR_RATIO_GCD

VECTOR_WHEEL_UNIT_STEP = 1          # 7x8 px per notch for a 322x368 reference
VECTOR_WHEEL_SHIFT_UNIT_STEP = 5    # five ratio steps while Shift is held
VECTOR_MIN_SCALE_MULTIPLIER = 0.10  # lower bound relative to automatic size
VECTOR_MAX_SCALE_MULTIPLIER = 5.00  # upper bound relative to automatic size

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

def load_position_cache(path: str) -> Dict[str, Dict[str, Union[int, float]]]:
    """
    Load cached vector placement.

    Older cache files containing only x/y remain valid; their manual scale
    defaults to 1.0 (the normal automatic size for that frame).
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
def get_frame_scale(frame_w: int, frame_h: int) -> float:
    return min(
        frame_w / REFERENCE_FRAME_W,
        frame_h / REFERENCE_FRAME_H
    )


def _round_positive_half_up(value: float) -> int:
    """Round a non-negative value conventionally: .5 always rounds upward."""
    return int(math.floor(float(value) + 0.5))


def ratio_size_from_units(units: int) -> Tuple[int, int]:
    """
    Convert an integer ratio-unit count into an exact aspect-locked size.

    Example for VECTOR_WIDTH=322, VECTOR_HEIGHT=368:
        reduced ratio = 7:8
        units 46 -> 322x368
        units 45 -> 315x360
        units 44 -> 308x352
    """
    units = max(1, int(units))
    return VECTOR_RATIO_W * units, VECTOR_RATIO_H * units


def ratio_units_from_size(width: int, height: int) -> int:
    """Return the nearest exact reduced-ratio unit count for a size."""
    # Width and height are both consulted so this remains robust if a future
    # base mask was not already perfectly quantized.
    by_w = float(width) / VECTOR_RATIO_W
    by_h = float(height) / VECTOR_RATIO_H
    return max(1, _round_positive_half_up((by_w + by_h) / 2.0))


def resize_mask_to_ratio_units(
    base_mask: Image.Image,
    ratio_units: int,
) -> Image.Image:
    """Resize a mask to an exact whole-number multiple of the SVG aspect ratio."""
    new_w, new_h = ratio_size_from_units(ratio_units)

    if base_mask.size == (new_w, new_h):
        return base_mask.copy()

    return base_mask.resize((new_w, new_h), Image.Resampling.LANCZOS)


def scale_vector_mask_for_frame(
    base_mask: Image.Image,
    frame_w: int,
    frame_h: int
):
    """
    Automatically scale the reference SVG for a frame, then QUANTIZE the result
    to the nearest exact whole-number aspect-ratio size.

    For the current 322x368 vector, all results are exact 7:8 multiples.
    """
    requested_scale = get_frame_scale(frame_w, frame_h)

    # The reference vector is VECTOR_REFERENCE_UNITS copies of the reduced
    # ratio. Scale that unit count, then snap to the nearest whole unit.
    ratio_units = max(
        1,
        _round_positive_half_up(VECTOR_REFERENCE_UNITS * requested_scale),
    )
    new_w, new_h = ratio_size_from_units(ratio_units)

    scaled_mask = base_mask.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )

    # Return the ACTUAL quantized scale, not the fractional requested scale.
    effective_scale = ratio_units / float(VECTOR_REFERENCE_UNITS)
    return scaled_mask, effective_scale


def resize_mask_with_multiplier(
    base_mask: Image.Image,
    multiplier: float,
) -> Image.Image:
    """
    Resize from an already-quantized automatic base mask while preserving the
    SVG aspect ratio EXACTLY in integer pixels.

    Instead of independently rounding width and height, the multiplier is
    applied to one integer ratio-unit count. This guarantees sizes such as
    322x368 -> 315x360 -> 308x352 with no off-ratio dimensions in between.
    """
    multiplier = max(
        VECTOR_MIN_SCALE_MULTIPLIER,
        min(VECTOR_MAX_SCALE_MULTIPLIER, float(multiplier)),
    )

    base_units = ratio_units_from_size(base_mask.width, base_mask.height)
    target_units = max(
        1,
        _round_positive_half_up(base_units * multiplier),
    )

    min_units = max(
        1,
        _round_positive_half_up(base_units * VECTOR_MIN_SCALE_MULTIPLIER),
    )
    max_units = max(
        min_units,
        _round_positive_half_up(base_units * VECTOR_MAX_SCALE_MULTIPLIER),
    )
    target_units = clamp(target_units, min_units, max_units)

    return resize_mask_to_ratio_units(base_mask, target_units)

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
    Return equally-spaced integer edges using one floor-divided cell size.

    Any remainder is deliberately excluded from the final edge. For example:

        split_edges(1935, 6) -> [0, 322, 644, 966, 1288, 1610, 1932]

    The remaining three pixels at the right edge are not included in a frame.
    """
    if parts <= 0:
        raise ValueError("parts must be greater than zero.")

    cell_size = total // parts
    if cell_size <= 0:
        raise ValueError(
            f"Cannot split {total} pixels into {parts} non-empty cells."
        )

    return [index * cell_size for index in range(parts + 1)]


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
    width: int,
    height: int,
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
    width: int,
    height: int,
) -> Optional[Image.Image]:
    if rendered is None:
        return None

    # Resize ONLY the rasterized VECTOR MASK canvas. Sprite pixels are never
    # resized. Transparent Illustrator artboard padding remains transparent.
    if rendered.size != (width, height):
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


def load_svg_mask(svg_path: str, width: int, height: int) -> Image.Image:
    """
    Rasterize the Illustrator SVG into an 8-bit alpha clipping mask.

    Transparent padding around the path is valid and preserved. This function
    tries the Illustrator appearance first, then progressively ignores styling
    and finally rebuilds a geometry-only SVG so CSS/masks/defs cannot make the
    path disappear.
    """
    if width <= 0 or height <= 0:
        raise ValueError("VECTOR_WIDTH and VECTOR_HEIGHT must be > 0")

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
    """
    Shows frame 0 with PREVIEW_PADDING source pixels around every side and the
    real SVG mask overlaid. The automatic frame-based scale is used as the
    starting size, but the user can resize the complete SVG canvas manually.

    Controls:
        Left / Right / Up / Down -> move exactly 1 SOURCE pixel
        Shift + Arrow             -> move 10 SOURCE pixels
        Mouse wheel up/down       -> next/previous exact aspect-ratio size
        Shift + mouse wheel       -> jump 5 exact ratio sizes
        Enter                     -> confirm
        Escape                    -> skip

    Wheel resizing is aspect locked, integer-quantized, and scales around the
    vector's current center. For 322x368, each normal wheel notch changes the
    size by exactly 7x8 pixels (322x368 -> 315x360 -> 308x352, etc.).
    """

    def __init__(
        self,
        frame_img: Image.Image,
        vector_mask: Image.Image,
        title: str,
        initial_position: Optional[Tuple[int, int]] = None,
        initial_scale_multiplier: float = 1.0,
    ):
        super().__init__()

        self.title(title)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

        self.frame_img = frame_img.convert("RGBA")

        # Keep an untouched copy of the automatic per-frame vector size. The
        # automatic size has already been snapped to the exact reduced SVG ratio.
        # Manual resizing changes ONE integer ratio-unit count, never width and
        # height independently, so every displayed/output size remains exact.
        self.base_vector_mask = vector_mask.convert("L").copy()
        self.base_ratio_units = ratio_units_from_size(
            self.base_vector_mask.width,
            self.base_vector_mask.height,
        )
        self.min_ratio_units = max(
            1,
            _round_positive_half_up(
                self.base_ratio_units * VECTOR_MIN_SCALE_MULTIPLIER
            ),
        )
        self.max_ratio_units = max(
            self.min_ratio_units,
            _round_positive_half_up(
                self.base_ratio_units * VECTOR_MAX_SCALE_MULTIPLIER
            ),
        )

        requested_units = _round_positive_half_up(
            self.base_ratio_units * float(initial_scale_multiplier)
        )
        self.ratio_units = clamp(
            requested_units,
            self.min_ratio_units,
            self.max_ratio_units,
        )
        self.scale_multiplier = self.ratio_units / float(self.base_ratio_units)
        self.vector_mask = resize_mask_to_ratio_units(
            self.base_vector_mask,
            self.ratio_units,
        )

        self.fw, self.fh = self.frame_img.size
        self.mw, self.mh = self.vector_mask.size
        self.preview_padding = int(PREVIEW_PADDING)

        if initial_position is None:
            self.x = (self.fw - self.mw) // 2
            self.y = (self.fh - self.mh) // 2
        else:
            self.x = int(initial_position[0])
            self.y = int(initial_position[1])

        # Result is (x, y, manual_scale_multiplier).
        self.result: Optional[Union[Tuple[int, int, float], str]] = None

        # Preview canvas is the source frame plus fixed padding on all sides.
        self.preview_w = self.fw + self.preview_padding * 2
        self.preview_h = self.fh + self.preview_padding * 2

        self.display_scale = min(
            CANVAS_MAX / self.preview_w,
            CANVAS_MAX / self.preview_h,
            1.0,
        )

        self.disp_w = max(1, int(round(self.preview_w * self.display_scale)))
        self.disp_h = max(1, int(round(self.preview_h * self.display_scale)))

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
            "Arrows = move 1 px    Shift+Arrows = 10 px    "
            "Wheel = next exact ratio size    Shift+Wheel = 5 sizes    Enter = Confirm"
        )
        tk.Label(self, text=instruction).grid(
            row=2,
            column=0,
            columnspan=5,
            padx=8,
            pady=(0, 8),
        )

        self.btn_center = tk.Button(
            self, text="Center", command=self.on_center, takefocus=False
        )
        self.btn_reset_size = tk.Button(
            self, text="Reset size", command=self.on_reset_size, takefocus=False
        )
        self.btn_confirm = tk.Button(
            self, text="Confirm", command=self.on_confirm, takefocus=False
        )
        self.btn_skip = tk.Button(
            self, text="Skip sheet", command=self.on_skip, takefocus=False
        )
        self.btn_quit = tk.Button(
            self, text="Quit", command=self.on_quit, takefocus=False
        )

        self.btn_center.grid(row=3, column=0, padx=4, pady=(0, 8))
        self.btn_reset_size.grid(row=3, column=1, padx=4, pady=(0, 8))
        self.btn_confirm.grid(row=3, column=2, padx=4, pady=(0, 8))
        self.btn_skip.grid(row=3, column=3, padx=4, pady=(0, 8))
        self.btn_quit.grid(row=3, column=4, padx=4, pady=(0, 8))

        # Movement is deliberately UNCLAMPED. mask_x/mask_y are real source-frame
        # coordinates and can be negative or greater than the frame bounds.
        self.bind("<Left>", lambda event: self.move_mask(-1, 0))
        self.bind("<Right>", lambda event: self.move_mask(1, 0))
        self.bind("<Up>", lambda event: self.move_mask(0, -1))
        self.bind("<Down>", lambda event: self.move_mask(0, 1))
        self.bind("<Shift-Left>", lambda event: self.move_mask(-10, 0))
        self.bind("<Shift-Right>", lambda event: self.move_mask(10, 0))
        self.bind("<Shift-Up>", lambda event: self.move_mask(0, -10))
        self.bind("<Shift-Down>", lambda event: self.move_mask(0, 10))
        self.bind("<Return>", lambda event: self.on_confirm())
        self.bind("<Escape>", lambda event: self.on_skip())

        # bind_all makes the wheel work while the pointer is over the Canvas,
        # labels, or buttons. These bindings are removed before the window closes.
        self.bind_all("<MouseWheel>", self.on_mousewheel)   # Windows / macOS
        self.bind_all("<Button-4>", self.on_mousewheel)     # Linux wheel up
        self.bind_all("<Button-5>", self.on_mousewheel)     # Linux wheel down

        self._update_preview()
        self.after(100, self.focus_force)

    def _cleanup_global_bindings(self) -> None:
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass

    def _make_padded_preview(self) -> Image.Image:
        """Build the source-frame preview with PREVIEW_PADDING on every side."""
        pad = self.preview_padding

        # Neutral opaque background makes transparent/out-of-frame areas visible.
        preview = Image.new(
            "RGBA",
            (self.preview_w, self.preview_h),
            (48, 48, 48, 255),
        )

        # Darken source pixels that will be clipped, but only INSIDE the source
        # frame. The vector outline itself is drawn later across the full preview.
        full_frame_mask = make_full_frame_mask(
            self.frame_img.size,
            self.vector_mask,
            self.x,
            self.y,
        )
        outside = ImageChops.invert(full_frame_mask)
        shade_alpha = outside.point(lambda p: (p * 145) // 255)
        shade = Image.new("RGBA", self.frame_img.size, (0, 0, 0, 0))
        shade.putalpha(shade_alpha)
        shaded_frame = Image.alpha_composite(self.frame_img, shade)
        preview.alpha_composite(shaded_frame, (pad, pad))

        # Place the SVG mask in PREVIEW coordinates so its path remains visible
        # when it extends outside the source-frame boundary.
        preview_mask = Image.new("L", preview.size, 0)
        preview_mask.paste(
            self.vector_mask,
            (self.x + pad, self.y + pad),
        )

        expanded = preview_mask.filter(ImageFilter.MaxFilter(5))
        contracted = preview_mask.filter(ImageFilter.MinFilter(5))
        outline_alpha = ImageChops.subtract(expanded, contracted)

        outline = Image.new("RGBA", preview.size, (255, 230, 0, 0))
        outline.putalpha(outline_alpha)
        preview = Image.alpha_composite(preview, outline)

        # Show complete SVG/output canvas bounds, including transparent SVG padding.
        draw = ImageDraw.Draw(preview)
        left = self.x + pad
        top = self.y + pad
        right = left + self.mw - 1
        bottom = top + self.mh - 1
        draw.rectangle((left, top, right, bottom), outline=(0, 220, 255, 255), width=1)

        # Source frame boundary, useful when the vector overlaps the padded area.
        draw.rectangle(
            (pad, pad, pad + self.fw - 1, pad + self.fh - 1),
            outline=(220, 220, 220, 255),
            width=1,
        )

        return preview

    def _update_preview(self) -> None:
        preview = self._make_padded_preview()

        if preview.size != (self.disp_w, self.disp_h):
            preview = preview.resize(
                (self.disp_w, self.disp_h),
                Image.Resampling.LANCZOS,
            )

        self.tk_preview = ImageTk.PhotoImage(preview)
        self.canvas.itemconfigure(self.canvas_image_id, image=self.tk_preview)

        self.position_var.set(
            f"Vector position: x={self.x}, y={self.y}   |   "
            f"output frame={self.mw}x{self.mh}   |   "
            f"ratio={VECTOR_RATIO_W}:{VECTOR_RATIO_H} (units={self.ratio_units})   |   "
            f"manual size={self.scale_multiplier * 100:.1f}%   |   "
            f"source frame={self.fw}x{self.fh}"
        )

    def move_mask(self, dx: int, dy: int) -> None:
        self.x += int(dx)
        self.y += int(dy)
        self._update_preview()

    def set_ratio_units(self, new_units: int) -> None:
        """Resize to an exact integer ratio step around the current vector center."""
        new_units = clamp(
            int(new_units),
            self.min_ratio_units,
            self.max_ratio_units,
        )

        new_mask = resize_mask_to_ratio_units(
            self.base_vector_mask,
            new_units,
        )
        new_w, new_h = new_mask.size

        if (new_w, new_h) == (self.mw, self.mh):
            self.ratio_units = new_units
            self.scale_multiplier = (
                self.ratio_units / float(self.base_ratio_units)
            )
            self._update_preview()
            return

        # Keep the vector centered at the same source-frame coordinate while
        # changing its size. Negative x/y remain intentionally allowed.
        center_x = self.x + self.mw / 2.0
        center_y = self.y + self.mh / 2.0

        self.vector_mask = new_mask
        self.ratio_units = new_units
        self.scale_multiplier = (
            self.ratio_units / float(self.base_ratio_units)
        )
        self.mw, self.mh = new_w, new_h

        self.x = int(round(center_x - self.mw / 2.0))
        self.y = int(round(center_y - self.mh / 2.0))

        self._update_preview()

    def set_scale_multiplier(self, new_multiplier: float) -> None:
        """
        Compatibility helper for cached V6 scale values.

        The requested multiplier is converted to the nearest integer ratio-unit
        count before resizing, so even old cache values cannot produce an
        off-ratio width/height.
        """
        new_multiplier = max(
            VECTOR_MIN_SCALE_MULTIPLIER,
            min(VECTOR_MAX_SCALE_MULTIPLIER, float(new_multiplier)),
        )
        new_units = _round_positive_half_up(
            self.base_ratio_units * new_multiplier
        )
        self.set_ratio_units(new_units)

    def on_mousewheel(self, event) -> str:
        if getattr(event, "delta", 0):
            direction = 1 if event.delta > 0 else -1
        else:
            direction = 1 if getattr(event, "num", None) == 4 else -1

        shift_held = bool(getattr(event, "state", 0) & 0x0001)
        unit_step = (
            VECTOR_WHEEL_SHIFT_UNIT_STEP
            if shift_held
            else VECTOR_WHEEL_UNIT_STEP
        )

        self.set_ratio_units(
            self.ratio_units + direction * unit_step
        )
        return "break"

    def on_reset_size(self) -> None:
        """Return to the exact automatic frame-scaled ratio size."""
        self.set_ratio_units(self.base_ratio_units)
        self.focus_force()

    def on_center(self) -> None:
        self.x = (self.fw - self.mw) // 2
        self.y = (self.fh - self.mh) // 2
        self._update_preview()
        self.focus_force()

    def on_confirm(self) -> None:
        self.result = (self.x, self.y, float(self.scale_multiplier))
        self._cleanup_global_bindings()
        self.destroy()

    def on_skip(self) -> None:
        self.result = None
        self._cleanup_global_bindings()
        self.destroy()

    def on_quit(self) -> None:
        self.result = RESULT_QUIT
        self._cleanup_global_bindings()
        self.destroy()


# ============================================================
# MAIN PROCESSING
# ============================================================

def process_sheet(
    sheet_path: str,
    hero_name: str,
    file_idx_in_folder: int,
    vector_mask: Image.Image,
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

    with Image.open(sheet_path) as source:
        sheet = source.convert("RGBA")

    original_size = sheet.size
    frames, xs, ys = slice_frames(sheet, ROWS, COLS)

    if len(frames) != ROWS * COLS:
        print("    -> Incorrect frame count; skipping.")
        return None, False

    first = frames[0]
    frame_w, frame_h = first.size

    # Automatic reference-frame scaling is the starting point. It is first
    # quantized to an exact integer aspect-ratio size; the GUI then moves among
    # those same exact ratio sizes with the mouse wheel.
    auto_scaled_vector_mask, vector_scale = scale_vector_mask_for_frame(
        vector_mask,
        frame_w,
        frame_h,
    )

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
        auto_scaled_vector_mask,
        title=f"{hero_name} | {sheet_name}",
        initial_position=starting_position,
        initial_scale_multiplier=starting_scale_multiplier,
    )
    gui.mainloop()

    result = gui.result

    if result == RESULT_QUIT:
        return None, True

    if result is None:
        print("    -> Skipped.")
        return None, False

    mask_x, mask_y, manual_scale_multiplier = result

    # Recreate the final mask from the untouched automatic-size base mask.
    # resize_mask_with_multiplier quantizes through the same integer ratio-unit
    # system, guaranteeing processing uses the exact aspect ratio shown in GUI.
    final_vector_mask = resize_mask_with_multiplier(
        auto_scaled_vector_mask,
        manual_scale_multiplier,
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
        f"to {len(frames)} frames..."
    )

    edited_frames = [
        extract_frame_through_vector(frame, final_vector_mask, mask_x, mask_y)
        for frame in frames
    ]

    rebuilt = rebuild_fixed_frame_sheet(edited_frames, ROWS, COLS)

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
    print(f"       auto vector frame: {auto_scaled_vector_mask.size} (frame scale={vector_scale:.4f})")
    print(f"       final output frame: {final_vector_mask.size}")
    print(f"       output sheet: {rebuilt.size}")

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
    print(f"REFERENCE VECTOR SIZE: {VECTOR_WIDTH}x{VECTOR_HEIGHT} @ {REFERENCE_FRAME_W}x{REFERENCE_FRAME_H} frame")
    print(f"PREVIEW PADDING: {PREVIEW_PADDING}px per side")
    print(
        f"VECTOR RATIO: {VECTOR_RATIO_W}:{VECTOR_RATIO_H} | "
        f"reference units={VECTOR_REFERENCE_UNITS} | "
        f"valid reference sizes step by {VECTOR_RATIO_W}x{VECTOR_RATIO_H}px"
    )
    print(
        f"WHEEL RESIZE: {VECTOR_WHEEL_UNIT_STEP} ratio unit per notch | "
        f"Shift={VECTOR_WHEEL_SHIFT_UNIT_STEP} units"
    )
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