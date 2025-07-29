from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import json
import time

def get_profile_stats(username):
    url = f"https://tracker.gg/marvel-rivals/profile/ign/{username}/overview"

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)

    try:
        driver.get(url)

        # ✅ Wait for the script tag to load (up to 10 seconds)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "__NEXT_DATA__"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")

        if not script_tag:
            print(f"❌ No embedded JSON data found for {username}.")
            return

        data = json.loads(script_tag.string)
        segments = data.get("props", {}).get("pageProps", {}).get("profile", {}).get("segments", [])

        if not segments:
            print(f"❌ No stats found for {username}.")
            return

        print(f"\n📊 Stats for {username}:")
        for seg in segments[:3]:
            char = seg["metadata"].get("name", "Unknown")
            kd = seg["stats"].get("kd", {}).get("value")
            matches = seg["stats"].get("matchesPlayed", {}).get("value")
            print(f"- {char}: K/D = {kd}, Matches = {matches}")

    except Exception as e:
        print(f"❌ Error with {username}: {e}")
    finally:
        driver.quit()
