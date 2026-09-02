from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

try:
    import config
except Exception as exc:  # Show a GUI error instead of closing immediately.
    config = None
    CONFIG_IMPORT_ERROR = exc
else:
    CONFIG_IMPORT_ERROR = None


# -----------------------------------------------------------------------------
# SETTINGS
# -----------------------------------------------------------------------------

HERO_DIRECTORY = Path(
    r"C:\Users\Chloroform\Desktop\MarvelBans\fGui Assets\Heroes"
)

# The viewer checks Heroes\mastery first, then Heroes itself. This supports both
# layouts without changing the filename-generation rule.
SEARCH_DIRECTORIES = (
    HERO_DIRECTORY / "mastery",
    HERO_DIRECTORY,
)

SHEET_WIDTH = 966
SHEET_HEIGHT = 1840
COLUMNS = 6
ROWS = 10
FRAME_WIDTH = SHEET_WIDTH // COLUMNS       # 161
FRAME_HEIGHT = SHEET_HEIGHT // ROWS        # 184
FRAME_COUNT = COLUMNS * ROWS               # 60

DISPLAY_SCALE = 1.0
DEFAULT_FPS = 30.0
SUPPORTED_EXTENSIONS = (".png", ".webp", ".jpg", ".jpeg")


def get_mastery_names() -> list[str]:
    """Return config.HERO_KEYS['name'] entries with duplicates removed."""
    if config is None:
        raise RuntimeError(f"Could not import config.py:\n{CONFIG_IMPORT_ERROR}")
    name_dict = {"name":[]}
    try:
        l = []
        for key in config.HERO_KEYS:
            n = config.HERO_KEYS[key]["name"]
            l.append(n)
        name_dict["name"] = l
            
            
        configured_names = name_dict["name"]
    except (AttributeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            'config.HERO_KEYS must contain an iterable under the key "name".'
        ) from exc

    if isinstance(configured_names, str):
        configured_names = [configured_names]

    names: list[str] = []
    seen: set[str] = set()

    for value in configured_names:
        name = str(value).strip()
        normalized = name.casefold()
        if name and normalized not in seen:
            seen.add(normalized)
            names.append(name)

    return names


def find_sheet(hero_name: str) -> Path | None:
    """Find <hero_name>0 with a supported image extension."""
    filename_stem = f"{hero_name}0"

    for directory in SEARCH_DIRECTORIES:
        for extension in SUPPORTED_EXTENSIONS:
            candidate = directory / f"{filename_stem}{extension}"
            if candidate.is_file():
                return candidate

    return None


def collect_sheets() -> tuple[list[tuple[str, Path]], list[str]]:
    sheets: list[tuple[str, Path]] = []
    missing: list[str] = []

    for hero_name in get_mastery_names():
        sheet_path = find_sheet(hero_name)
        if sheet_path is None:
            missing.append(hero_name)
        else:
            sheets.append((hero_name, sheet_path))

    return sheets, missing


