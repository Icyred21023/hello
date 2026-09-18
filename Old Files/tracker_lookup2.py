import undetected_chromedriver as uc
from collections import defaultdict
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
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
# --- NEW: helper to detect Chrome major version on Windows ---


def get_installed_chrome_major_version(default=139):
    

    path = r"C:\Program Files\Google\Chrome\Application"   # replace with your target path
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    try:
        for f in folders:
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', f):
                default = int(f.split('.')[0])
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

def kill_brave_selenium_instances():
    TARGET_SUBSTRING = "selenium_admin_profile"  # <--- match only the Selenium sessions

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "brave.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if TARGET_SUBSTRING.lower() in cmdline.lower():
                    print(f"🔪 Killing Brave PID {proc.pid} | CMD: {cmdline[:120]}...")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("✅ Finished scanning for Brave Selenium instances.")

uc.Chrome.__del__ = safe_del


def get_installed_brave_major_version(default=None):
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
def getTrackerGG_MatchDetails(driver, mid):
    
    time.sleep(0.15)
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/{mid}" 
    try:

        # GET STATS
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"] or "errors" in data:
            print(f"❌ Match data not found for match ID {mid}")
            return False
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Error loading JSON for match ID {mid}: {e}")

    

def getTrackerGGEncounters(player_name, driver, season, mode):
    #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
                #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"
    time.sleep(0.15)
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{ign_enc}/aggregated?localOffset=300&filter=encounters&mode=competitive" 
    try:

        # GET STATS
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"] or "errors" in data:
            print(f"❌ No matchd data {player_name}")
            return False
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Error loading JSON for {player_name}: {e}")
    
def getTrackerGGMatches(player_name, driver, season, mode):
    #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
                #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")
    time.sleep(0.15)
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/ign/{ign_enc}?mode={mode}&season={season}" 
    try:

        # GET STATS
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)

        
        ####################
        if "data" in data and not data["data"] or "errors" in data:
            print(f"❌ No matchd data {player_name}")
            return False
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Error loading JSON for {player_name}: {e}")


def getTrackerGGOverview(player_name, driver, mode):
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")  # safest; encodes spaces, unicode, symbols

    url = (
        f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/"
        f"{ign_enc}/segments/career?mode={mode}"
    )
    try:

        # GET STATS
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)

        

        if "data" in data and not data["data"] or "errors" in data:
            if isinstance(data["errors"], list):
                eror = data["errors"][0]["code"]
                if "private" in eror.lower():
                    print(f"❌ Profile for {player_name} is private.")
                    return "private"
                
            
            print(f"❌ No data found for {player_name}")
            return False
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Error loading JSON for {player_name}: {e}")
        return None

def getTrackerGGProfile(player_name, driver, season, mode):
    ign = (player_name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")  # safest; encodes spaces, unicode, symbols

    url = (
        f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/"
        f"{ign_enc}/segments/career?mode={mode}&season={season}"
    )
    try:

        # GET STATS
        driver.get(url)
        pre = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )
        raw_json = pre.text
        data = json.loads(raw_json)

        

        if "data" in data and not data["data"] or "errors" in data:
            if isinstance(data["errors"], list):
                eror = data["errors"][0]["code"]
                if "private" in eror.lower():
                    print(f"❌ Profile for {player_name} is private.")
                    return "private"
                
            
            print(f"❌ No data found for {player_name}: Season {season}. Retrying with season {season - 1}...")
            return False
        if data:
            return data
        else:
            return False
    except Exception as e:
        print(f"❌ Error loading JSON for {player_name}: {e}")
        return None


def check_matches_played(data):
    matches = data['data']['segments'][0]['stats']['matchesPlayed']['value']
    return matches

def getHerosList(dat):
            heros = []
            for segment in dat["data"]["segments"]:
                if segment["type"] == "hero":
                    heros.append(segment)
            return heros  

def getRolesList(dat):
            roles = []
            for segment in dat["data"]["segments"]:
                if segment["type"] == "hero-role":
                    roles.append(segment)
            return roles

