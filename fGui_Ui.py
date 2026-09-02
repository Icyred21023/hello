from __future__ import annotations

import os

import tkinter as tk

from typing import ClassVar, Literal, Union

from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageOps,
    ImageTk,
)

import config

# Replace these module names with the files where each helper is defined.
from fGui_ImgHelpers_beta import (
    ASSET_CACHE,
    cached_photoimage,
    clear_cached_photoimages,
    image_loader,
)
import os
import random
import tkinter as tk
from typing import Literal, Union
def split_edges(total: int, parts: int) -> "list[int]":
        base = total // parts
        rem = total % parts
        edges = [0]
        acc = 0
        for i in range(parts):
            acc += base + (1 if i < rem else 0)
            edges.append(acc)
        return edges
def s(v):
    if isinstance(v, (tuple, list)):
        return tuple(int(x * 1) for x in v)
    return int(v * 1)
class HeroImager:
    """Splice a cached sprite sheet and animate it on an existing canvas.

    ``master`` may be either a ``tk.Canvas`` or a ``SuperFrame``. Coordinates
    are canvas coordinates for a Canvas and local coordinates for a SuperFrame.

    Sheets are read left-to-right, then top-to-bottom. The fixed 966x1840,
    6x10 layout produces 60 frames of 161x184 pixels each.
    """

    SHEET_WIDTH: ClassVar[int] = 966
    SHEET_HEIGHT: ClassVar[int] = 1840
    COLUMNS: ClassVar[int] = 6
    ROWS: ClassVar[int] = 10
    FRAME_WIDTH: ClassVar[int] = SHEET_WIDTH // COLUMNS
    FRAME_HEIGHT: ClassVar[int] = SHEET_HEIGHT // ROWS
    FRAME_COUNT: ClassVar[int] = COLUMNS * ROWS

    # image_loader already caches the full raw sheet. This second cache avoids
    # repeating the crop/resize work when the same animation is placed twice.
    _pil_frame_cache: ClassVar[
        dict[tuple[str, tuple[int, int], int], tuple[Image.Image, ...]]
    ] = {}

    @staticmethod
    def _normalize_image_key(image_key: str) -> str:
        """Match ImageCache.normalize_key from fGui_ImgHelpers_beta."""
        return ASSET_CACHE.normalize_key(image_key)

    def __init__(
        self,
        master: Union[tk.Canvas, "SuperFrame"],
        image_key: str,
        *,
        x: float = 0,
        y: float = 0,
        anchor: str = "nw",
        bAnimated: bool = False,
        size: tuple[int, int] | None = None,
        scale: float = 1.0,
        fps: float = 34.0,
        loop: bool = True,
        autoplay: bool = True,
        start_frame: int = 0,
        tags: str | tuple[str, ...] | list[str] | None = None,
        canvas_args: dict | None = None,
    ) -> None:
        if not isinstance(image_key, str) or not image_key.strip():
            raise ValueError("image_key must be a non-empty string.")

        if isinstance(master, tk.Canvas):
            self.canvas = master
            self.super_frame = None
            self._origin_x = 0.0
            self._origin_y = 0.0
        elif hasattr(master, "Canvas") and hasattr(master, "bbox"):
            self.canvas = master.Canvas
            self.super_frame = master
            self._origin_x = float(master.bbox[0])
            self._origin_y = float(master.bbox[1])
        else:
            raise TypeError("master must be a tk.Canvas or SuperFrame.")

        if fps <= 0:
            raise ValueError("fps must be greater than zero.")
        if scale <= 0:
            raise ValueError("scale must be greater than zero.")

        self.master = master
        self.image_key = image_key
        self.x = float(x)
        self.y = float(y)
        self.anchor = anchor
        self.loop = bool(loop)
        self.fps = float(fps)
        self.delay_ms = max(1, round(1000 / self.fps))
        self.running = False
        self._after_id: str | None = None
        self._destroyed = False
        self.bStatic = not bAnimated

        if not bAnimated:
            self.super_frame.createSuperFrameImage(
                img_key=image_key,x=x, y=y, anc="nw")
            return

        output_size = self._get_output_size(size, scale)
        self._pil_frames = self._get_pil_frames(image_key, output_size)
        resampling = getattr(Image, "Resampling", Image)
        frame_variant_base = (
            "hero-animation-frame",
            output_size,
            int(resampling.LANCZOS),
            self.COLUMNS,
            self.ROWS,
        )
        self.frames = [
            cached_photoimage(
                image_key,
                frame_variant_base + (frame_index,),
                frame,
                self.canvas,
            )
            for frame_index, frame in enumerate(self._pil_frames)
        ]

        self.index = int(start_frame) % len(self.frames)
        create_args = {} if canvas_args is None else dict(canvas_args)
        create_args.pop("image", None)
        create_args.pop("anchor", None)
        create_args.pop("tags", None)

        self.image_id = self.canvas.create_image(
            self._origin_x + self.x - 4,
            self._origin_y + self.y,
            image=self.frames[self.index],
            anchor=self.anchor,
            tags=tags or (),
            **create_args,
        )
        self._store_canvas_references()

        if autoplay:
            self.play()

    @classmethod
    def clear_frame_cache(cls, image_key: str | None = None) -> None:
        """Clear cropped PIL frames without touching the main image cache."""
        if image_key is None:
            cls._pil_frame_cache.clear()
        else:
            normalized = cls._normalize_image_key(image_key)
            for key in tuple(cls._pil_frame_cache):
                if key[0] == normalized:
                    del cls._pil_frame_cache[key]

        clear_cached_photoimages(
            img_key=image_key,
            variant_namespace="hero-animation-frame",
        )

    @classmethod
    def _get_output_size(
        cls,
        size: tuple[int, int] | None,
        scale: float,
    ) -> tuple[int, int]:
        if size is not None:
            if len(size) != 2:
                raise ValueError("size must contain exactly two values.")
            return max(1, int(size[0])), max(1, int(size[1]))

        return (
            max(1, round(cls.FRAME_WIDTH * scale)),
            max(1, round(cls.FRAME_HEIGHT * scale)),
        )

    @classmethod
    def _get_pil_frames(
        cls,
        image_key: str,
        output_size: tuple[int, int],
    ) -> tuple[Image.Image, ...]:
        resampling = getattr(Image, "Resampling", Image)
        resample = resampling.LANCZOS
        cache_key = (cls._normalize_image_key(image_key), output_size, int(resample))

        cached = cls._pil_frame_cache.get(cache_key)
        if cached is not None:
            return cached

        # Placeholder requested by the caller: image_key is passed directly to
        # the project's cached loader. Change only this line if sheet lookup
        # later needs a prefix, suffix, or asset category.
        sheet = image_loader(image_key)

        if not isinstance(sheet, Image.Image):
            raise FileNotFoundError(
                f"image_loader could not load sprite sheet {image_key!r}."
            )

        expected = (cls.SHEET_WIDTH, cls.SHEET_HEIGHT)
        if sheet.size != expected:
            raise ValueError(
                f"Sprite sheet {image_key!r} is {sheet.size[0]}x{sheet.size[1]}; "
                f"expected {expected[0]}x{expected[1]}."
            )

        frames: list[Image.Image] = []
        for row in range(cls.ROWS):
            top = row * cls.FRAME_HEIGHT
            for column in range(cls.COLUMNS):
                left = column * cls.FRAME_WIDTH
                frame = sheet.crop(
                    (
                        left,
                        top,
                        left + cls.FRAME_WIDTH,
                        top + cls.FRAME_HEIGHT,
                    )
                )
                if frame.size != output_size:
                    frame = frame.resize(output_size, resample)
                frames.append(frame)

        result = tuple(frames)
        cls._pil_frame_cache[cache_key] = result
        return result

    def _store_canvas_references(self) -> None:
        """Follow SuperFrame's canvas reference convention for Tk/PIL images."""
        if not hasattr(self.canvas, "_images"):
            self.canvas._images = {}
        if not hasattr(self.canvas, "_pil_images"):
            self.canvas._pil_images = {}

        self.canvas._images[self.image_id] = self.frames[self.index]
        self.canvas._pil_images[self.image_id] = self._pil_frames[self.index]

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def current_frame(self) -> int:
        return self.index

    def show_frame(self, index: int) -> None:
        if self._destroyed:
            return

        if not 0 <= int(index) < self.frame_count:
            raise IndexError(
                f"frame index must be between 0 and {self.frame_count - 1}."
            )

        self.index = int(index)
        self.canvas.itemconfigure(
            self.image_id,
            image=self.frames[self.index],
        )
        self._store_canvas_references()

    def play(self) -> None:
        if self._destroyed or self.running:
            return

        self.running = True
        self._schedule_next_frame()

    def pause(self) -> None:
        self.running = False
        self._cancel_scheduled_frame()

    def stop(self) -> None:
        self.pause()
        if not self._destroyed:
            self.show_frame(0)

    def set_fps(self, fps: float) -> None:
        if fps <= 0:
            raise ValueError("fps must be greater than zero.")

        self.fps = float(fps)
        self.delay_ms = max(1, round(1000 / self.fps))
        if self.running:
            self._cancel_scheduled_frame()
            self._schedule_next_frame()

    def move_to(self, x: float, y: float) -> None:
        """Move using coordinates local to the original master."""
        self.x = float(x)
        self.y = float(y)
        if not self._destroyed:
            self.canvas.coords(
                self.image_id,
                self._origin_x + self.x,
                self._origin_y + self.y,
            )

    def _schedule_next_frame(self) -> None:
        if self.running and self._after_id is None:
            self._after_id = self.canvas.after(self.delay_ms, self._tick)

    def _cancel_scheduled_frame(self) -> None:
        if self._after_id is None:
            return

        try:
            self.canvas.after_cancel(self._after_id)
        except tk.TclError:
            pass
        finally:
            self._after_id = None

    def _tick(self) -> None:
        self._after_id = None
        if not self.running or self._destroyed:
            return

        next_index = self.index + 1
        if next_index >= self.frame_count:
            if not self.loop:
                self.running = False
                return
            next_index = 0

        try:
            self.show_frame(next_index)
        except tk.TclError:
            self.running = False
            self._destroyed = True
            return

        self._schedule_next_frame()

    def destroy(self) -> None:
        """Stop callbacks, delete the canvas item, and release Tk references."""
        if self._destroyed:
            return

        self.pause()
        try:
            self.canvas.delete(self.image_id)
        except tk.TclError:
            pass

        if hasattr(self.canvas, "_images"):
            self.canvas._images.pop(self.image_id, None)
        if hasattr(self.canvas, "_pil_images"):
            self.canvas._pil_images.pop(self.image_id, None)

        self.frames.clear()
        self._pil_frames = ()
        self._destroyed = True

