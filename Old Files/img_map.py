import os
from PIL import Image, ImageTk

def load_image_map(assets_folder, root):
    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image = Image.open(path)
            image_map[key] = ImageTk.PhotoImage(image, master=root)

    # Optional default image
    if "Default" not in image_map:
        image_map["Default"] = ImageTk.PhotoImage(Image.new("RGB", (100, 100), color="gray"), master=root)

    return image_map
