# -*- coding: utf-8 -*-
"""Check Upwork Connects balance via proposals page."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Try the proposals/settings page
page.evaluate("window.location.href = 'https://www.upwork.com/nx/proposals/'")
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

# Search for connects info
connects_info = page.evaluate("""(() => {
    const text = document.body.innerText;
    const lines = text.split('\\n');
    const results = [];
    for (const line of lines) {
        const l = line.trim();
        if (l.toLowerCase().includes('connect') && l.length < 100) {
            results.push(l);
        }
    }
    return results;
})()""")
print(f"\nConnects mentions: {connects_info}")

# Also check for available connects number
num = page.evaluate("""(() => {
    const text = document.body.innerText;
    const m = text.match(/Available[:\\s]*(\\d+)/i) || text.match(/(\\d+)\\s*(?:Available|Connects available)/i);
    return m ? m[0] : null;
})()""")
print(f"Connects number: {num}")

# Get first 1500 chars
text = page.evaluate("document.body.innerText.substring(0, 1500)")
print(f"\nPage text:\n{text[:1200]}")

pw.stop()
