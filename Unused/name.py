import os
import cv2
from PIL import Image
import numpy as np
import shutil

LEFT_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\MarvelRivals\MarvelGame\Marvel\ModManagerFiles\2 - ExportRawData\hhh\Exports\Marvel\Content\Marvel\UI\Textures\HeroPortrait\SquareHeroHead"
RIGHT_DIR = r"C:\Users\Corey\Desktop\py\marvel_tracker\New folder"
OUTPUT_DIR = r"C:\Users\Corey\Desktop\py\marvel_tracker\Output"

def load_images_from_folder(folder):
    images = {}
    for filename in os.listdir(folder):
        if filename.lower().endswith((".png", ".jpg")):
            path = os.path.join(folder, filename)
            images[filename] = cv2.cvtColor(np.array(Image.open(path).resize((128, 128))), cv2.COLOR_RGB2BGR)
    return images

def orb_similarity(img1, img2):
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)
    if des1 is None or des2 is None:
        return float("inf")
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)
    if not matches:
        return float("inf")
    return np.mean([m.distance for m in matches[:20]])

def rename_images():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    left_images = load_images_from_folder(LEFT_DIR)
    right_images = load_images_from_folder(RIGHT_DIR)

    for left_name, left_img in left_images.items():
        best_score = float("inf")
        best_match_name = None

        for right_name, right_img in right_images.items():
            score = orb_similarity(left_img, right_img)
            if score < best_score:
                best_score = score
                best_match_name = right_name

        if best_match_name:
            new_name = os.path.splitext(best_match_name)[0] + ".png"
            src_path = os.path.join(LEFT_DIR, left_name)
            dst_path = os.path.join(OUTPUT_DIR, new_name)
            print(f"Renaming '{left_name}' to '{new_name}' (score: {best_score:.2f})")
            shutil.copy(src_path, dst_path)

rename_images()
