"""Navigate to Freelancer.com login page."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print("Navigating to Freelancer login...")
page.evaluate("window.location.href = 'https://www.freelancer.com/login'")

time.sleep(3)
for i in range(15):
    try:
        if "Just a moment" in page.title():
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        elif "freelancer" in page.url.lower():
            break
        else:
            time.sleep(1)
    except:
        time.sleep(1)

time.sleep(2)
print(f"Title: {page.title()}")
print(f"URL: {page.url}")
print("\nPlease log in to Freelancer.com in the Chrome window.")

pw.stop()
