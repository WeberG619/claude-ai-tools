"""Navigate to Upwork login page in CDP Chrome."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Use existing tab or create new one
pages = context.pages
page = pages[0] if pages else context.new_page()

page.goto("https://www.upwork.com/ab/account-security/login",
          wait_until="domcontentloaded", timeout=30000)

# Wait for Cloudflare
for i in range(20):
    if "Just a moment" in page.title():
        print(f"  Waiting for Cloudflare... ({i+1})")
        time.sleep(2)
    else:
        break

time.sleep(3)
print(f"Title: {page.title()}")
print(f"URL: {page.url}")
print("\nPlease log in to Upwork in the Chrome window.")

pw.stop()
