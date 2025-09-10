import os
import re
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import cv2
import numpy as np

# Fallback preset crop
PRESET_LEFT, PRESET_TOP = 65, 45
PRESET_WIDTH, PRESET_HEIGHT = 217, 217

def extract_digits(name, length=7):
    """Extract first continuous sequence of digits of given length from filename."""
    match = re.search(r"\d{%d}" % length, name)
    return match.group(0) if match else None

def find_crop_box_template(full_img, ref_img, score_thresh=0.8):
    """
    Template matching with broad multi-scale search.
    Two passes:
      - 1.30–1.60 step 0.01
      - if no good match, 1.60–3.00 step 0.01
    Returns (box, score)
    """
    gray_full = cv2.cvtColor(np.array(full_img), cv2.COLOR_RGB2GRAY)
    gray_ref0 = cv2.cvtColor(np.array(ref_img), cv2.COLOR_RGB2GRAY)

    def try_scales(start, end, step):
        best_score = -1
        best_box = None
        s = start
        while s <= end + 1e-9:
            new_w = int(gray_ref0.shape[1] * s)
            new_h = int(gray_ref0.shape[0] * s)
            if new_w < 10 or new_h < 10:
                s += step
                continue
            scaled_ref = cv2.resize(gray_ref0, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            if scaled_ref.shape[0] > gray_full.shape[0] or scaled_ref.shape[1] > gray_full.shape[1]:
                s += step
                continue

            res = cv2.matchTemplate(gray_full, scaled_ref, cv2.TM_CCOEFF_NORMED)
            _, score, _, max_loc = cv2.minMaxLoc(res)
            if score > best_score:
                best_score = score
                left, top = max_loc
                right, bottom = left + scaled_ref.shape[1], top + scaled_ref.shape[0]
                best_box = (left, top, right, bottom)
            s += step
        return best_box, best_score

    # First pass
    box, score = try_scales(1.30, 1.60, 0.01)
    if score >= score_thresh:
        return box, score

    # Second pass
    box2, score2 = try_scales(1.60, 3.00, 0.01)
    if score2 > score:
        return box2, score2
    return box, score

def find_crop_box_orb(full_img, ref_img):
    """Use ORB keypoint matching to find crop region."""
    gray_full = cv2.cvtColor(np.array(full_img), cv2.COLOR_RGB2GRAY)
    gray_ref = cv2.cvtColor(np.array(ref_img), cv2.COLOR_RGB2GRAY)

    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray_ref, None)
    kp2, des2 = orb.detectAndCompute(gray_full, None)

    if des1 is None or des2 is None:
        return None, 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    if len(matches) < 4:
        return None, 0.0

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None, 0.0

    h, w = gray_ref.shape
    pts = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
    dst = cv2.perspectiveTransform(pts, H)

    x_min, y_min = np.min(dst[:, 0, :], axis=0)
    x_max, y_max = np.max(dst[:, 0, :], axis=0)
    box = (int(x_min), int(y_min), int(x_max), int(y_max))

    confidence = float(np.sum(mask)) / len(mask)
    return box, confidence

def crop_images():
    root = tk.Tk()
    root.withdraw()

    # Ask for directories
    full_dir = filedialog.askdirectory(title="Select directory containing FULL PNG files")
    if not full_dir:
        print("No directory selected. Exiting.")
        return
    ref_dir = filedialog.askdirectory(title="Select directory containing REFERENCE cropped PNGs")
    if not ref_dir:
        print("No reference directory selected. Exiting.")
        return

    # Output folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cropped_dir = os.path.join(script_dir, "cropped")
    os.makedirs(cropped_dir, exist_ok=True)

    # Build map: heroid -> reference file path
    ref_map = {}
    for fn in os.listdir(ref_dir):
        if fn.lower().endswith(".png"):
            if "Proficiency" in ref_dir:
                print("Profiency detected, using 8-digit IDs.")
                digits = extract_digits(fn, 8)
                bProficiency = True
            else:
                digits = extract_digits(fn, 7)
                bProficiency = False
            if digits:
                ref_map[digits] = os.path.join(ref_dir, fn)

    name = 0
    for filename in os.listdir(full_dir):
        if not filename.lower().endswith(".png"):
            continue
        full_path = os.path.join(full_dir, filename)

        try:
            full_img = Image.open(full_path)
            if bProficiency:
                digits = extract_digits(filename, 8)
            else:
                digits = extract_digits(filename, 7)
            ref_path = ref_map.get(digits)

            suffix = ""
            cropped = None

            if ref_path and os.path.exists(ref_path):
                ref_img = Image.open(ref_path)

                # Try template match first
                box, score = find_crop_box_template(full_img, ref_img)
                if box and score >= 0.8:
                    cropped = full_img.crop(box)
                    print(f"✅ Template match for {filename} (score={score:.3f})")

                else:
                    # Try ORB
                    box, conf = find_crop_box_orb(full_img, ref_img)
                    if box and conf >= 0.3:  # relax confidence since ORB is robust
                        cropped = full_img.crop(box)
                        print(f"✅ ORB match for {filename} (conf={conf:.2f})")
                    else:
                        # Fall back preset
                        left, top = PRESET_LEFT, PRESET_TOP
                        right, bottom = left + PRESET_WIDTH, top + PRESET_HEIGHT
                        cropped = full_img.crop((left, top, right, bottom))
                        suffix = "_nomatch"
                        print(f"⚠️ No match for {filename}; used preset crop.")
            else:
                # No reference at all
                left, top = PRESET_LEFT, PRESET_TOP
                right, bottom = left + PRESET_WIDTH, top + PRESET_HEIGHT
                cropped = full_img.crop((left, top, right, bottom))
                suffix = "_nomatch"
                print(f"⚠️ No reference for {filename}; used preset crop.")

            # Save
            base_name = f"{name}{suffix}.png"
            save_path = os.path.join(cropped_dir, base_name)
            while os.path.exists(save_path):
                name += 1
                base_name = f"{name}{suffix}.png"
                save_path = os.path.join(cropped_dir, base_name)

            cropped.save(save_path)
            name += 1

        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")

    print(f"\nAll cropped images saved in: {cropped_dir}")

if __name__ == "__main__":
    crop_images()
