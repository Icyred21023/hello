import os
import shutil
import tkinter as tk
from tkinter import filedialog

import helpers
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
    dir1 = filedialog.askopenfilenames(title="Files")

    heroes = []
    for file_path in dir1:



if __name__ == "__main__":
    main()