"""Fix validation errors and submit Playwright proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:50]}")
print(f"URL: {page.url[:80]}")

# Dump all select/dropdown elements
selects = page.evaluate("""(() => {
    const selects = document.querySelectorAll('select');
    return Array.from(selects).map(s => ({
        name: s.name || '',
        id: s.id || '',
        visible: s.offsetParent !== null,
        options: Array.from(s.options).map(o => ({value: o.value, text: o.textContent.trim()})),
        selected: s.value,
    }));
})()""")
print(f"\nSelect elements ({len(selects)}):")
for s in selects:
    vis = "VISIBLE" if s['visible'] else "hidden"
    print(f"  name={s['name']}, id={s['id']} ({vis}), selected={s['selected']}")
    for o in s['options']:
        print(f"    [{o['value']}] {o['text']}")

# Also check for custom dropdowns (Upwork uses role=combobox or data-test dropdowns)
custom_dd = page.evaluate("""(() => {
    const dds = document.querySelectorAll('[role="combobox"], [role="listbox"], [data-test*="dropdown"], [class*="select"], [class*="dropdown"]');
    return Array.from(dds).filter(d => d.offsetParent !== null).map(d => ({
        tag: d.tagName,
        role: d.getAttribute('role') || '',
        cls: (typeof d.className === 'string' ? d.className : '').substring(0, 60),
        text: d.textContent.trim().substring(0, 100),
        dataTest: d.getAttribute('data-test') || '',
    })).slice(0, 15);
})()""")
print(f"\nCustom dropdowns ({len(custom_dd)}):")
for d in custom_dd:
    print(f"  [{d['tag']}] role={d['role']}, data-test={d['dataTest']}, text={d['text'][:60]}")

# Try to find and fill the rate-increase fields
# These are likely select dropdowns or custom components
# Try clicking on "Select a frequency" area
print("\n=== Fixing rate increase fields ===")

# Look for the specific question sections
page_text = page.evaluate("""(() => {
    const body = document.body.innerText;
    const start = body.indexOf('How often do you want');
    if (start === -1) return '';
    return body.substring(start, start + 500);
})()""")
print(f"Rate increase section: {page_text[:300]}")

# Try to find all visible dropdowns/comboboxes near "rate increase"
rate_dropdowns = page.locator('[role="combobox"][data-test="dropdown-toggle"]:visible')
dd_count = rate_dropdowns.count()
print(f"\nVisible combobox dropdowns: {dd_count}")

for i in range(dd_count):
    dd = rate_dropdowns.nth(i)
    text = dd.text_content()
    print(f"  [{i}] {text[:50]}")

# Click each dropdown and select first valid option
for i in range(dd_count):
    dd = rate_dropdowns.nth(i)
    text = dd.text_content().strip()
    print(f"\n  Clicking dropdown [{i}]: {text[:40]}")
    try:
        dd.click(timeout=5000)
        time.sleep(1)

        # Look for options
        options = page.locator('[role="option"]:visible')
        opt_count = options.count()
        print(f"  Options: {opt_count}")
        for j in range(min(opt_count, 5)):
            opt_text = options.nth(j).text_content().strip()
            print(f"    [{j}] {opt_text}")

        # Select appropriate option
        if opt_count > 0:
            # For frequency: pick something reasonable
            for j in range(opt_count):
                opt_text = options.nth(j).text_content().strip().lower()
                if 'annually' in opt_text or 'yearly' in opt_text or '12' in opt_text:
                    options.nth(j).click()
                    print(f"  Selected: {options.nth(j).text_content().strip()}")
                    break
                elif '6 month' in opt_text or 'semi' in opt_text:
                    options.nth(j).click()
                    print(f"  Selected: {options.nth(j).text_content().strip()}")
                    break
            else:
                # Just pick first option if no good match
                if opt_count > 1:
                    options.nth(1).click()  # Skip first if it's a placeholder
                    print(f"  Selected option 1: {options.nth(1).text_content().strip()}")
                else:
                    options.nth(0).click()
                    print(f"  Selected option 0")
            time.sleep(1)
    except Exception as e:
        print(f"  Error: {e}")

# Also try regular select elements
for s in selects:
    if s['visible'] and not s['selected']:
        selector = f"#{s['id']}" if s['id'] else f"select[name='{s['name']}']"
        try:
            sel = page.locator(selector).first
            # Pick a reasonable option
            if len(s['options']) > 1:
                sel.select_option(index=1)
                print(f"  Filled select {selector}: option 1")
                time.sleep(0.5)
        except Exception as e:
            print(f"  Select fill error: {e}")

# Now try submitting again
print("\n=== Submitting ===")
time.sleep(2)

# Scroll to submit button
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(1)

submit = page.locator('button:has-text("Submit proposal")')
try:
    submit.click(timeout=10000)
    time.sleep(8)
    print(f"After submit URL: {page.url[:80]}")
    print(f"After submit title: {page.title()[:60]}")

    if "success" in page.url.lower() or "apply" not in page.url.lower():
        print("SUCCESS!")
    else:
        # Check for errors
        errors = page.evaluate("""(() => {
            const errs = document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]');
            return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 150)).filter(t => t.length > 3);
        })()""")
        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  {e[:100]}")

        # Check for confirmation checkbox
        checkbox = page.locator('input[type="checkbox"][value="agree"]')
        if checkbox.count() > 0:
            print("Found confirmation checkbox, clicking...")
            page.evaluate("""(() => {
                const cb = document.querySelector('input[type="checkbox"][value="agree"]');
                if (cb) cb.click();
            })()""")
            time.sleep(2)
            confirm = page.locator('button:has-text("Submit"), button:has-text("Yes")')
            for i in range(confirm.count()):
                try:
                    confirm.nth(i).click(timeout=3000)
                    break
                except:
                    continue
            time.sleep(5)
            print(f"Final URL: {page.url[:80]}")
            if "success" in page.url.lower():
                print("SUCCESS after confirm!")

except Exception as e:
    if "success" in page.url.lower():
        print("SUCCESS (timeout but navigated)")
    else:
        print(f"Submit error: {e}")

pw.stop()
