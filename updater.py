# updater.py

import os
import requests
import zipfile
import shutil
import sys
import time

VERSION_FILE = "version.txt"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/version.txt"
REMOTE_ZIP_URL = "https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/latest.zip"

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
    local_zip = "update_temp.zip"
    with open(local_zip, "wb") as f:
        f.write(requests.get(zip_url).content)
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(local_zip)

def backup_current_dir(version):
    print("Creating backup...")
    backup_path = os.path.join("update_backup", version)
    os.makedirs(backup_path, exist_ok=True)

    for item in os.listdir("."):
        if item in ("update_backup", "__pycache__", "debug", "update_temp"): continue
        if os.path.isdir(item):
            shutil.copytree(item, os.path.join(backup_path, item))
        else:
            shutil.copy2(item, os.path.join(backup_path, item))

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

            with open(VERSION_FILE, "w") as f:
                f.write(latest)

            print("Update complete. Restarting...")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Update canceled.")
    else:
        print("You are on the latest version.")