# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
ctx = browser.contexts[0]
page = [p for p in ctx.pages if 'newtab-footer' not in p.url][0]
page.evaluate("window.location.href = 'https://www.reddit.com/login/'")
time.sleep(4)
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")
print("Chrome is open on Reddit login. Please log in.")
pw.stop()
