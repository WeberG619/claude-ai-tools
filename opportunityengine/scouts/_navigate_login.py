"""Navigate CDP Chrome to Reddit login page so user can log in."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Use the existing tab instead of creating a new one
pages = context.pages
if pages:
    page = pages[0]
    print(f"Using existing tab: {page.title()}")
else:
    page = context.new_page()
    print("Created new tab")

page.goto("https://www.reddit.com/login/", wait_until="domcontentloaded", timeout=20000)
time.sleep(3)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")
print("\nReddit login page is open in the CDP Chrome browser.")
print("Please log in with your Reddit account.")
print("Once logged in, run _submit_all.py to send the DMs.")

pw.stop()