def mergeTrackerData(data_new, data_old):

    add_list = ["timePlayed","timePlayedWon","matchesPlayed","matchesWon","kills","deaths","assists","totalHeroDamage","totalHeroHeal","totalDamageTaken","lastKills","headKills", "soloKills","totalMvp","totalSvp", "shieldHits", "mainAttacks", "mainAttackHits", "summonerHits", "chaosHits", "featureNormalData1", "featureNormalData2", 'featureCriticalRate1CritHits', 'featureCriticalRate1Hits']
    avg_list = ["aas"]
    logic_list = ["kdRatio","kdaRatio","matchesWinPct","totalHeroDamagePerMinute","totalHeroHealPerMinute","totalDamageTakenPerMinute", "totalMvpPct", "totalSvpPct"]
    combined = copy.deepcopy(data_new)
    stats_old = data_old['data']['segments'][0]['stats']
    stats_new = combined['data']['segments'][0]['stats']
    heros_old = getHerosList(data_old)
    heros_new = getHerosList(combined)
    roles_old = getRolesList(data_old)
    roles_new = getRolesList(combined)
    for key in stats_new:
        if key in stats_old:
            #stat_type  = stats_new[key]['displayName']
            new_value = stats_new[key]['value']
            old_value = stats_old[key]['value']
            if key in add_list:
                if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                    together = new_value + old_value
                    stats_new[key]['value'] = together
                    stats_new[key]['displayValue'] = str(int(together)) if stats_new[key]['displayType'] == "Number" else stats_new[key]['displayValue']
            elif key in avg_list:
                if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                    together = (new_value + old_value) / 2
                    stats_new[key]['value'] = together
                    stats_new[key]['displayValue'] = str(int(together)) if stats_new[key]['displayType'] == "Number" else stats_new[key]['displayValue']
            else:
                continue
        else:
            stats_new[key] = stats_new[key]
    for hero_old_key in heros_old:
        bHeroFound = False
        hero_name_old = hero_old_key['metadata']['name']
        for hero_new_key in heros_new:
            hero_name_new = hero_new_key['metadata']['name']
            if hero_name_old == hero_name_new:
                bHeroFound = True
                stats_old_hero = hero_old_key['stats']
                stats_new_hero = hero_new_key['stats']
                for stat_key in stats_new_hero:
                    if stat_key in stats_old_hero:
                        new_value = stats_new_hero[stat_key]['value']
                        old_value = stats_old_hero[stat_key]['value']
                        if stat_key in add_list:
                            if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                                together = new_value + old_value
                                stats_new_hero[stat_key]['value'] = together
                                stats_new_hero[stat_key]['displayValue'] = str(int(together)) if stats_new_hero[stat_key]['displayType'] == "Number" else stats_new_hero[stat_key]['displayValue']
                        elif stat_key in avg_list:
                            if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                                together = (new_value + old_value) / 2
                                stats_new_hero[stat_key]['value'] = together
                                stats_new_hero[stat_key]['displayValue'] = str(int(together)) if stats_new_hero[stat_key]['displayType'] == "Number" else stats_new_hero[stat_key]['displayValue']
                        else:
                            continue
                    else:
                        stats_new_hero[stat_key] = stats_new_hero[stat_key]
        if not bHeroFound:
            combined['data']['segments'].append(hero_old_key)
        bHeroFound = False

    for role_old_key in roles_old:
        bRoleFound = False
        role_old_name = role_old_key['metadata']['name']
        for role_new_key in roles_new:
            role_new_name = role_new_key['metadata']['name']
            if role_old_name == role_new_name:
                bRoleFound = True
                stats_old_role = role_old_key['stats']
                stats_new_role = role_new_key['stats']
                
                for stat_key in stats_new_role:
                    if stat_key in stats_old_role:
                        if role_old_name == "Strategist" and stat_key == 'matchesPlayed':
                            print("Debug")
                        new_value = stats_new_role[stat_key]['value']
                        old_value = stats_old_role[stat_key]['value']
                        if stat_key in add_list:
                            if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                                together = new_value + old_value
                                stats_new_role[stat_key]['value'] = together
                                stats_new_role[stat_key]['displayValue'] = str(int(together)) if stats_new_role[stat_key]['displayType'] == "Number" else stats_new_role[stat_key]['displayValue']
                        elif stat_key in avg_list:
                            if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                                together = (new_value + old_value) / 2
                                stats_new_role[stat_key]['value'] = together
                                stats_new_role[stat_key]['displayValue'] = str(int(together)) if stats_new_role[stat_key]['displayType'] == "Number" else stats_new_role[stat_key]['displayValue']
                        else:
                            continue
                    else:
                        stats_new_role[stat_key] = stats_new_role[stat_key]
        
        if not bRoleFound:
            combined['data']['segments'].append(role_old_key)
        bRoleFound = False
        
                
    return combined

