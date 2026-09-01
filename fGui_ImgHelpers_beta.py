from __future__ import annotations

import os
from typing import Any, Hashable

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageTk

import helpers

import config
# =============================================================================
# ASSET PATHS
# =============================================================================

ASSETS_ROOTDIR = os.path.join(config.script_dir, "fGui Assets") # helpers.create_path("", "fGui Assets")
ASSETS_HEROES = os.path.join(ASSETS_ROOTDIR, "Heroes")
ASSETS_UI = os.path.join(ASSETS_ROOTDIR, "UI")
ASSETS_NAMEPLATES = os.path.join(ASSETS_ROOTDIR, "Nameplates")
ASSETS_MOOD = os.path.join(ASSETS_ROOTDIR, "Mood")

ASSETS_IDX: dict[str, str] = {
    "hero": ASSETS_HEROES,
    "heroes": ASSETS_HEROES,
    "ui": ASSETS_UI,
    "nameplate": ASSETS_NAMEPLATES,
    "nameplates": ASSETS_NAMEPLATES,
    "mood": ASSETS_MOOD,
    "moods": ASSETS_MOOD,
}


# =============================================================================
# IMAGE CACHE
# =============================================================================

class ImageCache:
    """
    Cache structure:

        Cache[img_key]["raw"] = first raw SuperImage
        Cache[img_key][variant_key] = first processed SuperImage

    Only the first SuperImage for a particular variant is stored.
    Later SuperImage instances borrow img_raw and img_tk from it.
    """

    def __init__(self) -> None:
        self.Cache: dict[str, dict[Hashable, SuperImage]] = {}

    @staticmethod
    def normalize_key(img_key: str) -> str:
        filename = os.path.basename(str(img_key))
        stem, _extension = os.path.splitext(filename)
        return stem.casefold()

    def get(
        self,
        img_key: str,
        variant_key: Hashable = "raw",
    ) -> SuperImage | None:
        key = self.normalize_key(img_key)
        return self.Cache.get(key, {}).get(variant_key)

    def store(
        self,
        super_image: SuperImage,
        variant_key: Hashable,
    ) -> SuperImage:
        """
        Keep the first SuperImage stored for this variant.

        Returns the canonical cached SuperImage.
        """
        key = self.normalize_key(super_image.img_key)
        variants = self.Cache.setdefault(key, {})

        return variants.setdefault(
            variant_key,
            super_image,
        )

    def get_raw(
        self,
        img_key: str,
    ) -> SuperImage | None:
        return self.get(img_key, "raw")

    def get_search_directories(
        self,
        idx: str | None = None,
    ) -> list[tuple[str, str]]:
        if idx is not None:
            normalized_idx = str(idx).strip().casefold()

            directory = ASSETS_IDX.get(normalized_idx)

            if directory is not None:
                return [(normalized_idx, directory)]

        return [
            ("ui", ASSETS_UI),
            ("heroes", ASSETS_HEROES),
            ("nameplates", ASSETS_NAMEPLATES),
            ("moods", ASSETS_MOOD),
        ]

    def find_path(
        self,
        img_key: str,
        idx: str | None = None,
    ) -> tuple[str, str] | None:
        filename = os.path.basename(str(img_key))

        if not os.path.splitext(filename)[1]:
            filename = f"{filename}.png"

        for category, directory in self.get_search_directories(idx):
            path = os.path.join(directory, filename)

            if os.path.isfile(path):
                return path, category

        return None

    def remove_image(
        self,
        img_key: str,
    ) -> bool:
        key = self.normalize_key(img_key)
        return self.Cache.pop(key, None) is not None

    def clear(self) -> None:
        self.Cache.clear()

    def describe(self) -> dict[str, list[Hashable]]:
        return {
            key: list(variants.keys())
            for key, variants in self.Cache.items()
        }


ASSET_CACHE = ImageCache()


# =============================================================================
# SUPER IMAGE
# =============================================================================

