# ocr_capture.py
import pyautogui
import easyocr
import numpy as np
from PIL import Image
import config
import os
#import torch
#print(torch.cuda.is_available())       # True = GPU available
#print(torch.cuda.get_device_name(0))
def scale_box(box, scale_x, scale_y):
    x1, y1, x2, y2 = box
    return (
        int(x1 * scale_x),
        int(y1 * scale_y),
        int(x2 * scale_x),
        int(y2 * scale_y)
    )

def offset_box(box, offset):
    x1, y1, x2, y2 = box
    return (
        int(x1 + offset),
        int(y1),
        int(x2 + offset),
        int(y2)
    )

def scale_boxes(boxes, scale_x, scale_y):
    return [scale_box(box, scale_x, scale_y) for box in boxes]

reader = easyocr.Reader(['en'], gpu=False)

original_res = (2560, 1440)
width, height = pyautogui.size()
target_res = (width, height)


scale_x = target_res[0] / original_res[0]  # 1920 / 2560 = 0.75
scale_y = target_res[1] / original_res[1]  # 1080 / 1440 = 0.75


FULL_CAPTURE_BOX = (1700, 250, 2300, 1115) # All Names ; The coordinates below are relative to this box
NAME_BOXES = [
    (210, 1, 610, 30), # Name 1
    (167, 167, 567, 197), # Name 2
    (128, 334, 528, 364), # Name 3
    (83, 500, 483, 530), # Name 4
    (44, 667, 444, 697), # Name 5
    (4, 834, 404, 864), # Name 6
]

if scale_x != 1 and scale_y != 1:
    # Scaled output
    scaled_full_box = scale_box(FULL_CAPTURE_BOX, scale_x, scale_y)
    scaled_name_boxes = scale_boxes(NAME_BOXES, scale_x, scale_y)
    FULL_CAPTURE_BOX = scaled_full_box
    NAME_BOXES = scaled_name_boxes
    print(f"Scaled OCR Coordinates for {target_res}\nFull Box: {FULL_CAPTURE_BOX}")

if scale_y == 1 and scale_x != 1:
    ox, oy = original_res
    width, height = target_res
    offset = width - ox
    scaled_full_box = offset_box(FULL_CAPTURE_BOX, offset)
    FULL_CAPTURE_BOX = scaled_full_box
    print(f"Offset OCR for {target_res} Ultra-Wide\nFull Box: {FULL_CAPTURE_BOX}")

def check_display_resolution():
    width, height = pyautogui.size()
    if width and height == 2540 and 1440:
        box = (1700, 250, 2300, 1115)
        boxes = [
            (210, 1, 610, 30), # Name 1
            (167, 167, 567, 197), # Name 2
            (128, 334, 528, 364), # Name 3
            (83, 500, 483, 530), # Name 4
            (44, 667, 444, 697), # Name 5
            (4, 834, 404, 864), # Name 6
            ]
    elif width and height == 3440 and 1440:
        box = (2300, 250, 2900,1115)
        boxes = [
            (250, 1, 650, 39),
            (207, 167, 607, 197),
            (167, 334, 567, 364), # Name 3
            (124, 501, 522, 531), # Name 4
            (85, 667, 485, 697), # Name 5
            (44, 834, 444, 864), # Name 6
            ]
    elif width and height == 3440 and 1440:
        box = (1275, 188, 1725,844)
        boxes = [
            (250, 1, 650, 39),
            (207, 167, 607, 197),
            (167, 334, 567, 364), # Name 3
            (124, 501, 522, 531), # Name 4
            (85, 667, 485, 697), # Name 5
            (44, 834, 444, 864), # Name 6
            ]
        


def capture_names():
    full_img = pyautogui.screenshot(region=FULL_CAPTURE_BOX)
    #full_img = Image.open(r"C:\Users\Corey\Desktop\d.png").convert("RGB")
    full_np = np.array(full_img)
    names = []
    cropped_imgs = [] 

    for box in NAME_BOXES:
        x1, y1, x2, y2 = box
        cropped = full_np[y1:y2, x1:x2]
        cropped_imgs.append(cropped)
        result = reader.readtext(
                            cropped,
                            detail=1,
                            paragraph=False,
                            min_size=5,            # smaller text gets detected
                            text_threshold=0.4,    # lower threshold → keeps more characters
                            low_text=0.3,          # allow "weaker" regions
                            link_threshold=0.4
                        )
        if result:
            name = result[0][1].strip()
            if "*" not in name:
                names.append(name)
            else:
                continue  # or skip with: continue
        else:
            continue

    if cropped_imgs:
        
        save_path = os.path.join(config.script_dir, "debug", "OCR_Capture.png")
        combined_img = np.concatenate(cropped_imgs, axis=0)
        Image.fromarray(combined_img).save(save_path)
        print(f"✅ Combined cropped image saved to {save_path}")

    return names
