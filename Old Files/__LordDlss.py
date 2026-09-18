"""
Pydroid 3 direct Real-ESRGAN upscaler
No BasicSR and no realesrgan pip package required.

Required:
    torch
    torchvision
    pillow
    numpy

Recommended model:
    RealESRGAN_x4plus_anime_6B
    - clean illustrated/game character artwork
    - smaller than the general x4plus model
    - generates more convincing edge/detail reconstruction than FSRCNN

Edit SETTINGS, then run.
"""

from __future__ import annotations

import gc
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
import lordopenai

# ============================================================
# SETTINGS
# ============================================================
import helpers


SPECIFIC_HEROES = False
#SPECIFIC_HEROES = ["selecthero"]

img_dir = helpers.create_path(folder="lord")
img_save_dir = helpers.create_path(folder="lord chatgpt")

INPUT_PATH = "/storage/emulated/0/Download/input.png"

# Leave empty to process INPUT_PATH.
# Set this to a folder to process all supported images inside it.
INPUT_FOLDER = img_dir

OUTPUT_FOLDER =  img_save_dir

# The network is natively 4x.
# OUTPUT_SCALE may be 2 or 4.
# At 2x, the model first reconstructs at 4x, then downsamples cleanly.
OUTPUT_SCALE = 4

# Lower this if Android closes the process or reports out-of-memory.
# 96 or 128 is a safe starting point. Try 160/192 if your phone has room.
TILE_SIZE = 128

# Context around each tile. Helps hide tile boundaries.
TILE_PAD = 12

# CPU threads. Your screenshot showed 8 available.
CPU_THREADS = 8

# Preserve transparent PNG edges.
ALPHA_EDGE_BLEED = False
ALPHA_BLEED_PASSES = 8

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

MODEL_URL = (
    "https://github.com/xinntao/Real-ESRGAN/releases/download/"
    "v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
)
MODEL_FILENAME = "RealESRGAN_x4plus_anime_6B.pth"


# ============================================================
# REAL-ESRGAN / RRDBNet ARCHITECTURE
# ============================================================

def default_init_weights(module_list, scale=1.0):
    if not isinstance(module_list, list):
        module_list = [module_list]

    for module in module_list:
        for layer in module.modules():
            if isinstance(layer, nn.Conv2d):
                nn.init.kaiming_normal_(
                    layer.weight,
                    a=0,
                    mode="fan_in",
                    nonlinearity="leaky_relu",
                )
                layer.weight.data *= scale
                if layer.bias is not None:
                    layer.bias.data.zero_()


class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat=64, num_grow_ch=32):
        super().__init__()

        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(
            num_feat + num_grow_ch,
            num_grow_ch,
            3,
            1,
            1,
        )
        self.conv3 = nn.Conv2d(
            num_feat + 2 * num_grow_ch,
            num_grow_ch,
            3,
            1,
            1,
        )
        self.conv4 = nn.Conv2d(
            num_feat + 3 * num_grow_ch,
            num_grow_ch,
            3,
            1,
            1,
        )
        self.conv5 = nn.Conv2d(
            num_feat + 4 * num_grow_ch,
            num_feat,
            3,
            1,
            1,
        )

        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

        default_init_weights(
            [self.conv1, self.conv2, self.conv3, self.conv4, self.conv5],
            0.1,
        )

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), dim=1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), dim=1)))
        x4 = self.lrelu(
            self.conv4(torch.cat((x, x1, x2, x3), dim=1))
        )
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), dim=1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, num_feat, num_grow_ch=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


def make_layer(block, num_blocks, **kwargs):
    return nn.Sequential(
        *(block(**kwargs) for _ in range(num_blocks))
    )


