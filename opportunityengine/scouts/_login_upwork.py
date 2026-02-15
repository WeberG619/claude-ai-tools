# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = [p for p in context.pages if 'newtab-footer' not in p.url][0]
page.evaluate("window.location.href = 'https://www.upwork.com/ab/account-security/login'")
time.sleep(4)
print(f"URL: {page.url[:80]}")
print("Please log in to Upwork.")
pw.stop()
