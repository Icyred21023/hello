# updater.py

import os
import sys
import stat
import time
import shutil
import zipfile
import requests
import tkinter as tk
from tkinter import messagebox

# --------------------------
# Paths & constants
# --------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(script_dir, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Icyred21023/hello/main/version.txt"
REMOTE_ZIP_URL = "https://github.com/Icyred21023/hello/archive/refs/heads/main.zip"

# --------------------------
# Permission & FS utilities
# --------------------------
def make_writable(path: str):
    """Remove read-only bit from a file or directory (Windows-safe)."""
    try:
        # Add write perms for owner (and keep read/exec if present)
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    except FileNotFoundError:
        pass
    except PermissionError:
        # Try a more permissive mask (mainly for *nix)
        try:
            os.chmod(path, 0o777)
        except Exception:
            pass

def chmod_tree_writable(root: str):
    """Recursively clear read-only bits for an entire tree."""
    if not os.path.exists(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        make_writable(dirpath)
        for d in dirnames:
            make_writable(os.path.join(dirpath, d))
        for f in filenames:
            make_writable(os.path.join(dirpath, f))

def on_rm_error(func, path, exc_info):
    """
    rmtree onerror handler: make the path writable and retry func(path).
    func is usually os.remove / os.rmdir / os.unlink.
    """
    make_writable(path)
    try:
        func(path)
    except Exception:
        try:
            os.chmod(path, 0o777)
            func(path)
        except Exception:
            raise

def rmtree_force(path: str):
    """Remove directory tree even if files are read-only."""
    if os.path.exists(path):
        shutil.rmtree(path, onerror=on_rm_error)

def safe_copy2(src: str, dst: str):
    """Clear read-only on destination, copy file, then ensure result is writable."""
    dst_dir = os.path.dirname(dst)
    if dst_dir and not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
    if os.path.exists(dst):
        make_writable(dst)
    shutil.copy2(src, dst)
    make_writable(dst)

def copytree_force(src: str, dst: str, **kwargs):
    """
    Remove dst (even if read-only), copy tree, then ensure new tree is writable.
    kwargs pass through to shutil.copytree (e.g., ignore=...).
    """
    rmtree_force(dst)
    shutil.copytree(src, dst, **kwargs)
    chmod_tree_writable(dst)

def norm_target(path_like: str) -> str:
    """Normalize a path argument to an absolute path under script_dir if needed."""
    return path_like if os.path.isabs(path_like) else os.path.join(script_dir, path_like)

# --------------------------
# Version utilities
# --------------------------
def get_current_version():
    if not os.path.exists(VERSION_FILE):
        return "0.0.0"
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def get_latest_version():
    try:
        headers = {"User-Agent": "hello-updater/1.0"}
        response = requests.get(REMOTE_VERSION_URL, timeout=10, headers=headers)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print("Failed to check for update:", e)
        return None

# --------------------------
# Download & extract
# --------------------------
def download_and_extract_zip(zip_url: str, extract_to: str):
    """
    Download a zip to a temp file, extract to extract_to (absolute or relative),
    and ensure extracted files are writable (not read-only).
    """
    print("Downloading update...")
    local_zip = os.path.join(script_dir, "update_temp.zip")

    headers = {"User-Agent": "hello-updater/1.0"}
    with requests.get(zip_url, stream=True, timeout=30, headers=headers) as response:
        response.raise_for_status()

        # Optional sanity check (GitHub often sets application/zip)
        ctype = response.headers.get("Content-Type", "")
        if "zip" not in ctype and "application/octet-stream" not in ctype:
            print("Warning: Content-Type does not look like a zip:", ctype)

        with open(local_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)

    extract_path = norm_target(extract_to)
    rmtree_force(extract_path)
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(local_zip, "r") as zip_ref:
        # Extract, then clear read-only on extracted content
        zip_ref.extractall(extract_path)

    try:
        os.remove(local_zip)
    except Exception:
        make_writable(local_zip)
        try:
            os.remove(local_zip)
        except Exception:
            pass

    # Ensure the extracted payload is writable
    chmod_tree_writable(extract_path)

# --------------------------
# Backup & apply
# --------------------------
def backup_current_dir(version: str):
    print("Creating backup...")
    backup_path = os.path.join(script_dir, "update_backup", version)
    os.makedirs(backup_path, exist_ok=True)

    def ignore_dirs(dirpath, contents):
        # Return a list of names to ignore in this dir
        ignore_names = {"update_backup", "update_temp", "__pycache__", "debug", "update_temp.zip"}
        return [name for name in contents if name in ignore_names]

    for item in os.listdir(script_dir):
        if item in ("update_backup", "__pycache__", "debug", "update_temp", "update_temp.zip"):
            continue
        src = os.path.join(script_dir, item)
        dst = os.path.join(backup_path, item)
        if os.path.isdir(src):
            copytree_force(src, dst, ignore=ignore_dirs)
        else:
            safe_copy2(src, dst)

def apply_update(from_path: str):
    """
    Copy extracted update contents over the current directory,
    forcibly replacing existing files/dirs (and keeping everything writable).
    """
    print("Applying update...")
    update_root = norm_target(from_path)

    # Detect inner folder from GitHub zip layout (e.g., hello-main/)
    subdirs = [d for d in os.listdir(update_root) if os.path.isdir(os.path.join(update_root, d))]
    if len(subdirs) == 1 and not os.listdir(update_root):  # (unlikely — keep fallback)
        update_root = os.path.join(update_root, subdirs[0])

    # More robust inner-folder detection: if there is exactly one dir and many zips use it
    if len(subdirs) == 1:
        possible = os.path.join(update_root, subdirs[0])
        # Check if that inner folder actually contains the payload (e.g., has files)
        if os.path.exists(possible) and any(os.scandir(possible)):
            update_root = possible

    # Ensure payload tree is writable
    chmod_tree_writable(update_root)

    for item in os.listdir(update_root):
        src = os.path.join(update_root, item)
        dst = os.path.join(script_dir, item)

        if os.path.isdir(src):
            copytree_force(src, dst)  # deletes dst if exists (even if read-only) and copies
        else:
            safe_copy2(src, dst)

    # As a final safeguard, make the whole app dir (except backup/temp) writable
    for item in os.listdir(script_dir):
        if item in ("update_backup", "update_temp", "__pycache__", "update_temp.zip"):
            continue
        path = os.path.join(script_dir, item)
        if os.path.isdir(path):
            chmod_tree_writable(path)
        else:
            make_writable(path)

# --------------------------
# Update flows
# --------------------------
def _finish_update_and_exit(latest: str):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(latest)

    # Tk message then exit (no restart here)
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Update Complete", "Update complete.\nPlease relaunch the program.")
    root.destroy()
    sys.exit(0)

def check_for_update(auto_accept: bool = False):
    current = get_current_version()
    latest = get_latest_version()
    if latest is None:
        return

    if latest != current:
        print(f"New version available: {latest} (current: {current})")

        if auto_accept:
            proceed = True
        else:
            root = tk.Tk()
            root.withdraw()
            proceed = messagebox.askyesno(
                "Update Available",
                f"A new version ({latest}) is available.\nUpdate now?"
            )
            root.destroy()

        if proceed:
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, "update_temp")
            apply_update("update_temp")
            rmtree_force(os.path.join(script_dir, "update_temp"))
            _finish_update_and_exit(latest)
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")

