import json
import os
import time
import config
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import re

# ============================================================
# SETTINGS
# ============================================================
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


PLAYER_UID = 1324925930
SEASON = 19

PAGE_URL = f"https://rivalsdata.com/player/{PLAYER_UID}"
API_URL = "https://api.rivalsdata.com/player/heroes"

# Your previous traffic shows Brave, so use Brave if installed.
BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expandvars(
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
    ),
]


def find_brave():
    for path in BRAVE_PATHS:
        if os.path.exists(path):
            return path

    return None


def create_driver():
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
    if os.path.exists(brave_path):
        bBraveBrowser = True
        data_dir = config.brave_data_dir
        browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        brave_major = get_installed_brave_major_version(default=147)
    # ---- CHROME BROWSER DETECTION ----
    else: 
        browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        bBraveBrowser = False
        data_dir = None
        chrome_major = get_installed_chrome_major_version(default=147)
        #print(f"Detected Chrome major version: {chrome_major}")
        

    
    options = uc.ChromeOptions()
    if bBraveBrowser:
        options.binary_location = browser_path
    profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")

    options.add_argument(f"--user-data-dir={profile_path}")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--start-minimized")
    options.set_capability(
    "goog:loggingPrefs",
    {
        "performance": "ALL",
        "browser": "ALL",
    },
)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    caps = DesiredCapabilities.CHROME.copy()
    caps["pageLoadStrategy"] = "eager"

    if bBraveBrowser:
        driver = uc.Chrome(options=options, desired_capabilities=caps, use_subprocess=False, user_multi_procs=False, version_main=brave_major)
    else:
        driver = uc.Chrome(options=options, desired_capabilities=caps, use_subprocess=False, user_multi_procs=False, version_main=chrome_major)
    return driver

def wait_for_page(driver, timeout=30):
    print(f"\nOpening:\n{PAGE_URL}\n")

    driver.get(PAGE_URL)

    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState")
        in ("interactive", "complete")
    )

    print("Page loaded.")
    print("Current URL:", driver.current_url)
    print("Title:", driver.title)


def get_heroes(driver, uid, season):
    """
    Execute the RivalsData /player/heroes POST request directly
    inside the currently loaded browser tab.

    Returns:
        {
            "ok": bool,
            "status": int,
            "statusText": str,
            "url": str,
            "body": parsed JSON or raw text
        }
    """

    script = """
    const callback = arguments[arguments.length - 1];

    const url = arguments[0];
    const uid = arguments[1];
    const season = arguments[2];

    fetch(url, {
        headers: {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache"
        },
        referrer: "https://rivalsdata.com/",
        body: JSON.stringify({
            uid: uid,
            season: season
        }),
        method: "POST",
        mode: "cors",
        credentials: "include"
    })
    .then(async response => {

        const text = await response.text();

        let body;

        try {
            body = JSON.parse(text);
        } catch {
            body = text;
        }

        callback({
            ok: response.ok,
            status: response.status,
            statusText: response.statusText,
            url: response.url,
            body: body
        });
    })
    .catch(error => {
        callback({
            ok: false,
            error: error.toString()
        });
    });
    """

    # Allow plenty of time for the async fetch.
    driver.set_script_timeout(30)

    return driver.execute_async_script(
        script,
        API_URL,
        uid,
        season,
    )


def main():
    driver = None

    try:
        driver = create_driver()

        # ----------------------------------------------------
        # Load actual player page first
        # ----------------------------------------------------

        wait_for_page(driver)

        # Small delay so any page initialization / Cloudflare
        # browser state can settle.
        time.sleep(2)

        # ----------------------------------------------------
        # Run /player/heroes fetch inside browser
        # ----------------------------------------------------

        print("\nRequesting:")
        print(API_URL)
        print(
            "Payload:",
            json.dumps(
                {
                    "uid": PLAYER_UID,
                    "season": SEASON,
                }
            ),
        )

        response = get_heroes(
            driver,
            PLAYER_UID,
            SEASON,
        )

        # ----------------------------------------------------
        # Print response information
        # ----------------------------------------------------

        print("\n" + "=" * 100)
        print("RESPONSE")
        print("=" * 100)

        print(
            json.dumps(
                response,
                indent=4,
                ensure_ascii=False,
            )
        )

        # Easier access to only the API JSON
        if response.get("ok"):
            heroes = response["body"]

            print("\n" + "=" * 100)
            print("HEROES JSON")
            print("=" * 100)

            print(
                json.dumps(
                    heroes,
                    indent=4,
                    ensure_ascii=False,
                )
            )

        else:
            print("\nREQUEST FAILED")
            print(response)

        input("\nPress ENTER to close browser...")

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()