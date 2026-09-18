# ocr_capture.py
import pyautogui
import mss
import numpy as np
from PIL import Image
import helpers
from ocr_text_color import preprocess_text_color

#import torch
#print(torch.cuda.is_available())       # True = GPU available
#print(torch.cuda.get_device_name(0))


PC_W, PC_H = pyautogui.size()
DEBUG_CAPTURE_BOX = (0, 0, PC_W, PC_H)


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
        
def fix_l_one(s: str) -> str:
    import re
    if not s:
        return s
    # only apply when string already has digits
    if not re.search(r"\d", s):
        return s

    # Replace l with 1 when next to a digit
    s = re.sub(r"(?<=\d)l|l(?=\d)", "1", s)
    # Optional: also handle capital I
    s = re.sub(r"(?<=\d)I|I(?=\d)", "1", s)
    return s

def capture_names(flag_debug=False):
    

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
    
    FULL_CAPTURE_BOX = (0, 0, 2560, 1440) # All Names ; The coordinates below are relative to this box
    NAME_BOXES = [
        (1909, 251, 2179, 280), # Name 1
        (1868, 417, 2138, 447), # Name 2
        (1828, 584, 2098, 614), # Name 3
        (1787, 751, 2057, 778), # Name 4
        (1746, 918, 2016, 946), # Name 5
        (1706, 1085, 1976, 1112), # Name 6
    ]
    NAME_BOXES = [
        (1910, 250, 2179, 279), # Name 1
        (1869, 416, 2138, 445), # Name 2
        (1828, 582, 2097, 611), # Name 3
        (1785, 750, 2054, 779), # Name 4
        (1746, 916, 2015, 945), # Name 5
        (1705, 1083, 1974, 1113), # Name 6
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
    
    ban_screenshot_path = helpers.create_path('ban_screenshot.png','debug')
    if not flag_debug:
        left, top, width, height = FULL_CAPTURE_BOX
        with mss.mss() as sct:
            mon = {"left": left, "top": top, "width": width, "height": height}
            full_bgra = np.array(sct.grab(mon))      # BGRA
            full_np = full_bgra[:, :, :3]            # BGR (OpenCV-style)
            helpers.save_img(f"___BAN_FULL.png", full_np)
        #full_img = pyautogui.screenshot(region=FULL_CAPTURE_BOX)
        
        
        #full_img.save(ban_screenshot_path)
    elif flag_debug:
        full_np = helpers.load_img("___BAN_FULL.png")
        #full_img = Image.open(ban_screenshot_path).convert("RGB")
        print(f"🛠️ Using debug screenshot...")
    #full_img = Image.open(r"C:\Users\Corey\Desktop\d.png").convert("RGB")
    #full_np = np.array(full_img)
    names = []
    cropped_imgs = [] 
    # import torch
    # import easyocr
    import ocr_text_color
    import ocr_openai
    # if torch.cuda.is_available():
    #     reader = easyocr.Reader(['en'], gpu=True)
    # else:
    #     reader = easyocr.Reader(['en'], gpu=False, quantize=True)
    num = 1
    cropped_masks = []
    for box in NAME_BOXES:
        
        x1, y1, x2, y2 = box
        cropped = full_np[y1:y2, x1:x2]
        cropped_imgs.append(cropped)

        mask = preprocess_text_color(
        cropped,
        targets=("#bebfcb", "#bfb1c2"),
        lab_thr=99,          # was 30 → increase a lot for AA edges
        use_edge_gate=False, # edge gate can delete weak pixels
        open_k=0,            # MORPH_OPEN removes thin strokes
        dilate_k=2,
        dilate_iter=2,
        invert=False,
    )
        
        helpers.save_img(f"___banImg_{num}.png", mask)
        num += 1
        cropped_masks.append(mask)
    
    appended_names = ocr_text_color.stack_name_crops(cropped_masks, bg="1e1e1e", pad_y=8)
    appended_names = ocr_text_color.add_row_separators(appended_names, cropped_masks, pad_y=8)
    
    import cv2

    helpers.save_img(
    "___banImg_appended.png",
    cv2.cvtColor(np.array(appended_names), cv2.COLOR_RGB2BGR)
)
    results = ocr_openai.read_6_names_from_image(appended_names)
    results = ocr_openai.parse_names_response(results)
    if results:
        for name in results:
            if '*' not in name and '#' not in name:
                names.append(name)

    else:
        for mask in cropped_masks:    
            result = reader.readtext(
                mask,                 # feed masked image, not raw crop
                detail=0,
                paragraph=False,
                
                min_size=3,
                text_threshold=0.55,
                low_text=0.25,
                link_threshold=0.35,
                mag_ratio=4,
                decoder="beamsearch",
                beamWidth=5
            )
        # result = reader.readtext(
        #                     mask,
        #                     detail=1,
        #                     paragraph=False,
        #                     min_size=5,            # smaller text gets detected
        #                     text_threshold=0.4,    # lower threshold → keeps more characters
        #                     low_text=0.3,          # allow "weaker" regions
        #                     link_threshold=0.4
        #                 )
            if result:
                if isinstance(result[0],str):
                    if '*' not in result[0] and '#' not in result[0]:
                        #result[0] = fix_l_one(result[0])
                        names.append(result[0].strip())
                        continue
                    else:
                        continue
                else:
                    best = max(result, key=lambda r: float(r[2] or 0.0))
                    if "*" not in best[1] and "#" not in best[1]:

                        names.append((best[1] or "").strip())
                    else:
                        continue
            else:
                continue 
        # else:
        #     names.append("")
        # if result:
        #     name = result[0][1].strip()
        #     if "*" not in name:
        #         names.append(name)
        #     else:
        #         continue  # or skip with: continue
        # else:
        #     continue

    #if cropped_imgs:
        
        #save_path = os.path.join(config.script_dir, "debug", "OCR_Capture.png")
        #combined_img = np.concatenate(cropped_imgs, axis=0)
        #Image.fromarray(combined_img).save(save_path)
        #print(f"✅ Combined cropped image saved to {save_path}")

    return names