def transformPrivateData(data, rankedseg):
    copied_names = []
    matches = copy.deepcopy(data['data']['matches'])
    season = data['data']['seas']
    overview_segments = data['data']['segments']
    priv_stats = data['data']['encounter_stats']
    match_counts = {}
    strategist = makeRoleDict("Strategist")
    duelist = makeRoleDict("Duelist")
    vanguard = makeRoleDict("Vanguard")
    overview_segments.extend([strategist, duelist, vanguard])
    variable_role = None
    role_map = {
    "Strategist": strategist,
    "Duelist": duelist,
    "Vanguard": vanguard,
}
    for match in matches:
        segments = match['segments']
        for segment in segments:
            bAddToRole = False
            seg_type = segment['type']
            if seg_type == "overview":
                name = segment['metadata']['platformInfo']['platformUserHandle']
            elif  seg_type == "hero":
                name = segment['metadata']['name']
                bAddToRole = True
                

                

            if name not in copied_names:

                copied_names.append(name)
                match_counts[name] = 1

                overview_segments.append(copy.deepcopy(segment))
                if bAddToRole:
                    role = segment['metadata']['roleName']
                    variable_role = role_map.get(role)
                    addFirstSegmentToRole(segment, variable_role)
                continue
            
            for ov in overview_segments:
                st = ov['type']
                if st == 'hero-role':
                    continue
                if st == 'overview':
                    ov_name = ov['metadata']['platformInfo']['platformUserHandle']
                elif st == 'hero':
                    ov_name = ov['metadata']['name']
                    role = segment['metadata']['roleName']
                    if role == "Strategist" or role == "Duelist" or role == "Vanguard":
                        variable_role = role_map.get(role)
                else:
                    print("Unknown segment type:", st)
                if name == ov_name:
                    match_counts[name] += 1
                    break

            ov['stats']['timePlayed']['value'] += segment['stats']['timePlayed']['value']
            if bAddToRole:
                variable_role['stats']['timePlayed']['value'] += segment['stats']['timePlayed']['value']

            ov['stats']['matchesPlayed']['value'] += segment['stats']['matchesPlayed']['value']
            if bAddToRole:
                variable_role['stats']['matchesPlayed']['value'] += segment['stats']['matchesPlayed']['value']

            ov['stats']['matchesWon']['value'] += segment['stats']['matchesWon']['value']
            if bAddToRole:
                variable_role['stats']['matchesWon']['value'] += segment['stats']['matchesWon']['value']

            ov['stats']['matchesWinPct']['value'] = round((ov['stats']['matchesWon']['value'] / ov['stats']['matchesPlayed']['value'] * 100), 2) if ov['stats']['matchesPlayed']['value'] > 0 else 0
            if bAddToRole:
                variable_role['stats']['matchesWinPct']['value'] = round((variable_role['stats']['matchesWon']['value'] / variable_role['stats']['matchesPlayed']['value'] * 100), 2) if variable_role['stats']['matchesPlayed']['value'] > 0 else 0

            ov['stats']['matchesWinPct']['displayValue'] = str(int(round(ov['stats']['matchesWinPct']['value']))) + "%"
            if bAddToRole:
                variable_role['stats']['matchesWinPct']['displayValue'] = str(int(round(variable_role['stats']['matchesWinPct']['value']))) + "%"
            ov['stats']['kills']['value'] += segment['stats']['kills']['value']
            if bAddToRole:
                variable_role['stats']['kills']['value'] += segment['stats']['kills']['value']

            ov['stats']['deaths']['value'] += segment['stats']['deaths']['value']
            if bAddToRole:
                variable_role['stats']['deaths']['value'] += segment['stats']['deaths']['value']

            ov['stats']['assists']['value'] += segment['stats']['assists']['value']
            if bAddToRole:
                variable_role['stats']['assists']['value'] += segment['stats']['assists']['value']

            matchesw = round(ov['stats']['matchesWon']['value'],1)

            if bAddToRole:
                matcheswr = round(variable_role['stats']['matchesWon']['value'],1)

            matchesl = round(ov['stats']['matchesPlayed']['value'] - ov['stats']['matchesWon']['value'],1)
            if bAddToRole:
                matcheslr = round(variable_role['stats']['matchesPlayed']['value'] - variable_role['stats']['matchesWon']['value'],1)

            time = ov['stats']['timePlayed']['value']
            if bAddToRole:
                time_role = variable_role['stats']['timePlayed']['value']
            kills = ov['stats']['kills']['value']
            if bAddToRole:
                kills_role = variable_role['stats']['kills']['value']
            assists = ov['stats']['assists']['value']
            if bAddToRole:
                assists_role = variable_role['stats']['assists']['value']
            deaths = ov['stats']['deaths']['value']
            if bAddToRole:
                deaths_role = variable_role['stats']['deaths']['value']

            ov['stats']['kdaRatio']['value'] = round(
                (kills + assists) / max(deaths, 1),
                2
            )
            if bAddToRole:
                variable_role['stats']['kdaRatio']['value'] = round(
                    (kills_role + assists_role) / max(deaths_role, 1),
                    2
            )
            ov['stats']['kdRatio']['value'] = round(
                (kills ) / max(deaths, 1),
                2
            )
            if bAddToRole:
                variable_role['stats']['kdRatio']['value'] = round(
                    (kills_role ) / max(deaths_role, 1),
                    2
                )
            
            ov['stats']['totalHeroDamage']['value'] += segment['stats']['totalHeroDamage']['value']
            if bAddToRole:
                variable_role['stats']['totalHeroDamage']['value'] += segment['stats']['totalHeroDamage']['value']

            damage = ov['stats']['totalHeroDamage']['value']
            if bAddToRole:
                damage_role = variable_role['stats']['totalHeroDamage']['value']

            ov['stats']['totalHeroDamagePerMinute']['value'] = round(damage / max((time/60000, 1)),2) 
            if bAddToRole:
                variable_role['stats']['totalHeroDamagePerMinute']['value'] = round(damage_role / max((time_role/60000, 1)),2)

            ov['stats']['totalHeroHeal']['value'] += segment['stats']['totalHeroHeal']['value']
            if bAddToRole:
                variable_role['stats']['totalHeroHeal']['value'] += segment['stats']['totalHeroHeal']['value']
            heal = ov['stats']['totalHeroHeal']['value']
            ov['stats']['totalHeroHealPerMinute']['value'] = round(heal / max((time/60000, 1)),2) 
            if bAddToRole:
                variable_role['stats']['totalHeroHealPerMinute']['value'] = round(variable_role['stats']['totalHeroHeal']['value'] / max((time_role/60000, 1)),2)
            #ov['stats']['totalHeroHealPerMinute']['value'] += segment['stats']['totalHeroHealPerMinute']['value']
            ov['stats']['totalDamageTaken']['value'] += segment['stats']['totalDamageTaken']['value']
            if bAddToRole:
                variable_role['stats']['totalDamageTaken']['value'] += segment['stats']['totalDamageTaken']['value']
            taken = ov['stats']['totalDamageTaken']['value']
            if bAddToRole:
                taken_role = variable_role['stats']['totalDamageTaken']['value']
            ov['stats']['totalDamageTakenPerMinute']['value'] = round(taken / max((time/60000, 1)),2)
            if bAddToRole:
                variable_role['stats']['totalDamageTakenPerMinute']['value'] = round(taken_role / max((time_role/60000, 1)),2)

            #ov['stats']['totalDamageTakenPerMinute']['value'] += segment['stats']['totalDamageTakenPerMinute']['value']
            ov['stats']['lastKills']['value'] += segment['stats']['lastKills']['value']
            if bAddToRole:
                variable_role['stats']['lastKills']['value'] += segment['stats']['lastKills']['value']
            ov['stats']['headKills']['value'] += segment['stats']['headKills']['value']
            if bAddToRole:
                variable_role['stats']['headKills']['value'] += segment['stats']['headKills']['value']
            ov['stats']['soloKills']['value'] += segment['stats']['soloKills']['value']
            if bAddToRole:
                variable_role['stats']['soloKills']['value'] += segment['stats']['soloKills']['value']
            ov['stats']['sessionHitRate']['value'] += segment['stats']['sessionHitRate']['value']
            
            ov['stats']['totalMvp']['value'] += segment['stats']['totalMvp']['value']
            if bAddToRole:
                variable_role['stats']['totalMvp']['value'] += segment['stats']['totalMvp']['value']
            ov['stats']['totalSvp']['value'] += segment['stats']['totalSvp']['value']
            if bAddToRole:
                variable_role['stats']['totalSvp']['value'] += segment['stats']['totalSvp']['value']
            mvps = ov['stats']['totalMvp']['value']
            svps = ov['stats']['totalSvp']['value']
            if st == 'overview':
                ov['stats']['totalMvpPct']['value'] = round((mvps / matchesw * 100) if matchesw else 0, 2)
                ov['stats']['totalMvpPct']['displayValue'] = f"{int(round(ov['stats']['totalMvpPct']['value']))}%"

                ov['stats']['totalSvpPct']['value'] = round((svps / matchesl * 100) if matchesl else 0, 2)
                ov['stats']['totalSvpPct']['displayValue'] = f"{int(round(ov['stats']['totalSvpPct']['value']))}%"


    
    # ov = overview_segments[0]
    # ovstats = ov['stats']
    # timeplayed = ovstats['timePlayed']['value']
    # matchesplayed = ovstats['matchesPlayed']['value']
    
    #for segment in overview_segments:




    rank_string = priv_stats['seasonRank']['metadata']['tierName']
    rank_string_short = priv_stats['seasonRank']['metadata']['tierShortName']
    rank_value = priv_stats['seasonRank']['value']
    rank_value_string = priv_stats['seasonRank']['displayValue']
    for d  in rankedseg['stats']['peakTiers']['value']:
        d['value'] = rank_value
        d['metadata']['tierName'] = rank_string
        d['metadata']['tierShort'] = rank_string_short
    l = rankedseg['stats']['lifetimePeakRanked']
    l['metadata']['tierName'] = rank_string
    l['metadata']['tierShort'] = rank_string_short
    l['value'] =  rank_value
    l['displayValue'] = rank_value_string



    for seg in overview_segments:
        if seg['type'] == 'overview':
            s = seg['stats']
            break
    mvps = s['totalMvp']['value']
    svps = s['totalSvp']['value']
    matcheswr = round(s['matchesWon']['value'],1)
    matcheslr = round(s['matchesPlayed']['value'] - s['matchesWon']['value'],1)
    s['totalMvpPct']['value'] = round((mvps / matcheswr * 100) if matcheswr else 0, 2)
    s['totalMvpPct']['displayValue'] = f"{int(round(s['totalMvpPct']['value']))}%"

    s['totalSvpPct']['value'] = round((svps / matcheslr * 100) if matcheslr else 0, 2)
    s['totalSvpPct']['displayValue'] = f"{int(round(s['totalSvpPct']['value']))}%"

    
    overview_segments.append(rankedseg)

    
    # "seasonRank": {
    #                 "displayName": "Rank Score",
    #                 "category": "skillrating",
    #                 "metadata": {
    #                     "unit": "RS",
    #                     "iconUrl": "https://trackercdn.com/cdn/tracker.gg/marvel-rivals/images/ranks/6.png?v=1734906804",
    #                     "tierName": "Grandmaster II",
    #                     "tierShortName": "GM2",
    #                     "color": "#9E4BFF",
    #                     "seasonName": "S5.5: Love is a Battlefield",
    #                     "seasonShortName": "S5.5"
    #                 },
    #                 "value": 4607.0,
    #                 "displayValue": "4,607",
    #                 "displayType": "String"
    #             }
    # template = {"displayName": "null",
    #                                         "displayCategory": "Game",
    #                                         "metadata": {},
    #                                         "category": "game",
    #                                         "value": 0,
    #                                         "displayValue": "0",
    #                                         "displayType": "Number"
    #                                     }
    # ov['stats']['matchesPlayed'] = {
    #                             "displayName": "Matches Played",
    #                             "displayCategory": "Game",
    #                             "category": "game",
    #                             "metadata": {},
    #                             "value": priv_stats['seasonMatchesPlayed']['value'],
    #                             "displayValue": str(priv_stats['seasonMatchesPlayed']['value']),
    #                             "displayType": "Number"
    #                         }
    # ov['stats']['matchesWinPct'] ={"displayName": "Win%",
    #                                 "displayCategory": "Game",
    #                                 "metadata": {},
    #                                 "category": "game",
    #                                 "value": priv_stats['seasonWinPct']['value'],
    #                                 "displayValue": str(priv_stats['seasonWinPct']['value']) + "%",
    #                                 "displayType": "NumberPercentage"
    #                             }
    # wins = priv_stats['seasonMatchesPlayed']['value'] * priv_stats['seasonWinPct']['value'] / 100
    # ov['stats']['matchesWon'] ={"displayName": "Wins",
    #                             "displayCategory": "Game",
    #                             "metadata": {},
    #                             "category": "game",
    #                             "value": int(wins),
    #                             "displayValue": str(int(wins)),
    #                             "displayType": "Number"
    #                         }
    # ov['stats']['kdRatio']['value'] = priv_stats['seasonKdRatio']['value']
    # ov['stats']['kdaRatio']['value'] = priv_stats['seasonKdRatio']['value']
    
    # ov['stats']['totalMvpPct'] = template.copy()
    # ov['stats']['totalMvp'] = template.copy()
    # ov['stats']['totalSvpPct'] = template.copy()
    # ov['stats']['totalSvp'] = template.copy()
    
    # ov['stats']['peakRanked'] = priv_stats['seasonRank']