def check_for_update2(auto_accept: bool = False):
    """
    Console flow (no tkinter confirm). Restarts the process on success.
    """
    current = get_current_version()
    latest = get_latest_version()
    if latest is None:
        return

    if latest != current:
        print(f"New version available: {latest} (current: {current})")

        proceed = auto_accept
        if not auto_accept:
            proceed = input("Update now? (y/n): ").lower().strip() == "y"

        if proceed:
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, "update_temp")
            apply_update("update_temp")
            rmtree_force(os.path.join(script_dir, "update_temp"))

            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(latest)

            print("Update complete. Restarting...")
            time.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")

# --------------------------
# Optional direct run
# --------------------------
if __name__ == "__main__":
    # Example: python updater.py --auto
    auto = "--auto" in sys.argv
    check_for_update(auto_accept=auto)

# # updater.py

# import os
# import requests
# import zipfile
# import shutil
# import sys
# import time
# import tkinter as tk
# from tkinter import messagebox

# script_dir = os.path.dirname(os.path.abspath(__file__))
# VERSION_FILE = os.path.join(script_dir, "version.txt")
# REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Icyred21023/hello/main/version.txt"
# REMOTE_ZIP_URL = "https://github.com/Icyred21023/hello/archive/refs/heads/main.zip"

# def get_current_version():
#     if not os.path.exists(VERSION_FILE):
#         return "0.0.0"
#     with open(VERSION_FILE) as f:
#         return f.read().strip()

# def get_latest_version():
#     try:
#         response = requests.get(REMOTE_VERSION_URL, timeout=5)
#         response.raise_for_status()
#         return response.text.strip()
#     except Exception as e:
#         print("Failed to check for update:", e)
#         return None

