from __future__ import annotations

import os
import random
import tkinter as tk

from typing import Literal, Union

from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageOps,
    ImageTk,
)

import config

# Replace these module names with the files where each helper is defined.
from fGui_ImgHelpers_beta import image_loader
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
class SpriteSheetAnimator:
    def __init__(
        self,
        master,
        hero,
        animated=True,              # NEW
        sheet_path=None,            # for animated
        rows=10,##
        cols=6,
        fps=24,
        badge=False,
        frame=False,
        scale=1,
        bg="#77789E",
        relief="sunken",
        borderwidth=1,
        size=None,
        bSubCrop=False,
        frame_height = 90,
        static_icon=None,           # NEW: for non-animated
        bSpecialBG=False,           # keep if you use it
    ):
        """
        animated:
          True  -> uses sprite sheet animation
          False -> renders a single static icon into the same canvas

        static_icon:
          Whatever key/path your createOnlyImage/_create_only_image uses.
        """
        SHEETS_DIR = os.path.join(config.script_dir, "assets_match_hd")
        
        self.master = master
        self.hero = hero
        self.animated = animated
        self.badge = badge
        self.frame = frame
        self.fps = fps
        self.delay_ms = int(1000 / fps) if fps else 0
        self.scale = scale
        self.rows = rows
        self.cols = cols
        self.size = size
        self.bSubCrop = bSubCrop
        self.running = False
        frame_height = frame_height if frame_height else 90
        # --- your existing vars ---
        self.colors = ['blue', 'green', 'pink', 'purple', 'white']
        self.herobg = "heromasterybg_"
        self.scaling_frame = int(frame_height / 90)
        self.image_sizeX = frame_height - 2
        self.image_sizeY = frame_height - 2
        # If you have crop_cache logic, keep it (only matters for animated sheets)
        sheet_key = self.hero + "_Master.png"
        # if self.animated and sheet_key in crop_cache:
        #     prev = crop_cache[sheet_key]
        #     self.subcrop_x = int(prev["x0"])
        #     self.subcrop_y = int(prev["y0"])
        #     self.subcrop_w = int(prev["side"])
        #     self.subcrop_h = int(prev["side"])
        #     self.bSubCrop = True
        #     self.size = (s(frame_height), s(frame_height))

        # --- wrapper + canvas (same for both) ---
        icon_wrap = tk.Frame(master, width=s(frame_height), height=s(frame_height), bg=bg,padx=0, pady=0)
        icon_wrap.pack(side="bottom",anchor="sw",pady=(0,0),padx=(0,0))
        icon_wrap.pack_propagate(False)

        self.canvas = tk.Canvas(
            icon_wrap,
            width=s(frame_height-3),
            height=s((frame_height-3)),
            bg=bg,
            highlightthickness=0,
            bd=borderwidth,
            relief=relief
        )
        self.canvas.pack(fill="both",side ="bottom",anchor="sw", expand=False,padx=0, pady=0)
        self.canvas.pack_propagate(False)

        # center + offsets
        dx, dy = (0,0)
        cx, cy = s(frame_height // 2), s(frame_height // 2)
        self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite")  # keep reference!
        self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")

        # optional special BG
        self.hero_bg_colored = None
        self.hero_bg_id = None
        if bSpecialBG:
            import random
            random_color = random.choice(self.colors)
            bg_name = self.herobg + random_color
            #self.hero_bg_colored = self.createOnlyImage(bg_name, size=(233, 104))

            self.hero_bg_id = self.canvas.create_image(s(frame_height // 2), s(frame_height // 2), image=self.hero_bg_colored, anchor="c")

        # ============================
        # STATIC MODE
        # ============================
        if not self.animated:
            # Load your normal hero icon and draw it onto canvas
            # Use your existing image loader (choose one that exists in this class)
            # If your loader returns a PIL.Image, convert to PhotoImage.
            # If it already returns PhotoImage, just use it.
            try:
                # OPTION A: if you have the same helper as outside:
                # pil = self._create_only_image(static_icon, (104, 104))  # but you likely don't in this class

                # OPTION B: if createOnlyImage returns ImageTk.PhotoImage directly:
                # img = self.createOnlyImage(static_icon, size=(s(104), s(104)))

                # safest: load PIL image first then convert (depends on your helpers)
                
                self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite", size=(frame_height-1, frame_height-1))  # keep reference!
                self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")
                self.static_img = self.createOnlyImage(static_icon, size=(self.image_sizeX, self.image_sizeY))
                if self.frame:
                    frame_ne = f"_prof_frame_{self.frame}4"
                    self.frame_ne_img = self.createOnlyImage(frame_ne, size=(s(190*self.scaling_frame), s(82*self.scaling_frame)))
                    self.frame_ne_id = self.canvas.create_image(s(frame_height), s(-1), tags=["frame"],image=self.frame_ne_img, anchor="ne")
                
                self.image_id = self.canvas.create_image(
                    cx + s(dx), cy + s(dy),
                    image=self.static_img,
                    anchor="center",
                    tags=["icon"]
                )

                if self.frame:
                    frame_sw = f"_prof_frame_{self.frame}12"
                    self.frame_sw_img = self.createOnlyImage(frame_sw, size=(s(190*self.scaling_frame), s(85*self.scaling_frame)))
                    self.frame_sw_id = self.canvas.create_image(s(0), s(frame_height-1), image=self.frame_sw_img, tags=["frame"],anchor="sw")

                if self.badge:
                    pass
                    
                    add = -2 if self.badge == 3 else 0
                    add = -4 if self.badge == 4 else add
                    
                    badge_name = f"_prof_badge{self.badge}"
                    self.badge_img = self.createOnlyImage(badge_name, bNearest=False, size=(s(37+add), s(37+add)))
                    self.badge_id = self.canvas.create_image(s(14), s(frame_height -13), image=self.badge_img, anchor="center")
                    #self.badge_id = self.canvas.create_image(s(14), s(13), image=self.badge_img, anchor="center")
                    
                self.canvas.tag_raise("frame", "icon")  # ensure frame is on top if it exists
                

                

                # img_pil = self.createOnlyImagePIL(static_icon)  # <-- implement or swap to your real loader
                # if self.size:
                #     # if size is already scaled, don't s() twice. assume size is pixels.
                #     w, h = self.size
                #     #img_pil = img_pil.resize((int(w), int(h)), Image.BICUBIC)
                # elif scale != 1:
                #     img_pil = img_pil.resize(
                #         (int(img_pil.size[0] * scale), int(img_pil.size[1] * scale)),
                #         Image.NEAREST
                #     )

                # self.static_img = ImageTk.PhotoImage(img_pil)
            except Exception:
                # fallback: try your other loader that already returns a PhotoImage
                self.icon_bg_img = self.createOnlyImage("_icon_bg_newwhite", size=(frame_height-1, frame_height-1))  # keep reference!
                self.bg_id = self.canvas.create_image(s((frame_height-1)), s(0), image=self.icon_bg_img, anchor="ne")
                self.static_img = self.createOnlyImage(static_icon, size=(frame_height-2, frame_height-2))
            
            

            #self.frame_overlay = self.createOnlyImage("gold_frame2", size=(s(128), s(128)))

            # self.frame_id = self.canvas.create_image(
            #     s(52), s(52),
            #     image=self.frame_overlay,
            #     anchor="center"
            # )

            self.frames = []
            self.index = 0
            return

        # ============================
        # ANIMATED MODE (your current logic)
        # ============================
        sheet, (sheet_w, sheet_h) = self.createOnlyImage1(sheet_path)

        xs = split_edges(sheet_w, cols)
        ys = split_edges(sheet_h, rows)

        frames = []
        for r in range(rows):
            for c in range(cols):
                x0, x1 = xs[c], xs[c + 1]
                y0, y1 = ys[r], ys[r + 1]

                if self.bSubCrop:
                    gx0 = x0 + self.subcrop_x
                    gy0 = y0 + self.subcrop_y
                    gx1 = gx0 + self.subcrop_w
                    gy1 = gy0 + self.subcrop_h
                    gx1 = min(gx1, x1)
                    gy1 = min(gy1, y1)
                    frame = sheet.crop((gx0, gy0, gx1, gy1))
                else:
                    frame = sheet.crop((x0, y0, x1, y1))

                if self.size:
                    # IMPORTANT: if self.size is already scaled by s(), don't s() again
                    w, h = self.size
                    frame = frame.resize((int(w), int(h)), Image.BICUBIC)
                elif scale != 1:
                    frame = frame.resize(
                        (int(frame.size[0] * scale), int(frame.size[1] * scale)),
                        Image.NEAREST
                    )

                frames.append(ImageTk.PhotoImage(frame))

        import random
        self.frames = frames
        self.index = random.randrange(len(self.frames)) if self.frames else 0

        if self.frame:
            frame_ne = f"_prof_frame_{self.frame}4"
            self.frame_ne_img = self.createOnlyImage(frame_ne, size=(s(190), s(82)))
            self.frame_ne_id = self.canvas.create_image(s(frame_height), s(-1), tags=["frame"], image=self.frame_ne_img, anchor="ne")
        

        if self.frames:
            self.image_id = self.canvas.create_image(
                cx + s(dx), cy + s(dy),
                image=self.frames[self.index],
                tags=["icon"],
                anchor="center"
            )
        if self.frame:
            frame_sw = f"_prof_frame_{self.frame}5"
            self.frame_sw_img = self.createOnlyImage(frame_sw, size=(s(190), s(85)))
            self.frame_sw_id = self.canvas.create_image(s(0), s(frame_height-1), tags=["frame"], image=self.frame_sw_img, anchor="sw")

        if self.badge:
            pass
            add = 0
            badge_name = f"_prof_badge{self.badge}"
            self.badge_img = self.createOnlyImage(badge_name, bNearest=False, size=(s(34+add), s(34+add)))
            self.badge_id = self.canvas.create_image(s(14), s(frame_height -14), image=self.badge_img, anchor="center")
        
        self.canvas.tag_raise("frame", "icon")  # ensure frame is on top if it exists
        

    def play(self):
        if not self.animated:
            return
        if not self.frames:
            return
        if self.running:
            return
        self.running = True
        self._tick()

    def stop(self):
        self.running = False

    def _tick(self):
        if not self.running:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.canvas.itemconfig(self.image_id, image=self.frames[self.index])
        self.canvas.after(self.delay_ms, self._tick)

            
            
    
    def _tick(self):
        if not self.running or not self.frames:
            return
        
        
        
        self.canvas.itemconfigure(self.image_id, image=self.frames[self.index])
        self.index = (self.index + 1) % len(self.frames)
        self.master.after(self.delay_ms, self._tick)

    def play(self):
        if not self.running:
            self.running = True
            self._tick()

    def pause(self):
        self.running = False

    def createOnlyImage1(self,player_img, size=None):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False
        sheet = img_raw.copy()
        return sheet, sheet.size
        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            resized = resized.resize(s(size), Image.BICUBIC)

            img_raw = ImageTk.PhotoImage(resized)
        si = img_raw.size 
        return img_raw, si
    def createOnlyImage(self,player_img, bNearest = False, size=None):
        img_raw = image_loader(player_img)
        if not img_raw:
            return False

        # Always start with a copy
        resized = img_raw.copy()

        # Only resize if size is provided (not False / None)
        if size:
            if bNearest:
                resized = resized.resize(s(size), Image.NEAREST)
            else:
                resized = resized.resize(s(size), Image.BICUBIC)

        img = ImageTk.PhotoImage(resized)
        return img


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

        if size:
            img_raw = img_raw.resize(self._s2(size), Image.BICUBIC)
        if mask_glow:
            if isinstance(mask_glow, tuple):
                bMask, bFlip = mask_glow
            else:
                bMask = mask_glow
                bFlip = False
            img_raw = apply_black_crops_mask(img_raw, "_GlowMask", flip=bFlip, resize_mask=True)

        if clip:
            img_raw = clip_to_region(img_raw, x,y,anc)
        img = ImageTk.PhotoImage(img_raw)



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
    
    

