"""Simple Upwork search - navigate and dump what we see."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Try "Most Recent" feed first
print("=== Most Recent Jobs ===")
page.evaluate("window.location.href = 'https://www.upwork.com/nx/find-work/most-recent'")
time.sleep(4)
for i in range(25):
    try:
        if "Just a moment" in page.title():
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        else:
            break
    except:
        time.sleep(2)
time.sleep(3)

print(f"Title: {page.title()[:60]}")
print(f"URL: {page.url[:80]}")

# Dump first 3000 chars of page
text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\nPage text:\n{text[:3000]}")

# Now try search
print(f"\n\n{'='*60}")
print("=== Search: python automation ===")
page.evaluate("window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=python+automation&sort=recency'")
time.sleep(4)
for i in range(25):
    try:
        if "Just a moment" in page.title():
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        else:
            break
    except:
        time.sleep(2)
time.sleep(3)

print(f"Title: {page.title()[:60]}")
print(f"URL: {page.url[:80]}")

text2 = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\nPage text:\n{text2[:3000]}")

pw.stop()
