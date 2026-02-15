# -*- coding: utf-8 -*-
"""Check Reddit inbox for responses to our DMs."""
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
            if "Just a moment" in page.title():
                time.sleep(2)
            elif page.title():
                return True
        except:
            time.sleep(1)
    return False

# ============================================================
# Check Reddit Inbox
# ============================================================
print("=" * 60)
print("REDDIT INBOX")
print("=" * 60)

safe_nav("https://www.reddit.com/message/inbox/")
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

text = page.evaluate("document.body.innerText.substring(0, 4000)")
print(f"\n{text[:3500]}")

# ============================================================
# Check Reddit Unread
# ============================================================
print("\n" + "=" * 60)
print("REDDIT UNREAD")
print("=" * 60)

safe_nav("https://www.reddit.com/message/unread/")
time.sleep(3)
print(f"URL: {page.url[:80]}")

text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\n{text[:2500]}")

# ============================================================
# Check Reddit Sent (confirm our DMs went through)
# ============================================================
print("\n" + "=" * 60)
print("REDDIT SENT")
print("=" * 60)

safe_nav("https://www.reddit.com/message/sent/")
time.sleep(3)
print(f"URL: {page.url[:80]}")

text = page.evaluate("document.body.innerText.substring(0, 4000)")
print(f"\n{text[:3500]}")

pw.stop()
