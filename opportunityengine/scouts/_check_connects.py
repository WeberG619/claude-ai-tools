# -*- coding: utf-8 -*-
"""Check Upwork Connects balance."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Go to connects page
page.evaluate("window.location.href = 'https://www.upwork.com/nx/plans/connects/'")
time.sleep(5)
for i in range(15):
    try:
        if "Just a moment" in page.title():
            time.sleep(2)
        else:
            break
    except:
        time.sleep(1)
time.sleep(2)

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Get connects info
text = page.evaluate("document.body.innerText.substring(0, 2000)")
print(f"\nPage text:\n{text[:1500]}")

pw.stop()
