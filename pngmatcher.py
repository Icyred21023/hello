import os
import sys
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog

# ============================
# Tuning knobs
# ============================
HIGH_CONF_THRESH = 0.96   # minimum score for template matching
ABS_MARGIN = 0.02         # absolute margin
REL_MARGIN = 0.03         # relative margin
ORB_CONF_THRESH = 0.3     # minimum inlier ratio for ORB acceptance

WRITE_SKIP_REPORT = True


def load_templates(match_dir):
    """Load all PNG templates (grayscale + optional alpha mask)."""
    templates = {}
    for fn in os.listdir(match_dir):
        if not fn.lower().endswith(".png"):
            continue
        path = os.path.join(match_dir, fn)
        tmpl_rgba = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if tmpl_rgba is None:
            continue

        if tmpl_rgba.ndim == 3 and tmpl_rgba.shape[2] == 4:
            bgr = tmpl_rgba[:, :, :3]
            alpha = tmpl_rgba[:, :, 3]
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            mask = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)[1]
        else:
            gray = cv2.cvtColor(tmpl_rgba, cv2.COLOR_BGR2GRAY) if tmpl_rgba.ndim == 3 else tmpl_rgba
            mask = None

        name = os.path.splitext(fn)[0]
        h, w = gray.shape[:2]
        templates[name] = {"img": gray, "mask": mask, "w": w, "h": h}
    return templates


def best_two_template_scores(img_gray, templates, available_names):
    """Compute best two template match scores."""
    scores = []
    H, W = img_gray.shape[:2]

    for name in available_names:
        tmpl = templates[name]
        tw, th = tmpl["w"], tmpl["h"]
        if th > H or tw > W:
            continue
        try:
            if tmpl["mask"] is not None:
                res = cv2.matchTemplate(img_gray, tmpl["img"], cv2.TM_CCORR_NORMED, mask=tmpl["mask"])
            else:
                res = cv2.matchTemplate(img_gray, tmpl["img"], cv2.TM_CCORR_NORMED)
            _, maxVal, _, _ = cv2.minMaxLoc(res)
            scores.append((name, float(maxVal)))
        except cv2.error as e:
            print(f"⚠️ matchTemplate error for {name}: {e}")

    if not scores:
        return []

    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[0]
    second = scores[1] if len(scores) > 1 else None
    return [top, second]


def passes_strict_thresholds(top, second):
    """Check if top match is high enough and unique enough."""
    name1, s1 = top
    if s1 < HIGH_CONF_THRESH:
        return False
    if second is None:
        return True
    name2, s2 = second
    if (s1 - s2) < ABS_MARGIN:
        return False
    if s1 < s2 * (1.0 + REL_MARGIN):
        return False
    return True


def find_crop_box_orb(img_gray, tmpl_gray):
    """ORB keypoint matching as fallback."""
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(tmpl_gray, None)
    kp2, des2 = orb.detectAndCompute(img_gray, None)
    if des1 is None or des2 is None:
        return None, 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    if len(matches) < 4:
        return None, 0.0

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None, 0.0

    h, w = tmpl_gray.shape
    pts = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
    dst = cv2.perspectiveTransform(pts, H)

    x_min, y_min = np.min(dst[:, 0, :], axis=0)
    x_max, y_max = np.max(dst[:, 0, :], axis=0)
    box = (int(x_min), int(y_min), int(x_max), int(y_max))
    confidence = float(np.sum(mask)) / len(mask)
    return box, confidence


def unique_target_path(dirpath, basename_no_ext, used_ext=".png"):
    """Avoid overwriting existing files."""
    candidate = os.path.join(dirpath, f"{basename_no_ext}{used_ext}")
    if not os.path.exists(candidate):
        return candidate
    i = 1
    while True:
        candidate = os.path.join(dirpath, f"{basename_no_ext}_{i}{used_ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def rename_with_safety(src_path, dst_path):
    os.rename(src_path, dst_path)


def main():
    root = tk.Tk()
    root.withdraw()
    in_dir = filedialog.askdirectory(title="Select directory containing input PNG files")
    if not in_dir:
        print("No directory selected. Exiting.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    match_dir = os.path.join(script_dir, "asset_match")
    if not os.path.isdir(match_dir):
        print(f"❌ Missing match directory: {match_dir}")
        return

    templates = load_templates(match_dir)
    if not templates:
        print(f"❌ No PNG templates found in: {match_dir}")
        return

    input_pngs = [f for f in os.listdir(in_dir) if f.lower().endswith(".png")]
    input_pngs.sort()
    available_names = set(templates.keys())
    skipped = []

    for fn in input_pngs:
        src_path = os.path.join(in_dir, fn)
        rgba = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
        if rgba is None:
            print(f"⚠️ Could not read image: {fn}")
            continue
        if rgba.ndim == 3 and rgba.shape[2] == 4:
            bgr = rgba[:, :, :3]
            img_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = cv2.cvtColor(rgba, cv2.COLOR_BGR2GRAY) if rgba.ndim == 3 else rgba

        if not available_names:
            print(f"⏭️ No names left for '{fn}'.")
            skipped.append({"file": fn, "top": None, "second": None})
            continue

        # Step 1: Template matching
        top_two = best_two_template_scores(img_gray, templates, available_names)
        use_orb = False
        if top_two and passes_strict_thresholds(top_two[0], top_two[1]):
            best_name, best_score = top_two[0]
            available_names.remove(best_name)
            dst_path = unique_target_path(in_dir, best_name)
            rename_with_safety(src_path, dst_path)
            print(f"✅ Template: '{fn}' → '{os.path.basename(dst_path)}' (score={best_score:.3f})")
            continue
        else:
            use_orb = True

        # Step 2: ORB fallback
        if use_orb:
            best_conf = 0.0
            best_name = None
            for name in available_names:
                tmpl_gray = templates[name]["img"]
                box, conf = find_crop_box_orb(img_gray, tmpl_gray)
                if box and conf > best_conf:
                    best_conf = conf
                    best_name = name

            if best_name and best_conf >= ORB_CONF_THRESH:
                available_names.remove(best_name)
                dst_path = unique_target_path(in_dir, best_name)
                rename_with_safety(src_path, dst_path)
                print(f"✅ ORB: '{fn}' → '{os.path.basename(dst_path)}' (conf={best_conf:.2f})")
            else:
                print(f"⏭️ SKIP '{fn}' (template + ORB failed)")
                skipped.append({"file": fn, "top": None, "second": None})

    print("\n==== SUMMARY ====")
    if skipped:
        print(f"Skipped {len(skipped)} file(s).")
        if WRITE_SKIP_REPORT:
            report_path = os.path.join(in_dir, "_skipped_report.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"Template threshold: {HIGH_CONF_THRESH}, margins ABS={ABS_MARGIN}, REL={REL_MARGIN}\n")
                f.write(f"ORB threshold: {ORB_CONF_THRESH}\n\n")
                for item in skipped:
                    f.write(f"{item['file']}\n")
        print("📝 Skip report saved.")
    else:
        print("All files matched successfully 🎉")


if __name__ == "__main__":
    main()
