from playwright.sync_api import sync_playwright

user_data_dir = r"C:\Users\Corey\AppData\Local\Google\Chrome\User Data"
profile_name = "Default"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        args=[f"--profile-directory={profile_name}"]
    )

    page = browser.new_page()
    page.goto("https://tracker.gg/marvel-rivals", timeout=30000)
    page.wait_for_timeout(8000)

    print("✅ Tracker.gg loaded with your real Chrome profile.")
    
