import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import json
import os
import subprocess
import config
if not config.mobile_mode:
    import psutil

def kill_selenium_chrome():
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'].lower() == 'chrome.exe':
                cmdline = ' '.join(proc.info['cmdline'])
                if '--user-data-dir' in cmdline and 'selenium' in cmdline.lower():
                    print(f"Killing Selenium Chrome PID {proc.pid}")
                    proc.kill()
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed == 0:
        print("No Selenium Chrome processes found.")
    else:
        print(f"✔ Killed {killed} Selenium Chrome processes.")

def kill_zombies():
    try:
        subprocess.run("taskkill /f /im chromedriver.exe", check=False)
        #subprocess.run("taskkill /f /im chrome.exe", check=False)
    except Exception as e:
        print("Warning: couldn't kill Chrome processes", e)



def safe_del(self):
    try:
        self.quit()
    except Exception:
        pass

uc.Chrome.__del__ = safe_del

def open_multiple_tracker_profiles(player_names):
    kill_selenium_chrome()
    season = "6"
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  # Optional
    profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")
    os.makedirs(profile_path, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1,1")

    driver = uc.Chrome(options=options)
    driver.set_window_position(-10000, 0)
    driver.set_window_size(1, 1)

    results = {}

    try:
        for player_name in player_names:
            url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"
            try:
                driver.get(url)
                pre = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                raw_json = pre.text
                data = json.loads(raw_json)
                print(f"✅ Data loaded for {player_name}")
                results[player_name] = data
            except Exception as e:
                print(f"❌ Error loading JSON for {player_name}: {e}")
                results[player_name] = None
            time.sleep(0.15)  # Optional: reduce load pressure
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    kill_selenium_chrome()
    return results