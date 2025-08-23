import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time, json, os, subprocess, re
import config
if not config.mobile_mode:
    import psutil

# --- NEW: helper to detect Chrome major version on Windows ---
def get_chrome_major_version(default=138):
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome",  # if on PATH
        "google-chrome",  # just in case
    ]
    for exe in candidates:
        try:
            out = subprocess.check_output([exe, "--version"], stderr=subprocess.STDOUT, text=True)
            # e.g. "Google Chrome 138.0.7204.185"
            m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return default

def kill_selenium_chrome():
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == 'chrome.exe':
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                if '--user-data-dir' in cmdline and 'selenium' in cmdline.lower():
                    print(f"Killing Selenium Chrome PID {proc.pid}")
                    proc.kill()
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    print("No Selenium Chrome processes found." if killed == 0 else f"✔ Killed {killed} Selenium Chrome processes.")

def kill_zombies():
    try:
        subprocess.run("taskkill /f /im chromedriver.exe", check=False)
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
    season = config.season
    mode = "competitive"

    # --- NEW: pin UC to your installed Chrome major version ---
    chrome_major = get_chrome_major_version(default=138)
    print(f"Detected Chrome major version: {chrome_major}")

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

    # IMPORTANT: pass version_main
    driver = uc.Chrome(options=options, version_main=chrome_major)

    # keep your tiny window behavior
    driver.set_window_position(-10000, 0)
    driver.set_window_size(1, 1)

    results = {}
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/ProfChloroform?"
    import copy
    try:
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)
        seas = data["data"]["metadata"]["currentSeason"]
        if seas > season:
            season = seas
            config.season = season
            script_dir = os.path.dirname(os.path.abspath(__file__))
            season_dir = os.path.join(script_dir, "season.txt")
            with open(season_dir, 'w') as f:
                f.write(config.season)
            print(f"Updated season to {config.season} in config.")

        
    except Exception as e:
        print(f"❌ Error loading  EARLY JSON for {player_name}: {e}")
    copi = copy.deepcopy(data)
    copi['data']['segments']  = []

        

    
    try:
        attempts = 0
        for player_name in player_names:
            attempts = 0
            max_attempts = 3
            season = config.season
            success = False
            while attempts < max_attempts and not success:
                url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
                #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"

                try:
                    driver.get(url)
                    pre = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "pre"))
                    )
                    raw_json = pre.text


                    data = json.loads(raw_json)


                    if "data" in data and not data["data"]:
                        if attempts <= 2:
                            print(f"❌ No data found for {player_name}: Season {season}. Retrying with season {season - 1}...")

                            season -= 1 if season > 1 else 1
                            attempts += 1
                            continue
                        else:
                            print(f"❌ No data found for {player_name} after multiple attempts.")
                            results[player_name] = None
                            break

                    copi['data']['segments']  = data['data']
                    data = copy.deepcopy(copi)
                    # seaso = int(data['data']['metadata']['currentSeason'])
                    # if seaso > season:
                    #     season = seaso
                    # seasons.append(seaso)
                    print(f"✅ Data loaded for {player_name}")
                    
                    results[player_name] = data
                    success = True
                except Exception as e:
                    print(f"❌ Error loading JSON for {player_name}: {e}")
                    results[player_name] = None
                    attempts += 1
                    success = True
                time.sleep(0.15)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    kill_selenium_chrome()
    return results
