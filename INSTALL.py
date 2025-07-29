import subprocess
import sys

def install_packages():
    packages = [
        "pillow",
        "pyautogui",
        "easyocr",
        "numpy",
        "undetected-chromedriver",
        "selenium",
        "psutil"
    ]
    for package in packages:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

if __name__ == "__main__":
    install_packages()
