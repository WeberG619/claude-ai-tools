"""Check Freelancer membership/bid pack options."""

import time
from playwright.sync_api import sync_playwright


def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=8000)
        print(f"Screenshot: {path}")
    except:
        print("Screenshot timed out")


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]
    page = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            page = p
            break

    if not page:
        print("No Freelancer tab")
        pw.stop()
        return

    # Navigate to the membership page
    page.goto("https://www.freelancer.com/membership", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    print(f"On: {page.url}")
    body = page.inner_text("body")[:3000]
    print(f"Page text:\n{body[:2000]}")

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_membership.png")

    # Scroll down to see plans
    page.evaluate("window.scrollBy(0, 600)")
    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_membership2.png")

    pw.stop()


if __name__ == "__main__":
    main()
