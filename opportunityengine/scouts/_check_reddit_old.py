# -*- coding: utf-8 -*-
"""Check Reddit messages using old.reddit.com which renders more reliably."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

def safe_nav(url, wait=6):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(15):
        try:
            t = page.title()
            if "Just a moment" in t:
                time.sleep(2)
            elif t:
                return True
        except:
            time.sleep(1)
    return False

# ============================================================
# Try old Reddit inbox (more reliable rendering)
# ============================================================
print("=" * 60)
print("OLD REDDIT INBOX")
print("=" * 60)

safe_nav("https://old.reddit.com/message/inbox/")
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

text = page.evaluate("document.body.innerText.substring(0, 5000)")
print(text[:4000])

# ============================================================
# Old Reddit Sent
# ============================================================
print("\n" + "=" * 60)
print("OLD REDDIT SENT")
print("=" * 60)

safe_nav("https://old.reddit.com/message/sent/")
time.sleep(3)
print(f"URL: {page.url[:80]}")

text = page.evaluate("document.body.innerText.substring(0, 5000)")
print(text[:4000])

# ============================================================
# Also check new Reddit notifications
# ============================================================
print("\n" + "=" * 60)
print("REDDIT NOTIFICATIONS")
print("=" * 60)

safe_nav("https://www.reddit.com/notifications")
time.sleep(3)
print(f"URL: {page.url[:80]}")

text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(text[:2500])

# ============================================================
# Check Reddit chat
# ============================================================
print("\n" + "=" * 60)
print("REDDIT CHAT")
print("=" * 60)

safe_nav("https://www.reddit.com/chat")
time.sleep(3)
print(f"URL: {page.url[:80]}")

text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(text[:2500])

pw.stop()
