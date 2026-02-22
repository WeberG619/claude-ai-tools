"""Verify Freelancer login and take screenshot of dashboard."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    # Find Freelancer tab or navigate
    fl_page = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl_page = p
            break

    if not fl_page:
        fl_page = context.new_page()

    fl_page.goto("https://www.freelancer.com/dashboard", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    url = fl_page.url
    print(f"URL: {url}")

    if "login" in url.lower():
        print("NOT LOGGED IN")
    else:
        print("LOGGED IN!")
        body = fl_page.inner_text("body")[:500]
        print(f"Dashboard: {body[:300]}")

    fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_verified.png")
    print("Screenshot saved")

    pw.stop()


if __name__ == "__main__":
    main()
