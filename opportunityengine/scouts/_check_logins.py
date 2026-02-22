"""Check login status on Freelancer and Upwork via Edge CDP."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]

    # Check Freelancer
    print("\n--- FREELANCER ---")
    fl_page = context.new_page()
    fl_page.goto("https://www.freelancer.com/dashboard", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    fl_url = fl_page.url
    print(f"URL: {fl_url}")
    if "login" in fl_url.lower() or "signup" in fl_url.lower():
        print("STATUS: NOT LOGGED IN")
        fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_login.png")
        # Navigate to login page
        fl_page.goto("https://www.freelancer.com/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_login.png")
        print("Login page opened - screenshot saved")
    else:
        print("STATUS: LOGGED IN")
        body = fl_page.inner_text("body")[:300]
        print(f"Page: {body[:200]}")
        fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_dashboard.png")

    # Check Upwork
    print("\n--- UPWORK ---")
    uw_page = context.new_page()
    uw_page.goto("https://www.upwork.com/nx/find-work/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    uw_url = uw_page.url
    print(f"URL: {uw_url}")
    if "login" in uw_url.lower() or "signup" in uw_url.lower() or "ab/account-security" in uw_url.lower():
        print("STATUS: NOT LOGGED IN")
        uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_login.png")
        print("Login page opened - screenshot saved")
    else:
        print("STATUS: LOGGED IN")
        body = uw_page.inner_text("body")[:300]
        print(f"Page: {body[:200]}")
        uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_dashboard.png")

    pw.stop()


if __name__ == "__main__":
    main()
