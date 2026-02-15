# -*- coding: utf-8 -*-
"""Check Reddit inbox for any responses to our DMs."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Navigate to Reddit inbox
page.evaluate("window.location.href = 'https://www.reddit.com/message/inbox/'")
time.sleep(5)
for i in range(10):
    try:
        if "Just a moment" not in page.title():
            break
        time.sleep(2)
    except:
        time.sleep(1)
time.sleep(2)

print(f"URL: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

# Get messages
text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\nInbox:\n{text[:2500]}")

pw.stop()
