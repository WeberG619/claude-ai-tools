# -*- coding: utf-8 -*-
"""Fix the Teach MCP submission - needs description field filled."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CDP_URL = "http://localhost:9222"

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

# Navigate to the Teach MCP job
url = "https://www.upwork.com/jobs/Teach-MCP_~022020941554783960036/"
page.evaluate(f"window.location.href = '{url}'")
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

# Check current state
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Check if already applied
already = page.evaluate("document.body.innerText.includes('already submitted')")
print(f"Already applied: {already}")

# Check connects
connects = page.evaluate("""(() => {
    const text = document.body.innerText;
    const m = text.match(/Available Connects:\\s*(\\d+)/);
    return m ? m[1] : 'unknown';
})()""")
print(f"Available Connects: {connects}")

if already:
    print("Already submitted - no action needed")
    pw.stop()
    exit()

# Click Apply
try:
    btn = page.locator('#submit-proposal-button').first
    if btn.is_visible(timeout=3000):
        btn.click(timeout=10000)
        time.sleep(6)
        print("Clicked Apply")
    else:
        page.locator('button:has-text("Apply now")').first.click(timeout=5000)
        time.sleep(6)
        print("Clicked Apply now")
except Exception as e:
    print(f"Apply click issue: {e}")

time.sleep(3)
print(f"Current URL: {page.url[:80]}")

if "apply" not in page.url.lower() and "proposal" not in page.url.lower():
    print("Not on apply page, exiting")
    pw.stop()
    exit()

# Check for description field (the error said "A description is needed")
# Look for all textareas and inputs
textareas = page.locator("textarea:visible")
ta_count = textareas.count()
print(f"\nVisible textareas: {ta_count}")

for i in range(ta_count):
    try:
        val = textareas.nth(i).input_value()[:50]
        ph = textareas.nth(i).get_attribute("placeholder") or ""
        name = textareas.nth(i).get_attribute("name") or ""
        aria = textareas.nth(i).get_attribute("aria-label") or ""
        print(f"  TA[{i}]: name='{name}' aria='{aria}' ph='{ph[:40]}' val='{val[:40]}'")
    except:
        print(f"  TA[{i}]: error reading")

# Check for any label with "description"
labels = page.evaluate("""(() => {
    const labels = document.querySelectorAll('label');
    const results = [];
    for (const l of labels) {
        const text = l.textContent.trim();
        if (text.toLowerCase().includes('descri')) {
            results.push({text: text.substring(0, 80), for: l.getAttribute('for') || ''});
        }
    }
    return results;
})()""")
print(f"\nDescription labels: {labels}")

# Check all visible inputs
inputs = page.locator('input:visible')
in_count = inputs.count()
print(f"\nVisible inputs: {in_count}")
for i in range(in_count):
    try:
        itype = inputs.nth(i).get_attribute("type") or ""
        name = inputs.nth(i).get_attribute("name") or ""
        ph = inputs.nth(i).get_attribute("placeholder") or ""
        val = inputs.nth(i).input_value()[:30]
        aria = inputs.nth(i).get_attribute("aria-label") or ""
        print(f"  IN[{i}]: type='{itype}' name='{name}' aria='{aria}' ph='{ph[:30]}' val='{val}'")
    except:
        print(f"  IN[{i}]: error")

# Get any error messages
errors = page.evaluate("""(() => {
    const els = document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"]');
    return Array.from(els).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 150)).filter(t => t.length > 3);
})()""")
print(f"\nErrors on page: {errors}")

pw.stop()
