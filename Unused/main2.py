
from PIL import Image, ImageGrab
import cv2
import numpy as np
import os
from collections import defaultdict

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
        return None, float("inf")

    match_scores = []  # Store (hero_name, score) pairs for sorting later
    best_score = float("inf")
    best_match = None

    for hero_name, variants in image_map.items():
        for variant in variants:
            variant_cv = cv2.cvtColor(np.array(variant.resize((128, 128))), cv2.COLOR_RGB2BGR)
            kp2, des2 = orb.detectAndCompute(variant_cv, None)
            if des2 is None:
                continue

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            if not matches:
                continue

            avg_distance = np.mean([m.distance for m in matches[:20]])
            match_scores.append((hero_name, avg_distance))

            if avg_distance < best_score:
                best_score = avg_distance
                best_match = hero_name

    # Optional: print top 4 matches if confidence is low
    if best_score > 50 and match_scores:
        print(f"⚠️ Low confidence (best score = {best_score:.2f}). Closest matches:")
        top_matches = sorted(match_scores, key=lambda x: x[1])[:4]
        for name, score in top_matches:
            print(f"  - {name}: {score:.2f}")

    return best_match, best_score


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

def capture_scoreboard_icons(region_box, dir,name_boxes=NAME_BOXES):
    """Captures a region of the screen and crops hero icons."""
    pic = os.path.join(dir,"Untitled2.png")
    full_img = Image.open(pic) #ImageGrab.grab(bbox=region_box)  # Use pyautogui or mss on Linux if needed
    cropped_icons = []

    for box in name_boxes:
        x1, y1, x2, y2 = box
        cropped = full_img.crop((x1 - region_box[0], y1 - region_box[1], x2 - region_box[0], y2 - region_box[1]))
        cropped_icons.append(cropped)

    return cropped_icons

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
            name = os.path.splitext(filename)[0]  # Remove .png
            base_name = name.split("_")[0].strip()  # Everything before the first _
            path = os.path.join(folder_path, filename)
            img = Image.open(path)
            image_map[base_name].append(img)

    return image_map



if __name__ == "__main__":
    REGION_BOX = (0, 0, 2560, 1440)  # example scoreboard area
    
    hero_icons,script_dir = load_hero_assets()

    cropped_icons = capture_scoreboard_icons(REGION_BOX,script_dir)

    for i, cropped in enumerate(cropped_icons):
        match_name, score = match_hero_icon(cropped, hero_icons)
        print(f"Slot {i+1}: Matched with {match_name} (Score: {score:.2f})")