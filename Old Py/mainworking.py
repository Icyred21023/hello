# main.py
import keyboard
import time
from ocr_capture import capture_names
from tracker_lookup import get_tracker_stats_api



print(">> Script running. Press F8 to OCR names and check tracker.gg...")

while True:
    keyboard.wait("F8")  # Blocks here until F8 is pressed
    names = capture_names()

    print("\n🎯 Captured Player Names:")
    for name in names:
        print(f"- {name}")

    print("\n🔎 Tracker.gg Profile URLs:")
    for name in names:
        if name:
            get_tracker_stats_api(name)
        else:
            print("[Empty OCR result]")
    
    print("\n✅ Done. Press F8 again to repeat...")
    time.sleep(1.5)

