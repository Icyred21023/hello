import os
import tkinter as tk
from tkinter import filedialog


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

    dir2 = filedialog.askdirectory(title="Select Directory 2 - Filename Source")
    if not dir2:
        print("No Directory 2 selected.")
        return

    files1 = get_png_files(dir1)
    files2 = get_png_files(dir2)

    print(f"\nDirectory 1 PNG count: {len(files1)}")
    print(f"Directory 2 PNG count: {len(files2)}")

    if len(files1) != len(files2):
        print("\nERROR: The directories do not contain the same number of PNG files.")
        return

    # Temporary rename first to avoid filename collisions.
    temp_files = []

    for i, old_name in enumerate(files1):
        old_path = os.path.join(dir1, old_name)

        temp_name = f"__TEMP_RENAME_{i:05d}__.png"
        temp_path = os.path.join(dir1, temp_name)

        os.rename(old_path, temp_path)
        temp_files.append(temp_name)

    # Rename temporary files to matching filenames from Directory 2.
    for i, temp_name in enumerate(temp_files):
        temp_path = os.path.join(dir1, temp_name)

        new_name = files2[i]
        new_path = os.path.join(dir1, new_name)

        os.rename(temp_path, new_path)

        print(f"{i + 1}. {files1[i]}  ->  {new_name}")

    print("\nDone.")
    print(f"Renamed {len(files1)} files.")


if __name__ == "__main__":
    main()