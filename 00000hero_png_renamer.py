import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import config


PNG_DIR = r"C:\Users\Chloroform\Desktop\MarvelBans\fGui Assets\Heroes\Photoshopped"

PREVIEW_MAX_W = 650
PREVIEW_MAX_H = 650

# Number of hero names visible when the dropdown is opened.
COMBO_DROPDOWN_HEIGHT = 25


def collect_pngs(root_dir):
    """Recursively collect all PNG files once at startup."""
    pngs = []

    for root, dirs, files in os.walk(root_dir):
        dirs.sort()
        files.sort()

        for filename in files:
            if filename.lower().endswith(".png"):
                pngs.append(os.path.join(root, filename))

    return pngs


def build_hero_name_list():
    """
    Build list from:
        config.HERO_KEYS[key]["name"]

    Then sort alphabetically, case-insensitive.
    """
    names = []

    for key in config.HERO_KEYS:
        try:
            name = str(config.HERO_KEYS[key]["name"]).strip()
            if name:
                names.append(name)
        except (KeyError, TypeError):
            print(
                f"Skipping HERO_KEYS entry {key!r}: "
                f"missing/invalid ['name']"
            )

    # Remove exact duplicates, then sort alphabetically.
    names = sorted(set(names), key=str.casefold)

    return names


