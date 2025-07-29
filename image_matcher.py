# image_matcher.py
import cv2
import numpy as np
from PIL import Image

def match_hero_icon(captured_icon, image_map):
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

# import cv2
# import numpy as np
# from PIL import Image

# def match_hero_icon(captured_icon, hero_icon_assets):
#     """
#     Matches a captured icon to known assets using ORB.
#     :param captured_icon: PIL.Image from scoreboard
#     :param hero_icon_assets: dict of {hero_name: PIL.Image}
#     :return: best_match_name, score
#     """
#     orb = cv2.ORB_create(nfeatures=500)

#     # Convert captured to OpenCV format
#     captured_cv = cv2.cvtColor(np.array(captured_icon.resize((128, 128))), cv2.COLOR_RGB2BGR)
#     kp1, des1 = orb.detectAndCompute(captured_cv, None)

#     best_score = float('inf')
#     best_match = None

#     for hero_name, icon_img in hero_icon_assets.items():
#         icon_cv = cv2.cvtColor(np.array(icon_img.resize((128, 128))), cv2.COLOR_RGB2BGR)
#         kp2, des2 = orb.detectAndCompute(icon_cv, None)

#         if des1 is None or des2 is None:
#             continue

#         bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
#         matches = bf.match(des1, des2)
#         matches = sorted(matches, key=lambda x: x.distance)

#         if len(matches) == 0:
#             continue

#         avg_distance = np.mean([m.distance for m in matches[:20]])

#         if avg_distance < best_score:
#             best_score = avg_distance
#             best_match = hero_name

#     return best_match, best_score