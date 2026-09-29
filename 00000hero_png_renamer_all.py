import os

# ------------------------------------------------------------------
# GLOBAL DIRECTORY
# ------------------------------------------------------------------
DIRECTORY = r"C:\Users\Chloroform\Documents\_fGuiDesign\New Heads 2\Photoshopped"


def rename_pngs():
    for filename in os.listdir(DIRECTORY):

        # Only PNG files containing "_p"
        if filename.lower().endswith(".png") and "_p" in filename:

            old_path = os.path.join(DIRECTORY, filename)

            new_filename = filename.replace("_p", "_l")
            new_path = os.path.join(DIRECTORY, new_filename)

            os.rename(old_path, new_path)

            print(f"Renamed: {filename} -> {new_filename}")


if __name__ == "__main__":
    rename_pngs()