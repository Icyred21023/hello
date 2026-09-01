"""
Pydroid 3 neural image upscaler
- Uses OpenCV dnn_superres with FSRCNN or EDSR
- Supports x2 and x4
- Preserves PNG transparency
- Can process one image or every image in a folder

Edit the SETTINGS section, then run.
"""


from __future__ import annotations
import lordopenai
import sys
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np


# =========================
# SETTINGS
# =========================

# One image:
INPUT_PATH = "/storage/emulated/0/Download/input.png"

# Or a folder. Set to "" to use INPUT_PATH.
INPUT_FOLDER = lordopenai.img_dir

OUTPUT_FOLDER = lordopenai.img_save_dir

# 2 or 4
SCALE = 4

# "fsrcnn" = much faster and tiny model; recommended on a phone
# "edsr"   = higher quality but much slower and ~37 MB
MODEL = "edsr"

# For transparent artwork, extend edge colors slightly beneath transparency
# before upscaling. This helps reduce dark/colored halos.
ALPHA_EDGE_BLEED = True

# Supported source types
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


MODEL_URLS = {
    ("fsrcnn", 2): (
        "https://raw.githubusercontent.com/Saafke/"
        "FSRCNN_Tensorflow/master/models/FSRCNN_x2.pb"
    ),
    ("fsrcnn", 4): (
        "https://raw.githubusercontent.com/Saafke/"
        "FSRCNN_Tensorflow/master/models/FSRCNN_x4.pb"
    ),
    ("edsr", 2): (
        "https://raw.githubusercontent.com/Saafke/"
        "EDSR_Tensorflow/master/models/EDSR_x2.pb"
    ),
    ("edsr", 4): (
        "https://raw.githubusercontent.com/Saafke/"
        "EDSR_Tensorflow/master/models/EDSR_x4.pb"
    ),
}


def check_requirements() -> None:
    if not hasattr(cv2, "dnn_superres"):
        raise RuntimeError(
            "\nYour OpenCV build does not contain cv2.dnn_superres.\n"
            "In Pydroid 3, install the repository plugin, then install "
            "'opencv-contrib-python' from Pydroid's Pip/package manager.\n"
            "After installing it, fully close and reopen Pydroid 3.\n"
        )


def download_model(model: str, scale: int, model_dir: Path) -> Path:
    key = (model.lower(), scale)
    if key not in MODEL_URLS:
        raise ValueError("MODEL must be 'fsrcnn' or 'edsr', and SCALE must be 2 or 4.")

    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{model.upper()}_x{scale}.pb"

    if model_path.exists() and model_path.stat().st_size > 1_000:
        return model_path

    print(f"Downloading model: {model_path.name}")
    print("This happens only once.")
    urllib.request.urlretrieve(MODEL_URLS[key], model_path)

    if not model_path.exists() or model_path.stat().st_size < 1_000:
        raise RuntimeError("Model download failed or produced an invalid file.")

    return model_path


def load_sr(model_path: Path, model: str, scale: int):
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(model_path))
    sr.setModel(model.lower(), scale)
    return sr


def bleed_colors_under_alpha(
    bgr: np.ndarray,
    alpha: np.ndarray,
    iterations: int = 6,
) -> np.ndarray:
    """
    Expands nearby opaque RGB colors a few pixels beneath fully transparent areas.
    The final alpha is restored, so this only improves antialiased edge colors.
    """
    result = bgr.copy()
    known = alpha > 0
    kernel = np.ones((3, 3), dtype=np.uint8)

    for _ in range(iterations):
        expanded_known = cv2.dilate(known.astype(np.uint8), kernel) > 0
        new_pixels = expanded_known & ~known

        if not np.any(new_pixels):
            break

        dilated = cv2.dilate(result, kernel)
        result[new_pixels] = dilated[new_pixels]
        known = expanded_known

    return result


