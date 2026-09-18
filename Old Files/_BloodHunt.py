import tkinter as tk
from tkinter import ttk

import config
import helpers
from PIL import ImageTk, Image
import os

class DPSCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DPS Calculator")
        self.root.geometry(f"{425 + int(850 * 0.55)}x850")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")
        self.hero_canvas_item = None
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 11))
        style.configure("Dark2.TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Dark.TCombobox", fieldbackground="#924D4D", background="#52bd38", foreground="#3c9fb1")

        self.hero_config_path = helpers.create_path("_blood_hunt_json.json", "debug")
        self.json_hero_config = helpers.load_json(self.hero_config_path)
        
        self.asset_dir = os.path.join(config.script_dir, "assets_exp")
            
        self.left_panel = tk.Frame(root, bg="#1e1e1e", width=425, height=850)
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)

        self.right_canvas = tk.Canvas(
            root,
            width=int(850 * 0.55),   # 75% of root height
            height=850,
            bg="#1e1e1e",
            highlightthickness=0
        )
        self.right_canvas.pack(side="right", fill="y")
        self.right_canvas.pack_propagate(False)
        self.container = tk.Frame(self.left_panel, bg="#1e1e1e")
        self.container.pack(padx=(20,5), pady=20, fill="both", expand=True)

        self.characters = ["Moon Knight", "Thor"]
        self.character_var = tk.StringVar(value="Moon Knight")

        self.input_labels_by_character = {
            "Moon Knight": [
                "Total Damage Bonus",
                "Total Output Boost",
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
                "Base DPS",
                "Critical DPS",
                "Precision DPS",
                "Total DPS",
                "Base Damage",
                "Critical Damage",
                "Precision Damage",
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
            row=0, column=0, sticky="w", pady=6
        )

        self.character_combo = ttk.Combobox(
            self.container,
            textvariable=self.character_var,
            values=self.characters,
            state="readonly",
            #style="Dark.TCombobox",
            foreground="#0f0f0f",
            background="#f8f8f8",
            width=14,
            takefocus=0,
            font=("Segoe UI", 10, "bold"),
        )
        self.character_combo.grid(row=0, column=1, pady=6, padx=8, sticky="e")
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
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            bd=2,
            padx=12,
            pady=5,
        )
        self.save_button.grid(row=2, column=1, columnspan=2, sticky="w", pady=(10, 0))

        self.results_frame = tk.Frame(self.container, bg="#1e1e1e")
        self.results_frame.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(15, 0))

        self.entries = {}
        self.result_vars = {}

        self.build_inputs()
        self.build_results()
        self.update_results()
        self.update_save_button_state()
        self.render_hero_image()

    def render_hero_image(self):
        if self.hero_canvas_item is not None:
            self.right_canvas.delete(self.hero_canvas_item)

        hero_image = self.load_image(self.character_var.get())
        y = 850
        x = 0
        if self.character_var.get() == "Moon Knight":
            y = 792
            x= 30
        self.hero_canvas_item = self.right_canvas.create_image(
            x,
            y,
            anchor="sw",
            image=hero_image
        )

        self.right_canvas.image = hero_image
    def load_image(self, hero):
        path = os.path.join(self.asset_dir,hero+".png")
        imgraw = Image.open(path)
        imgraw = imgraw.resize((850, 850), Image.BICUBIC)
        tk_image = ImageTk.PhotoImage(imgraw)
        return tk_image

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
        self.input_frame.grid_columnconfigure(0, minsize=230, weight=0)
        self.input_frame.grid_columnconfigure(1, minsize=120, weight=0)
        labels = self.input_labels_by_character[self.character_var.get()]
        if not self.json_hero_config:
            self.json_hero_config = {
                "Moon Knight": False,
                "Thor": False
            }
        
            

        for row, label_text in enumerate(labels):
            loaded_string = self.return_saved_label_value(label_text, self.json_hero_config.get(self.character_var.get(), False))
            ttk.Label(
                self.input_frame,
                text=label_text,
                style="Dark.TLabel",
            ).grid(row=row, column=0, sticky="w", pady=6)

            entry_var = tk.StringVar(value=loaded_string)

            entry_wrap = tk.Frame(
                self.input_frame,
                bg="#1A1A1A",
                bd=2,
                relief="sunken",
            )
            entry_wrap.grid(
                row=row,
                column=1,
                pady=6,
                padx=8,
                sticky="e"
            )

            entry = tk.Entry(
                entry_wrap,
                textvariable=entry_var,
                bg="#1A1A1A",
                fg="#ffffff",
                insertbackground="#ffffff",
                font=("Segoe UI", 10, "bold"),
                justify="right",
                width=8,
                relief="flat",
                bd=0,
            )
            entry.pack(side="left", fill='none', expand=True, padx=(6, 2), pady=4)

            if "Interval" not in label_text:
                tk.Label(
                    entry_wrap,
                    text="%",
                    bg="#1A1A1A",
                    fg="#aaaaaa",
                    font=("Segoe UI", 10, "bold"),
                ).pack(side="right", padx=(1, 0))

            entry_var.trace_add("write", self.on_entry_changed)
            self.entries[label_text] = entry_var

    def build_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        self.results_frame.grid_columnconfigure(0, minsize=230, weight=0)
        self.results_frame.grid_columnconfigure(1, minsize=120, weight=0)

        self.result_vars = {}

        labels = self.result_labels_by_character[self.character_var.get()]

        for row, label_text in enumerate(labels):
            ttk.Label(
                self.results_frame,
                text=label_text,
                style="Dark2.TLabel",
            ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 8))

            var = tk.StringVar(value="0")
            self.result_vars[label_text] = var

            tk.Label(
                self.results_frame,
                textvariable=var,
                bg="#111111",
                fg="#00ff99" if "Total" in label_text else "#efff97",
                font=("Segoe UI", 10, "bold"),
                relief="sunken",
                bd=2,
                padx=12,
                pady=4,
                width=14,
                anchor="e",
            ).grid(row=row, column=1, sticky="e", padx=(0, 0))

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
        character = self.character_var.get()

        return {
             
                label: float(var.get())
                for label, var in self.entries.items()
            
        }

    def save_current_character_fields(self):
        data = self.get_current_character_json_data()
        hero = self.character_var.get()
        hero_data = self.json_hero_config.get(hero, False)
        
        self.json_hero_config[hero] = data
        helpers.save_json(self.hero_config_path, self.json_hero_config)
            
        # Write your save logic here.
        # Example data format:
        # {
        #     "character": "Thor",
        #     "fields": {
        #         "Total Damage Bonus": 100.0,
        #         "Total Output Boost": 100.0
        #     }
        # }

        #print(json.dumps(data, indent=4))

        # Example save code if you want it later:
        #
        # with open("character_fields.json", "w") as f:
        #     json.dump(data, f, indent=4)

    def get_value(self, label):
        return float(self.entries[label].get())

    def calculate_moon_knight_values(self):
        total_damage_bonus = self.get_value("Total Damage Bonus") / 100
        total_output_boost = self.get_value("Total Output Boost") / 100
        critical_hit_rate = self.get_value("Critical Hit Rate") / 100
        critical_hit_multiplier = self.get_value("Critical Hit Multiplier") / 100
        precision_hit_rate = self.get_value("Precision Hit Rate") / 100
        precision_hit_multiplier = self.get_value("Precision Hit Multiplier") / 100
        lunar_glide_hit_interval = self.get_value("Lunar Glide Hit Interval")

        hitpersecond = 1 / lunar_glide_hit_interval
        base_hit_rate = 1 - (critical_hit_rate + precision_hit_rate)

        base_dps = total_damage_bonus * total_output_boost * 155 * base_hit_rate * hitpersecond * 30
        critical_dps = total_damage_bonus * total_output_boost * 155 * critical_hit_multiplier * critical_hit_rate * hitpersecond * 30
        precision_dps = total_damage_bonus * total_output_boost * 155 * precision_hit_multiplier * precision_hit_rate * hitpersecond * 30

        total_dps = base_dps + critical_dps + precision_dps

        base_d = total_damage_bonus * total_output_boost * 155 * 30
        critical_d = base_d * critical_hit_multiplier
        precision_d = base_d * precision_hit_multiplier
        total_d = base_d + critical_d + precision_d

        return {
            "Base DPS": base_dps,
            "Critical DPS": critical_dps,
            "Precision DPS": precision_dps,
            "Total DPS": total_dps,
            "Base Damage": base_d,
            "Critical Damage": critical_d,
            "Precision Damage": precision_d,
            "Total Damage": total_d,
        }

    def calculate_thor_values(self):
        total_damage_bonus = self.get_value("Total Damage Bonus") / 100
        total_output_boost = self.get_value("Total Output Boost") / 100
        critical_hit_rate = self.get_value("Critical Hit Rate") / 100
        critical_hit_multiplier = self.get_value("Critical Hit Multiplier") / 100
        precision_hit_rate = self.get_value("Precision Hit Rate") / 100
        precision_hit_multiplier = self.get_value("Precision Hit Multiplier") / 100

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

        lightning_crit_damage = lightning_base_damage * (1 + critical_hit_multiplier)
        lightning_precision_damage = lightning_base_damage * (1 + precision_hit_multiplier)

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