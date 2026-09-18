# text_color_preprocess.py
# --------------------------------------------
# Import this module and call preprocess_text_color(img, ...)
# Returns a uint8 mask (0/255) suitable for EasyOCR.

from __future__ import annotations
from typing import Iterable, Tuple, Union, Optional
import numpy as np

try:
    import cv2
except ImportError as e:
    raise ImportError("text_color_preprocess requires opencv-python (cv2).") from e

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


DEFAULT_TARGETS = ("#bebfcb", "#bfb1c2")


def _hex_to_bgr(h: str) -> np.ndarray:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {h!r}")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return np.array([b, g, r], dtype=np.uint8)


def _ensure_bgr_and_alpha(
    img: Union[np.ndarray, "Image.Image"]
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Returns:
      bgr: uint8 (H,W,3)
      alpha: uint8 (H,W) or None
    Supports:
      - numpy BGR / BGRA / RGB / RGBA
      - PIL RGB / RGBA
    """
    alpha = None

    # PIL input
    if PIL_AVAILABLE and isinstance(img, Image.Image):
        mode = img.mode
        if mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA") if "A" in mode else img.convert("RGB")
            mode = img.mode

        arr = np.array(img)
        if mode == "RGBA":
            alpha = arr[..., 3].copy()
            rgb = arr[..., :3]
        else:
            rgb = arr[..., :3]

        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return bgr.astype(np.uint8), alpha

    # numpy input
    if not isinstance(img, np.ndarray):
        raise TypeError("img must be a numpy array or a PIL Image.")

    if img.dtype != np.uint8:
        # best effort cast (assumes 0-255-ish)
        img = np.clip(img, 0, 255).astype(np.uint8)

    if img.ndim != 3 or img.shape[2] not in (3, 4):
        raise ValueError("numpy img must have shape (H,W,3) or (H,W,4).")

    if img.shape[2] == 4:
        # Assume BGRA (OpenCV default) unless user passed RGBA from elsewhere
        # Heuristic: if it looks like RGBA, user can pass force_rgb=True via wrapper (not included),
        # but for most pipelines it's BGRA.
        alpha = img[..., 3].copy()
        bgr = img[..., :3].copy()
        return bgr, alpha

    # 3-channel: assume BGR (OpenCV standard)
    bgr = img.copy()
    return bgr, None

def _lab_soft_mask(bgr: np.ndarray, hex_colors: Iterable[str], thr: float, softness: float = 0.35) -> np.ndarray:
    """
    Returns a grayscale mask (0..255) where closer-to-target pixels are whiter.
    - thr: roughly the cutoff distance
    - softness: fraction of thr used as a feather band
       (0.25–0.60 is typical)
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.int16)

    dists = []
    for h in hex_colors:
        tbgr = _hex_to_bgr(h)[None, None, :]
        tlab = cv2.cvtColor(tbgr, cv2.COLOR_BGR2LAB).astype(np.int16)
        diff = lab.astype(np.float32) - tlab.astype(np.float32)
        dist = np.linalg.norm(diff, axis=2)
        dists.append(dist)

    min_dist = np.minimum.reduce(dists).astype(np.float32)

    # Feather band around thr: pixels near thr get gray, inside gets white, outside gets black.
    band = max(1.0, float(thr) * float(softness))
    lo = float(thr) - band
    hi = float(thr) + band

    # Map: dist <= lo -> 255, dist >= hi -> 0, linear in between
    soft = (hi - min_dist) / (hi - lo)
    soft = np.nan_to_num(soft, nan=0.0, posinf=1.0, neginf=0.0)
    soft = np.clip(soft, 0.0, 1.0)

    return (soft * 255.0).astype(np.uint8)