class HeroPngRenamer:
    def __init__(self, root):
        self.root = root
        self.root.title("Hero PNG Renamer")
        self.root.configure(bg="#202020")

        if not os.path.isdir(PNG_DIR):
            messagebox.showerror(
                "Directory Not Found",
                f"PNG directory does not exist:\n\n{PNG_DIR}"
            )
            self.root.destroy()
            return

        self.png_files = collect_pngs(PNG_DIR)
        self.hero_names = build_hero_name_list()

        if not self.hero_names:
            messagebox.showerror(
                "No Hero Names",
                "config.HERO_KEYS did not contain any usable ['name'] entries."
            )
            self.root.destroy()
            return

        self.index = 0
        self.preview_photo = None

        # Persistent controls.
        self.selected_name = tk.StringVar(value="")
        self.lord_var = tk.BooleanVar(value=False)

        self._build_gui()

        if self.png_files:
            self.show_current_png()
        else:
            self.show_finished("No PNG files were found.")


    # ========================================================
    # GUI
    # ========================================================

    def _build_gui(self):
        main = tk.Frame(
            self.root,
            bg="#202020",
            padx=12,
            pady=12
        )
        main.pack(fill="both", expand=True)

        # ----------------------------------------------------
        # LEFT CONTROLS
        # ----------------------------------------------------

        controls = tk.Frame(
            main,
            bg="#292929",
            padx=15,
            pady=15
        )
        controls.pack(
            side="left",
            fill="y",
            padx=(0, 12)
        )

        tk.Label(
            controls,
            text="Hero Name",
            bg="#292929",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(
            anchor="w",
            pady=(0, 6)
        )

        tk.Label(
            controls,
            text="Type to filter:",
            bg="#292929",
            fg="#bdbdbd",
            font=("Arial", 9)
        ).pack(
            anchor="w",
            pady=(0, 3)
        )

        # Editable combobox:
        # - user can type into it
        # - KeyRelease filters the dropdown values
        # - height makes the dropdown much taller
        self.hero_combo = ttk.Combobox(
            controls,
            textvariable=self.selected_name,
            values=self.hero_names,
            state="normal",
            width=32,
            height=COMBO_DROPDOWN_HEIGHT
        )
        self.hero_combo.pack(
            anchor="w",
            fill="x"
        )

        self.hero_combo.bind(
            "<KeyRelease>",
            self.filter_hero_list
        )

        # When the user picks an item, restore the complete list
        # so filtering doesn't permanently alter available entries.
        self.hero_combo.bind(
            "<<ComboboxSelected>>",
            self.on_hero_selected
        )

        self.lord_check = tk.Checkbutton(
            controls,
            text="Lord?",
            variable=self.lord_var,
            bg="#292929",
            fg="white",
            activebackground="#292929",
            activeforeground="white",
            selectcolor="#202020",
            font=("Arial", 11)
        )
        self.lord_check.pack(
            anchor="w",
            pady=(12, 12)
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        button_row = tk.Frame(
            controls,
            bg="#292929"
        )
        button_row.pack(
            anchor="w",
            fill="x",
            pady=(0, 12)
        )

        self.rename_btn = tk.Button(
            button_row,
            text="Rename",
            command=self.rename_current,
            font=("Arial", 11, "bold")
        )
        self.rename_btn.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 4)
        )

        self.skip_btn = tk.Button(
            button_row,
            text="Skip",
            command=self.skip_current,
            font=("Arial", 11)
        )
        self.skip_btn.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(4, 0)
        )

        self.progress_label = tk.Label(
            controls,
            text="",
            bg="#292929",
            fg="#cfcfcf",
            justify="left",
            anchor="w",
            wraplength=260
        )
        self.progress_label.pack(
            anchor="w",
            fill="x",
            pady=(10, 0)
        )

        self.filename_label = tk.Label(
            controls,
            text="",
            bg="#292929",
            fg="white",
            justify="left",
            anchor="w",
            wraplength=260
        )
        self.filename_label.pack(
            anchor="w",
            fill="x",
            pady=(10, 0)
        )

        # ----------------------------------------------------
        # IMAGE PREVIEW
        # ----------------------------------------------------

        preview_frame = tk.Frame(
            main,
            bg="#111111",
            width=PREVIEW_MAX_W,
            height=PREVIEW_MAX_H
        )
        preview_frame.pack(
            side="left",
            fill="both",
            expand=True
        )
        preview_frame.pack_propagate(False)

        self.preview_label = tk.Label(
            preview_frame,
            bg="#111111",
            fg="white",
            text=""
        )
        self.preview_label.pack(
            fill="both",
            expand=True
        )


    # ========================================================
    # HERO FILTERING
    # ========================================================

    def filter_hero_list(self, event=None):
        """
        Filter combobox entries based on what the user typed.

        Matching is case-insensitive and checks whether the typed
        text occurs anywhere in the hero name.
        """
        typed = self.selected_name.get().strip()

        if not typed:
            filtered = self.hero_names
        else:
            typed_lower = typed.casefold()

            filtered = [
                name
                for name in self.hero_names
                if typed_lower in name.casefold()
            ]

        self.hero_combo["values"] = filtered


    def on_hero_selected(self, event=None):
        """
        After selecting a hero, restore the full alphabetized list.

        The currently selected name remains in the entry.
        """
        self.hero_combo["values"] = self.hero_names


    # ========================================================
    # CURRENT PNG
    # ========================================================

    def current_path(self):
        if 0 <= self.index < len(self.png_files):
            return self.png_files[self.index]

        return None


    def show_current_png(self):
        path = self.current_path()

        if path is None:
            self.show_finished("All PNGs have been processed.")
            return

        try:
            with Image.open(path) as img:
                img = img.convert("RGBA")

                original_size = img.size

                preview = img.copy()
                preview.thumbnail(
                    (PREVIEW_MAX_W, PREVIEW_MAX_H),
                    Image.Resampling.LANCZOS
                )

            self.preview_photo = ImageTk.PhotoImage(preview)

            self.preview_label.configure(
                image=self.preview_photo,
                text=""
            )

            self.progress_label.configure(
                text=(
                    f"Image {self.index + 1} / "
                    f"{len(self.png_files)}\n"
                    f"Original size: "
                    f"{original_size[0]} x {original_size[1]}"
                )
            )

            self.filename_label.configure(
                text=os.path.basename(path)
            )

            self.rename_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")

        except Exception as e:
            messagebox.showerror(
                "Preview Error",
                f"Could not open:\n\n{path}\n\n{e}"
            )


    # ========================================================
    # RENAME
    # ========================================================

    def rename_current(self):
        old_path = self.current_path()

        if old_path is None:
            return

        selected = self.selected_name.get().strip()

        if not selected:
            messagebox.showwarning(
                "No Hero Selected",
                "Select a hero name first."
            )
            return

        # Because the combobox is editable for filtering, make
        # sure the typed text corresponds to a real HERO_KEYS name.
        exact_match = None

        for hero_name in self.hero_names:
            if hero_name.casefold() == selected.casefold():
                exact_match = hero_name
                break

        if exact_match is None:
            messagebox.showwarning(
                "Select a Valid Hero",
                "The text in the hero box is only a filter or does "
                "not exactly match a hero name.\n\n"
                "Select a name from the dropdown before renaming."
            )
            return

        selected = exact_match

        new_base = selected

        # Lord checkbox intentionally persists between PNGs.
        if self.lord_var.get():
            new_base += "_l"

        new_filename = new_base + ".png"

        old_dir = os.path.dirname(old_path)
        new_path = os.path.join(
            old_dir,
            new_filename
        )

        if os.path.normcase(old_path) == os.path.normcase(new_path):
            print(f"[UNCHANGED] {old_path}")
            self.advance()
            return

        if os.path.exists(new_path):
            messagebox.showerror(
                "File Already Exists",
                "Cannot rename because this file already exists:\n\n"
                f"{new_path}"
            )
            return

        try:
            print(
                "[RENAME]\n"
                f"  FROM: {old_path}\n"
                f"  TO:   {new_path}"
            )

            os.rename(
                old_path,
                new_path
            )

        except Exception as e:
            messagebox.showerror(
                "Rename Failed",
                f"Could not rename:\n\n"
                f"{old_path}\n\n"
                f"to:\n\n"
                f"{new_path}\n\n"
                f"{e}"
            )
            return

        self.advance()


    # ========================================================
    # SKIP
    # ========================================================

    def skip_current(self):
        path = self.current_path()

        if path is None:
            return

        print(
            f"[SKIP] {path}"
        )

        self.advance()


    # ========================================================
    # NEXT
    # ========================================================

    def advance(self):
        self.index += 1
        self.show_current_png()


    # ========================================================
    # FINISHED
    # ========================================================

    def show_finished(self, message):
        self.preview_photo = None

        self.preview_label.configure(
            image="",
            text=message,
            font=("Arial", 16, "bold"),
            fg="white"
        )

        self.progress_label.configure(
            text=(
                f"Processed {self.index} / "
                f"{len(self.png_files)}"
            )
        )

        self.filename_label.configure(
            text=""
        )

        self.rename_btn.configure(
            state="disabled"
        )

        self.skip_btn.configure(
            state="disabled"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = HeroPngRenamer(root)
    root.mainloop()