def addFirstSegmentToRole(seg, role_seg):
    stats = seg['stats']
    role_stats = role_seg['stats']
    role_stats['timePlayed']['value'] += stats['timePlayed']['value']
    role_stats['timePlayedWon']['value'] += stats['timePlayedWon']['value']
    role_stats['matchesPlayed']['value'] += stats['matchesPlayed']['value']
    role_stats['matchesWon']['value'] += stats['matchesWon']['value']
    #role_stats['matchesWinPct']['value'] += stats['matchesWinPct']['value']
    role_stats['kills']['value'] += stats['kills']['value']
    role_stats['deaths']['value'] += stats['deaths']['value']
    role_stats['assists']['value'] += stats['assists']['value']
    role_stats['totalHeroDamage']['value'] += stats['totalHeroDamage']['value']
    role_stats['totalHeroHeal']['value'] += stats['totalHeroHeal']['value']
    role_stats['totalDamageTaken']['value'] += stats['totalDamageTaken']['value']
    role_stats['lastKills']['value'] += stats['lastKills']['value']
    role_stats['headKills']['value'] += stats['headKills']['value']
    role_stats['soloKills']['value'] += stats['soloKills']['value']
    role_stats['totalMvp']['value'] += stats['totalMvp']['value']
    role_stats['totalSvp']['value'] += stats['totalSvp']['value']
