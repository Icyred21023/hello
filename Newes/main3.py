
from PIL import Image, ImageGrab, ImageTk
import cv2
import numpy as np
import os
from collections import defaultdict
from matchups4 import counters
import config
#import pyautogui


class HeroMatch:
    def __init__(self, name, full, score, image):
        self.name = name
        self.fullname = full
        self.score = score
        self.image = image  # This is a PIL Image object

    def get_tk_image(self, size=(128, 128)):
        if self.image:
            return ImageTk.PhotoImage(self.image.resize(size))
        return None

# Example fixed boxes (replace with dynamic logic as needed)
NAME_BOXES = [
    (445, 395, 537, 487),  # Example enemy icon 1
    (445, 491, 537, 583),
    (445, 587, 537, 679),
    (445, 683, 537, 775),
    (445, 779, 537, 871),
    (445, 875, 537, 967)]

#     (1325, 395, 1417, 487),  # Example enemy icon 1
#     (1325, 491, 1417, 583),
#     (1325, 587, 1417, 679),
#     (1325, 683, 1417, 775),
#     (1325, 779, 1417, 871),
#     (1325, 875, 1417, 967)
# ]
def match_hero_icon(captured_icon, image_map):
    

    orb = cv2.ORB_create(nfeatures=500)
    captured_cv = cv2.cvtColor(np.array(captured_icon.resize((128, 128))), cv2.COLOR_RGB2BGR)
    kp1, des1 = orb.detectAndCompute(captured_cv, None)

    if des1 is None:
        return None, float("inf"), None

    match_scores = []  # Store (hero_name, score) pairs for sorting later
    best_score = float("inf")
    best_match = None

    for hero_base_name, variants in image_map.items():
        for variant in variants:
            img = variant["image"]
            full_name = variant["name"]
            base_name = variant["base_name"]

            variant_cv = cv2.cvtColor(np.array(img.resize((128, 128))), cv2.COLOR_RGB2BGR)
            kp2, des2 = orb.detectAndCompute(variant_cv, None)
            if des2 is None:
                continue

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            if not matches:
                continue

            avg_distance = np.mean([m.distance for m in matches[:20]])
            match_scores.append((base_name, full_name, avg_distance))

            if avg_distance < best_score:
                best_score = avg_distance
                best_base = base_name
                best_full = full_name
    # Optional: print top 4 matches if confidence is low
    if best_score > 50 and match_scores:
        print(f"⚠️ Low confidence (best score = {best_score:.2f}). Closest matches:")
        top_matches = sorted(match_scores, key=lambda x: x[2])[:4]
        for base, full, score in top_matches:
            print(f"  - {full}: {score:.2f}")

    return best_base, best_full, best_score


def match_hero_icoon(captured_icon, image_map):
    """
    Matches a captured scoreboard icon to known hero icons in image_map using ORB.
    
    :param captured_icon: PIL.Image object of the cropped icon from scoreboard
    :param image_map: dict {hero_name: PIL.Image} with preloaded hero icons
    :return: best_match_name, best_score
    """
    orb = cv2.ORB_create(nfeatures=500)
    captured_cv = cv2.cvtColor(np.array(captured_icon.resize((128, 128))), cv2.COLOR_RGB2BGR)
    kp1, des1 = orb.detectAndCompute(captured_cv, None)

    if des1 is None:
        return None, float("inf")

    best_score = float("inf")
    best_match = None

    for hero_name, icon_img in image_map.items():
        icon_cv = cv2.cvtColor(np.array(icon_img.resize((128, 128))), cv2.COLOR_RGB2BGR)
        kp2, des2 = orb.detectAndCompute(icon_cv, None)

        if des2 is None:
            continue

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        if not matches:
            continue

        matches = sorted(matches, key=lambda x: x.distance)
        avg_distance = np.mean([m.distance for m in matches[:20]])

        if avg_distance < best_score:
            best_score = avg_distance
            best_match = hero_name

    return best_match, best_score