class RRDBNet(nn.Module):
    def __init__(
        self,
        num_in_ch=3,
        num_out_ch=3,
        scale=4,
        num_feat=64,
        num_block=6,
        num_grow_ch=32,
    ):
        super().__init__()

        self.scale = scale
        self.conv_first = nn.Conv2d(
            num_in_ch,
            num_feat,
            3,
            1,
            1,
        )

        self.body = make_layer(
            RRDB,
            num_block,
            num_feat=num_feat,
            num_grow_ch=num_grow_ch,
        )

        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(
            num_feat,
            num_out_ch,
            3,
            1,
            1,
        )
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat

        feat = self.lrelu(
            self.conv_up1(
                F.interpolate(
                    feat,
                    scale_factor=2,
                    mode="nearest",
                )
            )
        )
        feat = self.lrelu(
            self.conv_up2(
                F.interpolate(
                    feat,
                    scale_factor=2,
                    mode="nearest",
                )
            )
        )

        out = self.conv_last(
            self.lrelu(self.conv_hr(feat))
        )
        return out


# ============================================================
# MODEL LOADING
# ============================================================

def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and destination.stat().st_size > 1_000_000:
        return

    print(f"Downloading {destination.name}...")
    print("This happens once and may take a moment.")

    temp_path = destination.with_suffix(destination.suffix + ".part")

    try:
        urllib.request.urlretrieve(url, str(temp_path))
        Path(str(temp_path)).replace(str(destination))
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    if not destination.exists() or destination.stat().st_size < 1_000_000:
        raise RuntimeError("The model download did not complete correctly.")


def load_model(model_path: Path) -> nn.Module:
    model = RRDBNet(
        num_in_ch=3,
        num_out_ch=3,
        scale=4,
        num_feat=64,
        num_block=6,
        num_grow_ch=32,
    )

    checkpoint = torch.load(
        str(model_path),
        map_location="cpu",
        weights_only=False,
    )

    if isinstance(checkpoint, dict):
        if "params_ema" in checkpoint:
            state_dict = checkpoint["params_ema"]
        elif "params" in checkpoint:
            state_dict = checkpoint["params"]
        else:
            state_dict = checkpoint
    else:
        raise RuntimeError("Unexpected model checkpoint structure.")

    # Some checkpoints may have a module. prefix.
    clean_state = {}
    for key, value in state_dict.items():
        if key.startswith("module."):
            key = key[7:]
        clean_state[key] = value

    model.load_state_dict(clean_state, strict=True)
    model.eval()

    # CPU inference.
    model = model.to(device="cpu", dtype=torch.float32)
    return model


# ============================================================
# IMAGE HELPERS
# ============================================================

def bleed_rgb_beneath_alpha(
    rgb: np.ndarray,
    alpha: np.ndarray,
    passes: int,
) -> np.ndarray:
    """
    Copies nearby opaque colors underneath transparent pixels.
    Alpha is restored later, so this only improves antialiased edges.
    """
    result = rgb.copy()
    known = alpha > 0

    height, width = known.shape

    for _ in range(passes):
        if known.all():
            break

        new_result = result.copy()
        new_known = known.copy()

        # 8-neighbor propagation.
        for dy, dx in (
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),            (0, 1),
            (1, -1),  (1, 0),   (1, 1),
        ):
            shifted_known = np.zeros_like(known)
            shifted_rgb = np.zeros_like(result)

            src_y0 = max(0, -dy)
            src_y1 = min(height, height - dy)
            src_x0 = max(0, -dx)
            src_x1 = min(width, width - dx)

            dst_y0 = max(0, dy)
            dst_y1 = min(height, height + dy)
            dst_x0 = max(0, dx)
            dst_x1 = min(width, width + dx)

            shifted_known[dst_y0:dst_y1, dst_x0:dst_x1] = (
                known[src_y0:src_y1, src_x0:src_x1]
            )
            shifted_rgb[dst_y0:dst_y1, dst_x0:dst_x1] = (
                result[src_y0:src_y1, src_x0:src_x1]
            )

            fill = (~new_known) & shifted_known
            new_result[fill] = shifted_rgb[fill]
            new_known[fill] = True

        result = new_result
        known = new_known

    return result


def pil_to_tensor(rgb: np.ndarray) -> torch.Tensor:
    array = np.ascontiguousarray(rgb.astype(np.float32) / 255.0)
    tensor = torch.from_numpy(array)
    tensor = tensor.permute(2, 0, 1).unsqueeze(0)
    return tensor


