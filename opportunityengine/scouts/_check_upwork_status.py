"""Check why Apply button is disabled on Upwork."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.new_page()

# Go to a job page
page.goto("https://www.upwork.com/jobs/Dynamo-Revit-Script-Review-and-Parameter-Value-Adjustment_~022019521479826811508",
          wait_until="domcontentloaded", timeout=30000)

# Wait for Cloudflare
for i in range(15):
    if "Just a moment" in page.title():
        time.sleep(2)
    else:
        break
time.sleep(5)

print(f"Title: {page.title()}")
print(f"URL: {page.url}")

# Check the Apply button state
btn_info = page.evaluate("""(() => {
    const btn = document.querySelector('#submit-proposal-button, button[aria-label="Apply now"]');
    if (!btn) return {found: false};
    return {
        found: true,
        disabled: btn.disabled,
        text: btn.textContent.trim(),
        title: btn.title || '',
        ariaLabel: btn.getAttribute('aria-label') || '',
        ariaExpanded: btn.getAttribute('aria-expanded') || '',
    };
})()""")
print(f"\nApply button: {btn_info}")

# Look for any message/tooltip near the button
msgs = page.evaluate("""(() => {
    const btn = document.querySelector('#submit-proposal-button');
    if (!btn) return [];
    const parent = btn.closest('section, div') || btn.parentElement;
    const texts = [];
    if (parent) {
        const els = parent.querySelectorAll('p, span, div, a');
        for (const el of els) {
            const t = el.textContent.trim();
            if (t.length > 5 && t.length < 200 && !t.includes('Apply now')) {
                texts.push(t);
            }
        }
    }
    return [...new Set(texts)].slice(0, 10);
})()""")

print(f"\nMessages near button:")
for m in msgs:
    print(f"  {m}")

# Check for Connects info
connects = page.evaluate("""(() => {
    const all = document.querySelectorAll('*');
    const results = [];
    for (const el of all) {
        const text = el.textContent || '';
        if ((text.toLowerCase().includes('connect') || text.toLowerCase().includes('proposal'))
            && el.children.length < 3
            && text.length < 100 && text.length > 3) {
            results.push(text.trim());
        }
    }
    return [...new Set(results)].slice(0, 15);
})()""")

print(f"\nConnects/proposal related text:")
for c in connects:
    print(f"  {c[:80]}")

# Check for profile completion warnings
warnings = page.evaluate("""(() => {
    const alerts = document.querySelectorAll('[role="alert"], [class*="warning"], [class*="banner"], [class*="notice"]');
    return Array.from(alerts).map(a => a.textContent.trim().substring(0, 150)).filter(t => t.length > 5);
})()""")

print(f"\nWarnings/alerts:")
for w in warnings:
    print(f"  {w[:100]}")

# Check profile status - navigate to profile
print(f"\n=== Checking profile ===")
page.goto("https://www.upwork.com/freelancers/settings/contactInfo", wait_until="domcontentloaded", timeout=20000)
time.sleep(5)
print(f"Profile URL: {page.url}")
print(f"Profile Title: {page.title()}")

page.close()
pw.stop()
