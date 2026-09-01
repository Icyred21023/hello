
import subprocess
import sys
import os
import tkinter as tk
from tkinter import messagebox
import helpers
import config

# ================================
# Dependency Auto-Checker (Dynamic, Fixed)
# ================================

def load_requirements(file_path=None):
    file_path = helpers.create_path("requirements_auto.txt", "debug")
    requirements = {}
    if not os.path.exists(file_path):
        print(f"⚠️ {file_path} not found. No dependencies checked.")
        return requirements

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                pkg, ver = line.split("==", 1)
                requirements[pkg.strip()] = f"{pkg.strip()}=={ver.strip()}"
            else:
                requirements[line.strip()] = line.strip()
    return requirements


import importlib.metadata as md

def check_and_install_dependencies(requirements=None):
    if requirements is None:
        requirements = load_requirements()

    if not requirements:
        print("⚠️ No packages to check (empty requirements).")
        return True

    installed = {dist.metadata["Name"].lower(): dist.version for dist in md.distributions()}
    installed_normalized = {
                    k.lower().replace("-", "_"): v
                    for k, v in installed.items()
                            }
    missing = []

    for pkg_name, pip_spec in requirements.items():
        normalized = pkg_name.lower().replace("-", "_")
        if normalized not in installed_normalized:
            missing.append(normalized)
            continue
        # Optional: check version mismatch
        current_ver = installed_normalized[normalized]
        if "==" in pip_spec:
            desired_ver = pip_spec.split("==", 1)[1]
            if desired_ver != current_ver:
                test_d = desired_ver
                test_c = current_ver
                if pkg_name == 'torch':
                    if '+' in desired_ver:
                        test_d = desired_ver.split('+')[0]  
                    if '+' in current_ver:
                        test_c = current_ver.split('+')[0]
                if test_d != test_c:
                    print(f"⚠️  Module Version mismatch: {pkg_name} ({test_c} != {desired_ver})")

    if not missing:
        print("✅ All modules locally installed.")
        return True

    # Tkinter dialog logic (same as before)
    msg = "The following packages are missing locally:\n\n" + "\n".join(missing) + \
          "\n\nWould you like to auto-install them now?"

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        answer = messagebox.askyesno("Missing Packages Detected", msg, parent=root, icon='question')
    finally:
        root.destroy()

    if answer:
        for pkg in missing:
            print(f"⬇️ Installing {pkg}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=False)

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo(
            "Installation Complete",
            "✅ All missing packages were installed.\nPlease restart the program.",
            parent=root
        )
        root.destroy()
        sys.exit()

    else:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        msg = "Would you like to hide this prompt?:\n\n" + "\n".join(missing) + \
          "\n\nIf program runs fine, hit yes."
        answer = messagebox.askyesno("Disable Module Check?", msg, parent=root, icon='question')
        if answer:
            config.dependency_check = False
            data = config.config_json
            data['dependency_check'] = False
            helpers.save_json(config.configpath, data)
            messagebox.showinfo(
                "Dependency Check Disabled",
                "✅ Dependency check has been disabled.\nYou can re-enable it in settings.",
                parent=root
            )
        root.destroy()
        return False



# Auto-run when imported directly
if __name__ == "__main__":
    reqs = load_requirements()
    check_and_install_dependencies(reqs)
