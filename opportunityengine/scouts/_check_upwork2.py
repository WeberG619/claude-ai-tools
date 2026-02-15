"""Check Upwork Apply button using existing tab (avoids Cloudflare on new pages)."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Use EXISTING tab (not new page - Cloudflare blocks new Playwright pages)
pages = context.pages
print(f"Open tabs: {len(pages)}")
for i, p in enumerate(pages):
    print(f"  [{i}] {p.title()[:50]} | {p.url[:60]}")

# Use the first real tab
page = pages[0] if pages else context.new_page()

# Navigate to job #139
job_url = "https://www.upwork.com/jobs/Dynamo-Revit-Script-Review-and-Parameter-Value-Adjustment_~022019521479826811508"
print(f"\nNavigating to job #139...")
page.goto(job_url, wait_until="domcontentloaded", timeout=30000)

# Wait for Cloudflare with longer patience
for i in range(30):
    title = page.title()
    if "Just a moment" in title:
        print(f"  Cloudflare wait... ({i+1}/30)")
        time.sleep(2)
    else:
        break

time.sleep(3)
print(f"\nTitle: {page.title()}")
print(f"URL: {page.url}")

if "Just a moment" in page.title():
    print("\nStill stuck on Cloudflare. Try navigating manually in the browser.")
    pw.stop()
    exit()

# Check Apply button
btn_info = page.evaluate("""(() => {
    // Look for various Apply button patterns
    const selectors = [
        '#submit-proposal-button',
        'button[aria-label="Apply now"]',
        'button:has-text("Apply now")',
        'a:has-text("Apply now")',
    ];
    for (const sel of selectors) {
        try {
            const btn = document.querySelector(sel);
            if (btn) {
                return {
                    found: true,
                    selector: sel,
                    disabled: btn.disabled,
                    text: btn.textContent.trim(),
                    title: btn.title || '',
                    ariaLabel: btn.getAttribute('aria-label') || '',
                    ariaDisabled: btn.getAttribute('aria-disabled') || '',
                    className: btn.className.substring(0, 100),
                    parentText: btn.parentElement ? btn.parentElement.textContent.trim().substring(0, 200) : '',
                };
            }
        } catch(e) {}
    }
    return {found: false};
})()""")
print(f"\nApply button: {btn_info}")

# Check for Connects info
connects = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n');
    const results = [];
    for (const line of lines) {
        const l = line.trim();
        if ((l.toLowerCase().includes('connect') || l.toLowerCase().includes('proposal') ||
             l.toLowerCase().includes('available') || l.toLowerCase().includes('membership') ||
             l.toLowerCase().includes('upgrade') || l.toLowerCase().includes('plan'))
            && l.length > 5 && l.length < 150) {
            results.push(l);
        }
    }
    return [...new Set(results)].slice(0, 20);
})()""")
print(f"\nConnects/membership text:")
for c in connects:
    print(f"  {c[:100]}")

# Check for any banners, warnings, tooltips
warnings = page.evaluate("""(() => {
    const sels = '[role="alert"], [class*="warning"], [class*="banner"], [class*="notice"], [class*="error"], [class*="tooltip"], [class*="upgrade"], [class*="limit"]';
    const els = document.querySelectorAll(sels);
    return Array.from(els).map(e => e.textContent.trim().substring(0, 200)).filter(t => t.length > 5);
})()""")
print(f"\nWarnings/banners:")
for w in warnings:
    print(f"  {w[:120]}")

# Check available Connects by going to the Connects page
print(f"\n=== Checking Connects balance ===")
page.goto("https://www.upwork.com/nx/plans/connects", wait_until="domcontentloaded", timeout=20000)
for i in range(15):
    if "Just a moment" in page.title():
        time.sleep(2)
    else:
        break
time.sleep(3)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

connects_text = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n');
    const results = [];
    for (const line of lines) {
        const l = line.trim();
        if ((l.toLowerCase().includes('connect') || l.toLowerCase().includes('available') ||
             l.toLowerCase().includes('balance') || l.includes('0') || l.includes('1'))
            && l.length > 2 && l.length < 100) {
            results.push(l);
        }
    }
    return [...new Set(results)].slice(0, 20);
})()""")
print(f"\nConnects page text:")
for c in connects_text:
    print(f"  {c[:100]}")

pw.stop()
