import tkinter as tk
from tkinter import ttk

import config
import helpers
from PIL import ImageTk, Image
import os


class DPSCalculatorApp:
    BASE_LEFT_W = 425
    BASE_H = 850
    BASE_CANVAS_W = int(850 * 0.55)

    def __init__(self, root):
        self.root = root
        self.root.title("DPS Calculator")
        self.root.configure(bg="#1e1e1e")

        # Android/Pydroid reports screen pixels differently than Windows.
        # Build everything from one scale value so fonts, padding, panels,
        # canvas, and hero image all shrink together.
        self.base_w = self.BASE_LEFT_W + self.BASE_CANVAS_W
        self.base_h = self.BASE_H
        screen_w = max(1, self.root.winfo_screenwidth())
        screen_h = max(1, self.root.winfo_screenheight())

        # Never scale up on desktop. Only shrink to fit small/Android screens.
        self.scale = min(screen_w / self.base_w, screen_h / self.base_h, 1.0)

        self.app_w = self.S(self.base_w)
        self.app_h = self.S(self.base_h)
        self.left_w = self.S(self.BASE_LEFT_W)
        self.canvas_w = self.S(self.BASE_CANVAS_W)

        self.root.geometry(f"{self.app_w}x{self.app_h}")
        self.root.minsize(self.S(300), self.S(500))
        self.root.resizable(True, True)

        self.hero_canvas_item = None
        self.hero_photo = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TLabel",
            background="#1e1e1e",
            foreground="#ffffff",
            font=("Segoe UI", self.font_size(11)),
        )
        style.configure(
            "Dark2.TLabel",
            background="#1e1e1e",
            foreground="#ffffff",
            font=("Segoe UI", self.font_size(11), "bold"),
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground="#924D4D",
            background="#52bd38",
            foreground="#3c9fb1",
            font=("Segoe UI", self.font_size(10), "bold"),
        )

        self.hero_config_path = helpers.create_path("_blood_hunt_json.json", "debug")
        self.json_hero_config = helpers.load_json(self.hero_config_path)

        self.asset_dir = os.path.join(config.script_dir, "assets_exp")

        self.main_frame = tk.Frame(root, bg="#1e1e1e")
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.grid_columnconfigure(0, minsize=self.left_w, weight=0)
        self.main_frame.grid_columnconfigure(1, minsize=self.canvas_w, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.left_panel = tk.Frame(
            self.main_frame,
            bg="#1e1e1e",
            width=self.left_w,
            height=self.app_h,
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.grid_propagate(True)

        self.right_canvas = tk.Canvas(
            self.main_frame,
            width=self.canvas_w,
            height=self.app_h,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.right_canvas.grid(row=0, column=1, sticky="nsew")

        self.container = tk.Frame(self.left_panel, bg="#1e1e1e")
        self.container.pack(
            padx=(self.S(14), self.S(4)),
            pady=self.S(12),
            fill="both",
            expand=True,
        )
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_columnconfigure(2, weight=1)
        self.container.grid_columnconfigure(3, weight=1)
        self.container.grid_rowconfigure(1, weight=0)
        self.container.grid_rowconfigure(3, weight=1)

        self.characters = ["Moon Knight", "Thor"]
        self.character_var = tk.StringVar(value="Moon Knight")

        self.input_labels_by_character = {
            "Moon Knight": [
                "Total Damage Bonus",
                "Total Output Boost",
                "Boss Damage Bonus",
                "Critical Hit Rate",
                "Critical Hit Multiplier",
                "Precision Hit Rate",
                "Precision Hit Multiplier",
                "Lunar Glide Hit Interval",
            ],
            "Thor": [
                "Total Damage Bonus",
                "Total Output Boost",
                "Critical Hit Rate",
                "Critical Hit Multiplier",
                "Precision Hit Rate",
                "Precision Hit Multiplier",
                "High-Speed Shock Enhancement",
                "High-Voltage Field Enhancement",
                "Rune Onslaught Enhancement",
            ],
        }

        self.result_labels_by_character = {
            "Moon Knight": [
                "Critical DPS",
                "Precision DPS",
                "Boss DPS",
                "Total DPS",
                "Critical Damage",
                "Precision Damage",
                "Boss Damage",
                "Total Damage",
            ],
            "Thor": [
                "Lightning Fire Rate",
                "Lightning Base Attack Speed",
                "Lightning Base Damage",
                "Lightning Base DPS",
                "Lightning Critical Damage",
                "Lightning Critical DPS",
                "Lightning Precision Damage",
                "Lightning Precision DPS",
                "Lightning Total DPS",
            ],
        }

        ttk.Label(self.container, text="Character", style="Dark.TLabel").grid(
            row=0, column=0, sticky="w", pady=self.S(4)
        )

        self.character_combo = ttk.Combobox(
            self.container,
            textvariable=self.character_var,
            values=self.characters,
            state="readonly",
            foreground="#0f0f0f",
            background="#f8f8f8",
            width=14,
            takefocus=0,
            font=("Segoe UI", self.font_size(10), "bold"),
        )
        self.character_combo.grid(
            row=0,
            column=1,
            pady=self.S(4),
            padx=self.S(6),
            sticky="ew",
        )
        self.character_combo.bind("<<ComboboxSelected>>", self.on_character_changed)

        self.input_frame = tk.Frame(self.container, bg="#1e1e1e")
        self.input_frame.grid(row=1, column=0, columnspan=4, sticky="nsew")

        self.save_button = tk.Button(
            self.container,
            text="Save Entered Stats",
            command=self.save_current_character_fields,
            state="disabled",
            bg="#1A1A1A",
            disabledforeground="#FF9797",
            foreground="#a6ff9b",
            activebackground="#0E0E0E",
            activeforeground="#5d8f62",
            font=("Segoe UI", self.font_size(10), "bold"),
            relief="raised",
            bd=max(1, self.S(2)),
            padx=self.S(8),
            pady=self.S(4),
        )
        self.save_button.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=(self.S(8), 0),
        )

        self.results_frame = tk.Frame(self.container, bg="#1e1e1e")
        self.results_frame.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="nsew",
            pady=(self.S(10), 0),
        )

        self.entries = {}
        self.result_vars = {}

        self.build_inputs()
        self.build_results()
        self.update_results()
        self.update_save_button_state()
        self.render_hero_image()

        # Re-render hero image when user resizes window / Android changes viewport.
        self.root.bind("<Configure>", self.on_root_resize)

    def S(self, value):
        return max(1, int(value * self.scale))

    def font_size(self, value):
        return max(7, int(value * self.scale))

    def on_root_resize(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        self.render_hero_image()

    def render_hero_image(self):
        if self.hero_canvas_item is not None:
            self.right_canvas.delete(self.hero_canvas_item)
            self.hero_canvas_item = None

        canvas_w = max(1, self.right_canvas.winfo_width())
        canvas_h = max(1, self.right_canvas.winfo_height())

        hero_image = self.load_image(self.character_var.get(), canvas_w, canvas_h)

        y = canvas_h
        x = 0
        if self.character_var.get() == "Moon Knight":
            y = min(canvas_h, self.S(792))
            x = self.S(30)

        self.hero_canvas_item = self.right_canvas.create_image(
            x,
            y,
            anchor="sw",
            image=hero_image,
        )

        self.hero_photo = hero_image
        self.right_canvas.image = hero_image

    def load_image(self, hero, canvas_w=None, canvas_h=None):
        path = os.path.join(self.asset_dir, hero + ".png")
        imgraw = Image.open(path)

        canvas_w = canvas_w or self.canvas_w
        canvas_h = canvas_h or self.app_h

        # Keep the hero image proportional and fit it to the available canvas.
        target = max(canvas_w, canvas_h)
        target = max(1, int(target))
        imgraw.thumbnail((target, target), Image.BICUBIC)

        return ImageTk.PhotoImage(imgraw)

    def on_character_changed(self, event=None):
        self.build_inputs()
        self.build_results()
        self.clear_results()
        self.update_results()
        self.update_save_button_state()
        self.render_hero_image()

        self.character_combo.selection_clear()
        self.root.focus()

    def return_saved_label_value(self, label, hero_data):
        if not hero_data:
            return ""

        return str(hero_data.get(label, ""))

    def build_inputs(self):
        for widget in self.input_frame.winfo_children():
            widget.destroy()

        self.entries = {}
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(1, weight=1)
        labels = self.input_labels_by_character[self.character_var.get()]
        if not self.json_hero_config:
            self.json_hero_config = {
                "Moon Knight": False,
                "Thor": False,
            }

        for row, label_text in enumerate(labels):
            loaded_string = self.return_saved_label_value(
                label_text,
                self.json_hero_config.get(self.character_var.get(), False),
            )
            ttk.Label(
                self.input_frame,
                text=label_text,
                style="Dark.TLabel",
            ).grid(row=row, column=0, sticky="w", pady=self.S(4))

            entry_var = tk.StringVar(value=loaded_string)

            entry_wrap = tk.Frame(
                self.input_frame,
                bg="#1A1A1A",
                bd=max(1, self.S(2)),
                relief="sunken",
            )
            entry_wrap.grid(
                row=row,
                column=1,
                pady=self.S(4),
                padx=self.S(6),
                sticky="ew",
            )
            entry_wrap.grid_columnconfigure(0, weight=1)

            entry = tk.Entry(
                entry_wrap,
                textvariable=entry_var,
                bg="#1A1A1A",
                fg="#ffffff",
                insertbackground="#ffffff",
                font=("Segoe UI", self.font_size(10), "bold"),
                justify="right",
                width=8,
                relief="flat",
                bd=0,
            )
            entry.grid(row=0, column=0, sticky="ew", padx=(self.S(4), self.S(2)), pady=self.S(3))

            if "Interval" not in label_text:
                tk.Label(
                    entry_wrap,
                    text="%",
                    bg="#1A1A1A",
                    fg="#aaaaaa",
                    font=("Segoe UI", self.font_size(10), "bold"),
                ).grid(row=0, column=1, sticky="e", padx=(self.S(1), self.S(2)))

            entry_var.trace_add("write", self.on_entry_changed)
            self.entries[label_text] = entry_var

    def build_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(1, weight=1)

        self.result_vars = {}

        labels = self.result_labels_by_character[self.character_var.get()]

        for row, label_text in enumerate(labels):
            ttk.Label(
                self.results_frame,
                text=label_text,
                style="Dark2.TLabel",
            ).grid(row=row, column=0, sticky="w", pady=self.S(4), padx=(0, self.S(6)))

            var = tk.StringVar(value="0")
            self.result_vars[label_text] = var

            tk.Label(
                self.results_frame,
                textvariable=var,
                bg="#111111",
                fg="#00ff99" if "Total" in label_text else "#efff97",
                font=("Segoe UI", self.font_size(10), "bold"),
                relief="sunken",
                bd=max(1, self.S(2)),
                padx=self.S(8),
                pady=self.S(3),
                width=12,
                anchor="e",
            ).grid(row=row, column=1, sticky="ew", padx=(0, 0))

    def on_entry_changed(self, *args):
        self.update_save_button_state()
        self.update_results()

    def all_fields_entered(self):
        for var in self.entries.values():
            value = var.get().strip()

            if value == "":
                return False

            try:
                float(value)
            except ValueError:
                return False

        return True

    def update_save_button_state(self):
        if self.all_fields_entered():
            self.save_button.config(state="normal")
        else:
            self.save_button.config(state="disabled")

    def get_current_character_json_data(self):
        return {
            label: float(var.get())
            for label, var in self.entries.items()
        }

    def save_current_character_fields(self):
        data = self.get_current_character_json_data()
        hero = self.character_var.get()

        self.json_hero_config[hero] = data
        helpers.save_json(self.hero_config_path, self.json_hero_config)

    def get_value(self, label):
        return float(self.entries[label].get())

    def calculate_moon_knight_values(self):
        total_damage_bonus = 1 + self.get_value("Total Damage Bonus") / 100
        boss_damage_bonus = total_damage_bonus + self.get_value("Boss Damage Bonus")/100
        total_output_boost = 1 + self.get_value("Total Output Boost") / 100
        critical_hit_rate = self.get_value("Critical Hit Rate") / 100
        critical_hit_multiplier = 1 + self.get_value("Critical Hit Multiplier") / 100
        precision_hit_rate = self.get_value("Precision Hit Rate") / 100
        precision_hit_multiplier = 1 + self.get_value("Precision Hit Multiplier") / 100
        lunar_glide_hit_interval = self.get_value("Lunar Glide Hit Interval")

        hitpersecond = 1 / lunar_glide_hit_interval
        base_hit_rate = 1 - (critical_hit_rate + precision_hit_rate)

        base_dps = total_damage_bonus * total_output_boost * 143 * base_hit_rate * hitpersecond * 21.3
        critical_dps = total_damage_bonus * total_output_boost * 143 * critical_hit_multiplier * critical_hit_rate * hitpersecond * 21.3
        precision_dps = total_damage_bonus * total_output_boost * 143 * precision_hit_multiplier * precision_hit_rate * hitpersecond * 21.3

        total_dps = base_dps + critical_dps + precision_dps
        total_boss_dps = base_dps/total_damage_bonus*boss_damage_bonus + critical_dps / total_damage_bonus*boss_damage_bonus+precision_dps/total_damage_bonus*boss_damage_bonus

        base_d = total_damage_bonus * total_output_boost * 143 * 21.3
        critical_d = base_d * critical_hit_multiplier
        precision_d = base_d * precision_hit_multiplier
        crit_b = critical_d/total_damage_bonus*boss_damage_bonus
        total_d = base_d + critical_d + precision_d
        total_boss = crit_b#base_d/total_damage_bonus*boss_damage_bonus+critical_d/total_damage_bonus*boss_damage_bonus+precision_d/total_damage_bonus*boss_damage_bonus

        return {
            "Base DPS": base_dps,
            "Critical DPS": critical_dps,
            "Precision DPS": precision_dps,
            "Total DPS": total_dps,
            "Boss DPS": total_boss_dps,
            "Base Damage": base_d,
            "Critical Damage": critical_d,
            "Precision Damage": precision_d,
            "Total Damage": total_d,
            "Boss Damage": total_boss
        }

    def calculate_thor_values(self):
        total_damage_bonus = 1 + self.get_value("Total Damage Bonus") / 100
        total_output_boost = 1 + self.get_value("Total Output Boost") / 100
        critical_hit_rate = self.get_value("Critical Hit Rate") / 100
        critical_hit_multiplier = 1 + self.get_value("Critical Hit Multiplier") / 100
        precision_hit_rate = self.get_value("Precision Hit Rate") / 100
        precision_hit_multiplier = 1 +    self.get_value("Precision Hit Multiplier") / 100

        high_speed_shock = self.get_value("High-Speed Shock Enhancement")
        high_voltage_field = self.get_value("High-Voltage Field Enhancement")
        rune_onslaught = self.get_value("Rune Onslaught Enhancement")

        base_attack_speed_persecond = 2

        lightning_firerate = (
            base_attack_speed_persecond
            * (1 + rune_onslaught / 100)
            * (1 + high_speed_shock / 100)
        )

        lightning_base_attack_speed = lightning_firerate

        lightning_base_damage = (
            total_damage_bonus
            * total_output_boost
            * 20000
            * (1 + high_voltage_field / 100)
        )

        lightning_base_dps = (
            lightning_base_attack_speed
            * lightning_base_damage
            * (1 - (critical_hit_rate + precision_hit_rate))
        )

        lightning_crit_damage = lightning_base_damage * (critical_hit_multiplier)
        lightning_precision_damage = lightning_base_damage * (precision_hit_multiplier)

        lightning_crit_dps = lightning_base_attack_speed * lightning_crit_damage * critical_hit_rate
        lightning_precision_dps = lightning_base_attack_speed * lightning_precision_damage * precision_hit_rate

        lightning_total_dps = (
            lightning_base_dps
            + lightning_crit_dps
            + lightning_precision_dps
        )

        return {
            "Lightning Fire Rate": lightning_firerate,
            "Lightning Base Attack Speed": lightning_base_attack_speed,
            "Lightning Base Damage": lightning_base_damage,
            "Lightning Base DPS": lightning_base_dps,
            "Lightning Critical Damage": lightning_crit_damage,
            "Lightning Critical DPS": lightning_crit_dps,
            "Lightning Precision Damage": lightning_precision_damage,
            "Lightning Precision DPS": lightning_precision_dps,
            "Lightning Total DPS": lightning_total_dps,
        }

    def calculate_values(self):
        if self.character_var.get() == "Thor":
            return self.calculate_thor_values()

        return self.calculate_moon_knight_values()

    def update_results(self, *args):
        if not self.all_fields_entered():
            self.clear_results()
            return

        try:
            results = self.calculate_values()
        except (ValueError, ZeroDivisionError):
            self.clear_results()
            return

        for label, var in self.result_vars.items():
            value = results.get(label, 0)

            if "Attack Speed" in label or "Fire Rate" in label:
                var.set(f"{value:,.2f}")
            else:
                var.set(f"{int(value):,.0f}")

    def clear_results(self):
        for var in self.result_vars.values():
            var.set("0")


if __name__ == "__main__":
    root = tk.Tk()
    app = DPSCalculatorApp(root)
    root.mainloop()