def load_image(path: Path) -> np.ndarray:
    # np.fromfile + imdecode is reliable with unusual filenames.
    raw = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ValueError(f"Could not decode image: {path}")

    return image


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()
    if suffix == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
    elif suffix in {".jpg", ".jpeg"}:
        params = [cv2.IMWRITE_JPEG_QUALITY, 95]
    elif suffix == ".webp":
        params = [cv2.IMWRITE_WEBP_QUALITY, 95]
    else:
        params = []

    ok, encoded = cv2.imencode(suffix, image, params)
    if not ok:
        raise RuntimeError(f"Could not encode output: {path}")

    encoded.tofile(str(path))


def upscale_image(
    sr,
    input_path: Path,
    output_path: Path,
    scale: int,
) -> None:
    image = load_image(input_path)

    # Normalize to BGR or BGRA.
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        alpha = None
    elif image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]
    elif image.shape[2] == 3:
        bgr = image
        alpha = None
    else:
        raise ValueError(f"Unsupported channel count in {input_path}")

    if alpha is not None and ALPHA_EDGE_BLEED:
        bgr = bleed_colors_under_alpha(bgr, alpha)

    start = time.perf_counter()
    upscaled_bgr = sr.upsample(bgr)

    if alpha is not None:
        target_size = (upscaled_bgr.shape[1], upscaled_bgr.shape[0])
        upscaled_alpha = cv2.resize(
            alpha,
            target_size,
            interpolation=cv2.INTER_LANCZOS4,
        )

        # Preserve fully transparent output where alpha rounds to zero.
        output = np.dstack((upscaled_bgr, upscaled_alpha))
        output[upscaled_alpha == 0, :3] = 0
    else:
        output = upscaled_bgr

    # Transparency requires PNG/WebP. Force PNG when source contains alpha.
    if alpha is not None and output_path.suffix.lower() not in {".png", ".webp"}:
        output_path = output_path.with_suffix(".png")

    save_image(output_path, output)

    elapsed = time.perf_counter() - start
    old_h, old_w = image.shape[:2]
    new_h, new_w = output.shape[:2]

    print(
        f"Done: {input_path.name}\n"
        f"      {old_w}x{old_h} -> {new_w}x{new_h}\n"
        f"      Saved: {output_path}\n"
        f"      Time: {elapsed:.2f} seconds"
    )


def collect_inputs() -> list[Path]:
    if INPUT_FOLDER.strip():
        folder = Path(INPUT_FOLDER)
        if not folder.is_dir():
            raise FileNotFoundError(f"Input folder does not exist: {folder}")

        files = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSIONS
        )

        if not files:
            raise FileNotFoundError(f"No supported images found in: {folder}")

        return files

    path = Path(INPUT_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Input image does not exist: {path}")

    return [path]

import os
def main() -> None:
    check_requirements()

    model = MODEL.lower().strip()
    scale = int(SCALE)

    script_dir = Path(__file__).resolve().parent
    model_path = download_model(model, scale, script_dir / "sr_models")
    sr = load_sr(model_path, model, scale)

    output_dir = Path(OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = collect_inputs()
    print(f"\nUsing {model.upper()} x{scale}")
    print(f"Images to process: {len(inputs)}\n")

    failures = 0

    for index, input_path in enumerate(inputs, start=1):
        print(f"[{index}/{len(inputs)}] {input_path.name}")

        # Keep original extension, except alpha inputs may be forced to PNG later.
        output_name = f"{input_path.stem}_x{scale}{input_path.suffix.lower()}"
        output_path = output_dir / output_name
        if os.path.exists(output_path):
            print(f"Skipping, already exists")
            continue

        try:
            upscale_image(sr, input_path, output_path, scale)
        except Exception as exc:
            failures += 1
            print(f"FAILED: {input_path}\nReason: {exc}\n")

    print(f"\nFinished. Successful: {len(inputs) - failures}; Failed: {failures}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