def addMissingHeroStatKeys(seg,season, win, mvp, svp, total_timePlayed):
    hero_time = seg['stats']['timePlayed']['value']
    hero_time_divided_by_total = round((hero_time / total_timePlayed), 1)
    roleUpper = seg['metadata']['roleName']
    stats = seg['stats']
    seg['attributes']['role'] = roleUpper.lower()
    seg['attributes']['mode'] = 'competitive'
    seg['attributes']['season'] = season

    # timePlayedWon
    stats['timePlayedWon'] = stats['timePlayed'].copy()
    stats['timePlayedWon']['displayName'] = "Time Played Won"
    if not win:
        stats['timePlayedWon']['value'] = 0
        stats['timePlayedWon']['displayValue'] = '0m'

    # matchesPlayed
    stats['matchesPlayed'] = {
                                "displayName": "Matches Played",
                                "displayCategory": "Game",
                                "category": "game",
                                "metadata": {},
                                "value": hero_time_divided_by_total,
                                "displayValue": str(hero_time_divided_by_total),
                                "displayType": "NumberPrecision1"
                            }
    
    # matchesWon
    stats['matchesWon'] = stats['matchesPlayed'].copy()
    stats['matchesWon']['displayName'] = "Wins"
    if not win:
        stats['matchesWon']['value'] = 0
        stats['matchesWon']['displayValue'] = '0'

    # matchesWinPct
    stats['matchesWinPct'] = {
                                "displayName": "Win %",
                                "displayCategory": "Game",
                                "category": "game",
                                "metadata": {},
                                "value": 0,
                                "displayValue": "0%",
                                "displayType": "NumberPercentage"
                        }
    
    # totalMvp and totalSvp
    stats['totalMvp'] = {
                            "displayName": "MVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 1 if mvp else 0,
                            "displayValue": "1" if mvp else "0",
                            "displayType": "Number"
                        }
    stats['totalSvp'] = {
                            "displayName": "SVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 1 if svp else 0,
                            "displayValue": "1" if svp else "0",
                            "displayType": "Number"
                        }
    
    
def addMissingOverviewStatKeys(seg,season, win, mvp, svp, total_timePlayed):        
    seg['attributes']['season'] = season
    seg['attributes']['mode'] = 'competitive'
    seg['metadata']['name'] = 'Competitive'
                        
    stats = seg['stats']

    # timePlayedWon
    stats['timePlayedWon'] = stats['timePlayed'].copy()
    stats['timePlayedWon']['displayName'] = "Time Played Won"
    if not win:
        stats['timePlayedWon']['value'] = 0
        stats['timePlayedWon']['displayValue'] = '0m'

    # matchesPlayed
    # matchesPlayed
    stats['matchesPlayed'] = {
                                "displayName": "Matches Played",
                                "displayCategory": "Game",
                                "category": "game",
                                "metadata": {},
                                "value": 1,
                                "displayValue": "1",
                                "displayType": "NumberPrecision1"
                            }
    
    # matchesWon
    # matchesWon
    stats['matchesWon'] = stats['matchesPlayed'].copy()
    stats['matchesWon']['displayName'] = "Wins"
    if not win:
        stats['matchesWon']['value'] = 0
        stats['matchesWon']['displayValue'] = '0'

    # matchesWinPct
    stats['matchesWinPct'] = {
                                "displayName": "Win %",
                                "displayCategory": "Game",
                                "category": "game",
                                "metadata": {},
                                "value": 100 if win else 0,
                                "displayValue": "100%" if win else "0%",
                                "displayType": "NumberPercentage"
                        }
    # totalMvp and totalSvp and %%
    stats['totalMvp'] = {
                            "displayName": "MVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 1 if mvp else 0,
                            "displayValue": "1" if mvp else "0",
                            "displayType": "Number"
                        }
    stats['totalSvp'] = {
                            "displayName": "SVPs",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 1 if svp else 0,
                            "displayValue": "1" if svp else "0",
                            "displayType": "Number"
                        }
    stats['totalMvpPct'] = {
                            "displayName": "MVP %",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 100 if mvp else 0,
                            "displayValue": "100%" if mvp else "0%",
                            "displayType": "NumberPrecision2"
                        }
    stats['totalSvpPct'] = {
                            "displayName": "SVP %",
                            "displayCategory": "Game",
                            "category": "game",
                            "metadata": {},
                            "value": 100 if svp else 0,
                            "displayValue": "100%" if svp else "0%",
                            "displayType": "NumberPrecision2"
                        }
    stats['peakRanked'] = stats['ranked'].copy()

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
    
