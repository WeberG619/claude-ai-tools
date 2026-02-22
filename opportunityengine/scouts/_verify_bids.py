"""Verify the $bid comments were posted."""
import time
from playwright.sync_api import sync_playwright

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    page = context.new_page()

    # Check user's comment history
    page.goto("https://old.reddit.com/user/Limp-Initial-8357/comments/", wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)

    body = page.inner_text("body")[:3000]
    safe_print(f"URL: {page.url}")
    safe_print(f"\n{body[:2000]}")

    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_verify_bids.png")
    page.close()
    pw.stop()

if __name__ == "__main__":
    main()
