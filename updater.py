# updater.py

import os
import requests
import zipfile
import shutil
import sys
import time

VERSION_FILE = "version.txt"
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_zip = os.path.join(script_dir, "update_temp.zip")

    response = requests.get(zip_url, stream=True)
    response.raise_for_status()

    # Check content type to ensure it's actually a zip
    if "zip" not in response.headers.get("Content-Type", ""):
        print("Error: Downloaded file is not a zip archive.")
        print("Content-Type:", response.headers.get("Content-Type"))
        return

    with open(local_zip, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    os.remove(local_zip)

def backup_current_dir(version):
    print("Creating backup...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backup_path = os.path.join(script_dir,"update_backup", version)
    os.makedirs(backup_path, exist_ok=True)

    def ignore_dirs(dir, contents):
        # prevent recursion into backup or temp folders
        return {"update_backup", "update_temp", "__pycache__", "debug"} & set(contents)

    for item in os.listdir("."):
        if item in ("update_backup", "__pycache__", "debug", "update_temp"):
            continue
        src = os.path.join(".", item)
        dst = os.path.join(backup_path, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=ignore_dirs)
        else:
            shutil.copy2(src, dst)


def apply_update(from_path):
    print("Applying update...")
    for item in os.listdir(from_path):
        src = os.path.join(from_path, item)
        dst = os.path.join(".", item)

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
        return  # Could not fetch

    if latest != current:
        print(f"New version available: {latest} (current: {current})")
        if auto_accept or input("Update now? (y/n): ").lower().strip() == "y":
            backup_current_dir(current)
            download_and_extract_zip(REMOTE_ZIP_URL, "update_temp")
            apply_update("update_temp")
            shutil.rmtree("update_temp")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            VERSION_FILE = os.path.join(script_dir, "version.txt")
            with open(VERSION_FILE, "w") as f:
                f.write(latest)

            print("Update complete. Restarting...")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")