class SuperImage:
    """
    Represents one image placement.

    Every placement creates a new SuperImage object.

    The first SuperImage created for each unique image variant becomes the
    cache source. Later objects borrow only image data from it while keeping
    independent placement information.
    """

    def __init__(
        self,
        img_key: str,
        *,
        SuperClass: Any,
        anc: str = "nw",
        size: tuple[int, int] | list[int] | None = None,
        bg: str | None = None,
        clip: bool = False,
        tint_alpha: bool = False,
        mask_glow: str | tuple[str, bool] | bool = False,
        factor: float = 0.5,
        tags: str | tuple[str, ...] | list[str] | bool | None = False,
        arh: dict[str, Any] | None = None,
        x: float = 0,
        y: float = 0,
        mask: bool | str = False,
        recolor: str | bool = False,
        idx: str | None = None,
        cache_result: bool = True,
        draw: bool = True,
    ) -> None:
        self.img_key = img_key
        self.idx = idx

        self.SuperFrame = SuperClass
        self.canvas = getattr(
            SuperClass,
            "Canvas",
            getattr(SuperClass, "canvas", None),
        )

        if self.canvas is None:
            raise AttributeError(
                "SuperClass must have a Canvas or canvas attribute."
            )

        self.anchor = anc
        self.size = self._normalize_size(size)
        self.background = bg

        self.clip = bool(clip)
        self.tint_alpha = bool(tint_alpha)
        self.mask_glow = mask_glow
        self.alpha_factor = float(factor)
        self.mask = mask
        self.recolor = recolor

        self.tags = tags
        self.canvas_args = {} if arh is None else dict(arh)

        self.requested_x = float(x)
        self.requested_y = float(y)

        self.actual_x: float | None = None
        self.actual_y: float | None = None

        self.original_size: tuple[int, int] | None = None
        self.final_size: tuple[int, int] | None = None

        self.source_path: str | None = None
        self.category: str | None = None

        self.img_raw: Image.Image | None = None
        self.img_tk: ImageTk.PhotoImage | None = None

        self.img_source: SuperImage | None = None

        self.is_cache_source = False
        self.loaded_from_cache = False

        self.canvas_item: int | None = None

        self.cache_result = bool(cache_result)

        self.variant_key = self.create_variant_key()

        if self.prepare_image() and draw:
            self.draw()

    # -------------------------------------------------------------------------
    # BASIC HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_size(
        size: tuple[int, int] | list[int] | None,
    ) -> tuple[int, int] | None:
        if size is None:
            return None

        if len(size) != 2:
            raise ValueError("size must contain exactly two values.")

        return (
            max(1, int(size[0])),
            max(1, int(size[1])),
        )

    def _scaled_size(self) -> tuple[int, int] | None:
        if self.size is None:
            return None

        scaler = getattr(self.SuperFrame, "_s2", None)

        if callable(scaler):
            scaled = scaler(self.size)

            return (
                max(1, int(scaled[0])),
                max(1, int(scaled[1])),
            )

        return self.size

    def _frame_bbox(self) -> tuple[float, float, float, float]:
        bbox = getattr(self.SuperFrame, "bbox", None)

        if bbox is None or len(bbox) != 4:
            raise AttributeError(
                "SuperClass must have bbox=(x1, y1, x2, y2)."
            )

        return (
            float(bbox[0]),
            float(bbox[1]),
            float(bbox[2]),
            float(bbox[3]),
        )

    def has_transformations(self) -> bool:
        return any(
            (
                self.size is not None,
                self.clip,
                self.tint_alpha,
                bool(self.mask_glow),
                bool(self.mask),
                bool(self.recolor),
            )
        )

    # -------------------------------------------------------------------------
    # CACHE KEY
    # -------------------------------------------------------------------------

    def create_variant_key(self) -> Hashable:
        """
        A variant key must represent every operation that changes pixels.

        Placement coordinates are included only for clipping because clipping
        depends on where the image is placed relative to the SuperFrame.
        """
        if not self.has_transformations():
            return "raw"

        if isinstance(self.mask_glow, tuple):
            glow_mask = self.mask_glow[0]
            glow_flip = bool(self.mask_glow[1])
        else:
            glow_mask = self.mask_glow
            glow_flip = False

        clip_data = None

        if self.clip:
            clip_data = (
                self._frame_bbox(),
                self.requested_x,
                self.requested_y,
                self.anchor,
            )

        return (
            "variant",
            self._scaled_size(),
            self.recolor,
            self.tint_alpha,
            round(self.alpha_factor, 5),
            self.mask,
            glow_mask,
            glow_flip,
            clip_data,
        )

    # -------------------------------------------------------------------------
    # LOAD AND CACHE PIPELINE
    # -------------------------------------------------------------------------

    def prepare_image(self) -> bool:
        """
        Processing order:

        1. Exact processed cache lookup.
        2. Raw cache lookup.
        3. Disk load if raw is absent.
        4. Copy raw source.
        5. Apply transformations.
        6. Create Tk PhotoImage.
        7. Cache first SuperImage for this variant.
        """
        cached_variant = ASSET_CACHE.get(
            self.img_key,
            self.variant_key,
        )

        if cached_variant is not None:
            self.pull_from_cache(cached_variant)
            return True

        raw_source = ASSET_CACHE.get_raw(self.img_key)

        if raw_source is None:
            raw_source = self.load_raw_source()

        if raw_source is None or raw_source.img_raw is None:
            return False

        self.source_path = raw_source.source_path
        self.category = raw_source.category
        self.original_size = raw_source.original_size

        if self.variant_key == "raw":
            self.img_raw = raw_source.img_raw
            self.img_source = raw_source

            if raw_source.img_tk is None:
                raw_source.img_tk = ImageTk.PhotoImage(
                    raw_source.img_raw,
                    master=self.canvas,
                )

            self.img_tk = raw_source.img_tk
            self.final_size = raw_source.img_raw.size

            canonical = ASSET_CACHE.store(self, "raw")

            if canonical is self:
                self.is_cache_source = True
            else:
                self.pull_from_cache(canonical)

            return True

        self.img_source = raw_source

        # Never modify the cached raw source.
        self.img_raw = raw_source.img_raw.copy()

        if not self.apply_transformations():
            return False

        if not self.create_tk_image():
            return False

        if self.cache_result:
            canonical = ASSET_CACHE.store(
                self,
                self.variant_key,
            )

            if canonical is self:
                self.is_cache_source = True
            else:
                self.pull_from_cache(canonical)

        return True

    def load_raw_source(self) -> SuperImage | None:
        """
        Load a source image and store it as a non-drawn raw SuperImage.
        """
        found = ASSET_CACHE.find_path(
            self.img_key,
            self.idx,
        )

        if found is None:
            found = ASSET_CACHE.find_path(
                "Default",
                self.idx,
            )

        if found is None:
            return None

        path, category = found

        try:
            with Image.open(path) as opened:
                raw = opened.convert("RGBA").copy()

        except (FileNotFoundError, OSError):
            return None

        source = SuperImage.__new__(SuperImage)

        source.img_key = self.img_key
        source.idx = self.idx

        source.SuperFrame = self.SuperFrame
        source.canvas = self.canvas

        source.anchor = "nw"
        source.size = None
        source.background = None

        source.clip = False
        source.tint_alpha = False
        source.mask_glow = False
        source.alpha_factor = 1.0
        source.mask = False
        source.recolor = False

        source.tags = False
        source.canvas_args = {}

        source.requested_x = 0.0
        source.requested_y = 0.0

        source.actual_x = None
        source.actual_y = None

        source.original_size = raw.size
        source.final_size = raw.size

        source.source_path = path
        source.category = category

        source.img_raw = raw
        source.img_tk = None

        source.img_source = None

        source.is_cache_source = True
        source.loaded_from_cache = False

        source.canvas_item = None

        source.cache_result = True
        source.variant_key = "raw"

        return ASSET_CACHE.store(
            source,
            "raw",
        )

    def pull_from_cache(
        self,
        cached: SuperImage,
    ) -> None:
        """
        Borrow only reusable image information.

        Placement data remains unique to this SuperImage.
        """
        self.img_source = cached

        self.img_raw = cached.img_raw
        self.img_tk = cached.img_tk

        self.source_path = cached.source_path
        self.category = cached.category

        self.original_size = cached.original_size
        self.final_size = cached.final_size

        self.loaded_from_cache = True

    # -------------------------------------------------------------------------
    # TRANSFORMATIONS
    # -------------------------------------------------------------------------

    def apply_transformations(self) -> bool:
        if self.img_raw is None:
            return False

        img = self.img_raw

        if self.recolor:
            img = self.recolor_white(
                img,
                str(self.recolor),
            )

        if self.tint_alpha:
            img = self.adjust_alpha(
                img,
                self.alpha_factor,
            )

        if self.mask:
            img = self.apply_shape_mask(
                img,
                self.mask,
            )

        scaled_size = self._scaled_size()

        if scaled_size is not None:
            img = img.resize(
                scaled_size,
                Image.Resampling.BICUBIC,
            )

        if self.mask_glow:
            if isinstance(self.mask_glow, tuple):
                mask_key = str(self.mask_glow[0])
                flip = bool(self.mask_glow[1])
            elif self.mask_glow is True:
                mask_key = "_GlowMask"
                flip = False
            else:
                mask_key = str(self.mask_glow)
                flip = False

            mask_source = ASSET_CACHE.get_raw(mask_key)

            if mask_source is None:
                mask_source = self.load_auxiliary_raw(mask_key)

            if mask_source is not None and mask_source.img_raw is not None:
                img = self.apply_black_crops_mask(
                    img,
                    mask_source.img_raw,
                    flip=flip,
                    resize_mask=True,
                )

        if self.clip:
            img = self.clip_to_frame(img)

        self.img_raw = img
        self.final_size = img.size

        return True

    def load_auxiliary_raw(
        self,
        img_key: str,
    ) -> SuperImage | None:
        found = ASSET_CACHE.find_path(img_key)

        if found is None:
            return None

        path, category = found

        try:
            with Image.open(path) as opened:
                raw = opened.convert("RGBA").copy()

        except (FileNotFoundError, OSError):
            return None

        source = SuperImage.__new__(SuperImage)

        source.img_key = img_key
        source.idx = None

        source.SuperFrame = self.SuperFrame
        source.canvas = self.canvas

        source.anchor = "nw"
        source.size = None
        source.background = None

        source.clip = False
        source.tint_alpha = False
        source.mask_glow = False
        source.alpha_factor = 1.0
        source.mask = False
        source.recolor = False

        source.tags = False
        source.canvas_args = {}

        source.requested_x = 0.0
        source.requested_y = 0.0

        source.actual_x = None
        source.actual_y = None

        source.original_size = raw.size
        source.final_size = raw.size

        source.source_path = path
        source.category = category

        source.img_raw = raw
        source.img_tk = None

        source.img_source = None

        source.is_cache_source = True
        source.loaded_from_cache = False

        source.canvas_item = None

        source.cache_result = True
        source.variant_key = "raw"

        return ASSET_CACHE.store(
            source,
            "raw",
        )

    # -------------------------------------------------------------------------
    # EFFECT METHODS
    # -------------------------------------------------------------------------

    @staticmethod
    def recolor_white(
        img: Image.Image,
        hex_color: str,
    ) -> Image.Image:
        img = img.convert("RGBA").copy()

        color = hex_color.lstrip("#")

        if len(color) != 6:
            raise ValueError(
                f"Invalid hex color: {hex_color!r}"
            )

        target = tuple(
            int(color[i:i + 2], 16)
            for i in (0, 2, 4)
        )

        pixels = img.load()

        for py in range(img.height):
            for px in range(img.width):
                r, g, b, a = pixels[px, py]

                if r > 240 and g > 240 and b > 240 and a > 0:
                    pixels[px, py] = (*target, a)

        return img

    @staticmethod
    def adjust_alpha(
        img: Image.Image,
        factor: float = 1.0,
    ) -> Image.Image:
        img = img.convert("RGBA").copy()

        factor = max(0.0, float(factor))

        alpha = img.getchannel("A")
        alpha = alpha.point(
            lambda value: min(
                255,
                max(0, round(value * factor)),
            )
        )

        img.putalpha(alpha)

        return img

    @staticmethod
    def apply_shape_mask(
        img: Image.Image,
        mask: bool | str,
    ) -> Image.Image:
        """
        mask=True or mask="circle" creates a circular alpha mask.

        Add more named shape masks here later if needed.
        """
        if mask not in (True, "circle"):
            return img

        img = img.convert("RGBA").copy()

        mask_img = Image.new(
            "L",
            img.size,
            0,
        )

        draw = ImageDraw.Draw(mask_img)

        draw.ellipse(
            (0, 0, img.width - 1, img.height - 1),
            fill=255,
        )

        original_alpha = img.getchannel("A")
        combined_alpha = ImageChops.multiply(
            original_alpha,
            mask_img,
        )

        img.putalpha(combined_alpha)

        return img

    @staticmethod
    def apply_black_crops_mask(
        img: Image.Image,
        mask_img: Image.Image,
        *,
        flip: bool = False,
        resize_mask: bool = False,
    ) -> Image.Image:
        """
        Black pixels erase.
        White pixels preserve.
        Transparent mask pixels do nothing.
        """
        img = img.convert("RGBA")
        mask_img = mask_img.convert("RGBA")

        if resize_mask and mask_img.size != img.size:
            mask_img = mask_img.resize(
                img.size,
                Image.Resampling.BICUBIC,
            )

        if flip:
            mask_img = mask_img.transpose(
                Image.Transpose.FLIP_LEFT_RIGHT,
            )

        source_alpha = img.getchannel("A")
        mask_alpha = mask_img.getchannel("A")

        gray = ImageOps.grayscale(mask_img)
        black_strength = ImageOps.invert(gray)

        erase_strength = ImageChops.multiply(
            black_strength,
            mask_alpha,
        )

        keep_mask = ImageOps.invert(erase_strength)

        new_alpha = ImageChops.multiply(
            source_alpha,
            keep_mask,
        )

        result = img.copy()
        result.putalpha(new_alpha)

        return result

    @staticmethod
    def anchor_to_top_left(
        x: float,
        y: float,
        width: int,
        height: int,
        anchor: str,
    ) -> tuple[float, float]:
        anchors = {
            "nw": (0.0, 0.0),
            "n": (0.5, 0.0),
            "ne": (1.0, 0.0),
            "w": (0.0, 0.5),
            "center": (0.5, 0.5),
            "c": (0.5, 0.5),
            "e": (1.0, 0.5),
            "sw": (0.0, 1.0),
            "s": (0.5, 1.0),
            "se": (1.0, 1.0),
        }

        if anchor not in anchors:
            raise ValueError(
                f"Invalid anchor: {anchor!r}"
            )

        horizontal, vertical = anchors[anchor]

        return (
            x - width * horizontal,
            y - height * vertical,
        )

    def clip_to_frame(
        self,
        img: Image.Image,
    ) -> Image.Image:
        frame_x1, frame_y1, frame_x2, frame_y2 = self._frame_bbox()

        global_x = frame_x1 + self.requested_x
        global_y = frame_y1 + self.requested_y

        img = img.convert("RGBA")

        img_width, img_height = img.size

        image_x, image_y = self.anchor_to_top_left(
            global_x,
            global_y,
            img_width,
            img_height,
            self.anchor,
        )

        clip_x1 = frame_x1 - image_x
        clip_y1 = frame_y1 - image_y
        clip_x2 = frame_x2 - image_x
        clip_y2 = frame_y2 - image_y

        clip_x1 = max(0, min(img_width, clip_x1))
        clip_y1 = max(0, min(img_height, clip_y1))
        clip_x2 = max(0, min(img_width, clip_x2))
        clip_y2 = max(0, min(img_height, clip_y2))

        clip_mask = Image.new(
            "L",
            img.size,
            0,
        )

        draw = ImageDraw.Draw(clip_mask)

        if clip_x2 > clip_x1 and clip_y2 > clip_y1:
            draw.rectangle(
                (
                    int(clip_x1),
                    int(clip_y1),
                    int(clip_x2) - 1,
                    int(clip_y2) - 1,
                ),
                fill=255,
            )

        result = Image.new(
            "RGBA",
            img.size,
            (0, 0, 0, 0),
        )

        result.paste(
            img,
            (0, 0),
            clip_mask,
        )

        return result

    # -------------------------------------------------------------------------
    # TK IMAGE AND DRAWING
    # -------------------------------------------------------------------------

    def create_tk_image(self) -> bool:
        if self.img_raw is None:
            return False

        self.img_tk = ImageTk.PhotoImage(
            self.img_raw,
            master=self.canvas,
        )

        return True

    def draw(self) -> int | bool:
        if self.img_tk is None:
            return False

        frame_x1, frame_y1, _frame_x2, _frame_y2 = self._frame_bbox()

        self.actual_x = frame_x1 + self.requested_x
        self.actual_y = frame_y1 + self.requested_y

        create_args = dict(self.canvas_args)

        if self.tags:
            create_args["tags"] = self.tags

        self.canvas_item = self.canvas.create_image(
            self.actual_x,
            self.actual_y,
            anchor=self.anchor,
            image=self.img_tk,
            **create_args,
        )

        self.store_canvas_references()

        return self.canvas_item

    def store_canvas_references(self) -> None:
        if self.canvas_item is None:
            return

        if not hasattr(self.canvas, "_images"):
            self.canvas._images = {}

        if not hasattr(self.canvas, "_pil_images"):
            self.canvas._pil_images = {}

        if not hasattr(self.canvas, "_super_images"):
            self.canvas._super_images = {}

        self.canvas._images[self.canvas_item] = self.img_tk
        self.canvas._pil_images[self.canvas_item] = self.img_raw
        self.canvas._super_images[self.canvas_item] = self

    # -------------------------------------------------------------------------
    # PLACEMENT CONTROL
    # -------------------------------------------------------------------------

    def move_to(
        self,
        x: float,
        y: float,
    ) -> bool:
        self.requested_x = float(x)
        self.requested_y = float(y)

        if self.canvas_item is None:
            return False

        frame_x1, frame_y1, _frame_x2, _frame_y2 = self._frame_bbox()

        self.actual_x = frame_x1 + self.requested_x
        self.actual_y = frame_y1 + self.requested_y

        self.canvas.coords(
            self.canvas_item,
            self.actual_x,
            self.actual_y,
        )

        return True

    def move_by(
        self,
        dx: float,
        dy: float,
    ) -> bool:
        if self.canvas_item is None:
            return False

        self.requested_x += float(dx)
        self.requested_y += float(dy)

        self.canvas.move(
            self.canvas_item,
            dx,
            dy,
        )

        coordinates = self.canvas.coords(
            self.canvas_item,
        )

        if len(coordinates) >= 2:
            self.actual_x = float(coordinates[0])
            self.actual_y = float(coordinates[1])

        return True

    def hide(self) -> None:
        if self.canvas_item is not None:
            self.canvas.itemconfigure(
                self.canvas_item,
                state="hidden",
            )

    def show(self) -> None:
        if self.canvas_item is not None:
            self.canvas.itemconfigure(
                self.canvas_item,
                state="normal",
            )

    def delete(self) -> None:
        if self.canvas_item is None:
            return

        item = self.canvas_item

        self.canvas.delete(item)

        if hasattr(self.canvas, "_images"):
            self.canvas._images.pop(item, None)

        if hasattr(self.canvas, "_pil_images"):
            self.canvas._pil_images.pop(item, None)

        if hasattr(self.canvas, "_super_images"):
            self.canvas._super_images.pop(item, None)

        self.canvas_item = None


