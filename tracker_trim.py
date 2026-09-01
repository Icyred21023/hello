#pylint:disable=W0621
import config
if not config.mobile_mode:
    import undetected_chromedriver as uc
    
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time, json, os, re


if not config.mobile_mode:
    import psutil
from datetime import date
import helpers

from urllib.parse import quote

BROWSER = None
driver_path = "s"


d = date.today()
DAY = d.day
MONTH = d.month
YEAR = d.year
DAY_COUNT = d.toordinal()
NAMES_LIST = []


def safe_del(self):
    try:
        self.quit()
    except Exception:
        pass
if not config.mobile_mode:
    uc.Chrome.__del__ = safe_del


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


class Browser:
    def __init__(self):

        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
        if os.path.exists(brave_path):
            self.bBraveBrowser = True
            data_dir = config.brave_data_dir
            browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
            kill_brave_selenium_instances()
            brave_major = get_installed_brave_major_version(default=147)
        # ---- CHROME BROWSER DETECTION ----
        else: 
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            self.bBraveBrowser = False
            data_dir = None
            chrome_major = get_installed_chrome_major_version(default=147)
            #print(f"Detected Chrome major version: {chrome_major}")
            kill_selenium_chrome()


        self.options = uc.ChromeOptions()
        if self.bBraveBrowser:
            self.options.binary_location = browser_path
        profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")

        self.options.add_argument(f"--user-data-dir={profile_path}")

        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--start-minimized")
    #     self.options.set_capability(
    #     "goog:loggingPrefs",
    #     {
    #         "performance": "ALL",
    #         "browser": "ALL",
    #     },
    # )
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--no-default-browser-check")
        self.options.add_argument("--no-first-run")
        self.caps = DesiredCapabilities.CHROME.copy()
        self.caps["pageLoadStrategy"] = "eager"

        if self.bBraveBrowser:
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
            
    def kill_all(self):
        kill_brave_selenium_instances() if self.bBraveBrowser else kill_selenium_chrome()
        

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
            
    def fetch_get(self, url, timeout=10):
        self.driver.set_script_timeout(timeout)
    
        script = """
            const url = arguments[0];
            const done = arguments[arguments.length - 1];
    
            fetch(url, {
                method: "GET",
                credentials: "include",
                headers: {
                    "Accept": "application/json, text/plain, */*"
                }
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
    
        result = self.driver.execute_async_script(script, url)
    
        if result.get("error"):
            raise RuntimeError(
                f"Browser fetch failed: {result['error']}"
            )
    
        if not result.get("ok"):
            # raise RuntimeError(
            #     f"HTTP {result.get('status')} "
            #     f"{result.get('statusText', '')}\\n"
            #     f"{result.get('text', '')[:1000]}"
            # )
            return {
    "errors": [
        {
            "code": "Collector::Private",
            "message": "Match history is private.",
            "data": {}
        }
    ]
}
    
        return json.loads(result["text"])
        
    def fetch_post(self, url, payload, timeout=10):
        self.driver.set_script_timeout(timeout)
    
        script = """
            const url = arguments[0];
            const payload = arguments[1];
            const done = arguments[arguments.length - 1];
    
            fetch(url, {
                method: "POST",
                mode: "cors",
                credentials: "include",
    
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
    
                referrer: "https://rivalsdata.com/",
                referrerPolicy: "strict-origin-when-cross-origin",
    
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
                    statusText: "",
                    error: String(error),
                    text: ""
                });
            });
        """
    
        result = self.driver.execute_async_script(
            script,
            url,
            payload
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
                f"Response was not valid JSON:\n"
                f"{result.get('text', '')[:1000]}"
            ) from exc




def build_rivalsdata_url_payload(kind="player", mid="null"):
    if "player" in kind.lower():
        return "https://api.rivalsdata.com/player", { "uid": config.USER_UID}
    elif "live" in kind.lower():
        return "https://api.rivalsdata.com/live", {"match_id": mid, "uid": config.USER_UID}
        
    
    

def build_tracker_url(ign=None, kind="matches",season = config.season):
    
    if ign is None:
        return False
        
    if "match" in kind.lower():
        return f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/ign/{ign}?mode=competitive&season={season}"
        
    elif "overview" in kind.lower():
        return f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{ign}/segments/career?mode=competitive"
        
    elif "profile" in kind.lower():
        return f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{ign}/segments/career?mode=competitive&season={season}"
        
    elif "bangcock" in kind.lower():
        return None
        
        
def safe_ign(name):
    ign = (name or "").strip()

    # IMPORTANT: Encode the path segment
    ign_enc = quote(ign, safe="")
    return ign_enc
    
from RDMO import Match, MatchHistory, Player
from typing import List

def parsePlayer(j: dict = None):
    status = j.get("status")
        
    if status is None:
        return False
    
    elif "battle_id" in status:
        mid = status.get("battle_id", False)
        return mid
    return False
    
    
def getLive():
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


    # Added only because the requested source excerpt ends here.
    global BROWSER
    if BROWSER is None:
        
        BROWSER = Browser()

    elif BROWSER.driver is None:
        BROWSER = Browser()
    else:
        #BROWSER.kill_all()
        print()
        
    b = BROWSER
    driver = b.driver
    driver.get(f"https://rivalsdata.com/player/{config.USER_UID}")
    if driver.title == "Just a moment...":
        b.set_captcha_window()
        b.wait_for_captcha()
        b.set_tiny_window()
    
    
    url, pay= build_rivalsdata_url_payload(kind="player")
    try:
        while True:
            data = b.fetch_post(url, pay)
            print(type(data))
            m = parsePlayer(data)
            if m:
                break
            time.sleep(5)
                       
    except Exception as e:
        print(e)
        
    try:
        url, pay = build_rivalsdata_url_payload(kind="live", mid=m)
        data = b.fetch_post(url, pay)
       
    except Exception as e:
        print(e)
    
    return data
    
def check_isPrivate(d):
    e = d.get("errors", None)
    if e:
        return False
    else:
        return True
    
def parseCurrentSeason(d):
    data = d.get("data", None)
    if data:
        current_season = data.get("currentSeasonInfo", None)
        if current_season:
            if "name" in current_season:
                st = current_season.get("name", None)
                match = re.search(r'S(\d+(?:\.\d+)?)', st)

                if match:
                    season = float(match.group(1))
                     # "9.5"
                    return season, int(season*2)
                
def doDebug(player: Player, ign: str):
    path = os.path.join(config.script_dir, "debug", "_LiveDebug")

    profile = os.path.join(path, f"{ign}_profile.json")
    matches = os.path.join(path, f"{ign}_matches.json")
    if os.path.exists(profile):
        with open(profile, "r", encoding="utf-8") as f:
            data = json.load(f)
            player.add_profile(data)
    if os.path.exists(matches):
        with open(matches, "r", encoding="utf-8") as f:
            data = json.load(f)
            player.add_matches(data)

        
def getTrackerGG(match: Match, bDebug: bool = False):
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
    #{"errors":[{"code":"CollectorResultStatus::Private","message":"The stat collector returned the following status code: Private","data":{}}]}
    
    


    # Added only because the requested source excerpt ends here.

    global BROWSER
    players = match.players
    if not bDebug:
        if BROWSER is None:
            BROWSER = Browser()
        elif BROWSER.driver is None:
            BROWSER = Browser()
        else:
            #BROWSER.kill_all()
            print()
        
        b = BROWSER
        driver = b.driver
        driver.get("https://tracker.gg/")
        if driver.title == "Just a moment...":
            b.set_captcha_window()
            b.wait_for_captcha()
            b.set_tiny_window()
        players = match.players

        data = b.fetch_get("https://api.tracker.gg/api/v2/marvel-rivals/standard/homepage?v=5")
        current_season, season_api = parseCurrentSeason(data)

        if season_api > config.season:
            print(f"Tracker.gg has a newer season ({season_api}) than the configured season ({config.season}). Updating config.season to {season_api}.")
            config.save_season(season_api)


    for player in players:
        if "*" in player.Name:
            player.bPrivate = True
            continue

        
        print(f"🔍 \033[1m - {player.Name}\033[0m")
        ign = safe_ign(player.Name)
        if bDebug:
            doDebug(player, ign)
            continue
        url = build_tracker_url(ign=ign, kind="matches")
        try:
            data = b.fetch_get(url)
            bSuccess = check_isPrivate(data)
            print(f"\t✅ \033[1m Match History\033[0m fetched successfully.") if bSuccess else print(f"\t❌ \033[1m Match History\033[0m is private or not available.")
            if bSuccess:
                if bDebug:
                    helpers.save_json(path=os.path.join(config.script_dir, "debug", "_LiveDebug", f"{ign}_matches.json"), data=data)
                player.add_matches(data)
        
            url = build_tracker_url(ign=ign, kind="profile")
        
            data = b.fetch_get(url)
            bSuccess = check_isPrivate(data)
            print(f"\t✅ \033[1m Profile\033[0m fetched successfully.\n") if bSuccess else print(f"\t❌ \033[1m Profile\033[0m is private or not available.\n")
            player.bPrivate = not bSuccess
            if bSuccess:
                if bDebug:
                    helpers.save_json(path=os.path.join(config.script_dir, "debug", "_LiveDebug", f"{ign}_profile.json"), data=data)
                player.add_profile(data)

            if player.seasonal_overview.matches_played and player.seasonal_overview.matches_played < 40:
                url = build_tracker_url(ign=ign, kind="profile", season=config.season-1)
                data = b.fetch_get(url)
                bSuccess = check_isPrivate(data)
            
                if bSuccess:
                    player.add_profile(data)
                    print(f"\t✅ \033[1m Previous Season Profile\033[0m fetched successfully.\n")
            player.Heroes = dict(
                sorted(
                    player.Heroes.items(),
                    key=lambda item: item[1].Stats.matches_played,
                    reverse=True
                )
            )
        except Exception as e:
            print(e)
    if not bDebug:
        b.kill_all()
def main():
        # Example usage
    bDebug = True
    live_data = config.livedebug if bDebug else getLive()
    from RDMO import Match
    match = Match(live_data)
    getTrackerGG(match)
    print()
    MATCH_PLAYERS = []
    for p in match.players:
        if "*" in p.Name:
            #print(f"Skipping {p.Name}: Private Account")
            continue
        MATCH_PLAYERS.append(p)
    return MATCH_PLAYERS
if __name__ == "__main__":
    # Example usage
    bDebug = True
    live_data = config.livedebug if bDebug else getLive()
    from RDMO import Match
    match = Match(live_data)
    getTrackerGG(match, bDebug)
    print()
    MATCH_PLAYERS = []
    for p in match.players:
        if "*" in p.Name:
            #print(f"Skipping {p.Name}: Private Account")
            continue
        MATCH_PLAYERS.append(p)

    
        
    
