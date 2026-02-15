"""Verify Upwork proposal was submitted."""
from playwright.sync_api import sync_playwright

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

for p in context.pages:
    print(f"Tab: {p.url[:80]} | {p.title()[:50]}")
    if "success" in p.url.lower() or "proposals" in p.url.lower():
        print(f"  >>> PROPOSAL PAGE: {p.url}")
        print(f"  >>> Title: {p.title()}")

pw.stop()
