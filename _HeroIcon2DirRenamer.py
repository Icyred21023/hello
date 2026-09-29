import os
import tkinter as tk
from tkinter import filedialog
import helpers
import config
def get_png_files(directory):
    return sorted(
        [
            f for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
            and f.lower().endswith(".png")
        ],
        key=str.lower
    )


def main():
    root = tk.Tk()
    root.withdraw()

    dir1 = filedialog.askdirectory(title="Select Directory 1 - Files To Rename")
    if not dir1:
        print("No Directory 1 selected.")
        return

    #dir2 = filedialog.askdirectory(title="Select Directory 2 - Filename Source")
    #if not dir2:
       # print("No Directory 2 selected.")
       # return

    files1 = get_png_files(dir1)
    #files2 = get_png_files(dir2)

    print(f"\nDirectory 1 PNG count: {len(files1)}")
    #print(f"Directory 2 PNG count: {len(files2)}")

    #if len(files1) != len(files2):
        #print("\nERROR: The directories do not contain the same number of PNG files.")
       # return

    # Temporary rename first to avoid filename collisions.
    temp_files = {}

    for i, old_name in enumerate(files1):
        old_path = os.path.join(dir1, old_name)
        #hero_id = old_name.split("_")[-1][1:5]
        hero_id = old_name.split("_")[2][0:4]
        hero_name = config.HERO_KEYS.get(hero_id, {}).get("name", None)
        
        if not hero_name:
            print(f"ERROR: Hero ID '{hero_id}' not found in HERO_KEYS.")
            continue 
        try:
            new_name = f"{hero_name}_icon3.png"
        except Exception as e:
            print(f"ERROR: Failed to create new name for '{old_name}': {e}")
            continue
        
        new_path = os.path.join(dir1, new_name)

        if os.path.exists(new_path):
            print(f"ERROR: Target already exists: {new_name}")
            continue

        os.rename(old_path, new_path)

    # # Rename temporary files to matching filenames from Directory 2.
    # for i, temp_name in enumerate(temp_files):
    #     temp_path = os.path.join(dir1, temp_name)

    #     new_name = files2[i]
    #     new_path = os.path.join(dir1, new_name)

    #     os.rename(temp_path, new_path)

    #     print(f"{i + 1}. {files1[i]}  ->  {new_name}")

    # print("\nDone.")
    # print(f"Renamed {len(files1)} files.")


if __name__ == "__main__":
    main()