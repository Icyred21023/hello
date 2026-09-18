# image_capture.py
from PIL import ImageGrab

# Example fixed boxes (replace with dynamic logic as needed)
NAME_BOXES = [
    (445, 395, 537, 487),  # Example enemy icon 1
    (445, 491, 537, 583),
    (445, 587, 537, 679),
    (445, 683, 537, 775),
    (445, 779, 537, 871),
    (445, 875, 537, 967),

    (1325, 395, 1417, 487),  # Example enemy icon 1
    (1325, 491, 1417, 583),
    (1325, 587, 1417, 679),
    (1325, 683, 1417, 775),
    (1325, 779, 1417, 871),
    (1325, 875, 1417, 967)
]

def capture_scoreboard_icons(region_box, name_boxes=NAME_BOXES):
    """Captures a region of the screen and crops hero icons."""
    full_img = ImageGrab.grab(bbox=region_box)  # Use pyautogui or mss on Linux if needed
    cropped_icons = []

    for box in name_boxes:
        x1, y1, x2, y2 = box
        cropped = full_img.crop((x1 - region_box[0], y1 - region_box[1], x2 - region_box[0], y2 - region_box[1]))
        cropped_icons.append(cropped)

    return cropped_icons
