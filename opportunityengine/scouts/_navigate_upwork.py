"""Navigate CDP Chrome to Upwork login."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

pages = context.pages
page = pages[0] if pages else context.new_page()
print(f"Using tab: {page.title()}")

page.goto("https://www.upwork.com/ab/account-security/login", wait_until="domcontentloaded", timeout=30000)
time.sleep(3)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")
print("\nUpwork login page is open. Please log in.")

pw.stop()