def _lab_min_distance_mask(
    bgr: np.ndarray,
    hex_colors: Iterable[str],
    thr: float
) -> np.ndarray:
    """
    Create mask where pixels are within LAB distance threshold of any target color.
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.int16)

    dists = []
    for h in hex_colors:
        tbgr = _hex_to_bgr(h)[None, None, :]
        tlab = cv2.cvtColor(tbgr, cv2.COLOR_BGR2LAB).astype(np.int16)
        diff = lab - tlab
        dist = np.sqrt(diff[..., 0] ** 2 + diff[..., 1] ** 2 + diff[..., 2] ** 2)
        dists.append(dist)

    min_dist = np.minimum.reduce(dists)
    mask = (min_dist <= float(thr)).astype(np.uint8) * 255
    return mask


def _cleanup_mask(mask: np.ndarray, open_k: int = 2, dilate_k: int = 2, dilate_iter: int = 1) -> np.ndarray:
    """
    Small morphology to remove specks + reconnect anti-aliased edges.
    """
    if open_k and open_k > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_k, open_k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

    if dilate_k and dilate_k > 0 and dilate_iter > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k, dilate_k))
        mask = cv2.dilate(mask, k, iterations=int(dilate_iter))

    return mask


def _edge_gate(bgr: np.ndarray, mask: np.ndarray, c1: int = 50, c2: int = 130, dilate_k: int = 3) -> np.ndarray:
    """
    Optional: require edges to reduce dynamic-background noise.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, c1, c2)

    if dilate_k and dilate_k > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k, dilate_k))
        edges = cv2.dilate(edges, k, iterations=1)

    return cv2.bitwise_and(mask, edges)

def strip_right_by_vertical_gap_band(
    mask: np.ndarray,
    gap_px: int = 16,

    # detect gap using only mid y band
    y_band_frac=(0.30, 0.70),

    # how far right the gap must start
    min_x_frac: float = 0.45,

    # NEW: tolerance controls
    max_white_per_col: int = 1,     # within y-band, a column counts "empty" if <= this many white pixels
    max_white_per_row: int = 0,     # row validation: band counts "empty" if row has <= this many white pixels
    row_pass_frac: float = 0.98,    # fraction of rows that must pass validation

    # optional cleanup before detection
    erode_k: int = 0,               # set 2 to shrink specks before detection
    clear_right: bool = True,
) -> np.ndarray:
    h, w = mask.shape[:2]
    if h == 0 or w == 0:
        return mask

    m = (mask > 0).astype(np.uint8)

    # Optional: erode slightly before detecting the gap (reduces specks)
    if erode_k and erode_k > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_k, erode_k))
        m_det = cv2.erode(m, k, iterations=1)
    else:
        m_det = m

    y0 = int(h * y_band_frac[0])
    y1 = int(h * y_band_frac[1])
    y0 = max(0, min(h, y0))
    y1 = max(0, min(h, y1))
    if y1 <= y0:
        y0, y1 = 0, h

    # Column sums in the detection band
    col_sum = m_det[y0:y1, :].sum(axis=0)

    # Column is "empty enough" if <= tolerance
    empty_col = (col_sum <= int(max_white_per_col)).astype(np.uint8)

    # Find runs of gap_px empty-enough columns
    window = np.ones(gap_px, dtype=np.uint8)
    empty_count = np.convolve(empty_col, window, mode="valid")
    candidates = np.where(empty_count == gap_px)[0]

    if candidates.size == 0:
        return mask

    candidates = candidates[candidates >= int(w * min_x_frac)]
    if candidates.size == 0:
        return mask

    # Prefer the rightmost candidate (most likely name→icon split)
    x_start = int(candidates[-1])

    # Validate rows: the band at x_start must be "mostly empty" row-by-row
    band = m[:, x_start:x_start + gap_px]
    row_sum = band.sum(axis=1)
    row_ok = (row_sum <= int(max_white_per_row))

    if row_ok.mean() < float(row_pass_frac):
        return mask

    out = mask.copy()
    if clear_right:
        out[:, x_start:] = 0
    else:
        out[:, x_start:x_start + gap_px] = 0
    return out