class MasterySheetViewer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mastery Sprite Sheet Viewer")
        self.root.configure(background="#151821")
        self.root.resizable(False, False)

        self.sheets, self.missing_names = collect_sheets()
        if not self.sheets:
            searched = "\n".join(str(path) for path in SEARCH_DIRECTORIES)
            raise RuntimeError(
                "No mastery sprite sheets were found.\n\n"
                f"Directories searched:\n{searched}"
            )

        self.sheet_index = 0
        self.frame_index = 0
        self.frames: list[ImageTk.PhotoImage] = []
        self.playing = False
        self.after_id: str | None = None
        self.fps = DEFAULT_FPS

        self.display_size = (
            round(FRAME_WIDTH * DISPLAY_SCALE),
            round(FRAME_HEIGHT * DISPLAY_SCALE),
        )

        self._build_ui()
        self._bind_keys()
        self.load_current_sheet()
        self.play()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Viewer.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
        )
        style.configure(
            "Viewer.TLabel",
            background="#151821",
            foreground="#f1f3f7",
            font=("Segoe UI", 10),
        )

        top = ttk.Frame(self.root, padding=(16, 14, 16, 8))
        top.pack(fill="x")

        self.hero_label = ttk.Label(
            top,
            text="",
            style="Viewer.TLabel",
            font=("Segoe UI", 16, "bold"),
            anchor="center",
        )
        self.hero_label.pack(fill="x")

        self.path_label = ttk.Label(
            top,
            text="",
            style="Viewer.TLabel",
            foreground="#9da6b8",
            anchor="center",
        )
        self.path_label.pack(fill="x", pady=(3, 0))

        canvas_width = self.display_size[0] + 40
        canvas_height = self.display_size[1] + 40
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_width,
            height=canvas_height,
            background="#090b10",
            highlightthickness=1,
            highlightbackground="#3b4252",
        )
        self.canvas.pack(padx=16, pady=8)

        self.image_item = self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
        )

        self.frame_label = ttk.Label(
            self.root,
            text="Frame 1 / 60",
            style="Viewer.TLabel",
            anchor="center",
        )
        self.frame_label.pack(fill="x", pady=(3, 8))

        controls = ttk.Frame(self.root, padding=(16, 0, 16, 8))
        controls.pack(fill="x")

        ttk.Button(
            controls,
            text="◀ Sheet",
            style="Viewer.TButton",
            command=self.previous_sheet,
        ).grid(row=0, column=0, padx=3)

        ttk.Button(
            controls,
            text="◀ Frame",
            style="Viewer.TButton",
            command=self.previous_frame,
        ).grid(row=0, column=1, padx=3)

        self.play_button = ttk.Button(
            controls,
            text="⏸ Pause",
            style="Viewer.TButton",
            command=self.toggle_play,
        )
        self.play_button.grid(row=0, column=2, padx=3)

        ttk.Button(
            controls,
            text="Frame ▶",
            style="Viewer.TButton",
            command=self.next_frame,
        ).grid(row=0, column=3, padx=3)

        ttk.Button(
            controls,
            text="Sheet ▶",
            style="Viewer.TButton",
            command=self.next_sheet,
        ).grid(row=0, column=4, padx=3)

        speed_row = ttk.Frame(self.root, padding=(16, 0, 16, 10))
        speed_row.pack(fill="x")

        ttk.Label(
            speed_row,
            text="FPS:",
            style="Viewer.TLabel",
        ).pack(side="left")

        self.fps_var = tk.DoubleVar(value=DEFAULT_FPS)
        self.fps_scale = ttk.Scale(
            speed_row,
            from_=1,
            to=60,
            variable=self.fps_var,
            command=self.set_fps,
        )
        self.fps_scale.pack(side="left", fill="x", expand=True, padx=8)

        self.fps_label = ttk.Label(
            speed_row,
            text=f"{DEFAULT_FPS:.0f}",
            style="Viewer.TLabel",
            width=3,
            anchor="e",
        )
        self.fps_label.pack(side="right")

        missing_text = (
            f"Loaded {len(self.sheets)} sheets"
            f" • Missing {len(self.missing_names)}"
            " • Space: play/pause • ←/→: frame • ↑/↓: sheet"
        )
        self.status_label = ttk.Label(
            self.root,
            text=missing_text,
            style="Viewer.TLabel",
            foreground="#8d96a8",
            anchor="center",
        )
        self.status_label.pack(fill="x", padx=16, pady=(0, 13))

    def _bind_keys(self) -> None:
        self.root.bind("<space>", lambda _event: self.toggle_play())
        self.root.bind("<Left>", lambda _event: self.previous_frame())
        self.root.bind("<Right>", lambda _event: self.next_frame())
        self.root.bind("<Up>", lambda _event: self.previous_sheet())
        self.root.bind("<Down>", lambda _event: self.next_sheet())
        self.root.bind("<Home>", lambda _event: self.go_to_frame(0, pause=True))
        self.root.bind(
            "<End>",
            lambda _event: self.go_to_frame(FRAME_COUNT - 1, pause=True),
        )

    def _splice_sheet(self, path: Path) -> list[ImageTk.PhotoImage]:
        with Image.open(path) as opened:
            sheet = opened.convert("RGBA").copy()

        expected_size = (SHEET_WIDTH, SHEET_HEIGHT)
        if sheet.size != expected_size:
            raise ValueError(
                f"{path.name} is {sheet.width}x{sheet.height}; "
                f"expected {SHEET_WIDTH}x{SHEET_HEIGHT}."
            )

        resampling = getattr(Image, "Resampling", Image)
        frames: list[ImageTk.PhotoImage] = []

        for row in range(ROWS):
            top = row * FRAME_HEIGHT
            for column in range(COLUMNS):
                left = column * FRAME_WIDTH
                frame = sheet.crop(
                    (
                        left,
                        top,
                        left + FRAME_WIDTH,
                        top + FRAME_HEIGHT,
                    )
                )
                if frame.size != self.display_size:
                    frame = frame.resize(self.display_size, resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(frame, master=self.root))

        return frames

    def load_current_sheet(self) -> None:
        hero_name, path = self.sheets[self.sheet_index]

        try:
            new_frames = self._splice_sheet(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not load sprite sheet", str(exc))
            return

        # Update the canvas before releasing the previous sheet's PhotoImages.
        old_frames = self.frames
        self.frames = new_frames
        self.frame_index = 0
        self.canvas.itemconfigure(
            self.image_item,
            image=self.frames[self.frame_index],
        )
        old_frames.clear()

        self.hero_label.configure(
            text=f"{hero_name}  ({self.sheet_index + 1} / {len(self.sheets)})"
        )
        self.path_label.configure(text=str(path))
        self._update_frame_label()

    def _update_frame_label(self) -> None:
        row = self.frame_index // COLUMNS + 1
        column = self.frame_index % COLUMNS + 1
        self.frame_label.configure(
            text=(
                f"Frame {self.frame_index + 1} / {FRAME_COUNT}"
                f"    •    Row {row}, Column {column}"
            )
        )

    def go_to_frame(self, index: int, *, pause: bool = False) -> None:
        if not self.frames:
            return
        if pause:
            self.pause()

        self.frame_index = int(index) % len(self.frames)
        self.canvas.itemconfigure(
            self.image_item,
            image=self.frames[self.frame_index],
        )
        self._update_frame_label()

    def previous_frame(self) -> None:
        self.go_to_frame(self.frame_index - 1, pause=True)

    def next_frame(self) -> None:
        self.go_to_frame(self.frame_index + 1, pause=True)

    def _change_sheet(self, amount: int) -> None:
        resume_after_load = self.playing
        self.pause()
        self.sheet_index = (self.sheet_index + amount) % len(self.sheets)
        self.load_current_sheet()
        if resume_after_load:
            self.play()

    def previous_sheet(self) -> None:
        self._change_sheet(-1)

    def next_sheet(self) -> None:
        self._change_sheet(1)

    def play(self) -> None:
        if self.playing or not self.frames:
            return
        self.playing = True
        self.play_button.configure(text="⏸ Pause")
        self._schedule_tick()

    def pause(self) -> None:
        self.playing = False
        self.play_button.configure(text="▶ Play")
        self._cancel_tick()

    def toggle_play(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def _schedule_tick(self) -> None:
        if self.playing and self.after_id is None:
            delay_ms = max(1, round(1000 / self.fps))
            self.after_id = self.root.after(delay_ms, self._tick)

    def _cancel_tick(self) -> None:
        if self.after_id is None:
            return
        try:
            self.root.after_cancel(self.after_id)
        except tk.TclError:
            pass
        self.after_id = None

    def _tick(self) -> None:
        self.after_id = None
        if not self.playing:
            return
        self.go_to_frame(self.frame_index + 1)
        self._schedule_tick()

    def set_fps(self, value: str) -> None:
        self.fps = max(1.0, float(value))
        self.fps_label.configure(text=f"{self.fps:.0f}")
        if self.playing:
            self._cancel_tick()
            self._schedule_tick()

    def close(self) -> None:
        self.pause()
        self.frames.clear()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        MasterySheetViewer(root)
    except Exception as exc:
        messagebox.showerror("Mastery Sprite Sheet Viewer", str(exc), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