def open_multiple_tracker_profiles(player_names):
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
        chrome_major = get_installed_chrome_major_version(default=138)
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
    

    results = {}
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/BicZilla"
    
    try:
        print("test")
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
                f.write(str(config.season))
            print(f"Updated season to {config.season} in config.")

        
    except Exception as e:
        print(f"")
    try:

        copi = copy.deepcopy(data)
        copi['data']['segments']  = []
        if isinstance(season, str):
                            ss = int(season)
        else:
                            ss = season
            
        encount = {"encounters":[]}
    except Exception as e:

        print(f"Error during initial data fetch: {e}")
        #pa = helpers.create_path(f"_Tracker_InitialFetchError.json", 'debug')
        #helpers.save_json(pa, data)
        
    #time.sleep(1.5)
    try:
        attempts = 0
        private_players = []
        potential_teammates = []
        count = 0
        for player_name in player_names:
            overview = None
            time.sleep(0.15)


            attempts = 0
            max_attempts = 3
            season = config.season
            success = False
            #print(f"Checking Season {season} for {player_name}...")
            # if player_name == "EyeingFlux" or player_name == "ProfChloroform":
            #     data = "private"
            
            overview = getTrackerGGOverview(player_name, driver, mode)
            if overview == "private":
                private_players.append(player_name)
                print(f"🔒 {player_name} is Private.")
                continue
            if isinstance(overview, type(None)):
                print(f"❌ Errors encountered while fetching overview for {player_name}. Skipping player.")
                results[player_name] = None
                continue
            time.sleep(0.15)

            data = getTrackerGGProfile(player_name, driver, season, mode)
                
            if data == "private":
                private_players.append(player_name)
                print(f"🔒 {player_name} is Private.")
                #results[player_name] = None
                continue

            if not data:
                data_older = getTrackerGGProfile(player_name, driver, season - 1, mode)
                if data_older:
                    
                    matches = getTrackerGGMatches(player_name, driver, season, mode)
                    if matches:
                        de= helpers.create_path(f"_!Tracker_{player_name}_Matches.json", 'debug')
                        helpers.save_json(de, data)
                        match_data = matches['data']['matches']
                    else:
                        match_data = []
                    copi['data']['segments']  = data_older['data']
                    copi['data']['matches'] = match_data
                    
                    copi['data']['seas'] = [str(ss - 1)]
                    if overview:
                        copi['data']['full_overview'] = overview['data']
                    data_older = copy.deepcopy(copi)
                    results[player_name] = data_older
                    print(f"✅ {player_name} data fetched for season {season - 1}.")
                    if player_name not in potential_teammates:
                        potential_teammates.append(player_name)
                    continue
                else:
                    print(f"❌ {player_name} data not found.")
                    results[player_name] = None
                    continue
            if "data" in data and not data["data"] or "errors" in data:
                #print(f"... No data found for {player_name}: Season {season}. Retrying with season {season - 1}...")
                time.sleep(0.15)
                data_older = getTrackerGGProfile(player_name, driver, season - 1, mode)

                if data_older:
                    
                    matches = getTrackerGGMatches(player_name, driver, season, mode)
                    if matches:
                        match_data = matches['data']['matches']
                    else:
                        match_data = []
                    copi['data']['segments']  = data_older['data']
                    copi['data']['matches'] = match_data
                    copi['data']['seas'] = [str(ss - 1)]
                    if overview:
                        copi['data']['full_overview'] = overview['data']
                    data_older = copy.deepcopy(copi)
                    results[player_name] = data_older
                    print(f"✅ {player_name} data fetched for season {season - 1}.")
                    if player_name not in potential_teammates:
                        potential_teammates.append(player_name)
                    continue
                else:
                    print(f"❌ {player_name} data not found.")
                    results[player_name] = None
                    continue
            if data:
                matches = getTrackerGGMatches(player_name, driver, season, mode)
                if matches:
                    match_data = matches['data']['matches']
                else:
                    match_data = []
                copi['data']['segments']  = data['data']
                copi['data']['matches'] = match_data
                copi['data']['seas'] = [str(ss)]
                if overview:
                        copi['data']['full_overview'] = overview['data']
                data = copy.deepcopy(copi)
                #pa = helpers.create_path(f"_Tracker_{player_name}_S{season}.json", 'debug')
                #helpers.save_json(pa, data)
                matches_played = check_matches_played(data)
                if matches_played <= 25:
                    time.sleep(0.15)
                    data_older = getTrackerGGProfile(player_name, driver, season - 1, mode)
                    if data_older:
                        print(f"✅ {player_name} data fetched for seasons {season} and {season - 1}. Merging.")
                        copi['data']['segments']  = data_older['data']
                        data_older = copy.deepcopy(copi)
                        #pa = helpers.create_path(f"_Tracker_{player_name}_S{season -1}.json", 'debug')
                        #helpers.save_json(pa, data_older)
                        combined_data = mergeTrackerData(data, data_older)
                        combined_data['data']['seas'].append(str(ss-1))
                        results[player_name] = combined_data
                        if player_name not in potential_teammates:
                            potential_teammates.append(player_name)
                        continue
                    else:
                        print(f"✅ {player_name} data fetched for season {season}.")
                        results[player_name] = data
                        if player_name not in potential_teammates:
                            potential_teammates.append(player_name)
                        continue
                else:
                    print(f"✅ {player_name} data fetched for season {season}.")
                    results[player_name] = data
                    if player_name not in potential_teammates:
                        potential_teammates.append(player_name)
                    continue
            
            else:
                print(f"❌ {player_name} data not found.")
                results[player_name] = None
                continue
        
        possible_teammates = [x for x in player_names if x not in set(private_players)]
        ranked_peaks_copy = None
        # teammate_dict = {}
        # mid_used = []
        # for potential in potential_teammates:
        #     ranked_peaks_copy = copy.deepcopy(results[potential]['data']["segments"][1])
        #     time.sleep(0.15)
        #     data = getTrackerGGEncounters(teammate, driver, season, mode)
        #     if data:
        #         #encount["encounters"].append(data)
        #         encounters_list = data['data']['teammates']
        #         teammate_dict[potential] = {"mids": []}
        #         for priv in private_players:
        #             js = {priv: {"data":{"segments":[], "matches":[], 'mids': [],'mids_used':[], 'teammates': []}}}
        #             for encounter  in encounters_list:
        #                 name = encounter["platformInfo"]["platformUserHandle"]
                        
        #                 if name == priv:
                            
        #                     private_stats = copy.deepcopy(encounter['stats'])
        #                     teammate_dict[potential][priv] = {"stats": private_stats}
        #                     print(f"Found potential teammate {potential} for private player {priv}.")
        #         if len(teammate_dict[potential]) > 0:
        #             history = results[teammate]['data']["matches"]
        #             mid_list = []
        #             for match in history:
        #                 count += 1
        #                 if count >7:
        #                     break
        #                 mid = match['attributes']['id']
        #                 mid_list.append(mid)
                    
                        
        #             teammate_dict[potential]['mids'] = mid_list
        #             for mid in mid_list:
        #                 if mid in  mid_used:
        #                     continue
        #                 mid_used.append(mid)
        #                 match_details = getTrackerGG_MatchDetails(driver, mid)
        #                 if match_details:
        #                     match_segments = match_details['data']['segments']
        #                     bFound = False
        #                     bMvp = False
        #                     bSvp = False
        #                     match_duration = 0
        #                     new_segments = []
        #                     bWin = False

        #                     for priv in teammate_dict[potential]:
        #                         for segment in match_segments:

        #                             if segment['type'] == 'player':
        #                                 player = segment['metadata']['platformInfo']["platformUserHandle"]
        #                                 if player == priv:
        #                                     print(f"Found match {mid} for private player {priv} with teammate {potential}.")
        #                                     if not bFound:
        #                                         match_data_copy = copy.deepcopy(match_details['data'])
        #                                         overview_st = copy.deepcopy(segment)
        #                                         match_duration = segment['stats']['timePlayed']['value']
        #                                         bWin = segment['metadata']['result'] == "win"
        #                                         bMvp = bool(segment['metadata'].get('isMvp', False))
        #                                         bSvp = bool(segment['metadata'].get('isSvp', False))
        #                                         overview_st["type"] = "overview"
        #                                         addMissingOverviewStatKeys(overview_st,ss,bWin,bMvp,bSvp,match_duration)
        #                                         new_segments = [overview_st]
        #                                         bFound = True
        #                                     accountid = segment['attributes']['accountId']


                
        #     else:
        #         continue
                    



        if config.bPrivateLookup:
            for private_player in private_players:
                flag = False
                js = {private_player: {"data":{"segments":[], "matches":[], 'mids': [],'mids_used':[], 'teammates': []}}}
                list_of_teaammates = []
                mid_list = []
                stats = []
                
                
                private_stats = None
                for teammate in possible_teammates:
                    if not results[teammate]:
                        continue
                    if not ranked_peaks_copy:
                        ranked_peaks_copy = copy.deepcopy(results[teammate]['data']["segments"][1])
                    time.sleep(0.15)
                    data = getTrackerGGEncounters(teammate, driver, season, mode)

                    if data:
                        encount["encounters"].append(data)
                        encounters_list = data['data']['teammates']
                        for encounter  in encounters_list:
                            name = encounter["platformInfo"]["platformUserHandle"]
                            if name == private_player:

                                print(f"Found encounters for private player {private_player} with teammate {teammate}.")
                                if private_stats:


                                    m1 = private_stats['matchesPlayed']['value']
                                    m2 = encounter['stats']['matchesPlayed']['value']
                                    if m2 > m1:
                                        private_stats = copy.deepcopy(encounter['stats'])
                                else:
                                    private_stats = copy.deepcopy(encounter['stats'])
                                
                                history = results[teammate]['data']["matches"]
                                count = 0
                                mid_list = []
                                for match in history:
                                    count += 1
                                    if count >15:
                                        break
                                    mid = match['attributes']['id']
                                    js[private_player]['data']["mids"].append(mid)
                                if teammate not in js[private_player]['data']["teammates"]:
                                    js[private_player]['data']["teammates"].append(teammate)
                                flag = True

                        
                        
                        
                if flag:
                    hero_stats = []
                    overview_stats = []
                    overall_flag = False
                    match_data_copy = None
                    
                    for mid in js[private_player]['data']["mids"]:
                        new_segments  = []
                        bWin = False
                        bMvp = False
                        bSvp = False
                        match_duration = False
                        if mid in js[private_player]['data']["mids_used"]:
                            continue
                        accountid = None
                        match_details = getTrackerGG_MatchDetails(driver, mid)
                        
                        private_in_match = False
                        if match_details:
                            match_segments = match_details['data']['segments']
                            for segment in match_segments:
                                if segment['type'] == 'player':

                                    player = segment['metadata']['platformInfo']["platformUserHandle"]
                                    if player == private_player:
                                        if not private_in_match:
                                            match_data_copy = copy.deepcopy(match_details['data'])
                                            overview_st = copy.deepcopy(segment)
                                            match_duration = segment['stats']['timePlayed']['value']
                                            bWin = segment['metadata']['result'] == "win"
                                            bMvp = bool(segment['metadata'].get('isMvp', False))
                                            bSvp = bool(segment['metadata'].get('isSvp', False))
                                            overview_st["type"] = "overview"
                                            addMissingOverviewStatKeys(overview_st,ss,bWin,bMvp,bSvp,match_duration)
                                            new_segments.append(overview_st)
                                            private_in_match = True
                                            overall_flag = True
                                        accountid = segment['attributes']['accountId']
                                        
                                        
                                elif segment['type'] == 'hero' and accountid:
                                    if segment['attributes']['accountId'] == accountid:
                                        new = copy.deepcopy(segment)
                                        addMissingHeroStatKeys(new,ss,bWin,bMvp,bSvp,match_duration)
                                        new_segments.append(new)
                            if match_data_copy and private_in_match:

                                match_data_copy['segments'] = new_segments
                                js[private_player]['data']["matches"].append(copy.deepcopy(match_data_copy))
                            js[private_player]['data']["mids_used"].append(mid)
                            
                    # js[private_player]['data']["hero_stats"] = hero_stats
                    # js[private_player]['data']["overview_stats"] = overview_stats
                    if overall_flag:
                        copi['data']['matches'] = js[private_player]['data']["matches"]
                        copi['data']['segments']  = []
                        
                        copi['data']['encounter_stats']  = private_stats
                        copi['data']['seas'] = [str(ss)]
                        data_private = copy.deepcopy(copi)
                        transformPrivateData(data_private,ranked_peaks_copy)
                        data_private['data']['userInfo']['isPremium'] = 69
                        results[private_player] = data_private
                    else:
                        results[private_player] = None
                else:
                    results[private_player] = None

            en = encount["encounters"]
            if len(en) > 0:
                de= helpers.create_path(f"_!Tracker_Encounters_S{season}.json", 'debug')
                helpers.save_json(de, encount)
                print(f"✅ Saved encounters data for {len(en)} players.")




                    

    except Exception as e:
        print(f"❌ Error : {e}")

    finally:
        try:
            # for player_name in player_names:
            #     if results[player_name] is None:
            #         continue

                #time.sleep(0.15)
                

            #driver._ensure_close(type(driver), driver)
            driver.quit()
        except Exception:
            pass
    kill_brave_selenium_instances()
    #driver._ensure_close(type(driver), driver)
    return results
                

    #         while attempts < max_attempts and not success:
    #             url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}/segments/career?mode={mode}&season={season}"
    #             #url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{player_name}?&season={season}"

    #             try:
    #                 driver.get(url)
    #                 pre = WebDriverWait(driver, 10).until(
    #                     EC.presence_of_element_located((By.TAG_NAME, "pre"))
    #                 )
    #                 raw_json = pre.text


    #                 data = json.loads(raw_json)


    #                 if "data" in data and not data["data"]:
    #                     if attempts < 2:
    #                         print(f"❌ No data found for {player_name}: Season {season}. Retrying with season {season - 1}...")

    #                         season -= 1 if season > 1 else 1
    #                         attempts += 1
    #                         continue
    #                     elif attempts + 1 == 3:
    #                         print(f"❌ No data found for {player_name} after multiple attempts.")
    #                         results[player_name] = None
    #                         break
    #                 # if "errors" in data:
    #                 #     if attempts < 2:
    #                 #         print(f"❌ No data found for {player_name}: Season {season}. Retrying with season {season - 1}...")

    #                 #         season -= 1 if season > 1 else 1
    #                 #         attempts += 1
    #                 #         continue
    #                 #     elif attempts + 1 == 3:
    #                 #         print(f"❌ No data found for {player_name} after multiple attempts.")
    #                 #         results[player_name] = None
    #                 #         break
    #                 if data:
    #                     copi['data']['segments']  = data['data']
    #                     data = copy.deepcopy(copi)
    #                     # seaso = int(data['data']['metadata']['currentSeason'])
    #                     # if seaso > season:
    #                     #     season = seaso
    #                     # seasons.append(seaso)
    #                     print(f"✅ Data loaded for {player_name}")
                        
    #                     results[player_name] = data
    #                     success = True
    #                 else:
    #                     results[player_name] = None
    #             except Exception as e:
    #                 print(f"❌ Error loading JSON for {player_name}: {e}")
    #                 #results[player_name] = None
    #                 attempts += 1
    #                 success = True
    #                 time.sleep(0.05)
                    
    #             time.sleep(0.05)
    # finally:
    #     try:
    #         #driver._ensure_close(type(driver), driver)
    #         driver.quit()
    #     except Exception:
    #         pass
    # kill_brave_selenium_instances()
    # #driver._ensure_close(type(driver), driver)
    # return results

# def open_tracker_profile(player_name):
#     season = config.season
#     mode = "competitive"

#     chrome_major = get_installed_chrome_major_version(default=138)
#     options = uc.ChromeOptions()

#     # create a fresh temporary profile directory for this run
#     profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")
#     os.makedirs(profile_path, exist_ok=True)

#     # optional: keep Chrome quiet
#     options.add_argument(f"--user-data-dir={profile_path}")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("--window-size=1,1")

#     driver = None
#     results = None
#     import copy

#     try:
#         driver = uc.Chrome(options=options, version_main=chrome_major)
#         driver.set_window_position(-10000, 0)
#         driver.set_window_size(1, 1)

#         # ... rest of your scraping logic unchanged ...

#     finally:
#         try:
#             if driver:
#                 driver.quit()
#         except Exception:
#             pass

#     return {player_name: results}
