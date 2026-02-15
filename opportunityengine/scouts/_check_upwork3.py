"""Check Upwork using JS navigation to avoid Cloudflare blocking Playwright goto()."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

pages = context.pages
page = pages[0]
print(f"Current: {page.title()[:50]} | {page.url[:60]}")

# Navigate via JS instead of Playwright goto (avoids Cloudflare fingerprinting)
job_url = "https://www.upwork.com/jobs/Dynamo-Revit-Script-Review-and-Parameter-Value-Adjustment_~022019521479826811508"
page.evaluate(f"window.location.href = '{job_url}'")

# Wait for navigation
for i in range(40):
    time.sleep(2)
    title = page.title()
    url = page.url
    print(f"  [{i+1}] {title[:40]}... | {url[:50]}")
    if "Just a moment" not in title and "upwork.com" in url:
        break

time.sleep(3)
print(f"\nFinal Title: {page.title()}")
print(f"Final URL: {page.url}")

if "Just a moment" in page.title():
    print("\nStill Cloudflare blocked.")
    print("Trying Connects page directly...")
    page.evaluate("window.location.href = 'https://www.upwork.com/nx/plans/connects'")
    for i in range(20):
        time.sleep(2)
        if "Just a moment" not in page.title():
            break
    time.sleep(3)
    print(f"Connects page: {page.title()}")

    if "Just a moment" not in page.title():
        body = page.evaluate("document.body.innerText")
        print(f"\nPage text (first 500 chars):")
        print(body[:500])
else:
    # We're on the job page - check Apply button
    btn_info = page.evaluate("""(() => {
        const btn = document.querySelector('#submit-proposal-button, button[aria-label="Apply now"]');
        if (!btn) return {found: false, buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim().substring(0,40)).filter(t => t.length > 2).slice(0, 10)};
        return {
            found: true,
            disabled: btn.disabled,
            text: btn.textContent.trim(),
            title: btn.title || '',
            ariaDisabled: btn.getAttribute('aria-disabled') || '',
        };
    })()""")
    print(f"\nApply button: {btn_info}")

    # Get connects/proposal info from page
    connects = page.evaluate("""(() => {
        const body = document.body.innerText;
        const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 150);
        return lines.filter(l =>
            l.toLowerCase().includes('connect') ||
            l.toLowerCase().includes('proposal') ||
            l.toLowerCase().includes('require') ||
            l.toLowerCase().includes('available') ||
            l.toLowerCase().includes('upgrade') ||
            l.toLowerCase().includes('credit') ||
            l.toLowerCase().includes('free')
        ).slice(0, 20);
    })()""")
    print(f"\nRelevant text:")
    for c in connects:
        print(f"  {c[:100]}")

pw.stop()