class SuperFrame:
    def __init__(
            self, 
            master: Union[tk.Canvas, "SuperFrame", None] = None,
            bd: float | str  = 0,
            bg: str | None = None,
            border: float | str  = 0,
            borderwidth: float | str  = 0,
            height: int  = 0,
            width: int = 0,
            relief: Literal["raised", "sunken", "flat", "ridge", "solid", "groove"] = "flat"
            ):
        self.bOuter = False
        self.YList = []
        if isinstance(master, tk.Canvas):
            print("master is a tk.Canvas")
            self.Canvas: tk.Canvas = master
            self.Master = master
            self.Outer = self
            self.MasterWidth = master.winfo_reqwidth()
            self.MasterHeight = master.winfo_reqheight()
            
            
            

        elif isinstance(master, SuperFrame):
            print("master is a SuperFrame")
            self.Canvas: tk.Canvas = master.Canvas
            self.Master: Union[tk.Canvas, "SuperFrame"] = master
            self.MasterWidth = master.winfo_reqwidth()
            self.MasterHeight = master.winfo_reqheight()
            self.Outer = master.Outer
            self.bOuter = True

        elif master is None:
            print("no master")

        else:
            raise TypeError(
                "master must be tk.Canvas, SuperFrame, or None"
            )
        self.height = height
        self.width = width
        self.bg = bg
        self.bd = bd
        self.border = border
        self.borderwidth = borderwidth
        self.relief = relief
        self.bbox = (5,5)
    def pack(
            self,
            fill: None | Literal["x", "y", "both"] = None,
            expand: bool = False,
            padx: int = 0,
            pady: int = 0,
            side: Literal["left", "right", "top", "bottom"] = "top",
            ):
        free = 0
        if self.bOuter and len(self.Outer.YList) > 0 and self.Outer.bbox != (5,5):
            free = self.Outer.bbox[1]

            for coord in self.Outer.YList:
                if coord >=free:
                    free = coord
            free += 1
        if fill == "both":
            w = self.MasterWidth
            h = self.MasterHeight
        elif fill == "x":
            h = self.height
            w = self.MasterWidth
        elif fill == "y":
            w = self.width
            h = self.MasterHeight
        else:
            w = self.width
            h = self.height

        x1,y1,x2,y2 = (0,0,0,0)
        if self.bOuter:
            x1,y1,x2,y2 = self.Outer.bbox

        # w = w-padx
        # h = h-pady
        if free != 0:
            free -= y1
        self.bbox = (0+padx+x1, 0+pady+y1+free, w-padx+x1, h-pady+y1+free)
        self.width = self.bbox[2] - self.bbox[0]
        self.height = self.bbox[3] - self.bbox[1]
        #self.bbox = self.get_global_bbox(localb=self.bbox, parent=self.Master.bbox if not self.bOuter else (0,0,self.MasterWidth,self.MasterHeight))
        if self.bOuter:
            self.Outer.YList.append(self.bbox[3])
        if self.bg:
            self.Canvas.create_rectangle(
                self.bbox,
                fill=self.bg,
                outline="",
                tags=(f"{id(self)}_bg",)
            )

    def place(
            self,
            x: int  = 0,
            y: int  = 0,
            relx: float | None = None,
            rely: float | None = None,
            anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"] = "nw",
            relwidth: float | None = None,
            relheight: float | None = None,
            ):
        self.bbox = (x, y, x + self.width, y + self.height)
        self.width = self.bbox[2] - self.bbox[0]
        self.height = self.bbox[3] - self.bbox[1]
        #self.bbox = self.get_global_bbox(localb=self.bbox, parent=(0,0,self.MasterWidth,self.MasterHeight))
        print(self.bbox)

    def draw_frame(self):
        canvas = self.Canvas
        x1, y1, x2, y2 = self.bbox
        y2r = y2
        x2 -=1 
        
        
        light = "#8283A8"
        dark = "#403E5C"
        darkInside = "#050717",
        darkInside2 = "#0C0F22"

        #top_left = light if raised else dark
        #bottom_right = dark if raised else light
        return
        for i in range (0,self.relief_width):

            self.bg_items.append(
                self.canvas.create_line(
                    x1, y1, x2, y1,
                    fill=top_left,
                    width=1,
                    tags=(f"{key}_relief", "region_bg")
                )
            )


            self.bg_items.append(
                self.canvas.create_line(
                    x1, y1, x1, y2,
                    fill=top_left,
                    width=1,
                    tags=(f"{key}_relief", "region_bg")
                )
            )

            self.bg_items.append(
                self.canvas.create_line(
                    x1, y2, x2, y2,
                    fill=bottom_right,
                    width=1,
                    tags=(f"{key}_relief", "region_bg")
                )
            )

            self.bg_items.append(
                self.canvas.create_line(
                    x2, y1, x2, y2r,
                    fill=bottom_right,
                    width=1,
                    tags=(f"{key}_relief", "region_bg")
                )
            )
            x1 += 1
            y1 += 1
            x2 -= 1
            y2 -= 1
            bFlag = True if self.relief_width == 2 or i >= 1 else False
            print(f"i={i}, relief_width={self.relief_width}, bFlag={bFlag}")
            if bFlag:

                light = "#555555"
                dark = "#838383"
                top_left = light if raised else dark
                bottom_right = dark if raised else light
        self.fx.append(f"{key}_relief")

        
    def winfo_reqwidth(self):
        return self.width

    def winfo_reqheight(self):
        return self.height

    def get_global_bbox(self, localb, parent):
        lx1, ly1, lx2, ly2 = localb
        px1, py1, _, _ = parent

        return (
            lx1 + px1,
            ly1 + py1,
            lx2 + px1,
            ly2 + py1,
        )
    def _s2(self, xy):
        """Your existing s(...) scaler expects tuples sometimes."""
        return xy
    def createSuperFrameImage(
        self,
        img_key: str,
        anc="nw",
        size=None,
        bg=None,
        clip=False,
        tint_alpha=False,
        mask_glow = False,
        factor=0.5,
        tags = False,
        arh=None,
        x=0,
        y=0,
        mask=False,
        recolor=False,
    ):
        """
        
        Your original createCanvasImage converted to a method.
        Keeps the "canvas holds references" behavior.
        """
        canvas = self.Canvas
        
        def recolor_white(img, hex_color):
            """
            Replace white pixels with given hex color.
            Keeps transparency.
            """
            img = img.convert("RGBA")

            # Convert hex → RGB tuple
            hex_color = hex_color.lstrip("#")
            target = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            pixels = img.load()

            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]

                    # Only affect near-white pixels (tolerance helps antialiasing)
                    if r > 240 and g > 240 and b > 240 and a > 0:
                        pixels[x, y] = (*target, a)

            return img
        def apply_black_crops_mask(img, mask, flip=False, resize_mask=False):
            """
            img: already-loaded PIL image
            mask_path: path to black/white mask image
            black = erase, white = keep
            """
            img = img.convert("RGBA")
            mask = image_loader(mask)
            mask = mask.convert("RGBA")



            if resize_mask and mask.size != img.size:
                mask = mask.resize(img.size, Image.BICUBIC)
            if flip:
                mask = mask.transpose(Image.FLIP_LEFT_RIGHT)

            src_alpha = img.getchannel("A")

            # Mask channels
            r, g, b, a = mask.split()

            # Convert RGB to grayscale brightness
            gray = ImageOps.grayscale(mask)   # black=0, white=255

            # We want black areas to erase, so invert brightness:
            # black -> 255 erase strength
            # white -> 0 erase strength
            black_strength = ImageOps.invert(gray)

            # Transparent parts of mask should do nothing,
            # so multiply erase strength by mask alpha
            erase_strength = ImageChops.multiply(black_strength, a)

            # Invert erase strength to make a "keep" mask
            keep_mask = ImageOps.invert(erase_strength)

            # Apply to source alpha
            new_alpha = ImageChops.multiply(src_alpha, keep_mask)

            out = img.copy()
            out.putalpha(new_alpha)
            return out
        def adjust_alpha(img_rgba, factor=1.0):
            img_rgba = img_rgba.convert("RGBA")
            r, g, b, a = img_rgba.split()

            # scale alpha
            a = a.point(lambda px: int(px * factor))

            img_rgba.putalpha(a)
            return img_rgba
        def clip_to_region(img: "Image",x=int,y=int,anc="nw"):
                       
            

            frame_x1, frame_y1, frame_x2, frame_y2 = self.bbox

            # Convert local frame coords into global canvas coords
            gx = frame_x1 + x
            gy = frame_y1 + y

            img = img.convert("RGBA")
            img_w, img_h = img.size

            def anchor_to_top_left(x, y, w, h, anc="nw"):
                if anc == "nw":
                    return x, y
                if anc == "n":
                    return x - w / 2, y
                if anc == "ne":
                    return x - w, y
                if anc == "w":
                    return x, y - h / 2
                if anc in ("center", "c"):
                    return x - w / 2, y - h / 2
                if anc == "e":
                    return x - w, y - h / 2
                if anc == "sw":
                    return x, y - h
                if anc == "s":
                    return x - w / 2, y - h
                if anc == "se":
                    return x - w, y - h
                raise ValueError(f"Invalid anchor: {anc}")

            # Image top-left in GLOBAL canvas coords
            ix, iy = anchor_to_top_left(gx, gy, img_w, img_h, anc)

            # Convert frame bbox from GLOBAL coords into IMAGE-LOCAL coords
            clip_x1 = frame_x1 - ix
            clip_y1 = frame_y1 - iy
            clip_x2 = frame_x2 - ix
            clip_y2 = frame_y2 - iy

            # Clamp to actual image bounds
            clip_x1 = max(0, min(img_w, clip_x1))
            clip_y1 = max(0, min(img_h, clip_y1))
            clip_x2 = max(0, min(img_w, clip_x2))
            clip_y2 = max(0, min(img_h, clip_y2))

            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)

            draw.rectangle(
                (
                    int(clip_x1),
                    int(clip_y1),
                    int(clip_x2) - 1,
                    int(clip_y2) - 1,
                ),
                fill=255,
            )

            result = Image.new("RGBA", img.size, (0, 0, 0, 0))
            result.paste(img, (0, 0), mask)

            return result

        if arh is None:
            arh = {}

        scaled_size = None
        if size:
            scaled = self._s2(size)
            scaled_size = (int(scaled[0]), int(scaled[1]))

        if isinstance(mask_glow, tuple):
            glow_cache_key = (
                str(mask_glow[0]),
                bool(mask_glow[1]),
            )
        else:
            glow_cache_key = (bool(mask_glow), False)

        clip_cache_key = None
        if clip:
            clip_cache_key = (
                tuple(float(value) for value in self.bbox),
                float(x),
                float(y),
                str(anc),
            )

        photo_variant_key = (
            "superframe-image",
            scaled_size,
            str(recolor) if recolor else False,
            bool(tint_alpha),
            round(float(factor), 5),
            str(mask) if mask else False,
            glow_cache_key,
            clip_cache_key,
        )
        

        img_raw = image_loader(img_key)


        if not img_raw:
            return False

        
        if recolor:
            img_raw = recolor_white(img_raw, recolor)

        if tint_alpha:
            img_raw = adjust_alpha(img_raw, factor=factor)  # light gray/white
        if mask:
            img_raw = img_raw.convert("RGBA")
            #img_raw = make_circle(img_raw)

        if scaled_size:
            img_raw = img_raw.resize(scaled_size, Image.BICUBIC)
        if mask_glow:
            if isinstance(mask_glow, tuple):
                bMask, bFlip = mask_glow
            else:
                bMask = mask_glow
                bFlip = False
            img_raw = apply_black_crops_mask(img_raw, "_GlowMask", flip=bFlip, resize_mask=True)

        if clip:
            img_raw = clip_to_region(img_raw, x,y,anc)
        img = cached_photoimage(
            img_key,
            photo_variant_key,
            img_raw,
            canvas,
        )



        # if bg is not None:
        #     canvas.configure(bg=bg)

        x += self.bbox[0]
        y += self.bbox[1]
        if tags:
            item = canvas.create_image(s(x), s(y), anchor=anc, image=img, tags=tags, **arh)
        else:
            item = canvas.create_image(s(x), s(y), anchor=anc, image=img, **arh)

        # store tkinter image refs
        if not hasattr(canvas, "_images"):
            canvas._images = {}

        canvas._images[item] = img

        # store editable PIL image
        if not hasattr(canvas, "_pil_images"):
            canvas._pil_images = {}

        canvas._pil_images[item] = img_raw   # <--- THIS IS THE IMPORTANT ONE
        

        return item

    def createSuperFrameText(
        self,
        text: str,
        fill: str,
        font= None,
        anchor = "nw",
        x=0,
        y=0
    ):
        canvas = self.Canvas
        def anchor_to_top_left(x, y, w, h, anc="nw"):
                if anc == "nw":
                    return x, y
                if anc == "n":
                    return x - w / 2, y
                if anc == "ne":
                    return x - w, y
                if anc == "w":
                    return x, y - h / 2
                if anc in ("center", "c"):
                    return x - w / 2, y - h / 2
                if anc == "e":
                    return x - w, y - h / 2
                if anc == "sw":
                    return x, y - h
                if anc == "s":
                    return x - w / 2, y - h
                if anc == "se":
                    return x - w, y - h

                raise ValueError(f"Invalid anchor: {anc}")  

        def measure_text(canvas, text, font_spec):
            from tkinter import font
            f = font.Font(root=canvas, font=font_spec)

            w = f.measure(text)
            h = f.metrics("linespace")

            return w, h
        
        #w,h = measure_text(canvas,text, font)
        
        box = self.bbox
        #ix, iy = anchor_to_top_left(x,y,w,h,anchor)
        x += self.bbox[0]
        y += self.bbox[1]
        x1,y1,x2,y2 = box

        txt = canvas.create_text(
            x,
            y,
            text=text,
            fill=fill,
            font=font,
            anchor=anchor,
        )
        # self._create_supercanvas_text(
        #     canvas,
        #     text=self.player.name,
        #     fill="white",
        #     font=fonttk(refrig_heavy,23,"bold"),
        #     anchor="sw",
        #     x= s(6),
        #     y= s(44)
        #     )
        return txt
    
    
