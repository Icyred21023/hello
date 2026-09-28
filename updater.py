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
# ============================================================
# UPDATE CLEANUP EXCLUSIONS
# ============================================================
#
# These paths are RELATIVE to script_dir.
#
# EXCLUDED FILES:
#   Put individual files here that should NEVER be deleted.
#
#   Examples:
#       "config.json",
#       "user_settings.json",
#       "data/my_database.json",
#
# EXCLUDED FOLDERS:
#   Put folders here that should NEVER be deleted.
#   EVERYTHING inside an excluded folder is automatically protected,
#   including all subfolders and files.
#
#   Examples:
#       "UserData",
#       "Cache",
#       "assets/custom",
#
# Use forward slashes "/" for nested paths.
# Matching is case-insensitive on purpose.
# ============================================================

DELETE_EXCLUDED_FILES = {
    # "config.json",
    # "user_settings.json",
}

DELETE_EXCLUDED_FOLDERS = {
    ".git",
    "update_temp",
    ".vscode",
    "update_backup",
    "_update_logs",
    "__pycache__",
    "debug",
    "config",
    "Developer",
    "_Mastery_Sheet_Editor",


    # Add your own below:
    # "UserData",
    # "Custom Assets",
    # "data/cache",
}
def get_current_version():
    if not os.path.exists(VERSION_FILE):
        return "0.0.0"
    with open(VERSION_FILE) as f:
        return f.read().strip()


def delete_obsolete_update_files(update_root, destination_root, log=print):
    """
    Delete files/folders from destination_root that no longer exist
    in update_root.

    Files/folders listed in DELETE_EXCLUDED_FILES or
    DELETE_EXCLUDED_FOLDERS are never deleted.

    Excluding a folder automatically excludes its entire contents.

    Returns:
        True if cleanup completed successfully.
        False if one or more deletions failed.
    """

    def normalize_relative_path(path):
        return path.replace("\\", "/").strip("/").lower()

    excluded_files = {
        normalize_relative_path(path)
        for path in DELETE_EXCLUDED_FILES
    }

    excluded_folders = {
        normalize_relative_path(path)
        for path in DELETE_EXCLUDED_FOLDERS
    }

    def is_excluded(relative_path, is_directory=False):
        relative_path = normalize_relative_path(relative_path)

        # Exact excluded file
        if not is_directory and relative_path in excluded_files:
            return True

        # Excluded folder OR anything contained within one
        for excluded_folder in excluded_folders:

            if relative_path == excluded_folder:
                return True

            if relative_path.startswith(excluded_folder + "/"):
                return True

        return False

    success = True

    log("Checking for obsolete files and directories...")

    # topdown=True lets us completely skip excluded folders and prevents
    # os.walk() from descending into them.
    for current_root, dirs, files in os.walk(destination_root, topdown=True):

        relative_root = os.path.relpath(current_root, destination_root)

        if relative_root == ".":
            relative_root = ""

        # --------------------------------------------------------
        # DIRECTORIES
        # --------------------------------------------------------

        # Use a copy because we may remove entries from dirs.
        for directory_name in dirs[:]:

            destination_path = os.path.join(
                current_root,
                directory_name
            )

            relative_path = os.path.relpath(
                destination_path,
                destination_root
            )

            if is_excluded(relative_path, is_directory=True):
                log(f"🔒 Keeping excluded directory: {relative_path}")

                # Prevent os.walk() from entering it.
                dirs.remove(directory_name)

                continue

            source_path = os.path.join(
                update_root,
                relative_path
            )

            # Folder no longer exists in repo/update.
            if not os.path.isdir(source_path):

                try:
                    log(f"🗑️ Removing obsolete directory: {relative_path}")

                    shutil.rmtree(destination_path)

                    # Don't walk into a directory we just deleted.
                    dirs.remove(directory_name)

                except Exception as e:
                    log(
                        f"❌ Failed removing obsolete directory "
                        f"{relative_path}: {e}"
                    )
                    success = False

        # --------------------------------------------------------
        # FILES
        # --------------------------------------------------------

        for file_name in files:

            destination_path = os.path.join(
                current_root,
                file_name
            )

            relative_path = os.path.relpath(
                destination_path,
                destination_root
            )

            if is_excluded(relative_path, is_directory=False):
                log(f"🔒 Keeping excluded file: {relative_path}")
                continue

            source_path = os.path.join(
                update_root,
                relative_path
            )

            # File no longer exists in repo/update.
            if not os.path.isfile(source_path):

                try:
                    log(f"🗑️ Removing obsolete file: {relative_path}")

                    os.remove(destination_path)

                except Exception as e:
                    log(
                        f"❌ Failed removing obsolete file "
                        f"{relative_path}: {e}"
                    )
                    success = False

    return success

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
    # ------------------------------------------------------------
# DELETE FILES/FOLDERS THAT NO LONGER EXIST IN THE REPO
# ------------------------------------------------------------
    import config
    if success and not config.IS_ADMIN:
        yesno = messagebox.askyesno("Update Cleanup", "Do you want to remove obsolete files from the previous version?\n\nThis will delete files/folders that no longer exist in the update package.\n\nExcluded files/folders will be kept.\n\nClick 'Yes' to proceed with cleanup, or 'No' to skip.")
        if not yesno:
            cleanup_success = delete_obsolete_update_files(
                update_root=update_root,
                destination_root=script_dir,
                log=log
            )

            if not cleanup_success:
                success = False
                string_ = "❌ Update cleanup failed. Check update logs."
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
            #backup_current_dir(current)
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
            #backup_current_dir(current)
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