def _strip_right_icon_by_gap(mask: np.ndarray,
                             min_gap_px: int = 8,
                             min_icon_area: int = 40,
                             icon_min_height_frac: float = 0.35) -> np.ndarray:
    """
    Removes a right-side icon by finding a large horizontal gap between connected components.
    Works with variable name length.

    - min_gap_px: required empty-x gap between end of text and start of icon
    - min_icon_area: ignore tiny specks
    - icon_min_height_frac: icon must be at least this fraction of mask height
                            (helps avoid removing punctuation/letters)
    """
    h, w = mask.shape[:2]
    if w == 0 or h == 0:
        return mask

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    comps = []
    for i in range(1, num):
        x, y, cw, ch, area = stats[i]
        if area < min_icon_area:
            continue
        comps.append((x, y, cw, ch, area, i))

    if len(comps) < 2:
        return mask

    comps.sort(key=lambda t: t[0])  # sort by x

    # Compute gaps between consecutive components
    gaps = []
    for a, b in zip(comps, comps[1:]):
        ax, ay, aw, ah, aa, ai = a
        bx, by, bw, bh, ba, bi = b
        gap = bx - (ax + aw)
        gaps.append((gap, a, b))

    # Find the largest gap that is "big enough"
    best = max(gaps, key=lambda t: t[0])
    best_gap, left_comp, right_comp = best

    if best_gap < min_gap_px:
        return mask  # no clear separation

    # Everything at/after right_comp is the "right group" (likely icon)
    split_x = right_comp[0]

    # Validate that the right group is icon-like (tall-ish / dense-ish)
    # Measure combined bbox + area of right group
    right_ids = []
    rx1, ry1 = 10**9, 10**9
    rx2, ry2 = -1, -1
    r_area = 0
    for (x, y, cw, ch, area, i) in comps:
        if x >= split_x:
            right_ids.append(i)
            rx1 = min(rx1, x); ry1 = min(ry1, y)
            rx2 = max(rx2, x + cw); ry2 = max(ry2, y + ch)
            r_area += area

    if not right_ids:
        return mask

    r_w = rx2 - rx1
    r_h = ry2 - ry1
    if r_h < int(h * icon_min_height_frac):
        return mask  # too short to be the icon group (avoid nuking text)

    # Density check: icons are usually compact/dense vs text strokes
    density = r_area / max(1, (r_w * r_h))
    if density < 0.08:
        return mask  # too sparse to be icon (likely text fragments)

    # Remove right group
    out = mask.copy()
    for i in right_ids:
        out[labels == i] = 0
    return out
def mask_to_col_dict(mask: np.ndarray) -> dict[int, list[int]]:
    """
    mask: shape (H,W) or (H,W,3)
    Returns: {col_index: [row0, row1, ...]} where each value is 0 or 1
    """
    if mask.ndim == 3:
        # convert to single channel by taking any channel
        mask = mask[..., 0]

    # ensure 0/1
    m = (mask > 0).astype(np.uint8)

    h, w = m.shape
    col_dict = {}
    for x in range(w):
        col_dict[x] = m[:, x].tolist()  # top->bottom
    return col_dict

def apply_mask_keep_text(
    img_bgr: np.ndarray,
    mask: np.ndarray,
    bg_color=(45, 45, 45)  # white background
) -> np.ndarray:
    """
    Keeps original text pixels, replaces background with solid color.
    img_bgr: (H,W,3)
    mask: (H,W) 0 or 255
    """
    if mask.ndim == 3:
        mask = mask[..., 0]

    m = (mask > 0)[..., None]  # shape (H,W,1) boolean

    bg = np.full_like(img_bgr, bg_color, dtype=np.uint8)
    out = np.where(m, img_bgr, bg)
    return out

def hex_to_rgb(hex_str: str):
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Bad hex color: {hex_str}")
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def _to_pil_rgb(im):
    # numpy -> PIL
    if not isinstance(im, Image.Image):
        im = Image.fromarray(im)

    # normalize modes
    if im.mode == "RGBA":
        # composite over dark bg so text stays visible
        bg = Image.new("RGB", im.size, (30, 30, 30))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")

    return im
from PIL import ImageDraw

def add_row_separators(img: Image.Image, crops, pad_y=6, sep_h=2, sep_color=(80,80,80)):
    # draws separators in the padding gaps
    draw = ImageDraw.Draw(img)
    y = 0
    for i, c in enumerate(crops[:-1]):
        h = c.shape[0] if hasattr(c, "shape") else c.height
        y += h
        y_mid = y + pad_y // 2
        draw.rectangle([0, y_mid, img.width, y_mid + sep_h], fill=sep_color)
        y += pad_y
    return img

def stack_name_crops(crops, pad_y=6, bg=(30,30,30), align="left"):
    """
    crops: list of numpy arrays or PIL Images
    bg: tuple (r,g,b) OR hex string like '1e1e1e' or '#1e1e1e'
    returns: PIL.Image RGB stacked vertically
    """
    if isinstance(bg, str):
        bg = hex_to_rgb(bg)

    rows = [_to_pil_rgb(im) for im in crops]

    max_w = max(im.width for im in rows) if rows else 1
    total_h = sum(im.height for im in rows) + pad_y * max(0, len(rows) - 1)

    out = Image.new("RGB", (max_w, total_h), bg)

    y = 0
    for im in rows:
        if align == "center":
            x = (max_w - im.width) // 2
        elif align == "right":
            x = max_w - im.width
        else:
            x = 0

        out.paste(im, (x, y))
        y += im.height + pad_y

    return out
