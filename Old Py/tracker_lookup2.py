# tracker_lookup.py
import urllib.parse
import time
import undetected_chromedriver as uc

def open_tracker_profile_with_undetected_chrome(player_name):
    platforms = ["ign","steam", "xbox", "psn"]
    encoded = urllib.parse.quote(player_name)

    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--start-maximized")

    try:
        driver = uc.Chrome(options=options)

        for platform in platforms:
            url = f"https://tracker.gg/marvel-rivals/profile/{platform}/{encoded}/overview"
            print(f"Trying: {url}")
            driver.get(url)
            time.sleep(3)  # wait for Cloudflare or page to load

            if "Overview" in driver.title or "Marvel Rivals" in driver.title:
                print(f"✅ Found: {url}")
                return driver, url

        print(f"❌ No profile found for {player_name}")
        driver.quit()
        return None, None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
