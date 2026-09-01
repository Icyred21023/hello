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


import datetime

def apply_update(from_path):
    print("Applying update...")

    # --- ROOT PATHS ---
    update_root = os.path.join(script_dir, from_path)
    safe_log_dir = os.path.join(script_dir, "_update_logs")  # 🧩 outside normal folders
    os.makedirs(safe_log_dir, exist_ok=True)

    # --- LOG FILE SETUP ---
    log_path = os.path.join(
        safe_log_dir, f"update_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    def log(msg):
        print(msg)
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception as e:
            print(f"[LOGGING ERROR] {e}")

    log(f"🕒 Update started at {datetime.datetime.now().isoformat()}")
    log(f"Source: {update_root}")
    log(f"Destination: {script_dir}")

    # Detect nested GitHub folder
    subdirs = [d for d in os.listdir(update_root) if os.path.isdir(os.path.join(update_root, d))]
    if len(subdirs) == 1:
        update_root = os.path.join(update_root, subdirs[0])
        log(f"Detected nested folder: {update_root}")
    string_ = 'null'
    success = True
    copied_items = []
    failed_items = []

    # --- COPY EVERYTHING EXCEPT version.txt ---
    for item in os.listdir(update_root):
        if item.lower() == "version.txt":
            log("Skipping version.txt (will copy last).")
            continue
        

        src = os.path.join(update_root, item)
        dst = os.path.join(script_dir, item)

        try:
            if os.path.isdir(src):
                # if item.lower() == "gui_assets":
                #     log("Setting failure")
                #     success = False
                #     string_ = "❌ Error copying gui_assets: [WinError 32] \nThe process cannot access the file because it is being used by another process: \n'c:\\Users\\Corey\\Desktop\\marvel_tracker_V5\\gui_assets\\season_bg2.png'\n\nExiting"
                #     failed_items.append((item, "Fail"))
                #     break
                if os.path.exists(dst):
                    log(f"🗑️ Removing old directory: {dst}")
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                log(f"📁 Copied directory: {item}")
            else:
                shutil.copy2(src, dst)
                log(f"📄 Copied file: {item}")
            copied_items.append(item)
        except Exception as e:
            string_=  f"❌ Error copying {item}: {e}"
            log(f"❌ Error copying {item}: {e}")
            success = False
            failed_items.append((item, str(e)))
            break

    # --- Step 2: Copy version.txt only if everything succeeded ---
    version_src = os.path.join(update_root, "version.txt")
    version_dst = os.path.join(script_dir, "version.txt")

    if success:
        if os.path.exists(version_src):
            try:
                tmp_version = version_dst + ".new"
                shutil.copy2(version_src, tmp_version)
                os.replace(tmp_version, version_dst)
                log("✅ Update completed successfully — version.txt replaced.")
            except Exception as e:
                log(f"⚠️ Failed to replace version.txt: {e}")
                success = False
        else:
            log("⚠️ No version.txt found in update package.")
            string_ = "⚠️ No version.txt found in update package."
            success = False
    else:
        log("⚠️ Update aborted before version.txt copy due to earlier errors.")


    # --- Step 3: Write summary ---
    log("\n=== Update Summary ===")
    log(f"Copied items: {len(copied_items)}")
    for c in copied_items:
        log(f"  - {c}")
    if failed_items:
        log(f"❌ Failed items: {len(failed_items)}")
        for f_item, err in failed_items:
            log(f"  - {f_item}: {err}")
    else:
        log("No failures encountered.")

    # ✅ Explicit and reliable final result
    result = "SUCCESS" if success and not failed_items else "FAILED"
    log(f"✅ Update status: {result}")
    log(f"Log saved to: {log_path}")
    log("🕒 Update finished.\n")

    # (Optional) Write a small result flag for external checks
    try:
        with open(os.path.join(os.path.dirname(log_path), "update_result.txt"), "w") as f:
            f.write(result)
    except Exception as e:
        print(f"[Warning] Could not write update_result.txt: {e}")

    return success , string_ and not failed_items

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
            root.attributes("-topmost", True)
            result = messagebox.askyesno("Update Available", f"A new version ({latest}) is available.\nUpdate now?",icon='question')
            root.destroy()
            proceed = result

        if proceed:
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, os.path.join(script_dir, "update_temp"))
            result, string_ = apply_update(os.path.join(script_dir, "update_temp"))
            shutil.rmtree(os.path.join(script_dir, "update_temp"))
            if result:
                string, string2, sym = "✅ Update Success", "Please relaunch the program.", 'info'

            else:
                string, string2, sym = "❌ Update Failed", "Update encountered errors.\nPlease check the logs in _update_logs.\nRetry by relaunching.\nExiting....", 'error'
            # with open(VERSION_FILE, "w") as f:
            #     f.write(latest)

            # Show message dialog
            root = tk.Tk()
            root.withdraw()  # Hide main window
            root.attributes("-topmost", True)
            if string_ == 'null':
                string_ = string2
            messagebox.showinfo(title=string, message=string_, icon=sym)
            
            root.destroy()
            sys.exit(0)
        else:
            print("Update canceled.")
            return
    else:
        print(f"✅ Running latest version: {current}")
        return

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