def tensor_to_uint8(tensor: torch.Tensor) -> np.ndarray:
    tensor = tensor.squeeze(0).clamp(0.0, 1.0)
    tensor = tensor.permute(1, 2, 0).contiguous()
    array = tensor.cpu().numpy()
    return np.round(array * 255.0).astype(np.uint8)


# ============================================================
# TILED INFERENCE
# ============================================================

@torch.inference_mode()
def upscale_tiled(
    model: nn.Module,
    input_tensor: torch.Tensor,
    tile_size: int,
    tile_pad: int,
    scale: int = 4,
) -> torch.Tensor:
    _, channels, height, width = input_tensor.shape

    if tile_size <= 0 or (height <= tile_size and width <= tile_size):
        return model(input_tensor)

    output = torch.zeros(
        (1, channels, height * scale, width * scale),
        dtype=torch.float32,
        device="cpu",
    )

    tiles_x = (width + tile_size - 1) // tile_size
    tiles_y = (height + tile_size - 1) // tile_size
    total_tiles = tiles_x * tiles_y
    tile_number = 0

    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile_number += 1
            print(
                f"\r    Tile {tile_number}/{total_tiles}",
                end="",
                flush=True,
            )

            x_start = x
            y_start = y
            x_end = min(x + tile_size, width)
            y_end = min(y + tile_size, height)

            x_pad_start = max(x_start - tile_pad, 0)
            y_pad_start = max(y_start - tile_pad, 0)
            x_pad_end = min(x_end + tile_pad, width)
            y_pad_end = min(y_end + tile_pad, height)

            input_tile = input_tensor[
                :,
                :,
                y_pad_start:y_pad_end,
                x_pad_start:x_pad_end,
            ]

            output_tile = model(input_tile)

            # Coordinates of the non-padded tile in the final output.
            out_x_start = x_start * scale
            out_y_start = y_start * scale
            out_x_end = x_end * scale
            out_y_end = y_end * scale

            # Crop padding away from the model output.
            crop_x_start = (x_start - x_pad_start) * scale
            crop_y_start = (y_start - y_pad_start) * scale
            crop_x_end = crop_x_start + (x_end - x_start) * scale
            crop_y_end = crop_y_start + (y_end - y_start) * scale

            output[
                :,
                :,
                out_y_start:out_y_end,
                out_x_start:out_x_end,
            ] = output_tile[
                :,
                :,
                crop_y_start:crop_y_end,
                crop_x_start:crop_x_end,
            ]

            del input_tile, output_tile
            gc.collect()

    print()
    return output


# ============================================================
# PROCESSING
# ============================================================

