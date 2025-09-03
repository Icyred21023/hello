# updater.py

import os
import requests
import zipfile
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox

script_dir = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(script_dir, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Icyred21023/hello/main/version.txt"
REMOTE_ZIP_URL = "https://github.com/Icyred21023/hello/archive/refs/heads/main.zip"

def get_current_version():
    if not os.path.exists(VERSION_FILE):
        return "0.0.0"
    with open(VERSION_FILE) as f:
        return f.read().strip()

def get_latest_version():
    try:
        response = requests.get(REMOTE_VERSION_URL, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print("Failed to check for update:", e)
        return None

def download_and_extract_zip(zip_url, extract_to):
    print("Downloading update...")
    local_zip = os.path.join(script_dir, "update_temp.zip")

    response = requests.get(zip_url, stream=True)
    response.raise_for_status()

    if "zip" not in response.headers.get("Content-Type", ""):
        print("Error: Downloaded file is not a zip archive.")
        print("Content-Type:", response.headers.get("Content-Type"))
        return

    with open(local_zip, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    extract_path = os.path.join(script_dir, extract_to)
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    os.remove(local_zip)

def backup_current_dir(version):
    print("Creating backup...")
    backup_path = os.path.join(script_dir, "update_backup", version)
    number = 0
    while os.path.exists(backup_path):
        number += 1
        new_version = version + '(' + str(number) + ')'
        backup_path = os.path.join(script_dir, "update_backup", new_version)
    os.makedirs(backup_path, exist_ok=True)

    def ignore_dirs(dir, contents):
        return {"update_backup", "update_temp", "__pycache__", "debug"} & set(contents)

    for item in os.listdir(script_dir):
        if item in ("update_backup", "__pycache__", "debug", "update_temp"):
            continue
        src = os.path.join(script_dir, item)
        dst = os.path.join(backup_path, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=ignore_dirs)
        else:
            shutil.copy2(src, dst)

def apply_update(from_path):
    print("Applying update...")
    update_root = os.path.join(script_dir, from_path)

    # Detect inner folder from GitHub zip layout
    subdirs = [d for d in os.listdir(update_root) if os.path.isdir(os.path.join(update_root, d))]
    if len(subdirs) == 1:
        update_root = os.path.join(update_root, subdirs[0])

    for item in os.listdir(update_root):
        src = os.path.join(update_root, item)
        dst = os.path.join(script_dir, item)

        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

def check_for_update(auto_accept=False):
    current = get_current_version()
    latest = get_latest_version()
    if latest is None:
        return
    one, two, three = current.split('.')
    cu = one + two + three
    one2, two2, three2 = latest.split('.')
    la = one2 + two2 + three2

    if int(cu) < int(la):
        print(f"New version available: {latest} (current: {current})")
        proceed = False

        if auto_accept:
            proceed = True
        else:
            # Create temporary root for messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            result = messagebox.askyesno("Update Available", f"A new version ({latest}) is available.\nUpdate now?")
            root.destroy()
            proceed = result

        if proceed:
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, os.path.join(script_dir, "update_temp"))
            apply_update(os.path.join(script_dir, "update_temp"))
            shutil.rmtree(os.path.join(script_dir, "update_temp"))

            with open(VERSION_FILE, "w") as f:
                f.write(latest)

            # Show message dialog
            root = tk.Tk()
            root.withdraw()  # Hide main window
            messagebox.showinfo("Update Complete", "Update complete.\nPlease relaunch the program.")
            root.destroy()

            sys.exit()  # Exit instead of restart
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")

def check_for_update2(auto_accept=False):
    current = get_current_version()
    latest = get_latest_version()
    if latest is None:
        return

    if latest != current:
        print(f"New version available: {latest} (current: {current})")
        if auto_accept or input("Update now? (y/n): ").lower().strip() == "y":
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, "update_temp")
            apply_update("update_temp")
            shutil.rmtree(os.path.join(script_dir, "update_temp"))

            with open(VERSION_FILE, "w") as f:
                f.write(latest)

            print("Update complete. Restarting...")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")
