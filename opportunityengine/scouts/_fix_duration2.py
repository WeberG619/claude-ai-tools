"""Fix duration dropdown and submit Upwork proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = None
for p in context.pages:
    if "apply" in p.url.lower():
        page = p
        break

if not page:
    print("No proposal page found")
    pw.stop()
    exit(1)

print(f"On: {page.url}")

# Scroll down to see the full form
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(1)

# Find elements near "How long" text using JS
print("\n=== Finding duration field ===")
result = page.evaluate("""(() => {
    const all = document.querySelectorAll('*');
    const results = [];
    for (const el of all) {
        const ownText = Array.from(el.childNodes)
            .filter(n => n.nodeType === 3)
            .map(n => n.textContent.trim())
            .join('');
        if (ownText.toLowerCase().includes('how long') || ownText.toLowerCase().includes('select a duration')) {
            results.push({
                tag: el.tagName,
                text: ownText.substring(0, 80),
                cls: (el.className || '').substring(0, 60),
                role: el.getAttribute('role') || '',
                dt: el.getAttribute('data-test') || ''
            });
        }
    }
    return results;
})()""")

for item in result:
    print(f"  {item['tag']} role={item['role']} dt={item['dt']} text='{item['text'][:50]}'")

# Find all select elements
print("\n=== Select elements ===")
selects_info = page.evaluate("""(() => {
    const selects = document.querySelectorAll('select');
    return Array.from(selects).map(s => ({
        name: s.name,
        id: s.id,
        vis: s.offsetParent !== null,
        opts: Array.from(s.options).slice(0, 6).map(o => o.value + '|' + o.text.trim())
    }));
})()""")

for sel in selects_info:
    print(f"  name={sel['name']}, id={sel['id']}, visible={sel['vis']}")
    for o in sel['opts']:
        print(f"    {o}")

# Find the duration dropdown - look for button/element with "Select a duration" text
print("\n=== Looking for duration dropdown ===")
found = page.evaluate("""(() => {
    // Search for any element that looks like a duration selector
    const btns = document.querySelectorAll('button, [role="combobox"], [role="listbox"], [data-test*="dropdown"]');
    const results = [];
    for (const btn of btns) {
        const text = btn.textContent.trim();
        if (text.includes('Select a duration') || text.includes('duration')) {
            results.push({
                tag: btn.tagName,
                text: text.substring(0, 60),
                role: btn.getAttribute('role') || '',
                dt: btn.getAttribute('data-test') || '',
                aria: btn.getAttribute('aria-haspopup') || ''
            });
        }
    }
    return results;
})()""")

for item in found:
    print(f"  {item['tag']} role={item['role']} dt={item['dt']} aria={item['aria']} text='{item['text'][:50]}'")

# Click the duration dropdown
if found:
    # Click using text matching
    el = page.locator('text="Select a duration"').first
    try:
        el.click(timeout=5000)
        print("  Clicked 'Select a duration'")
        time.sleep(1)

        # Look for options
        options = page.locator('[role="option"]:visible, [role="menuitemradio"]:visible, [data-test="dropdown-option"]:visible')
        count = options.count()
        print(f"  Found {count} options")
        for i in range(min(count, 10)):
            print(f"    [{i}] {options.nth(i).inner_text().strip()}")

        # Select "Less than 1 week" or "1 to 2 weeks" or similar
        for i in range(count):
            text = options.nth(i).inner_text().strip().lower()
            if "1" in text and "week" in text:
                print(f"  Selecting: {options.nth(i).inner_text().strip()}")
                options.nth(i).click()
                time.sleep(1)
                break
        else:
            # Select first valid option
            if count > 0:
                first_text = options.nth(0).inner_text().strip()
                print(f"  Selecting first option: {first_text}")
                options.nth(0).click()
                time.sleep(1)
    except Exception as e:
        print(f"  Click failed: {e}")

        # Alternative: try aria-haspopup buttons
        has_popup = page.locator('button[aria-haspopup]:visible')
        for i in range(has_popup.count()):
            text = has_popup.nth(i).inner_text().strip()
            if "duration" in text.lower() or "select" in text.lower():
                print(f"  Trying aria-haspopup button: '{text}'")
                has_popup.nth(i).click()
                time.sleep(1)
                break

# Check errors
print("\n=== Errors check ===")
time.sleep(1)
errs = page.evaluate("""(() => {
    const alerts = document.querySelectorAll('[role="alert"]');
    return Array.from(alerts).map(a => a.textContent.trim().substring(0, 100)).filter(t => t.length > 3);
})()""")
for e in errs:
    print(f"  {e}")

# If no duration errors, submit
if not any("duration" in e.lower() or "how long" in e.lower() or "empty" in e.lower() for e in errs):
    print("\n=== Submitting ===")
    submit = page.locator('button:has-text("Submit proposal")')
    if submit.is_visible():
        submit.click()
        time.sleep(8)
        print(f"  URL: {page.url}")
        if "apply" not in page.url.lower():
            print("  SUCCESS!")
        else:
            print("  Still on apply page")
else:
    print("\n  Duration still needs to be set - check browser")

pw.stop()
