import os
import re
import time
import psutil
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import base64

# ============================================================
# SETTINGS
# ============================================================
import config
TARGET_URL = f"https://rivalsdata.com/player/{config.USER_UID}"   # <-- PUT YOUR URL HERE

#TARGET_URL = f"https://rivalsdata.com/player/159685691" 

LIVE_TAB_TEXT = "Live Game"
WAIT_TIMEOUT = 15

def wait_for_json_response(
    driver,
    target_url,
    timeout=15
):
    end_time = time.time() + timeout

    while time.time() < end_time:

        logs = driver.get_log("performance")

        for entry in logs:
            try:
                message = json.loads(
                    entry["message"]
                )["message"]

            except Exception:
                continue

            if message["method"] != "Network.responseReceived":
                continue

            params = message["params"]
            response = params["response"]

            url = response["url"]

            # Exact endpoint
            if url != target_url:
                continue

            print("\nFOUND TARGET API")
            print("URL:", url)
            print("STATUS:", response["status"])
            print("TYPE:", params.get("type"))

            request_id = params["requestId"]

            # ResponseReceived can occasionally happen slightly
            # before Chrome makes the body available.
            for _ in range(20):
                try:
                    result = driver.execute_cdp_cmd(
                        "Network.getResponseBody",
                        {
                            "requestId": request_id
                        }
                    )

                    body = result["body"]

                    if result.get("base64Encoded"):
                        body = base64.b64decode(
                            body
                        ).decode(
                            "utf-8",
                            errors="replace"
                        )

                    try:
                        return json.loads(body)

                    except json.JSONDecodeError:
                        print("Response was not JSON:")
                        print(body)
                        return body

                except Exception:
                    time.sleep(0.1)

        time.sleep(0.05)

    print("Timed out waiting for:", target_url)
    return None
# ============================================================
# PROCESS / VERSION HELPERS
# ============================================================

def kill_brave_selenium_instances():
    TARGET_SUBSTRING = "selenium_admin_profile"

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "brave.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])

                if TARGET_SUBSTRING.lower() in cmdline.lower():
                    print(
                        f"Killing Brave PID {proc.pid} | "
                        f"CMD: {cmdline[:120]}..."
                    )
                    proc.kill()

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def kill_selenium_chrome():
    killed = 0

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "chrome.exe":
                cmdline = " ".join(proc.info.get("cmdline") or [])

                if "--user-data-dir" in cmdline and "selenium" in cmdline.lower():
                    print(f"Killing Selenium Chrome PID {proc.pid}")
                    proc.kill()
                    killed += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed == 0:
        print("No Selenium Chrome processes found.")
    else:
        print(f"Killed {killed} Selenium Chrome processes.")


def get_installed_chrome_major_version(default=144):
    path = r"C:\Program Files\Google\Chrome\Application"

    try:
        folders = [
            f
            for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f))
        ]

        for f in folders:
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", f):
                major = int(f.split(".")[0])
                print(f"Chrome version: {major} from folder: {f}")
                return major

    except Exception:
        pass

    return default


# ============================================================
# DRIVER
# ============================================================

def build_driver():
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"
    chrome_path = r"C:\Program Files\Google\Chrome\Application"

    # ---- BRAVE FIRST ----
    if os.path.exists(brave_path):
        using_brave = True
        browser_path = (
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        )

        kill_brave_selenium_instances()

    # ---- CHROME FALLBACK ----
    else:
        using_brave = False
        browser_path = (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )

        chrome_major = get_installed_chrome_major_version(default=144)
        print(f"Detected Chrome major version: {chrome_major}")

        kill_selenium_chrome()

    options = uc.ChromeOptions()
    options.set_capability(
    "goog:loggingPrefs",
    {"performance": "ALL"}
)

    if using_brave:
        options.binary_location = browser_path

    profile_path = os.path.join(
        os.environ["TEMP"],
        "selenium_admin_profile"
    )

    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-minimized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if using_brave:
        driver = uc.Chrome(
            options=options,
            version_main=146
        )

    else:
        driver = uc.Chrome(
            options=options,
            version_main=chrome_major
        )
    driver.execute_cdp_cmd("Network.enable", {})
    return driver


# ============================================================
# LIVE TAB CLICK
# ============================================================

def click_live_tab(driver):
    """
    Finds the site's Live Game tab.

    The site's React tab definition uses:
        id: "live-game"
        label: "Live Game"

    We target the visible label because the internal React id is not
    guaranteed to become an HTML id attribute.
    """

    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # Preferred: click an actual button/tab/link whose visible text is Live Game.
    preferred_xpath = (
        "//*["
        "(self::button or self::a or @role='tab')"
        " and normalize-space(.)='Live Game'"
        "]"
    )

    try:
        live_tab = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, preferred_xpath)
            )
        )

    except Exception:
        # Fallback in case the tab component renders a different clickable tag.
        fallback_xpath = "//*[normalize-space(.)='Live Game']"

        live_tab = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, fallback_xpath)
            )
        )

    # Scroll it into view in case the page has a horizontal/vertical tab bar.
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
        live_tab
    )

    time.sleep(0.25)

    try:
        driver.get_log("performance")
        live_tab.click()
        live_data = wait_for_json_response(
        driver,
        "https://api.rivalsdata.com/live"
    )
        if live_data:
            print("\nLIVE JSON:")
            print(
                json.dumps(
                    live_data,
                    indent=4
                )
            )
        return live_data
    except Exception:
        # JS click fallback for pages with overlays/custom JS controls.
        driver.execute_script(
            "arguments[0].click();",
            live_tab
        )

    print("Clicked Live Game tab.")


# ============================================================
# MAIN
# ============================================================
def parsePlayer(j):
    status = j.get("status").get("status")
        
    if status is None:
        status = j.get("status")
        mid = status.get("battle_id", None)
        return mid
    for code in status:
        if code == "6":
            mid = status[code]['extra'].get('battle_id', None)

            return mid
    if "battle_id" in status:
        mid = status.get("battle_id", False)
        return mid
    return False
def main():
    driver = None

    try:
        driver = build_driver()

        print(f"Opening: {TARGET_URL}")
        driver.get(TARGET_URL)

        # Wait until the page has at least loaded its body.
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        live = click_live_tab(driver)

        print("Live Game tab click complete.")

        # Keep browser open so you can inspect what happened.
        from rivalsdataMatchObject import LiveMatch
        MatchObject = LiveMatch(live, 111, config.USER_UID)
        #name_list = [player.Name for player in MatchObject.Players]

    except Exception as e:
        print(f"ERROR: {e}")

        if driver:
            input("Press ENTER to close browser...")

    finally:
        if driver:
            try:
                driver.quit()
                kill_brave_selenium_instances()
                kill_selenium_chrome()
    
                return MatchObject
            except Exception:
                pass


if __name__ == "__main__":
    main()