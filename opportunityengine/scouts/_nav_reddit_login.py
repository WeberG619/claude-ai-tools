# -*- coding: utf-8 -*-
"""Navigate to Reddit login."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = None
for p in context.pages:
    if 'newtab-footer' not in p.url:
        page = p
        break
if not page:
    page = context.pages[0]

page.evaluate("window.location.href = 'https://www.reddit.com/login/'")
time.sleep(5)
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")
print("\nPlease log in to Reddit, then tell me when ready.")

pw.stop()
