import undetected_chromedriver as uc
from collections import defaultdict
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time, json, os, subprocess, re, platform, shutil
import config
import copy
if not config.mobile_mode:
    import psutil
from datetime import date
import helpers
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote


driver_path = "s"


d = date.today()
DAY = d.day
MONTH = d.month
YEAR = d.year
DAY_COUNT = d.toordinal()
NAMES_LIST = []
# --- NEW: helper to detect Chrome major version on Windows ---

def safe_del(self):
    try:
        self.quit()
    except Exception:
        pass
uc.Chrome.__del__ = safe_del
def kill_brave_selenium_instances():
    TARGET_SUBSTRING = "selenium_admin_profile"  # <--- match only the Selenium sessions

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "brave.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if TARGET_SUBSTRING.lower() in cmdline.lower():
                    print(f"SSS Killing Brave PID {proc.pid} | CMD: {cmdline[:120]}...")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("✅ Finished scanning for Brave Selenium instances.")
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


def get_installed_chrome_major_version(default=147):
    

    path = r"C:\Program Files\Google\Chrome\Application"   # replace with your target path
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    try:
        for f in folders:
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', f):
                default = int(f.split('.')[0])
                print(f"\n🛈 Chrome version: 🛈 {default} from folder: {f}\n")
                return default
            else:
                return default
    except Exception:
        pass
    return default

def get_installed_brave_major_version(default=147):
    

    path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"   # replace with your target path
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    try:
        for f in folders:
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', f):
                default = int(f.split('.')[0])
                print(f"\n🛈 Brave version: 🛈 {default} from folder: {f}\n")
                return default
            else:
                return default
    except Exception:
        pass
    return default
    
   
def make_uc_driver(options):
    chrome_major = get_installed_chrome_major_version()
    if chrome_major:
        driver_path = ChromeDriverManager(driver_version=f"{chrome_major}").install()
    else:
        driver_path = ChromeDriverManager().install()

    # Pass driver_path directly to UC → no cache copy
    driver = uc.Chrome(
        driver_executable_path=driver_path,
        options=options,
    )
    return driver
    
#chrome_major = get_chrome_major_version(default=138)






def kill_zombies():
    try:
        subprocess.run("taskkill /f /im chromedriver.exe", check=False)
    except Exception as e:
        print("Warning: couldn't kill Chrome processes", e)



def kill_brave_selenium_instances():
    TARGET_SUBSTRING = "selenium_admin_profile"  # <--- match only the Selenium sessions

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "brave.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if TARGET_SUBSTRING.lower() in cmdline.lower():
                    print(f"AAA Killing Brave PID {proc.pid} | CMD: {cmdline[:120]}...")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("✅ Finished scanning for Brave Selenium instances.")




def get_installed_brave_major_versionOLD(default=None):
    """
    Inspect typical install folder for Brave and parse version folder names like 115.0.5790.0.
    Returns int major version (e.g. 115) or default (None recommended) if not found.
    """
    system = platform.system()
    # Look at Windows application folder (versioned subfolders)
    paths_to_check = []
    if system == "Windows":
        base = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
        paths_to_check.append(base)
    elif system == "Linux":
        # Some distros keep version folders under /opt or similar; try common place
        paths_to_check.append("/opt/brave.com/brave")
        # also check /usr/lib or snap paths if you want (less version foldering)
    elif system == "Darwin":
        # macOS bundles don't typically have version folders like Chrome; skip
        return default

    regex = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
    for base in paths_to_check:
        try:
            if not base or not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                full = os.path.join(base, name)
                if os.path.isdir(full) and regex.match(name):
                    try:
                        return int(name.split('.')[0])
                    except Exception:
                        continue
        except Exception:
            continue
    return default



def get_brave_binary_path():
    """
    Return a likely Brave binary path for the running OS, or None if not found.
    """
    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/brave-browser",
            "/usr/bin/brave",
            "/snap/bin/brave",
            "/opt/brave.com/brave/brave",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Brave-Browser.app/Contents/MacOS/Brave Browser",
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # fallback: try to find via shutil.which
    for exe in ("brave-browser", "brave"):
        path = shutil.which(exe)
        if path:
            return path
    return None

def make_uc_driver_for_brave(options, brave_binary=None):
    """
    Create an undetected-chromedriver Chrome instance pointing at Brave.
    If a Brave major version is available, pass version_main to uc.Chrome so webdriver_manager will fetch a matching driver.
    If no version found, fall back to letting uc pick the driver.
    """
    brave_bin = brave_binary or get_brave_binary_path()
    if brave_bin:
        options.binary_location = brave_bin
        print(f"Using Brave binary at: {brave_bin}")
    else:
        print("Brave binary NOT found. You can set the path manually via options.binary_location.")

    brave_major = get_installed_brave_major_version(default=None)
    if brave_major:
        print(f"Detected Brave major version: {brave_major}")
        # preferred: let uc handle driver via version_main
        driver = uc.Chrome(options=options, version_main=brave_major)
    else:
        print("Could not detect Brave major version — launching UC without version_main (driver auto-selected).")
        driver = uc.Chrome(options=options)
    return driver

