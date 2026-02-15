# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

# Force navigate via address bar approach
print(f"Current: {page.url[:60]}")
page.evaluate("window.location.href = 'https://www.reddit.com/chat'")
time.sleep(6)
print(f"After nav: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

# If still on old page, try goto
if 'chat' not in page.url:
    try:
        page.goto("https://www.reddit.com/chat", wait_until="domcontentloaded", timeout=15000)
        time.sleep(3)
        print(f"After goto: {page.url[:60]}")
    except Exception as e:
        print(f"goto failed: {e}")

pw.stop()
