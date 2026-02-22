"""Check if the bid was actually placed by navigating to My Bids page."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        print("No Freelancer tab found")
        pw.stop()
        return

    # Navigate to My Bids
    fl.goto("https://www.freelancer.com/users/bids", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    print(f"URL: {fl.url}")
    body = fl.inner_text("body")[:3000]
    print(f"\n{body[:2000]}")

    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_my_bids.png")

    pw.stop()


if __name__ == "__main__":
    main()
