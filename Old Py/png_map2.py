import os
from PIL import Image, ImageTk

assets_folder = r"C:\Users\Corey\Desktop\py\marvel_tracker\assets"
image_map = {}

for filename in os.listdir(assets_folder):
    if filename.lower().endswith(".png"):
        key = os.path.splitext(filename)[0]  # filename without extension
        path = os.path.join(assets_folder, filename)
        image_map[key] = ImageTk.PhotoImage(Image.open(path))

print(image_map)