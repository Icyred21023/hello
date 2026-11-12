import os
import shutil
import tkinter as tk
from tkinter import filedialog


def get_png_files(directory):
    """Return a set of PNG filenames found directly inside directory."""
    return {
        filename
        for filename in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, filename))
        and filename.lower().endswith(".png")
    }


def main():
    root = tk.Tk()
    root.withdraw()

    print("Select first directory...")
    dir1 = filedialog.askdirectory(title="Select First Directory")

    if not dir1:
        print("No first directory selected.")
        return

    print("Select second directory...")
    dir2 = filedialog.askdirectory(title="Select Second Directory")

    if not dir2:
        print("No second directory selected.")
        return

    files1 = get_png_files(dir1)
    files2 = get_png_files(dir2)

    if len(files1) > len(files2):
        bigger = files1
        smaller = files2
        bigger_dir = dir1
    else:
        bigger = files2
        smaller = files1
        bigger_dir = dir2

    diff = []

    for f in bigger:
        if f not in smaller:
            diff.append(f)

    for i, f in enumerate(diff):
        print(f"{i + 1}. {f}")

    if not diff:
        print("No different files found.")
        return

    print("\nSelect directory to copy the different files to...")
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if not output_dir:
        print("No output directory selected.")
        return

    for f in diff:
        src = os.path.join(bigger_dir, f)
        dst = os.path.join(output_dir, f)

        shutil.copy2(src, dst)
        print(f"Copied: {f}")

    print(f"\nCopied {len(diff)} files to:")
    print(output_dir)


if __name__ == "__main__":
    main()