# def download_and_extract_zip(zip_url, extract_to):
#     print("Downloading update...")
#     local_zip = os.path.join(script_dir, "update_temp.zip")

#     response = requests.get(zip_url, stream=True)
#     response.raise_for_status()

#     if "zip" not in response.headers.get("Content-Type", ""):
#         print("Error: Downloaded file is not a zip archive.")
#         print("Content-Type:", response.headers.get("Content-Type"))
#         return

#     with open(local_zip, "wb") as f:
#         for chunk in response.iter_content(chunk_size=8192):
#             if chunk:
#                 f.write(chunk)

#     extract_path = os.path.join(script_dir, extract_to)
#     with zipfile.ZipFile(local_zip, 'r') as zip_ref:
#         zip_ref.extractall(extract_path)

#     os.remove(local_zip)

# def backup_current_dir(version):
#     print("Creating backup...")
#     backup_path = os.path.join(script_dir, "update_backup", version)
#     os.makedirs(backup_path, exist_ok=True)

#     def ignore_dirs(dir, contents):
#         return {"update_backup", "update_temp", "__pycache__", "debug"} & set(contents)

#     for item in os.listdir(script_dir):
#         if item in ("update_backup", "__pycache__", "debug", "update_temp"):
#             continue
#         src = os.path.join(script_dir, item)
#         dst = os.path.join(backup_path, item)
#         if os.path.isdir(src):
#             if os.path.exists(dst):
#                 shutil.rmtree(dst)
#             shutil.copytree(src, dst, ignore=ignore_dirs)
#         else:
#             shutil.copy2(src, dst)

# def apply_update(from_path):
#     print("Applying update...")
#     update_root = os.path.join(script_dir, from_path)

#     # Detect inner folder from GitHub zip layout
#     subdirs = [d for d in os.listdir(update_root) if os.path.isdir(os.path.join(update_root, d))]
#     if len(subdirs) == 1:
#         update_root = os.path.join(update_root, subdirs[0])

#     for item in os.listdir(update_root):
#         src = os.path.join(update_root, item)
#         dst = os.path.join(script_dir, item)

#         if os.path.isdir(src):
#             if os.path.exists(dst):
#                 shutil.rmtree(dst)
#             shutil.copytree(src, dst)
#         else:
#             shutil.copy2(src, dst)

# def check_for_update(auto_accept=False):
#     current = get_current_version()
#     latest = get_latest_version()
#     if latest is None:
#         return

#     if latest != current:
#         print(f"New version available: {latest} (current: {current})")
#         proceed = False

#         if auto_accept:
#             proceed = True
#         else:
#             # Create temporary root for messagebox
#             root = tk.Tk()
#             root.withdraw()  # Hide the main window
#             result = messagebox.askyesno("Update Available", f"A new version ({latest}) is available.\nUpdate now?")
#             root.destroy()
#             proceed = result

#         if proceed:
#             backup_current_dir(current)
#             download_and_extract_zip(REMOTE_ZIP_URL, os.path.join(script_dir, "update_temp"))
#             apply_update(os.path.join(script_dir, "update_temp"))
#             shutil.rmtree(os.path.join(script_dir, "update_temp"))

#             with open(VERSION_FILE, "w") as f:
#                 f.write(latest)

#             # Show message dialog
#             root = tk.Tk()
#             root.withdraw()  # Hide main window
#             messagebox.showinfo("Update Complete", "Update complete.\nPlease relaunch the program.")
#             root.destroy()

#             sys.exit()  # Exit instead of restart
#         else:
#             print("Update canceled.")
#     else:
#         print("You are on the latest version.")

# def check_for_update2(auto_accept=False):
#     current = get_current_version()
#     latest = get_latest_version()
#     if latest is None:
#         return

#     if latest != current:
#         print(f"New version available: {latest} (current: {current})")
#         if auto_accept or input("Update now? (y/n): ").lower().strip() == "y":
#             backup_current_dir(current)
#             download_and_extract_zip(REMOTE_ZIP_URL, "update_temp")
#             apply_update("update_temp")
#             shutil.rmtree(os.path.join(script_dir, "update_temp"))

#             with open(VERSION_FILE, "w") as f:
#                 f.write(latest)

#             print("Update complete. Restarting...")
#             time.sleep(1)
#             os.execv(sys.executable, ['python'] + sys.argv)
#         else:
#             print("Update canceled.")
#     else:
#         print("You are on the latest version.")
