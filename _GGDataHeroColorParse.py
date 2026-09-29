import json
import os
import re
import tkinter as tk
from tkinter import filedialog

from PIL import Image


# ============================================================
# CHANGE THESE PATHS
# ============================================================
JSON1_PATH = r"C:\Users\Chloroform\Desktop\MarvelBans\_HeroKeys.json"   # example: hero id -> {"name": "..."}
JSON2_PATH = r"C:\Users\Chloroform\Desktop\MarvelBans\colors2.json"   # example: hero name -> "#RRGGBB"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_png_files(directory):
    return [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and f.lower().endswith(".png")
    ]


def extract_id_from_filename(filename):
    """
    Example:
        img_herologo_1011_logo.png  ->  "1011"
    """
    name_no_ext = os.path.splitext(filename)[0]
    match = re.search(r"_(\d+)_", name_no_ext)
    if match:
        return match.group(1)

    # fallback: first number found anywhere
    match = re.search(r"(\d+)", name_no_ext)
    if match:
        return match.group(1)

    return None


def hex_to_rgb(hex_color):
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid color code: {hex_color}")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def recolor_white_logo(input_path, output_path, target_rgb):
    """
    Recolors a white logo PNG by replacing visible pixels with target_rgb
    while preserving transparency/alpha.
    """
    img = Image.open(input_path).convert("RGBA")
    _, _, _, alpha = img.split()

    recolored = Image.new("RGBA", img.size, target_rgb + (0,))
    recolored.putalpha(alpha)
    recolored.save(output_path)


def main():
    root = tk.Tk()
    root.withdraw()

    print("Select the directory containing the PNG logo files...")
    png_dir = filedialog.askdirectory(title="Select PNG Directory")

    if not png_dir:
        print("No directory selected.")
        return

    output_dir = os.path.join(png_dir, "Outputs")
    os.makedirs(output_dir, exist_ok=True)

    try:
        json1 = load_json(JSON1_PATH)
        json2 = load_json(JSON2_PATH)
    except Exception as e:
        print(f"Failed to load JSON files: {e}")
        return

    png_files = get_png_files(png_dir)

    if not png_files:
        print("No PNG files found.")
        return

    print(f"Found {len(png_files)} PNG files.")
    print(f"Outputs will be saved to:\n{output_dir}\n")

    for filename in png_files:
        try:
            hero_id = extract_id_from_filename(filename)
            if not hero_id:
                print(f"Skipping {filename} - could not extract ID.")
                continue

            if hero_id not in json1:
                print(f"Skipping {filename} - ID {hero_id} not found in JSON1.")
                continue

            hero_name = json1[hero_id]["name"]

            if hero_name not in json2:
                print(f"Skipping {filename} - HeroName '{hero_name}' not found in JSON2.")
                continue

            color_code = json2[hero_name]
            target_rgb = hex_to_rgb(color_code)

            input_path = os.path.join(png_dir, filename)
            output_filename = f"{hero_name}_icon.png"
            output_path = os.path.join(output_dir, output_filename)

            recolor_white_logo(input_path, output_path, target_rgb)

            print(f"Saved: {output_filename}  |  ID: {hero_id}  |  Color: {color_code}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()