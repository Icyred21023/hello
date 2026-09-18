#!/usr/bin/env python3
"""
Sprite Sheet Cell Editor / Animator / Exporter

Requires: Pillow (pip install pillow)

- Load one PNG sprite sheet.
- Define rows/columns with integer-only cell boundaries.
- Inspect/edit every cell crop rectangle.
- Animate or step frame-by-frame.
- Set integer FPS and integer scale percentage.
- While paused, shift each frame locally while preserving its cell dimensions;
  vacated pixels are transparent RGBA (0,0,0,0).
- Export offset-applied unscaled/scaled cells, rebuilt unscaled/scaled sheets,
  a source PNG copy, and full JSON metadata.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError as exc:
    raise SystemExit("Pillow is required. Install it with: pip install pillow") from exc

APP_TITLE = "Sprite Sheet Cell Editor"
BG = "#151426"
PANEL = "#1d1c30"
PANEL_2 = "#24223b"
TEXT = "#f5f5f7"
MUTED = "#a9a8b5"
ACCENT = "#fcd92e"
ENTRY_BG = "#2c2a45"
CANVAS_BG = "#101019"


@dataclass
class Cell:
    index: int
    row: int
    col: int
    x0: int
    y0: int
    x1: int
    y1: int
    dx: int = 0
    dy: int = 0

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


class SpriteSheetEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1500x900")
        self.root.minsize(1180, 720)
        self.root.configure(bg=BG)

        self.image_path: Optional[Path] = None
        self.original_image: Optional[Image.Image] = None
        self.cells: list[Cell] = []
        self.grid_rows = 0
        self.grid_cols = 0
        self.selected_index = 0
        self.playing = False
        self.after_id: Optional[str] = None
        self.preview_photo: Optional[ImageTk.PhotoImage] = None
        self.sheet_photo: Optional[ImageTk.PhotoImage] = None

        self.rows_var = tk.IntVar(value=10)
        self.cols_var = tk.IntVar(value=6)
        self.fps_var = tk.IntVar(value=12)
        self.scale_var = tk.IntVar(value=100)
        self.x0_var = tk.IntVar(value=0)
        self.y0_var = tk.IntVar(value=0)
        self.x1_var = tk.IntVar(value=1)
        self.y1_var = tk.IntVar(value=1)
        self.dx_var = tk.IntVar(value=0)
        self.dy_var = tk.IntVar(value=0)
        self.file_var = tk.StringVar(value="No PNG loaded")
        self.frame_info_var = tk.StringVar(value="Load a PNG to begin.")
        self.status_var = tk.StringVar(value="Ready")

        self._setup_ttk()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _setup_ttk(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dark.Treeview", background=PANEL_2, fieldbackground=PANEL_2,
                        foreground=TEXT, rowheight=24, borderwidth=0)
        style.configure("Dark.Treeview.Heading", background="#302e49", foreground=TEXT, relief="flat")
        style.map("Dark.Treeview", background=[("selected", "#5a4f20")], foreground=[("selected", "#ffffff")])

    def _label(self, parent, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=TEXT)

    def _button(self, parent, text: str, command, width: Optional[int] = None) -> tk.Button:
        kw = dict(text=text, command=command, bg=ACCENT, fg="#151426",
                  activebackground="#c7ac25", activeforeground="#151426",
                  relief="flat", cursor="hand2", padx=8, pady=4)
        if width is not None:
            kw["width"] = width
        return tk.Button(parent, **kw)

    def _spin(self, parent, variable: tk.IntVar, from_: int, to: int, width: int = 7) -> tk.Spinbox:
        return tk.Spinbox(parent, from_=from_, to=to, textvariable=variable, width=width,
                          bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT, buttonbackground=PANEL_2,
                          relief="flat", highlightthickness=1,
                          highlightbackground="#3a3857", highlightcolor=ACCENT)

    def _section_title(self, parent, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg="#11101b", fg=TEXT, anchor="w",
                        padx=8, pady=6, font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 6))
        self._button(top, "Load PNG", self.load_png).pack(side="left", padx=(0, 8))
        tk.Label(top, textvariable=self.file_var, bg=BG, fg=TEXT, anchor="w").pack(
            side="left", fill="x", expand=True, padx=(0, 10))
        self._label(top, "Rows").pack(side="left", padx=(6, 3))
        self._spin(top, self.rows_var, 1, 200, 5).pack(side="left")
        self._label(top, "Cols").pack(side="left", padx=(8, 3))
        self._spin(top, self.cols_var, 1, 200, 5).pack(side="left")
        self._button(top, "Build Grid", self.build_grid).pack(side="left", padx=8)
        self._button(top, "Export All", self.export_all).pack(side="left", padx=(0, 2))

        controls = tk.Frame(self.root, bg=PANEL)
        controls.pack(fill="x", padx=10, pady=(0, 8))
        self._button(controls, "◀ Prev", self.prev_frame).pack(side="left", padx=(8, 3), pady=7)
        self.play_button = self._button(controls, "▶ Play", self.toggle_play)
        self.play_button.pack(side="left", padx=3, pady=7)
        self._button(controls, "Next ▶", self.next_frame).pack(side="left", padx=3, pady=7)
        self._label(controls, "FPS").pack(side="left", padx=(14, 4))
        fps_spin = self._spin(controls, self.fps_var, 1, 120, 5)
        fps_spin.pack(side="left")
        fps_spin.bind("<Return>", lambda e: self._restart_animation_if_playing())
        self._label(controls, "Scale %").pack(side="left", padx=(14, 4))
        scale_spin = self._spin(controls, self.scale_var, 1, 1000, 6)
        scale_spin.pack(side="left")
        scale_spin.bind("<Return>", lambda e: self.refresh_preview())
        scale_spin.bind("<FocusOut>", lambda e: self.refresh_preview())
        self._button(controls, "Apply Scale Preview", self.refresh_preview).pack(side="left", padx=(5, 10))
        self._label(controls, "All crop/offset coordinates are integer pixels.").pack(side="left", padx=8)

        body = tk.PanedWindow(self.root, orient="horizontal", sashwidth=6, bg=BG, bd=0, relief="flat")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        left, center, right = (tk.Frame(body, bg=PANEL) for _ in range(3))
        body.add(left, minsize=430)
        body.add(center, minsize=430)
        body.add(right, minsize=430)

        self._section_title(left, "Sprite Sheet / Selected Cell").pack(fill="x")
        self.sheet_canvas = tk.Canvas(left, bg=CANVAS_BG, highlightthickness=0)
        self.sheet_canvas.pack(fill="both", expand=True, padx=8, pady=8)

        self._section_title(center, "Frame Preview").pack(fill="x")
        self.preview_canvas = tk.Canvas(center, bg=CANVAS_BG, highlightthickness=0, height=430)
        self.preview_canvas.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        tk.Label(center, textvariable=self.frame_info_var, bg=PANEL, fg=TEXT, justify="left",
                 anchor="w", font=("Consolas", 10)).pack(fill="x", padx=10, pady=(2, 8))

        editor = tk.LabelFrame(center, text=" Selected Frame — integer pixels only ",
                               bg=PANEL, fg=TEXT, bd=1, relief="solid", padx=8, pady=8)
        editor.pack(fill="x", padx=8, pady=(0, 8))
        coord_grid = tk.Frame(editor, bg=PANEL)
        coord_grid.pack(fill="x")
        defs = [("x0", self.x0_var, 0, 0), ("y0", self.y0_var, 0, 2),
                ("x1", self.x1_var, 1, 0), ("y1", self.y1_var, 1, 2)]
        for text, var, row, col in defs:
            self._label(coord_grid, text).grid(row=row, column=col, sticky="e", padx=(4, 4), pady=3)
            self._spin(coord_grid, var, -100000, 100000, 9).grid(row=row, column=col + 1, sticky="w", padx=(0, 10), pady=3)
        self._button(coord_grid, "Apply Rect", self.apply_rect).grid(row=0, column=4, rowspan=2, padx=8, sticky="ns")
        self._button(coord_grid, "Reset Cell", self.reset_current_rect).grid(row=0, column=5, rowspan=2, padx=4, sticky="ns")

        offset_frame = tk.Frame(editor, bg=PANEL)
        offset_frame.pack(fill="x", pady=(10, 0))
        self._label(offset_frame, "Local X").pack(side="left", padx=(4, 4))
        self._spin(offset_frame, self.dx_var, -100000, 100000, 8).pack(side="left")
        self._label(offset_frame, "Y").pack(side="left", padx=(10, 4))
        self._spin(offset_frame, self.dy_var, -100000, 100000, 8).pack(side="left")
        self._button(offset_frame, "Apply Offset", self.apply_offset).pack(side="left", padx=8)
        self._button(offset_frame, "←", lambda: self.nudge(-1, 0), 3).pack(side="left", padx=2)
        self._button(offset_frame, "→", lambda: self.nudge(1, 0), 3).pack(side="left", padx=2)
        self._button(offset_frame, "↑", lambda: self.nudge(0, -1), 3).pack(side="left", padx=2)
        self._button(offset_frame, "↓", lambda: self.nudge(0, 1), 3).pack(side="left", padx=2)
        tk.Label(editor, text="Offsets are editable only while paused. Vacated pixels are RGBA (0,0,0,0); cell size stays fixed.",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left").pack(fill="x", pady=(8, 0))

        self._section_title(right, "Cell Coordinates").pack(fill="x")
        table_wrap = tk.Frame(right, bg=PANEL)
        table_wrap.pack(fill="both", expand=True, padx=8, pady=8)
        columns = ("frame", "row", "col", "x0", "y0", "x1", "y1", "w", "h", "dx", "dy")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Dark.Treeview", selectmode="browse")
        headings = {"frame": "#", "row": "R", "col": "C", "x0": "x0", "y0": "y0", "x1": "x1", "y1": "y1", "w": "W", "h": "H", "dx": "dX", "dy": "dY"}
        widths = {"frame": 42, "row": 38, "col": 38, "x0": 58, "y0": 58, "x1": 58, "y1": 58, "w": 52, "h": 52, "dx": 48, "dy": 48}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=35, anchor="center", stretch=False)
        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        right_buttons = tk.Frame(right, bg=PANEL)
        right_buttons.pack(fill="x", padx=8, pady=(0, 8))
        self._button(right_buttons, "Reset All", self.reset_all).pack(side="left")
        self._button(right_buttons, "Export All", self.export_all).pack(side="right")

        tk.Label(self.root, textvariable=self.status_var, bg="#11101b", fg=MUTED,
                 anchor="w", padx=8).pack(fill="x", side="bottom")
        self.sheet_canvas.bind("<Configure>", lambda e: self.refresh_sheet_view())
        self.preview_canvas.bind("<Configure>", lambda e: self.refresh_preview())

    # ---------- load/grid ----------
    def load_png(self) -> None:
        path = filedialog.askopenfilename(title="Select sprite sheet PNG", filetypes=[("PNG images", "*.png")])
        if not path:
            return
        try:
            img = Image.open(path)
            img.load()
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return
        self.stop_animation()
        self.image_path = Path(path)
        self.original_image = img.convert("RGBA")
        self.file_var.set(f"{self.image_path.name} — {self.original_image.width}×{self.original_image.height}")
        self.build_grid()

    @staticmethod
    def integer_bounds(total: int, count: int) -> list[int]:
        return [(i * total) // count for i in range(count + 1)]

    def build_grid(self) -> None:
        if self.original_image is None:
            messagebox.showinfo("No image", "Load a PNG first.")
            return
        try:
            rows, cols = int(self.rows_var.get()), int(self.cols_var.get())
        except Exception:
            messagebox.showerror("Invalid grid", "Rows and columns must be whole numbers.")
            return
        if rows <= 0 or cols <= 0 or rows > self.original_image.height or cols > self.original_image.width:
            messagebox.showerror("Invalid grid", "Rows/columns must be positive and cannot exceed image pixel dimensions.")
            return
        self.stop_animation()
        xs = self.integer_bounds(self.original_image.width, cols)
        ys = self.integer_bounds(self.original_image.height, rows)
        self.grid_rows = rows
        self.grid_cols = cols
        self.cells = []
        idx = 0
        for r in range(rows):
            for c in range(cols):
                self.cells.append(Cell(idx, r, c, xs[c], ys[r], xs[c+1], ys[r+1]))
                idx += 1
        self.selected_index = 0
        self.refresh_tree()
        self.select_frame(0)
        self.status_var.set(f"Built {rows}×{cols} grid = {len(self.cells)} frames with integer-only boundaries.")

    def default_rect_for_cell(self, cell: Cell) -> tuple[int, int, int, int]:
        xs = self.integer_bounds(self.original_image.width, self.grid_cols)
        ys = self.integer_bounds(self.original_image.height, self.grid_rows)
        return xs[cell.col], ys[cell.row], xs[cell.col+1], ys[cell.row+1]

    # ---------- cell selection/edit ----------
    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for c in self.cells:
            self.tree.insert("", "end", iid=str(c.index), values=(c.index+1, c.row+1, c.col+1,
                c.x0, c.y0, c.x1, c.y1, c.width, c.height, c.dx, c.dy))

    def update_tree_row(self, c: Cell) -> None:
        if self.tree.exists(str(c.index)):
            self.tree.item(str(c.index), values=(c.index+1, c.row+1, c.col+1,
                c.x0, c.y0, c.x1, c.y1, c.width, c.height, c.dx, c.dy))

    def on_tree_select(self, event=None) -> None:
        sel = self.tree.selection()
        if sel:
            self.select_frame(int(sel[0]), sync_tree=False)

    def select_frame(self, index: int, sync_tree: bool = True) -> None:
        if not self.cells:
            return
        self.selected_index = max(0, min(index, len(self.cells)-1))
        c = self.cells[self.selected_index]
        self.x0_var.set(c.x0); self.y0_var.set(c.y0); self.x1_var.set(c.x1); self.y1_var.set(c.y1)
        self.dx_var.set(c.dx); self.dy_var.set(c.dy)
        if sync_tree and self.tree.exists(str(c.index)):
            self.tree.selection_set(str(c.index)); self.tree.focus(str(c.index)); self.tree.see(str(c.index))
        self.refresh_preview(); self.refresh_sheet_view()

    def validate_rect(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        if x0 < 0 or y0 < 0 or x1 > self.original_image.width or y1 > self.original_image.height:
            messagebox.showerror("Invalid rectangle", f"Keep the rect inside 0..{self.original_image.width} × 0..{self.original_image.height}.")
            return False
        if x1 <= x0 or y1 <= y0:
            messagebox.showerror("Invalid rectangle", "x1 must be > x0 and y1 must be > y0.")
            return False
        return True

    def apply_rect(self) -> None:
        if not self.cells:
            return
        try:
            x0, y0, x1, y1 = map(int, (self.x0_var.get(), self.y0_var.get(), self.x1_var.get(), self.y1_var.get()))
        except Exception:
            messagebox.showerror("Invalid values", "Coordinates must be whole numbers.")
            return
        if not self.validate_rect(x0, y0, x1, y1):
            return
        c = self.cells[self.selected_index]
        c.x0, c.y0, c.x1, c.y1 = x0, y0, x1, y1
        self.update_tree_row(c); self.refresh_preview(); self.refresh_sheet_view()
        self.status_var.set(f"Frame {c.index+1}: crop rectangle updated.")

    def apply_offset(self) -> None:
        if not self.cells:
            return
        if self.playing:
            messagebox.showinfo("Pause first", "Pause the animation before adjusting frame position.")
            return
        try:
            dx, dy = int(self.dx_var.get()), int(self.dy_var.get())
        except Exception:
            messagebox.showerror("Invalid values", "Offsets must be whole numbers.")
            return
        c = self.cells[self.selected_index]
        c.dx, c.dy = dx, dy
        self.update_tree_row(c); self.refresh_preview()

    def nudge(self, dx: int, dy: int) -> None:
        if not self.cells:
            return
        if self.playing:
            messagebox.showinfo("Pause first", "Pause the animation before nudging frames.")
            return
        c = self.cells[self.selected_index]
        c.dx += int(dx); c.dy += int(dy)
        self.dx_var.set(c.dx); self.dy_var.set(c.dy)
        self.update_tree_row(c); self.refresh_preview()

    def reset_current_rect(self) -> None:
        if not self.cells:
            return
        c = self.cells[self.selected_index]
        c.x0, c.y0, c.x1, c.y1 = self.default_rect_for_cell(c)
        c.dx = c.dy = 0
        self.update_tree_row(c); self.select_frame(c.index)

    def reset_all(self) -> None:
        if self.cells and messagebox.askyesno("Reset all", "Reset all crop rectangles and offsets?"):
            self.build_grid()

    # ---------- frame processing ----------
    def get_cell_crop(self, c: Cell) -> Image.Image:
        return self.original_image.crop((c.x0, c.y0, c.x1, c.y1)).convert("RGBA")

    @staticmethod
    def apply_local_offset(image: Image.Image, dx: int, dy: int) -> Image.Image:
        out = Image.new("RGBA", image.size, (0, 0, 0, 0))
        out.alpha_composite(image, dest=(int(dx), int(dy)))
        return out

    def get_processed_cell(self, c: Cell, scaled: bool) -> Image.Image:
        img = self.apply_local_offset(self.get_cell_crop(c), c.dx, c.dy)
        if scaled:
            p = max(1, int(self.scale_var.get()))
            nw = max(1, (img.width * p + 50) // 100)
            nh = max(1, (img.height * p + 50) // 100)
            if (nw, nh) != img.size:
                img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        return img

    @staticmethod
    def checkerboard(w: int, h: int, tile: int = 14) -> Image.Image:
        img = Image.new("RGBA", (max(1,w), max(1,h)), (55,55,65,255))
        d = ImageDraw.Draw(img)
        a, b = (55,55,65,255), (80,80,92,255)
        for y in range(0, h, tile):
            for x in range(0, w, tile):
                d.rectangle((x,y,x+tile-1,y+tile-1), fill=a if ((x//tile)+(y//tile))%2==0 else b)
        return img

    # ---------- preview ----------
    def refresh_preview(self) -> None:
        if self.original_image is None or not self.cells:
            self.preview_canvas.delete("all")
            return
        try:
            p = max(1, min(int(self.scale_var.get()), 1000))
        except Exception:
            p = 100
        self.scale_var.set(p)
        c = self.cells[self.selected_index]
        raw = self.get_processed_cell(c, False)
        scaled = self.get_processed_cell(c, True)
        cw, ch = max(50,self.preview_canvas.winfo_width()), max(50,self.preview_canvas.winfo_height())
        display = scaled
        max_w, max_h = max(1,cw-40), max(1,ch-40)
        if display.width > max_w or display.height > max_h:
            fit = min(max_w*10000//display.width, max_h*10000//display.height)
            dw, dh = max(1,display.width*fit//10000), max(1,display.height*fit//10000)
            display = display.resize((dw, dh), Image.Resampling.NEAREST)
        bg = self.checkerboard(cw, ch)
        bg.alpha_composite(display, ((cw-display.width)//2, (ch-display.height)//2))
        self.preview_photo = ImageTk.PhotoImage(bg)
        self.preview_canvas.delete("all"); self.preview_canvas.create_image(0,0,anchor="nw",image=self.preview_photo)
        self.frame_info_var.set(
            f"Frame {c.index+1}/{len(self.cells)}   Grid R{c.row+1} C{c.col+1}\n"
            f"Crop [x0,y0,x1,y1): [{c.x0}, {c.y0}, {c.x1}, {c.y1}]   Source size: {raw.width}×{raw.height}\n"
            f"Local offset: dx={c.dx}, dy={c.dy}   Scale: {p}%   Scaled size: {scaled.width}×{scaled.height}")

    def refresh_sheet_view(self) -> None:
        if self.original_image is None:
            self.sheet_canvas.delete("all"); return
        cw, ch = max(50,self.sheet_canvas.winfo_width()), max(50,self.sheet_canvas.winfo_height())
        iw, ih = self.original_image.size
        fit = max(1, min(cw*10000//iw, ch*10000//ih))
        dw, dh = max(1,iw*fit//10000), max(1,ih*fit//10000)
        display = self.original_image.resize((dw, dh), Image.Resampling.NEAREST)
        self.sheet_photo = ImageTk.PhotoImage(display)
        self.sheet_canvas.delete("all")
        ox, oy = (cw-dw)//2, (ch-dh)//2
        self.sheet_canvas.create_image(ox,oy,anchor="nw",image=self.sheet_photo)
        for c in self.cells:
            x0, y0 = ox+c.x0*fit//10000, oy+c.y0*fit//10000
            x1, y1 = ox+c.x1*fit//10000, oy+c.y1*fit//10000
            sel = c.index == self.selected_index
            self.sheet_canvas.create_rectangle(x0,y0,x1,y1,outline=ACCENT if sel else "#7c7a91",width=3 if sel else 1)

    # ---------- animation ----------
    def toggle_play(self) -> None:
        self.stop_animation() if self.playing else self.start_animation()

    def start_animation(self) -> None:
        if self.cells:
            self.playing = True; self.play_button.config(text="⏸ Pause"); self._schedule_next()

    def stop_animation(self) -> None:
        self.playing = False
        if hasattr(self, "play_button"):
            self.play_button.config(text="▶ Play")
        if self.after_id is not None:
            try: self.root.after_cancel(self.after_id)
            except tk.TclError: pass
            self.after_id = None

    def _restart_animation_if_playing(self) -> None:
        if self.playing:
            self.stop_animation(); self.start_animation()

    def _schedule_next(self) -> None:
        if not self.playing: return
        try: fps = max(1, min(int(self.fps_var.get()), 120))
        except Exception: fps = 12
        self.fps_var.set(fps)
        self.after_id = self.root.after(max(1,1000//fps), self._animation_tick)

    def _animation_tick(self) -> None:
        if self.playing and self.cells:
            self.select_frame((self.selected_index+1) % len(self.cells)); self._schedule_next()

    def prev_frame(self) -> None:
        self.stop_animation()
        if self.cells: self.select_frame((self.selected_index-1) % len(self.cells))

    def next_frame(self) -> None:
        self.stop_animation()
        if self.cells: self.select_frame((self.selected_index+1) % len(self.cells))

    # ---------- export ----------
    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def pack_grid(frames: list[Image.Image], cells: list[Cell], rows: int, cols: int) -> tuple[Image.Image, dict[int, dict]]:
        col_widths, row_heights = [0]*cols, [0]*rows
        for img, c in zip(frames, cells):
            col_widths[c.col] = max(col_widths[c.col], img.width)
            row_heights[c.row] = max(row_heights[c.row], img.height)
        xs, ys = [0], [0]
        for w in col_widths: xs.append(xs[-1]+w)
        for h in row_heights: ys.append(ys[-1]+h)
        sheet = Image.new("RGBA", (max(1,xs[-1]), max(1,ys[-1])), (0,0,0,0))
        slots = {}
        for img, c in zip(frames, cells):
            x, y = xs[c.col], ys[c.row]
            sheet.alpha_composite(img, dest=(x,y))
            slots[c.index] = {"x0":x,"y0":y,"x1":x+img.width,"y1":y+img.height,
                              "width":img.width,"height":img.height,
                              "slot_width":col_widths[c.col],"slot_height":row_heights[c.row]}
        return sheet, slots

    def export_all(self) -> None:
        if self.original_image is None or self.image_path is None or not self.cells:
            messagebox.showinfo("Nothing to export", "Load a PNG and build the grid first."); return
        self.stop_animation()
        folder = filedialog.askdirectory(title="Select output folder")
        if not folder: return
        out = Path(folder); un_dir = out/"cells_unscaled"; sc_dir = out/"cells_scaled"
        un_dir.mkdir(parents=True, exist_ok=True); sc_dir.mkdir(parents=True, exist_ok=True)
        rows, cols = self.grid_rows, self.grid_cols
        if rows <= 0 or cols <= 0:
            messagebox.showerror("Invalid grid", "Build the grid before exporting."); return
        scale = max(1,int(self.scale_var.get())); fps = max(1,int(self.fps_var.get()))
        un_frames, sc_frames, meta_cells = [], [], []
        for c in self.cells:
            un, sc = self.get_processed_cell(c,False), self.get_processed_cell(c,True)
            name = f"frame_{c.index+1:04d}_r{c.row+1:02d}_c{c.col+1:02d}.png"
            un.save(un_dir/name); sc.save(sc_dir/name)
            un_frames.append(un); sc_frames.append(sc)
            meta_cells.append({
                "index_zero_based":c.index, "frame_number_one_based":c.index+1,
                "row_zero_based":c.row, "column_zero_based":c.col,
                "crop_rect_xyxy_exclusive":{"x0":c.x0,"y0":c.y0,"x1":c.x1,"y1":c.y1},
                "source_cell_size":{"width":c.width,"height":c.height},
                "local_offset_pixels":{"dx":c.dx,"dy":c.dy},
                "unscaled_output_size":{"width":un.width,"height":un.height},
                "scaled_output_size":{"width":sc.width,"height":sc.height},
                "files":{"unscaled":str(Path("cells_unscaled")/name),"scaled":str(Path("cells_scaled")/name)}})
        un_sheet, un_slots = self.pack_grid(un_frames,self.cells,rows,cols)
        sc_sheet, sc_slots = self.pack_grid(sc_frames,self.cells,rows,cols)
        stem = self.image_path.stem
        un_sheet_path = out/f"{stem}_reassembled_unscaled.png"
        sc_sheet_path = out/f"{stem}_reassembled_scaled_{scale}pct.png"
        un_sheet.save(un_sheet_path); sc_sheet.save(sc_sheet_path)
        original_copy = out/f"{stem}_original.png"; shutil.copy2(self.image_path, original_copy)
        for m in meta_cells:
            i = m["index_zero_based"]
            m["reassembled_unscaled_sheet_rect"] = un_slots[i]
            m["reassembled_scaled_sheet_rect"] = sc_slots[i]
        metadata = {
            "format_version":1, "application":APP_TITLE,
            "coordinate_rules":{"all_coordinates_are_integer_pixels":True,
                "crop_rect_xyxy_is_half_open":True,
                "crop_rect_description":"[x0, y0, x1, y1), width=x1-x0, height=y1-y0",
                "local_offset_keeps_cell_dimensions":True,
                "exposed_offset_area_rgba":[0,0,0,0]},
            "original_image":{"source_filename":self.image_path.name,
                "source_path":str(self.image_path.resolve()),"copied_file":original_copy.name,
                "width":self.original_image.width,"height":self.original_image.height,
                "mode_used_for_processing":"RGBA","sha256":self.sha256_file(self.image_path)},
            "grid":{"rows":rows,"columns":cols,"frame_count":len(self.cells),
                "initial_partition_method":"boundary[i] = (i * total_pixels) // count",
                "frame_order":"row-major"},
            "animation_preview":{"fps":fps},
            "scaling":{"percent_integer":scale,"resize_filter":"Pillow LANCZOS",
                "dimension_rounding":"nearest integer using (dimension*percent + 50)//100"},
            "exports":{"unscaled_cells_folder":"cells_unscaled","scaled_cells_folder":"cells_scaled",
                "unscaled_reassembled_sheet":un_sheet_path.name,"scaled_reassembled_sheet":sc_sheet_path.name,
                "unscaled_reassembled_sheet_size":{"width":un_sheet.width,"height":un_sheet.height},
                "scaled_reassembled_sheet_size":{"width":sc_sheet.width,"height":sc_sheet.height}},
            "cells":meta_cells}
        meta_path = out/f"{stem}_sprite_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self.status_var.set(f"Export complete: {out}")
        messagebox.showinfo("Export complete", f"Saved {len(self.cells)} unscaled + {len(self.cells)} scaled cells, 2 rebuilt sheets, original copy, and JSON metadata.")

    def close(self) -> None:
        self.stop_animation(); self.root.destroy()


def main() -> None:
    root = tk.Tk()
    SpriteSheetEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
