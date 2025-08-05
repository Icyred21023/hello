import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, "type_matchup.json")  # Output JSON file
JSON_PATH = os.path.join(script_dir, "matchup.json")      # JSON file with character keys
IMAGE_FOLDER = os.path.join(script_dir, "assets_characters")     # Folder where PNGs are stored



# === GUI CLASS ===
class CharacterTaggerApp:
    def __init__(self, root, characters, image_folder):

        self.root = root
        self.characters = list(characters.keys())
        self.data = characters
        self.image_folder = image_folder
        self.index = 0
        self.copy = self.data.copy()

        self.root.title("Character Tagger")
        self.root.geometry("400x400")

        self.left_frame = tk.Frame(root, width=200, height=400)
        self.right_frame = tk.Frame(root, width=200, height=400)
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame.pack(side="right", fill="both")

        self.image_label = None
        self.name_label = None
        self.current_image = None

        self.create_right_buttons()
        self.display_current_character()

    def create_right_buttons(self):
        options = ["Dive", "Dive / Brawl", "Brawl", "Brawl / Poke", "Poke"]
        for option in options:
            btn = tk.Button(self.right_frame, text=option, width=20,
                            command=lambda opt=option: self.select_category(opt))
            btn.pack(pady=5)

    def display_current_character(self):
        # Clear left frame
        for widget in self.left_frame.winfo_children():
            widget.destroy()

        if self.index >= len(self.characters):
            tk.Label(self.left_frame, text="All characters tagged!").pack(pady=20)
            return

        name = self.characters[self.index]
        self.name_label = tk.Label(self.left_frame, text=name, font=("Arial", 16))
        self.name_label.pack(pady=10)

        img_path = os.path.join(self.image_folder, f"{name}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            img.thumbnail((150, 150))
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label = tk.Label(self.left_frame, image=self.current_image)
            self.image_label.pack()
        else:
            self.image_label = tk.Label(self.left_frame, text="Image not found")
            self.image_label.pack()

    # === PLACEHOLDER FUNCTION (you will write this) ===
    def on_category_selected(self, character_name, category):
        self.copy[character_name]["category"] = category
        # Put your logic here, e.g., updating JSON, saving elsewhere, etc.

    def select_category(self, category):
        if self.index >= len(self.characters):
            print(self.copy)
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.copy, f, indent=4, ensure_ascii=False)
            return

        current_name = self.characters[self.index]
        self.on_category_selected(current_name, category)

        self.index += 1
        self.display_current_character()



# === MAIN PROGRAM ===
if __name__ == "__main__":
    # Load JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        characters = json.load(f)

    # Create window
    root = tk.Tk()
    app = CharacterTaggerApp(root, characters, IMAGE_FOLDER)
    root.mainloop()
