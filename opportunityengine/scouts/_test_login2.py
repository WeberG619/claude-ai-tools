"""Test Reddit login - try homepage first, then compose with recipient."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.new_page()

# Try homepage first
print("=== Testing Reddit Homepage ===")
page.goto("https://www.reddit.com", wait_until="domcontentloaded", timeout=20000)
time.sleep(4)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Check if we can see user info
try:
    # Look for avatar/username in top right
    html = page.content()
    if "Prove your humanity" in html:
        print("CAPTCHA on homepage too")
    elif "login" in page.url.lower():
        print("Redirected to login")
    else:
        print("Homepage loaded OK")
        # Check for username
        expand_btn = page.query_selector('button[aria-label="Expand user menu"]')
        if expand_btn:
            print("User menu found - LOGGED IN")
except Exception as e:
    print(f"Error: {e}")

# Now try compose with recipient
print("\n=== Testing Compose with Recipient ===")
page.goto("https://www.reddit.com/message/compose/?to=Penoliya_Haruhi",
          wait_until="domcontentloaded", timeout=20000)
time.sleep(4)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

html = page.content()
if "Prove your humanity" in html:
    print("CAPTCHA on compose page")
elif "login" in page.url.lower():
    print("Redirected to login")
else:
    print("Compose page loaded!")
    inputs = page.query_selector_all("input, textarea")
    for inp in inputs:
        name = inp.get_attribute("name") or ""
        print(f"  Field: {name}")

# Try the chat/DM approach instead
print("\n=== Testing Reddit Chat ===")
page.goto("https://www.reddit.com/message/messages",
          wait_until="domcontentloaded", timeout=20000)
time.sleep(4)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

page.close()
pw.stop()