def makeRoleDict(role):
    template = {
                    "type": "hero-role",
                    "attributes": {
                        "roleId": role.lower(),
                        "season": 11,
                        "mode": "competitive"
                    },
                    "metadata": {
                        "name": role,
                        "imageUrl": "https://trackercdn.com/cdn/tracker.gg/marvel-rivals/images/roles/duelist.png"
                    },
                    "expiryDate": "0001-01-01T00:00:00+00:00",
                    "stats": {
                        "timePlayed": {
                            "displayName": "Time Played",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0m",
                            "displayType": "TimeSeconds"
                        },
                        "timePlayedWon": {
                            "displayName": "Time Played Won",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "4h 39m",
                            "displayType": "TimeSeconds"
                        },
                        "matchesPlayed": {
                            "displayName": "Matches Played",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "NumberPrecision1"
                        },
                        "matchesWon": {
                            "displayName": "Wins",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "matchesWinPct": {
                            "displayName": "Win %",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0%",
                            "displayType": "NumberPercentage"
                        },
                        "kills": {
                            "displayName": "Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "deaths": {
                            "displayName": "Deaths",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "30",
                            "displayType": "Number"
                        },
                        "assists": {
                            "displayName": "Assists",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "kdRatio": {
                            "displayName": "K/D Ratio",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "NumberPrecision2"
                        },
                        "kdaRatio": {
                            "displayName": "KDA Ratio",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "NumberPrecision2"
                        },
                        "totalHeroDamage": {
                            "displayName": "Damage",
                            "displayCategory": "Damage",
                            "category": "damage",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "totalHeroDamagePerMinute": {
                            "displayName": "Damage/Min",
                            "displayCategory": "Damage",
                            "category": "damage",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "totalHeroHeal": {
                            "displayName": "Healing",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": 0,
                            "displayType": "Number"
                        },
                        "totalHeroHealPerMinute": {
                            "displayName": "Healing/Min",
                            "displayCategory": "Healing",
                            "category": "healing",
                            "metadata": {},
                            "value": 0.0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "totalDamageTaken": {
                            "displayName": "Damage Blocked",
                            "displayCategory": "Damage",
                            "category": "damage",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "totalDamageTakenPerMinute": {
                            "displayName": "Damage Blocked/Min",
                            "displayCategory": "Damage",
                            "category": "damage",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "lastKills": {
                            "displayName": "Last Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "headKills": {
                            "displayName": "Head Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "soloKills": {
                            "displayName": "Solo Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "survivalKills": {
                            "displayName": "Survival Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 578,
                            "displayValue": "578",
                            "displayType": "Number"
                        },
                        "continueKills": {
                            "displayName": "Continue Kills",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 158,
                            "displayValue": "158",
                            "displayType": "Number"
                        },
                        "continueKills3": {
                            "displayName": "Continue Kills 3",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 29,
                            "displayValue": "29",
                            "displayType": "Number"
                        },
                        "continueKills4": {
                            "displayName": "Continue Kills 4",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 6,
                            "displayValue": "6",
                            "displayType": "Number"
                        },
                        "continueKills5": {
                            "displayName": "Continue Kills 5",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 2,
                            "displayValue": "2",
                            "displayType": "Number"
                        },
                        "continueKills6": {
                            "displayName": "Continue Kills 6",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 1,
                            "displayValue": "1",
                            "displayType": "Number"
                        },
                        "mainAttacks": {
                            "displayName": "Main Attacks",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 1613588,
                            "displayValue": "1,613,588",
                            "displayType": "Number"
                        },
                        "mainAttackHits": {
                            "displayName": "Main Attack Hits",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 613287,
                            "displayValue": "613,287",
                            "displayType": "Number"
                        },
                        "shieldHits": {
                            "displayName": "Shield Hits",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 169158,
                            "displayValue": "169,158",
                            "displayType": "Number"
                        },
                        "summonerHits": {
                            "displayName": "Summoner Hits",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 12382,
                            "displayValue": "12,382",
                            "displayType": "Number"
                        },
                        "chaosHits": {
                            "displayName": "Chaos Hits",
                            "displayCategory": "Combat",
                            "category": "combat",
                            "metadata": {},
                            "value": 82809,
                            "displayValue": "82,809",
                            "displayType": "Number"
                        },
                        "totalMvp": {
                            "displayName": "MVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        },
                        "totalSvp": {
                            "displayName": "SVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 0,
                            "displayValue": "0",
                            "displayType": "Number"
                        }
                    }}
    return template
def getTrackerGG_MatchDetails(mid):
    
    time.sleep(0.15)
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/{mid}" 
    try:

        # GET STATS
        # driver.get(url)
        # pre = WebDriverWait(driver=driver, timeout=4,poll_frequency=0.1).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "pre"))
        # )

        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception: fetching MATCH DETAILS for {mid}: {e}")
        if "ERR_INTERNET_DISCONNECTED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            return "END"
        return False

def is_chrome_error_page(driver):
    text = f"{driver.title}\n{driver.page_source}"
    markers = (
        "ERR_TIMED_OUT",
        "ERR_CONNECTION_RESET",
        "ERR_CONNECTION_CLOSED",
        "ERR_NAME_NOT_RESOLVED",
        "ERR_INTERNET_DISCONNECTED",
        "ERR_NETWORK_CHANGED",
    )
    return next((m for m in markers if m in text), None)



def getTrackerGGEncounters(player_name, season, mode):
    #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
                #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"
    time.sleep(0.15)
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{ign_enc}/aggregated?localOffset=300&filter=encounters&mode=competitive" 
    try:

        # GET STATS
        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception: fetching ENCOUNTERS for {player_name}: {e}")
        if "ERR_INTERNET_DISCONNECTED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            return "END"
        return False
    
def getTrackerGGMatches(player_name,  season, mode):
    #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
                #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")
    time.sleep(0.15)
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/ign/{ign_enc}?mode={mode}&season={season}" 
    try:

        # GET STATS
        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception:fetching MATCHES for {player_name}: {e}")
        return False


def getTrackerGGOverview(player_name, mode):
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")  # safest; encodes spaces, unicode, symbols

    url = (
        f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/"
        f"{ign_enc}/segments/career?mode={mode}"
    )
    try:

        # GET STATS
        # driver.get(url)
        # err = is_chrome_error_page(driver)

        err = BROWSER.get_test(url)
        if err:
            return False 
        pre = BROWSER.fetch_url(url)
        
        # WebDriverWait(driver=driver, timeout=4,poll_frequency=0.1).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "pre"))
        # )
        raw_json = pre.text
        data = json.loads(raw_json)

        

        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception: fetching OVERVIEW for {player_name}: {e}")
        if "ERR_INTERNET_DISCONNECTED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            return "END"
        return False
    
def getTrackerGGCareerAllTime(player_name ):
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")  # safest; encodes spaces, unicode, symbols

    url = (
        f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{ign_enc}/segments/career?mode=all"
    )
    try:

        # GET STATS
        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        # pre = WebDriverWait(driver=driver, timeout=4,poll_frequency=0.1).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "pre"))
        # )
        raw_json = pre.text
        data = json.loads(raw_json)

        

        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception: fetching ALLTIME for {player_name}: {e}")
        if "ERR_INTERNET_DISCONNECTED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            return "END"
        return False

def getTrackerGGProfile(player_name, season, mode):
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")  # safest; encodes spaces, unicode, symbols

    url = (
        f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/"
        f"{ign_enc}/segments/career?mode={mode}&season={season}"
    )
    try:

        # GET STATS
        
        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        raw_json = pre.text
        data = json.loads(raw_json)

        

        if "data" in data and not data["data"]:
            #print(f"❌ No matchd data {player_name}")
            return False
        error_check = data.get("errors", False)
        if error_check:
            if isinstance(error_check, list) and len(error_check) > 0:
                eror = error_check[0].get("code", False)
                if eror and isinstance(eror, str):
                    if "Private" in eror:
                        #print(f"❌ Profile for {player_name} is private.")
                        return "private"
                    else:
                        return False
                if "private" in eror.lower():
                    #print(f"❌ Profile for {player_name} is private.")
                    return "private"
        
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Exception: fetching PROFILE for {player_name}: {e}")
        if "ERR_INTERNET_DISCONNECTED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            return "END"
        return False


def check_matches_played(data):
    matches = data['data']['segments'][0]['stats']['matchesPlayed']['value']
    return matches


import copy

ADD_STATS = {
    "timePlayed",
    "timePlayedWon",
    "matchesPlayed",
    "matchesWon",
    "kills",
    "deaths",
    "assists",
    "totalHeroDamage",
    "totalHeroHeal",
    "totalDamageTaken",
    "lastKills",
    "headKills",
    "soloKills",
    "totalMvp",
    "totalSvp",
    "shieldHits",
    "mainAttacks",
    "mainAttackHits",
    "summonerHits",
    "chaosHits",
    "featureNormalData1",
    "featureNormalData2",
    "featureCriticalRate1CritHits",
    "featureCriticalRate1Hits",
}


def getHerosList(dat):
    return [segment for segment in dat["data"]["segments"] if segment["type"] == "hero"]


def getRolesList(dat):
    return [segment for segment in dat["data"]["segments"] if segment["type"] == "hero-role"]


def index_segments_by_name(segments):
    out = {}
    for seg in segments:
        name = seg.get("metadata", {}).get("name")
        if name:
            out[name] = seg
    return out


def merge_stat_blocks(stats_new, stats_old):
    """
    Merge only additive/raw stats from stats_old into stats_new, in place.
    Ignores displayValue and all derived/rate stats.
    """
    for stat_key, old_stat in stats_old.items():
        if stat_key not in stats_new:
            stats_new[stat_key] = copy.deepcopy(old_stat)
            stats_new[stat_key].pop("displayValue", None)
            continue

        if stat_key not in ADD_STATS:
            continue

        new_stat = stats_new[stat_key]
        new_value = new_stat.get("value")
        old_value = old_stat.get("value")

        if not isinstance(new_value, (int, float)) or not isinstance(old_value, (int, float)):
            continue

        new_stat["value"] = new_value + old_value
        new_stat.pop("displayValue", None)


def mergeTrackerData(data_new, data_old):
    """
    Merge data_old into data_new IN PLACE and return data_new.
    Only raw/additive stats are merged.
    """
    segments_new = data_new["data"]["segments"]

    # overview block
    merge_stat_blocks(
        data_new["data"]["segments"][0]["stats"],
        data_old["data"]["segments"][0]["stats"],
    )

    # heroes
    heroes_new_by_name = index_segments_by_name(getHerosList(data_new))
    for hero_old in getHerosList(data_old):
        hero_name = hero_old.get("metadata", {}).get("name")
        hero_new = heroes_new_by_name.get(hero_name)

        if hero_new:
            merge_stat_blocks(hero_new["stats"], hero_old["stats"])
        else:
            copied = copy.deepcopy(hero_old)
            for stat in copied.get("stats", {}).values():
                stat.pop("displayValue", None)
            segments_new.append(copied)

    # roles
    roles_new_by_name = index_segments_by_name(getRolesList(data_new))
    for role_old in getRolesList(data_old):
        role_name = role_old.get("metadata", {}).get("name")
        role_new = roles_new_by_name.get(role_name)

        if role_new:
            merge_stat_blocks(role_new["stats"], role_old["stats"])
        else:
            copied = copy.deepcopy(role_old)
            for stat in copied.get("stats", {}).values():
                stat.pop("displayValue", None)
            segments_new.append(copied)

    return data_new


def updateFinalHeroStats(hero_stats):
    print()("Updating final hero stats...")

def get_browser_major_version(exe_path: str, default: int = 144) -> int:
    try:
        out = subprocess.check_output([exe_path, "--version"], text=True, stderr=subprocess.STDOUT)
        # Brave outputs like: "Brave Browser 144.0.7559.110"
        # Chrome outputs like: "Google Chrome 144.0.7559.110"
        m = re.search(r"(\d+)\.", out)
        return int(m.group(1)) if m else default
    except Exception:
        return default
    
def fetch_pre_json(driver, url, label="request"):
    try:
        err = BROWSER.get_test(url)
        if err:
            return False 
        
        
        pre = BROWSER.fetch_url(url)
        data = json.loads(pre.text)

        if ("data" in data and not data["data"]) or ("errors" in data):
            return data

        return data
    except Exception as e:
        print(f"❌ Error loading JSON for {label}: {e}")
        return None
        
def build_player_result(seed_data, segments, matches, seasons, overview_data=None, alltime=False):
    base = seed_data["data"]
    alldata = alltime.get("data", False) if isinstance(alltime, dict) else False
    out = {
        "data": {
            "metadata": dict(base.get("metadata", {})),
            "userInfo": dict(base.get("userInfo", {})),
            "platformInfo": dict(base.get("platformInfo", {})),
            "segments": segments,
            "matches": matches,
            "alltime_segments": alldata,
            "seas": [str(s) for s in seasons],
        }
    }

    if "expiryDate" in base:
        out["data"]["expiryDate"] = base["expiryDate"]

    if overview_data:
        a = False if overview_data == "private" else overview_data.get("data", {})
        out["data"]["full_overview"] = a

    return out
 
def check_matches_played_from_segments(segments):
    try:
        if not segments or len(segments) == 0:
            return 0
        return segments[0]["stats"]["matchesPlayed"]["value"]
    except Exception:
        return 0
    
        

def open_multiple_tracker_profiles(player_names):
    # ----------------------------
    # Browser setup
    # ----------------------------
    #kill_selenium_chrome()
    # brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
    # chrome_path = r"C:\Program Files\Google\Chrome\Application"



    # # ---- BRAVE BROWSER DETECTION ----

    # if os.path.exists(brave_path):
    #     bBraveBrowser = True
    #     data_dir = config.brave_data_dir
    #     browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    #     kill_brave_selenium_instances()
    #     brave_major = get_installed_brave_major_version(default=147)



    # # ---- CHROME BROWSER DETECTION ----

    # else: # os.path.exists(chrome_path):
    #     browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    #     bBraveBrowser = False
    #     data_dir = None
    #     chrome_major = get_installed_chrome_major_version(default=147)
    #     #print(f"Detected Chrome major version: {chrome_major}")
    #     kill_selenium_chrome()
    

    season = config.season
    mode = "competitive"

    # # --- NEW: pin UC to your installed Chrome major version ---
    # #chrome_major = get_installed_chrome_major_version(default=138)
    # #print(f"Detected Chrome major version: {chrome_major}")
    # brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    # options = uc.ChromeOptions()
    # if bBraveBrowser:
    #     options.binary_location = browser_path
    # # options.add_argument("--headless=new")  # Optional
    # profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")
    # #os.makedirs(profile_path, exist_ok=True)
    # options.add_argument(f"--user-data-dir={profile_path}")
    
    # options.add_argument("--disable-gpu")
    # options.add_argument("--start-minimized")
    
    # #options.add_argument("--no-first-run")
    # #options.add_argument("--no-default-browser-check")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--no-default-browser-check")
    # options.add_argument("--no-first-run")
    # caps = DesiredCapabilities.CHROME.copy()
    # caps["pageLoadStrategy"] = "eager"
    # #options.add_argument("--window-size=1,1")
    
    # # IMPORTANT: pass version_main
    # if bBraveBrowser:
    #     #brave_major = get_browser_major_version(browser_path, default=144)
    #     #print(f"Detected Brave (Chromium) major version: {brave_major}")
    #     #options.user_data_dir = data_dir

    #     driver = uc.Chrome(options=options, desired_capabilities=caps, use_subprocess=False, user_multi_procs=False, version_main=brave_major)
        
    # else:
    #     driver = uc.Chrome(options=options, desired_capabilities=caps, use_subprocess=False, user_multi_procs=False, version_main=chrome_major)

    # # keep your tiny window behavior
    # driver.set_window_size(1, 1)
    # driver.set_window_position(2559, 1439)
    

    results = {}

    try:
        # ----------------------------
        # Seed payload for metadata/current season
        # ----------------------------
        seed_url = "https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/EyeingFlux"
        pre = BROWSER.fetch_url(seed_url)
        # pre = WebDriverWait(driver=driver, timeout=4,poll_frequency=0.1).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "pre"))
        # )
        seed_data = json.loads(pre.text)

        try:
            api_current_season = int(seed_data["data"]["metadata"]["currentSeason"])
            if api_current_season > season:
                season = api_current_season
                config.season = season

                script_dir = os.path.dirname(os.path.abspath(__file__))
                season_path = os.path.join(script_dir, "season.txt")
                with open(season_path, "w") as f:
                    f.write(str(season))

                print(f"Updated season to {config.season} in config.")
        except Exception:
            pass

        # ----------------------------
        # Per-player fetch
        # ----------------------------
        
        for player_name in player_names:
            player_log = ""
            log_idx = 1
            time.sleep(0.15)
            print(f"\n🔍 Fetching {player_name}...")
            overview = getTrackerGGOverview(player_name, mode)

            if overview == "private":
                player_log += f"{log_idx} - 🔒 OVERVIEW {mode} is Private.\n"
                log_idx += 1

            elif overview is None or overview is False:
                player_log += f"{log_idx} - ❌ OVERVIEW {mode} fetch failed.\n"
                log_idx += 1
            else:
                player_log += f"{log_idx} - ✅ OVERVIEW {mode} fetched successfully.\n"
                log_idx += 1

            
            alltime_data = getTrackerGGCareerAllTime(player_name)
            

            if alltime_data == "private":
                player_log += f"{log_idx} - 🔒 LIFETIME STATS are Private.\n"
                log_idx += 1

            elif alltime_data is None or alltime_data is False:
                player_log += f"{log_idx} - ❌ LIFETIME STATS fetch failed.\n"
                log_idx += 1
            else:
                player_log += f"{log_idx} - ✅ LIFETIME STATS fetched successfully.\n"
                log_idx += 1
                

            current_profile = None
            old_profile = None
            old_result = None
            player_result = None
            match_list = []
            seasons_used = []

            def profile_is_valid(profile):
                return (
                    profile
                    and profile != "private"
                    and not (("data" in profile and not profile["data"]) or ("errors" in profile))
                )

            # ----------------------------
            # Try current season profile first
            # ----------------------------
           
            fetched_current = getTrackerGGProfile(player_name,  season, mode)

            if fetched_current == "private":
                player_log += f"{log_idx} - 🔒 PROFILE for {mode} S{season} is Private.\n"
                log_idx += 1
            elif fetched_current is None or fetched_current is False:
                player_log += f"{log_idx} - ❌ PROFILE for {mode} S{season} fetch failed.\n"
                log_idx += 1
            else:
                current_profile = fetched_current
                player_log += f"{log_idx} - ✅ PROFILE for {mode} S{season} fetched successfully.\n"
                log_idx += 1

            # ----------------------------
            # If current exists, fetch matches and decide whether old season is needed
            # ----------------------------
            if current_profile:
                matches = getTrackerGGMatches(player_name,  season, mode)
                match_list = matches["data"].get("matches", []) if matches and "data" in matches else []
                if len(match_list) == 0:
                    player_log += f"{log_idx} - ⚠️ MATCH HISTORY fetch failed. {mode} S{season}.\n"
                    log_idx += 1
                player_result = build_player_result(
                    seed_data=seed_data,
                    segments=current_profile["data"],
                    matches=match_list,
                    seasons=[season],
                    alltime=alltime_data,
                    overview_data=overview,
                )
                seasons_used = [season]

                matches_played = check_matches_played_from_segments(player_result["data"].get("segments", []))

                if matches_played < 25:
                    player_log += f"{log_idx} - ⚠️ Fetching previous season data: Matches played < 25.\n"
                    log_idx += 1

                    fetched_old = getTrackerGGProfile(player_name, season - 1, mode)
                    if fetched_old == "private":
                        player_log += f"{log_idx} - 🔒 PROFILE for {mode} S{season-1} is Private.\n"
                        log_idx += 1
                    elif fetched_old is None or fetched_old is False:
                
                            player_log += f"{log_idx} - ❌ PROFILE for {mode} S{season-1} fetch failed.\n"
                            log_idx += 1
                    else:
                        old_profile = fetched_old
                        old_result = {
                            "data": {
                                "segments": old_profile["data"]
                            }
                        }

                        mergeTrackerData(player_result, old_result)
                        player_result["data"]["seas"].append(str(season - 1))
                        seasons_used.append(season - 1)

                        player_log += f"{log_idx} - ✅ Older Profile for {mode} S{season-1} fetched and merged successfully.\n"
                        log_idx += 1
                else:
                    player_log += f"{log_idx} - ✅ Season {season} matches played: {matches_played}. Using current season only.\n"
                    log_idx += 1

            # ----------------------------
            # No current profile -> try previous season only
            # ----------------------------
            else:
                Trigger = True
                if fetched_current != "private":

                
                    fetched_old = getTrackerGGProfile(player_name,  season - 1, mode)
                    if fetched_old == "private":
                        player_log += f"{log_idx} - 🔒 PROFILE for {mode} S{season-1} is Private.\n"
                        log_idx += 1
                        player_log += f"{log_idx} - ❌ No current or previous season profile found for {player_name}. Building incomplete result.\n"
                        log_idx += 1
                        player_result = buildBlankResult(seed_data, overview=overview, alltime_data=alltime_data)

                    elif fetched_old is None or fetched_old is False:
                
                        player_log += f"{log_idx} - ❌ Profile for {mode} S{season-1} fetch failed.\n"
                        log_idx += 1
                        player_log += f"{log_idx} - ❌ No current or previous season profile found for {player_name}. Building incomplete result.\n"
                        log_idx += 1
                        player_result = buildBlankResult(seed_data, overview=overview, alltime_data=alltime_data)
                    else:
                        old_profile = fetched_old

                        player_result = build_player_result(
                            seed_data=seed_data,
                            segments=old_profile["data"],
                            matches=[],
                            seasons=[season - 1],
                            overview_data=overview,
                            alltime=alltime_data,
                        )
                        seasons_used = [season - 1]

                        player_log += f"{log_idx} - ✅ Older Profile for {mode} S{season-1} fetched and merged successfully.\n"
                        log_idx += 1
                else:
                    # Build blank result
                    player_log += f"{log_idx} - ❌ No current or previous season profile found for {player_name}. Building incomplete result.\n"
                    log_idx += 1

                    player_result = buildBlankResult(
                        seed_data=seed_data,
                        overview=overview,
                        alltime_data=alltime_data,
                    )
                    seasons_used = []
            print(player_log)
            results[player_name] = player_result

    except Exception as e:
        print(f"❌ EXCEPTION at Main Tracker Block: {e}")
        #if player_log:
            #print(player_log)
        results[player_name] = buildBlankResult(seed_data, overview=overview, alltime_data=alltime_data)

    

    kill_brave_selenium_instances()
    return results

def buildBlankResult(seed_data, overview=None, alltime_data=False):
    return build_player_result(
                        seed_data=seed_data,
                        segments=[],
                        matches=[],
                        seasons=[],
                        alltime=alltime_data,
                        overview_data=overview,
                    )
                

def buildDriver():
    # ----------------------------
    # Browser setup
    # ----------------------------
    #kill_selenium_chrome()
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
    chrome_path = r"C:\Program Files\Google\Chrome\Application"



    # ---- BRAVE BROWSER DETECTION ----

    if os.path.exists(brave_path):
        bBraveBrowser = True
        data_dir = config.brave_data_dir
        browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        kill_brave_selenium_instances()



    # ---- CHROME BROWSER DETECTION ----

    else: # os.path.exists(chrome_path):
        browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        bBraveBrowser = False
        data_dir = None
        chrome_major = get_installed_chrome_major_version(default=144)
        print(f"Detected Chrome major version: {chrome_major}")
        kill_selenium_chrome()
    

    season = config.season
    mode = "competitive"

    # --- NEW: pin UC to your installed Chrome major version ---
    #chrome_major = get_installed_chrome_major_version(default=138)
    #print(f"Detected Chrome major version: {chrome_major}")
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    options = uc.ChromeOptions()
    if bBraveBrowser:
        options.binary_location = browser_path
    # options.add_argument("--headless=new")  # Optional
    profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")
    #os.makedirs(profile_path, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_path}")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--start-minimized")
    
    #options.add_argument("--no-first-run")
    #options.add_argument("--no-default-browser-check")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_argument("--window-size=1,1")
    
    # IMPORTANT: pass version_main
    if bBraveBrowser:
        #brave_major = get_browser_major_version(browser_path, default=144)
        #print(f"Detected Brave (Chromium) major version: {brave_major}")
        #options.user_data_dir = data_dir

        driver = uc.Chrome(options=options, version_main=146)
        
    else:
        driver = uc.Chrome(options=options, version_main=chrome_major)

    # keep your tiny window behavior
    driver.set_window_size(1, 1)
    driver.set_window_position(2559, 1439)
    

    return driver
import random
def fetchNamesForDB(names):
    global NAMES_LIST
    driver = buildDriver()
    from playerNEW import Player
    from stats_db import StatsDB
    dbd = StatsDB()
    NAMES_LIST = []
    NAMES_LIST = dbd.get_all_player_names()
    names_path = helpers.create_path(file="names_list.txt", folder=config.sqlite_db_dir)
    helpers.save_list(names_path, NAMES_LIST)
    count = 0
    try:
        for name in names:
            if name not in NAMES_LIST:
                NAMES_LIST.append(name)
            print(f"Fetching encounters for {name}...")
            time.sleep(random.uniform(1, 2.5))
            encounter_data = getTrackerGGEncounters(name, driver, config.season, "competitive")
            if not encounter_data:
                count += 1
                print(f"❌ Chrome error page detected while fetching encounters for {name}. Skipping.")
                if count >= 3:
                    print(f"1) Count Error - {count}")
                    break
                continue
            if encounter_data and "data" in encounter_data and "enemies" in encounter_data["data"]:
                enemies = encounter_data['data'].get('enemies', None)
                if enemies:
                    st = iterateEnemiesTeammates(enemies, driver, dbd)

                    if not st:
                        count += 1
                        if count >= 3:
                            print(f"2) Count Error - {count}")
                            break
                    if st == "END":
                        print("❌ Internet disconnected detected. Ending fetch.")
                        break
                    else:
                        print(f"\n✅ 1/2 {name}'s encounters fetched. Saving DB 💾")
                        dbd.close()
                        dbd = StatsDB()  # reopen to refresh connection
                        
                        helpers.save_list(names_path, NAMES_LIST)


                teammates = encounter_data['data'].get('teammates', None)
                if teammates:
                    st = iterateEnemiesTeammates(teammates, driver, dbd)
                    if not st:
                        count += 1
                        if count >= 3:
                            print(f"3) Count Error - {count}")
                            break
                    if st == "END":
                        print("❌ Internet disconnected detected. Ending fetch.")
                        break
                    else:
                        print(f"\n✅ 1/2 {name}'s encounters fetched. Saving DB 💾")
                        dbd.close()
                        dbd = StatsDB()  # reopen to refresh connection
                        
                        helpers.save_list(names_path, NAMES_LIST)

        
        dbd.close()
        helpers.save_list(names_path, NAMES_LIST)
    except Exception as e:
        print(f"❌ Error during fetchNamesForDB: {e}")
    finally:
        try:
            driver.quit()
            dbd.close()
            helpers.save_list(names_path, NAMES_LIST)
        except Exception:
            pass
        kill_brave_selenium_instances()


def iterateEnemiesTeammates(enList, driver, dbd):
    from playerNEW import Player
    from stats_db import StatsDB
    global NAMES_LIST
    if enList is None:
        return False
    if len(enList) < 1:
        return False
    count = 0
    for dic in enList:
        try:
            ign = dic['platformInfo'].get('platformUserHandle', None)

            if ign:
                if ign in NAMES_LIST:
                    print(f"⚠️ {ign} already in DB. Skipping.")
                    continue
                
                time.sleep(random.uniform(1, 2.5))

                overview = getTrackerGGOverview(ign, driver,"competitive")
                
                if overview == "private":
                    print(f"🔒 {ign} is Private.")
                    
                    continue
                if overview == "END":
                    return "END"
                if overview == "ERROR":
                    print(f"❌ Chrome error page detected while fetching overview for {ign}. Skipping.")
                    return "ERROR"
                    continue
                if not overview:
                    print(f"❌ Failed overview fetch for {ign}.")
                    count += 1
                    if count >= 3:
                        print(f"4) Count Error - {count}")
                        return False
                    continue
                print(f"✅ {ign} overview fetched.")
                json_data = buildJSONTemplate(overview, ign)
                p = Player(name=ign, json_data=json_data, bDB=True)
                obs = dbd.upsert_players([p])
                NAMES_LIST.append(ign)
    
        except Exception as e:
            print(f"❌ Error processing {ign}: {e}")
            continue
    return True



def buildJSONTemplate(overview, ign):
    data2 = {
            "data": {
                "metadata": {
                    "lastUpdated": {
                        "value": "2000-01-01T00:00:00+00:00",
                        "displayValue": "2000-01-01T00:00:00.0000000+00:00"
                    },
                    "level": 45,
                    "gamemodes": [
                        {
                            "id": "competitive",
                            "name": "Competitive"
                        },
                        {
                            "id": "quick-match",
                            "name": "Quick Match"
                        },
                        {
                            "id": "arcade",
                            "name": "Arcade"
                        },
                        {
                            "id": "18v18-annihilation",
                            "name": "18v18 Annihilation"
                        },
                        {
                            "id": "tournament",
                            "name": "Tournament"
                        },
                        {
                            "id": "event",
                            "name": "Event"
                        }
                    ],
                    "currentSeason": 13,
                    "defaultSeason": 13,
                    "seasons": [
                        {
                            "id": 13,
                            "name": "S6.5: Night at the Museum",
                            "shortName": "S6.5"
                        },
                        {
                            "id": 12,
                            "name": "S6: Night at the Museum",
                            "shortName": "S6"
                        },
                        {
                            "id": 11,
                            "name": "S5.5: Love is a Battlefield",
                            "shortName": "S5.5"
                        },
                        {
                            "id": 10,
                            "name": "S5: Love is a Battlefield",
                            "shortName": "S5"
                        },
                        {
                            "id": 9,
                            "name": "S4.5: Heart of the Dragon",
                            "shortName": "S4.5"
                        },
                        {
                            "id": 8,
                            "name": "S4: Heart of the Dragon",
                            "shortName": "S4"
                        },
                        {
                            "id": 7,
                            "name": "S3.5: The Abyss Awakens",
                            "shortName": "S3.5"
                        },
                        {
                            "id": 6,
                            "name": "S3: The Abyss Awakens",
                            "shortName": "S3"
                        },
                        {
                            "id": 5,
                            "name": "S2.5: Hellfire Gala",
                            "shortName": "S2.5"
                        },
                        {
                            "id": 4,
                            "name": "S2: Hellfire Gala",
                            "shortName": "S2"
                        },
                        {
                            "id": 3,
                            "name": "S1.5: Eternal Night Falls",
                            "shortName": "S1.5"
                        },
                        {
                            "id": 2,
                            "name": "S1: Eternal Night Falls",
                            "shortName": "S1"
                        },
                        {
                            "id": 1,
                            "name": "S0: Dooms' Rise",
                            "shortName": "S0"
                        }
                    ]
                },
                "userInfo": {
                    "userId": None,
                    "isPremium": False,
                    "isVerified": False,
                    "isInfluencer": False,
                    "isPartner": False,
                    "countryCode": None,
                    "customAvatarUrl": None,
                    "customHeroUrl": None,
                    "customAvatarFrame": None,
                    "customAvatarFrameInfo": None,
                    "premiumDuration": None,
                    "socialAccounts": [],
                    "badges": None,
                    "pageviews": 157,
                    "xpTier": None,
                    "isSuspicious": None
                },
                "platformInfo": {
                    "platformSlug": "ign",
                    "platformUserId": None,
                    "platformUserHandle": ign,
                    "platformUserIdentifier": ign,
                    "avatarUrl": "https://trackercdn.com/cdn/tracker.gg/marvel-rivals/images/items/nameplates/avatars/31049203.jpg?v=1736499894",
                    "additionalParameters": None
                },
                "segments": [],
                "matches": [],
                "seas": [
                    "13",
                    "12"
                ],
                "expiryDate": "2026-03-16T11:18:17.2272207+00:00",
                "full_overview": overview["data"]
        }}
    return data2

class Browser:
    def __init__(self):

        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
        if os.path.exists(brave_path):
            bBraveBrowser = True
            data_dir = config.brave_data_dir
            browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
            kill_brave_selenium_instances()
            brave_major = get_installed_brave_major_version(default=147)
        # ---- CHROME BROWSER DETECTION ----
        else: 
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            bBraveBrowser = False
            data_dir = None
            chrome_major = get_installed_chrome_major_version(default=147)
            #print(f"Detected Chrome major version: {chrome_major}")
            kill_selenium_chrome()

        
        self.options = uc.ChromeOptions()
        if bBraveBrowser:
            self.options.binary_location = browser_path
        profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")

        self.options.add_argument(f"--user-data-dir={profile_path}")
        
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--start-minimized")
        self.options.set_capability(
        "goog:loggingPrefs",
        {
            "performance": "ALL",
            "browser": "ALL",
        },
    )
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--no-default-browser-check")
        self.options.add_argument("--no-first-run")
        self.caps = DesiredCapabilities.CHROME.copy()
        self.caps["pageLoadStrategy"] = "eager"

        if bBraveBrowser:
            self.driver = uc.Chrome(options=self.options, desired_capabilities=self.caps, use_subprocess=False, user_multi_procs=False, version_main=brave_major)
        else:
            self.driver = uc.Chrome(options=self.options, desired_capabilities=self.caps, use_subprocess=False, user_multi_procs=False, version_main=chrome_major)
        self.driver.execute_cdp_cmd(
        "Network.enable",
        {
            "maxTotalBufferSize": 100_000_000,
            "maxResourceBufferSize": 50_000_000,
            "maxPostDataSize": 10_000_000,
        },
    )
        self.driver.set_window_size(1, 1)
        self.driver.set_window_position(2559, 1439)

    def wait_for_captcha(self, timeout=60):
        try:
            WebDriverWait(self.driver, timeout).until(
                    lambda d: d.title != "Just a moment..."
                )
            return True
        except Exception:
            return False
        
    def set_captcha_window(self):
        self.driver.set_window_size(1200, 900)
        self.driver.set_window_position(100, 100)

    def set_tiny_window(self):
        self.driver.set_window_size(1, 1)
        self.driver.set_window_position(2559, 1439)
    
    def get_driver(self):
        return self.driver
    def get_test(self,url):

        driver = self.driver
        driver.get(url)
        text = f"{driver.title}\n{driver.page_source}"
        markers = (
            "ERR_TIMED_OUT",
            "ERR_CONNECTION_RESET",
            "ERR_CONNECTION_CLOSED",
            "ERR_NAME_NOT_RESOLVED",
            "ERR_INTERNET_DISCONNECTED",
            "ERR_NETWORK_CHANGED",
        )
        return next((m for m in markers if m in text), None)
    def close(self):
        driver,self.driver=self.driver,None
        if driver is not None:
            try: driver.quit()
            except Exception: pass
    
    def fetch_url(self, url):
        self.driver.get(url)
        pre = WebDriverWait(driver=self.driver, timeout=4,poll_frequency=0.1).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        return pre
    
    def get(self, url):
        self.driver.get(url)
        text = f"{self.driver.title}\n{self.driver.page_source}"
        markers = (
            "ERR_TIMED_OUT",
            "ERR_CONNECTION_RESET",
            "ERR_CONNECTION_CLOSED",
            "ERR_NAME_NOT_RESOLVED",
            "ERR_INTERNET_DISCONNECTED",
            "ERR_NETWORK_CHANGED",
        )
        return next((m for m in markers if m in text), None)
    
    def fetch_post(self, url, payload, timeout=10):
        self.driver.set_script_timeout(timeout)

        script = """
            const url = arguments[0];
            const payload = arguments[1];
            const done = arguments[arguments.length - 1];

            fetch(url, {
                method: "POST",
                credentials: "include",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            })
            .then(async response => {
                const text = await response.text();

                done({
                    ok: response.ok,
                    status: response.status,
                    statusText: response.statusText,
                    url: response.url,
                    contentType: response.headers.get("content-type"),
                    text: text
                });
            })
            .catch(error => {
                done({
                    ok: false,
                    status: 0,
                    error: String(error),
                    text: ""
                });
            });
        """

        result = self.driver.execute_async_script(
            script,
            url,
            payload,
        )

        if result.get("error"):
            raise RuntimeError(
                f"Browser fetch failed: {result['error']}"
            )

        if not result.get("ok"):
            raise RuntimeError(
                f"HTTP {result.get('status')} "
                f"{result.get('statusText', '')}\n"
                f"{result.get('text', '')[:1000]}"
            )

        try:
            return json.loads(result["text"])
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Response was not valid JSON.\n"
                f"Content-Type: {result.get('contentType')}\n"
                f"Body: {result.get('text', '')[:1000]}"
            ) from exc
    
BROWSER = Browser()