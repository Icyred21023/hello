import config
import helpers
import os

ASSETS_ROOTDIR = helpers.create_path("", "fGui Assets")
ASSETS_HEROES = os.path.join(ASSETS_ROOTDIR, "Heroes")
ASSETS_UI = os.path.join(ASSETS_ROOTDIR, "UI")
ASSETS_NAMEPLATES = os.path.join(ASSETS_ROOTDIR, "Nameplates")
ASSETS_MOOD = os.path.join(ASSETS_ROOTDIR, "Mood")

ASSETS_IDX = {"heroes": ASSETS_HEROES, "ui": ASSETS_UI, "nameplates":
ASSETS_NAMEPLATES, "moods": ASSETS_ROOTDIR}

class ImageCache:
  def __init__(self)
    self.Cache = {}
  def image_loader(self, img_key, img_type=None, idx = None):
  
    img_type = "raw" if img_type is None else img_type
    img_raw = CACHED_IMGS.get(img_key).get(img_type) or CACHED_IMGS.get("Default")
    if not img_raw:
        dirs = None
        if idx is not None:
          
          for key in ASSETS_IDX:
            if idx.lower in key or idx.lower == key:
              dirs = [ASSETS_IDX.get(idx.lower(), None)]
              break
            
        if dirs is None:
          dirs = [ASSETS_UI, ASSETS_HEROES, ASSETS_NAMEPLATES, ASSETS_MOOD]
          
        for directory in dirs:

            try:
                img_path = os.path.join(directory, f"{img_key}.png")
                img_raw = Image.open(img_path)
                
                CACHED_IMGS[img_key] = {"raw": img_raw, "tk": False,
                "mask":False} # Cache it

            except FileNotFoundError:
                #print(f"Image not found: {img_key} in {directory}")
                continue

        if not img_raw:
            return False
    return img_raw
    
    
ASSET_CACHE = ImageCache()    

class SuperImage:
  def __init__(self, img_key: str, size=None, SuperClass = None, x=0,y=0, clip=False, mask=False, tags=None)
  self.canvas = SuperClass.canvas
  self.SuperFrame = SuperClass
  self.img_raw = image_loader(#finish)
  self.img_source = #cache or direct
  



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
            img_raw = make_circle(img_raw)

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