def capture_scoreboard_icons(region_box, dir,flag, name_boxes=NAME_BOXES):
    """Captures a region of the screen and crops hero icons."""
    print(f"Capture Scoreboard Screenshot: {not config.debug_mode}")
    if config.debug_mode:
        pic = os.path.join(dir,"Screenshot.png")
        full_img = Image.open(pic)
    else:
        pic = os.path.join(dir,"Screenshot.png")
        full_img = ImageGrab.grab(bbox=region_box)
        full_img.save(pic)
    #full_img = Image.open(pic) #ImageGrab.grab(bbox=region_box)  # Use pyautogui or mss on Linux if needed
    cropped_icons = []
    cropped_enemy_icons = []

    enemy_boxes = [
    (1325, 395, 1417, 487),  # Example enemy icon 1
    (1325, 491, 1417, 583),
    (1325, 587, 1417, 679),
    (1325, 683, 1417, 775),
    (1325, 779, 1417, 871),
    (1325, 875, 1417, 967)
 ]

    if flag:
        name_boxes = [
        (885, 395, 977, 487),  # Example enemy icon 1
        (885, 491, 977, 583),
        (885, 587, 977, 679),
        (885, 683, 977, 775),
        (885, 779, 977, 871),
        (885, 875, 977, 967)]

        enemy_boxes = [
        (1765, 395, 1857, 487),  # Example enemy icon 1
        (1765, 491, 1857, 583),
        (1765, 587, 1857, 679),
        (1765, 683, 1857, 775),
        (1765, 779, 1857, 871),
        (1765, 875, 1857, 967)
        ]

    for box in name_boxes:
        x1, y1, x2, y2 = box
        cropped = full_img.crop((x1 - region_box[0], y1 - region_box[1], x2 - region_box[0], y2 - region_box[1]))
        cropped_icons.append(cropped)
        
    for box in enemy_boxes:
        x1, y1, x2, y2 = box
        cropped = full_img.crop((x1 - region_box[0], y1 - region_box[1], x2 - region_box[0], y2 - region_box[1]))
        cropped_enemy_icons.append(cropped)

    return cropped_icons,cropped_enemy_icons

def load_hero_assets():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    assets_folder = os.path.join(script_dir, "asset_match")

    image_map = load_image_map(assets_folder)
    #for filename in os.listdir(assets_folder):
        #if filename.lower().endswith(".png"):
            #key = os.path.splitext(filename)[0]
         #   path = os.path.join(assets_folder, filename)
          #  image_map[key] = Image.open(path)  # Store PIL images instead
    return image_map,script_dir
    
def load_image_map(folder_path):
    image_map = defaultdict(list)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".png"):
            name = os.path.splitext(filename)[0]           # Full filename without extension
            base_name = name.split("_")[0].strip()         # First part before _
            path = os.path.join(folder_path, filename)
            img = Image.open(path)

            # Save full info per variant
            image_map[base_name].append({
                "base_name": base_name,
                "name": name,
                "image": img
            })

    return image_map

def create_heromatches_from_lists(blue_names, red_names, default_score=20):
    bluematches = []
    redmatches = []

    for name in blue_names:
        match = HeroMatch(name, name, default_score, False)
        bluematches.append(match)

    for name in red_names:
        match = HeroMatch(name, name, default_score, False)
        redmatches.append(match)

    hero_icons,script_dir = load_hero_assets()

    return blue_names, red_names, bluematches, redmatches,hero_icons


def main3():
    ultra_flag = False
    width, height = 2560,1440
    REGION_BOX = (0, 0, width, height)  # example scoreboard area
    target_w = 2560
    target_h = 1440
    if width != target_w:
        if height == target_h:
            ultra_flag = True
    
    hero_icons,script_dir = load_hero_assets()
    
    cropped_icons,cropped_enemy_icons = capture_scoreboard_icons(REGION_BOX,script_dir,ultra_flag)
    blueteam =[]
    redteam = []
    bluematches = []
    redmatches = []
    for i, cropped in enumerate(cropped_icons):
        base_name, full_name, score = match_hero_icon(cropped, hero_icons)
        if base_name is None:
            return (None,) * 5

        if score >= 55:
            bluematches.append(HeroMatch(base_name, full_name, score, cropped))
        else:
            bluematches.append(HeroMatch(base_name, full_name, score, False))

        blueteam.append(base_name)
        print(f"Slot {i+1}: Matched with {full_name} (Score: {score:.2f})")
    for i, cropped in enumerate(cropped_enemy_icons):
        base_name, full_name, score = match_hero_icon(cropped, hero_icons)

        if score >= 55:
            redmatches.append(HeroMatch(base_name, full_name,score, cropped))
        else:
            redmatches.append(HeroMatch(base_name, full_name, score, False))

        redteam.append(base_name)
        print(f"Slot {i+1}: Matched with {full_name} (Score: {score:.2f})")
    print(f"Blue Team = \n{blueteam}")
    print(f"Red Team = \n{redteam}")
    return blueteam,redteam,bluematches,redmatches,hero_icons
    counters(blueteam,redteam)
    
    