# =============================================================================
# SUPERFRAME WRAPPER FUNCTION
# =============================================================================



# =============================================================================
# OPTIONAL LEGACY LOADER
# =============================================================================

def image_loader(
    img_key: str,
    img_type: str | None = None,
    idx: str | None = None,
):
    """
    Compatibility helper for older code.

    img_type:
        "raw"   -> Pillow image
        "tk"    -> Tk PhotoImage if already created
        "object" -> cached SuperImage
    """
    img_type = "raw" if img_type is None else img_type.casefold()

    source = ASSET_CACHE.get_raw(img_key)

    if source is None:
        found = ASSET_CACHE.find_path(
            img_key,
            idx,
        )

        if found is None:
            found = ASSET_CACHE.find_path(
                "Default",
                idx,
            )

        if found is None:
            return False

        path, category = found

        try:
            with Image.open(path) as opened:
                raw = opened.convert("RGBA").copy()

        except (FileNotFoundError, OSError):
            return False

        source = SuperImage.__new__(SuperImage)

        source.img_key = img_key
        source.idx = idx

        source.SuperFrame = None
        source.canvas = None

        source.anchor = "nw"
        source.size = None
        source.background = None

        source.clip = False
        source.tint_alpha = False
        source.mask_glow = False
        source.alpha_factor = 1.0
        source.mask = False
        source.recolor = False

        source.tags = False
        source.canvas_args = {}

        source.requested_x = 0.0
        source.requested_y = 0.0

        source.actual_x = None
        source.actual_y = None

        source.original_size = raw.size
        source.final_size = raw.size

        source.source_path = path
        source.category = category

        source.img_raw = raw
        source.img_tk = None

        source.img_source = None

        source.is_cache_source = True
        source.loaded_from_cache = False

        source.canvas_item = None

        source.cache_result = True
        source.variant_key = "raw"

        source = ASSET_CACHE.store(
            source,
            "raw",
        )

    if img_type == "raw":
        return source.img_raw

    if img_type == "tk":
        return source.img_tk

    if img_type in ("object", "superimage"):
        return source

    return False