def darken_non_grey_lab(bgr: np.ndarray,
                        chroma_thr: float = 35.0,
                        darken_to: int = 20,
                        feather: float = 0.25) -> np.ndarray:
    """
    Darken pixels that are 'colorful' (high chroma) while keeping grey-ish pixels.
    - chroma_thr: higher = less aggressive, lower = more aggressive
    - darken_to: output value (0-255) for colored regions (in BGR space after blend)
    - feather: softness around threshold (0.15–0.5)
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

    # a,b around 128 is neutral grey; distance from (128,128) = chroma
    a = lab[..., 1] - 128.0
    b = lab[..., 2] - 128.0
    chroma = np.sqrt(a*a + b*b)  # 0..~180

    band = max(1.0, chroma_thr * feather)
    lo = chroma_thr - band
    hi = chroma_thr + band

    # w = 0 (grey-ish) -> keep original, w = 1 (colorful) -> darken
    w = (chroma - lo) / (hi - lo)
    w = np.clip(w, 0.0, 1.0).astype(np.float32)

    dark = np.full_like(bgr, int(darken_to), dtype=np.uint8).astype(np.float32)
    out = (bgr.astype(np.float32) * (1.0 - w[..., None]) + dark * (w[..., None]))
    return np.clip(out, 0, 255).astype(np.uint8)

def preprocess_text_color(
    img: Union[np.ndarray, "Image.Image"],
    targets: Iterable[str] = DEFAULT_TARGETS,
    lab_thr: float = 30.0,
    use_alpha_gate: bool = False,
    alpha_min: int = 25,
    use_edge_gate: bool = False,
    invert: bool = False,
    # morphology
    open_k: int = 2,
    dilate_k: int = 2,
    dilate_iter: int = 1,
    # edge params
    edge_c1: int = 20,
    edge_c2: int = 120,
    edge_dilate_k: int = 1,
) -> np.ndarray:
    """
    Main API:
      - Pass in an image (numpy BGR/BGRA or PIL RGB/RGBA).
      - Returns a uint8 0/255 mask suitable for EasyOCR.

    Notes:
      - lab_thr: start at ~30 for anti-aliased UI text. Tune 24–38.
      - use_edge_gate: helps when background is dynamic and similar colors appear.
      - use_alpha_gate: only helps if input actually has an alpha channel.
    """
    bgr, alpha = _ensure_bgr_and_alpha(img)

    bgr = darken_non_grey_lab(
    bgr,
    chroma_thr=30.0,   # try 10–18
    darken_to=10,      # 0–30
    feather=0.0
)
    
    mask = _lab_soft_mask(bgr, targets, lab_thr, softness=0)
    #mask = _lab_min_distance_mask(bgr, targets, lab_thr)
    
    if use_alpha_gate and alpha is not None:
        a = (alpha >= int(alpha_min)).astype(np.uint8) * 255
        mask = cv2.bitwise_and(mask, a)



    #mask = _strip_right_icon_by_gap(mask, min_gap_px=10)

    if use_edge_gate:
        mask = _edge_gate(bgr, mask, c1=edge_c1, c2=edge_c2, dilate_k=edge_dilate_k)

    if invert:
        mask = cv2.bitwise_not(mask)

    mask = strip_right_by_vertical_gap_band(
        mask,
        gap_px=11,
        y_band_frac=(0.35, 0.65),
        max_white_per_col=1,     # allow 1 speck per column in the detect band
        max_white_per_row=0,     # stricter per-row validation
        row_pass_frac=0.98,
        erode_k=2,               # shrink specks just for detection
        min_x_frac=0.20,
    )
    col_dict = mask_to_col_dict(mask)
    #print(f"Column pixel data: {col_dict}")
    gap = 0
    for column in col_dict:
        if sum(col_dict[column]) == 0:
            gap += 1
        else:
            gap = 0
        if gap >= 10:

            if int(column) <20:
                mask[:, :column-5] = 0
                continue
            elif gap >= 11:
                mask[:, column:] = 0
                break
    mask = apply_mask_keep_text(bgr, mask, bg_color=(30,30,30))
    #mask_big = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    # gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    # blur = cv2.GaussianBlur(gray, (3,3), 0)
    # _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return mask