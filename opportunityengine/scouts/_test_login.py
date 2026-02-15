"""Test if Reddit login session works in CDP profile."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.new_page()

# Navigate to Reddit compose page directly - if logged in, it'll load
page.goto("https://www.reddit.com/message/compose/", wait_until="domcontentloaded", timeout=20000)
time.sleep(5)

url = page.url
title = page.title()
print(f"URL: {url}")
print(f"Title: {title}")

if "login" in url.lower():
    print("NOT LOGGED IN - redirected to login")
else:
    print("LOGGED IN - compose page loaded")
    # Check for form elements
    inputs = page.query_selector_all("input, textarea")
    for inp in inputs:
        name = inp.get_attribute("name") or ""
        placeholder = inp.get_attribute("placeholder") or ""
        itype = inp.get_attribute("type") or ""
        print(f"  Field: name={name}, placeholder={placeholder}, type={itype}")

page.close()
pw.stop()
