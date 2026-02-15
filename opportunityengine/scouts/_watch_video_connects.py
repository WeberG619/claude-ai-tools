# -*- coding: utf-8 -*-
"""Watch safety video on Upwork to earn 8 free Connects."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Click the "Watch now" button/link on proposals page
# First make sure we're on the proposals page
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

print(f"On: {page.title()[:40]}")

# Find and click "Watch now"
try:
    watch_btn = page.locator('a:has-text("Watch now"), button:has-text("Watch now")').first
    if watch_btn.is_visible(timeout=5000):
        watch_btn.click(timeout=5000)
        time.sleep(5)
        print(f"Clicked Watch now")
        print(f"URL: {page.url[:80]}")
        print(f"Title: {page.title()[:60]}")

        # Wait for video to potentially play
        time.sleep(70)  # Wait over 1 minute for the video

        # Check if there's a "Claim" or "Done" button
        page_text = page.evaluate("document.body.innerText.substring(0, 1000)")
        print(f"\nPage text after video:\n{page_text[:600]}")

        # Try clicking any claim/done/continue button
        page.evaluate("""(() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.toLowerCase();
                if ((text.includes('claim') || text.includes('done') || text.includes('continue') || text.includes('collect')) && btn.offsetParent) {
                    btn.click();
                    return true;
                }
            }
            return false;
        })()""")
        time.sleep(3)
        print(f"\nFinal URL: {page.url[:80]}")
    else:
        print("Watch now button not visible")
except Exception as e:
    print(f"Error: {e}")

# Check connects balance
page.evaluate("window.location.href = 'https://www.upwork.com/nx/find-work/best-matches'")
time.sleep(5)
for i in range(10):
    try:
        if "Just a moment" not in page.title():
            break
        time.sleep(2)
    except:
        time.sleep(1)
time.sleep(2)

connects = page.evaluate("""(() => {
    const text = document.body.innerText;
    const m = text.match(/Available Connects[:\\s]*(\\d+)/i) || text.match(/(\\d+)\\s*Available/i);
    return m ? m[0] : 'not found';
})()""")
print(f"\nConnects: {connects}")

pw.stop()