def collect_inputs() -> list[Path]:
    if INPUT_FOLDER.strip():
        folder = Path(INPUT_FOLDER)
        if not folder.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder}")

        files = sorted(
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        if not files:
            raise FileNotFoundError(
                f"No supported images found in {folder}"
            )

        return files

    path = Path(INPUT_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    return [path]


def process_image(
    model: nn.Module,
    input_path: Path,
    output_dir: Path,
) -> None:
    start = time.perf_counter()

    with Image.open(input_path) as source:
        source.load()
        has_alpha = source.mode in ("RGBA", "LA") or (
            source.mode == "P" and "transparency" in source.info
        )

        rgba = source.convert("RGBA")
        rgba_array = np.array(rgba, dtype=np.uint8)

    rgb = rgba_array[:, :, :3]
    alpha = rgba_array[:, :, 3]

    if has_alpha and ALPHA_EDGE_BLEED:
        rgb = bleed_rgb_beneath_alpha(
            rgb,
            alpha,
            ALPHA_BLEED_PASSES,
        )

    input_tensor = pil_to_tensor(rgb)

    output_tensor = upscale_tiled(
        model=model,
        input_tensor=input_tensor,
        tile_size=TILE_SIZE,
        tile_pad=TILE_PAD,
        scale=4,
    )

    output_rgb = tensor_to_uint8(output_tensor)

    del input_tensor, output_tensor
    gc.collect()

    native_height, native_width = output_rgb.shape[:2]

    alpha_image = Image.fromarray(alpha, mode="L").resize(
        (native_width, native_height),
        resample=Image.Resampling.LANCZOS,
    )

    rgb_image = Image.fromarray(output_rgb, mode="RGB")

    if OUTPUT_SCALE == 2:
        target_size = (
            rgba_array.shape[1] * 2,
            rgba_array.shape[0] * 2,
        )
        rgb_image = rgb_image.resize(
            target_size,
            resample=Image.Resampling.LANCZOS,
        )
        alpha_image = alpha_image.resize(
            target_size,
            resample=Image.Resampling.LANCZOS,
        )
    elif OUTPUT_SCALE != 4:
        raise ValueError("OUTPUT_SCALE must be either 2 or 4.")

    if has_alpha:
        output_image = rgb_image.convert("RGBA")
        output_image.putalpha(alpha_image)

        output_name = (
            f"{input_path.stem}_RealESRGAN_x{OUTPUT_SCALE}.png"
        )
    else:
        output_image = rgb_image
        extension = ".png" if input_path.suffix.lower() == ".png" else ".jpg"
        output_name = (
            f"{input_path.stem}_RealESRGAN_x{OUTPUT_SCALE}{extension}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name

    if output_image.mode == "RGBA":
        output_image.save(output_path, format="PNG", compress_level=0)
    elif output_path.suffix.lower() == ".jpg":
        output_image.save(
            output_path,
            format="JPEG",
            quality=96,
            subsampling=0,
        )
    else:
        output_image.save(output_path, format="PNG", compress_level=0)

    elapsed = time.perf_counter() - start
    old_width = rgba_array.shape[1]
    old_height = rgba_array.shape[0]
    new_width, new_height = output_image.size

    print(
        f"    {old_width}x{old_height} -> {new_width}x{new_height}\n"
        f"    Saved: {output_path}\n"
        f"    Time: {elapsed:.1f} seconds"
    )
import os

def makeoutputpath(input_path,output_dir):
    output_name = (
            f"{input_path.stem}_RealESRGAN_x{OUTPUT_SCALE}.png"
        )
    
      
    extension = ".png" if input_path.suffix.lower() == ".png" else ".jpg"
    output_name = (
            f"{input_path.stem}_RealESRGAN_x{OUTPUT_SCALE}{extension}"
        )

   
    output_path = output_dir / output_name
    return output_path

def main() -> None:
    print("Direct Real-ESRGAN for Pydroid 3")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Torch: {torch.__version__}")

    torch.set_num_threads(max(1, int(CPU_THREADS)))

    # Reduces unnecessary gradient and JIT overhead.
    torch.set_grad_enabled(False)

    script_dir = Path(__file__).resolve().parent
    model_path = script_dir / "realesrgan_models" / MODEL_FILENAME

    download_file(MODEL_URL, model_path)

    print("Loading RealESRGAN_x4plus_anime_6B...")
    model = load_model(model_path)

    inputs = collect_inputs()
    output_dir = Path(OUTPUT_FOLDER)

    print(f"Images: {len(inputs)}")
    print(f"Tile size: {TILE_SIZE}")
    print(f"Output scale: {OUTPUT_SCALE}x\n")

    failures = 0

    for index, input_path in enumerate(inputs, start=1):
        print(f"[{index}/{len(inputs)}] {input_path.name}")
        out = makeoutputpath(input_path, output_dir)
        print(out)
        try:
            if os.path.exists(str(out)):
                print("Skipping already upscaled image.")
                continue
            process_image(model, input_path, output_dir)
        except Exception as error:
            failures += 1
            print(f"    FAILED: {error}")

        gc.collect()

    print(
        f"\nFinished: {len(inputs) - failures} succeeded, "
        f"{failures} failed."
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as error:
        print(f"\nERROR: {type(error).__name__}: {error}")
        sys.exit(1)
