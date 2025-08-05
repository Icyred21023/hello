import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

class JsonEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JSON Editor – dps / hps / health")
        self.geometry("780x520")
        self.minsize(680, 420)

        # State
        self.data = {}
        self.current_file = None
        self.current_key = None

        # Layout: two panes
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_menu()
        self._build_left()
        self._build_right()
        self._build_status()

    # ---------- UI BUILDERS ----------
    def _build_menu(self):
        m = tk.Menu(self)
        filem = tk.Menu(m, tearoff=0)
        filem.add_command(label="Open…", command=self.open_file)
        filem.add_separator()
        filem.add_command(label="Save", command=self.save_file, state="disabled")
        filem.add_command(label="Save As…", command=self.save_as, state="disabled")
        filem.add_separator()
        filem.add_command(label="Exit", command=self.destroy)
        m.add_cascade(label="File", menu=filem)
        self.config(menu=m)
        self.file_menu = filem

    def _build_left(self):
        left = tk.Frame(self, bd=1, relief="sunken")
        left.grid(row=1, column=0, sticky="nsw")
        left.grid_propagate(False)
        left.configure(width=250)
        left.rowconfigure(1, weight=1)

        tk.Label(left, text="Items", anchor="w", padx=8, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="ew")
        self.listbox = tk.Listbox(left, exportselection=False)
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        sb = tk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=sb.set)

    def _build_right(self):
        right = tk.Frame(self, padx=12, pady=12)
        right.grid(row=1, column=1, sticky="nsew")
        for i in range(2):
            right.columnconfigure(i, weight=(1 if i == 1 else 0))

        # Header
        self.title_label = tk.Label(right, text="No item selected", font=("Segoe UI", 12, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Editable fields
        self.fields = {}
        row = 1
        for key in ("dps", "hps", "health"):
            tk.Label(right, text=key, font=("Segoe UI", 10)).grid(row=row, column=0, sticky="e", pady=6, padx=(0, 8))
            var = tk.StringVar()
            entry = tk.Entry(right, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            self.fields[key] = var
            row += 1

        # Buttons
        btns = tk.Frame(right)
        btns.grid(row=row, column=0, columnspan=2, sticky="w", pady=(16, 0))
        tk.Button(btns, text="Apply to Current", command=self.apply_current).pack(side="left")
        tk.Button(btns, text="Revert", command=self.revert_current).pack(side="left", padx=8)

    def _build_status(self):
        self.status = tk.StringVar(value="Open a JSON file to begin.")
        bar = tk.Label(self, textvariable=self.status, bd=1, relief="sunken", anchor="w")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")

    # ---------- FILE OPS ----------
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                messagebox.showerror("Error", "Top-level JSON must be an object (dict).")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open:\n{e}")
            return

        self.data = data
        self.current_file = path
        self.current_key = None
        self._populate_listbox()
        self._clear_fields()
        self._set_status(f"Opened: {os.path.basename(path)}")
        self.file_menu.entryconfig("Save", state="normal")
        self.file_menu.entryconfig("Save As…", state="normal")

    def save_file(self):
        if not self.current_file:
            return self.save_as()
        # create backup
        try:
            backup = self.current_file + ".bak"
            if os.path.exists(self.current_file):
                with open(self.current_file, "rb") as src, open(backup, "wb") as dst:
                    dst.write(src.read())
        except Exception as e:
            # Non-fatal
            self._set_status(f"Warning: could not backup: {e}")

        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self._set_status(f"Saved: {os.path.basename(self.current_file)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def save_as(self):
        if not self.data:
            return
        path = filedialog.asksaveasfilename(
            title="Save JSON As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        self.current_file = path
        self.save_file()

    # ---------- LIST / SELECTION ----------
    def _populate_listbox(self):
        self.listbox.delete(0, tk.END)
        # sort keys alphabetically
        for k in sorted(self.data.keys(), key=str.lower):
            self.listbox.insert(tk.END, k)

    def on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        key = self.listbox.get(sel[0])
        self.current_key = key
        self.title_label.config(text=key)
        self.revert_current()
        self._set_status(f"Selected: {key}")

    # ---------- APPLY / REVERT ----------
    def apply_current(self):
        if not self.current_key:
            return
        node = self.data.get(self.current_key, {})
        if not isinstance(node, dict):
            messagebox.showerror("Error", f"Item '{self.current_key}' is not an object.")
            return
        try:
            # Convert to numbers (int if exact, else float)
            for k in ("dps", "hps", "health"):
                raw = self.fields[k].get().strip()
                if raw == "":
                    # allow empty -> remove the key (optional behavior)
                    if k in node: del node[k]
                    continue
                num = float(raw)
                if num.is_integer():
                    num = int(num)
                node[k] = num
            self._set_status(f"Applied changes to: {self.current_key}")
        except ValueError:
            messagebox.showerror("Invalid value", "Please enter numeric values for dps, hps, and health.")

    def revert_current(self):
        if not self.current_key:
            self._clear_fields()
            return
        node = self.data.get(self.current_key, {})
        # Fill from JSON; if missing, show empty
        for k in ("dps", "hps", "health"):
            val = node.get(k, "")
            self.fields[k].set("" if val == "" else str(val))

    # ---------- UTILS ----------
    def _clear_fields(self):
        self.title_label.config(text="No item selected")
        for var in self.fields.values():
            var.set("")

    def _set_status(self, msg):
        self.status.set(msg)

if __name__ == "__main__":
    app = JsonEditor()
    app.mainloop()
