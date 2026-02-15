"""Fix the duration dropdown on Upwork proposal and submit."""
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

# Find the duration section - look for the text "How long will this project take?"
print("\n=== Finding duration field ===")

# Dump the HTML around the duration section
duration_html = page.evaluate("""
    // Find all elements containing "duration" or "how long"
    const all = document.querySelectorAll('*');
    const results = [];
    for (const el of all) {
        const text = el.textContent || '';
        const tag = el.tagName;
        if ((text.toLowerCase().includes('how long') || text.toLowerCase().includes('duration'))
            && tag !== 'HTML' && tag !== 'BODY' && tag !== 'MAIN'
            && el.children.length < 5) {
            results.push({
                tag: tag,
                class: el.className?.substring?.(0, 80) || '',
                text: text.trim().substring(0, 100),
                id: el.id || '',
                role: el.getAttribute('role') || '',
                children: el.children.length
            });
        }
    }
    return results.slice(0, 15);
""")

for item in duration_html:
    print(f"  {item['tag']} class='{item['class'][:50]}' role='{item['role']}' text='{item['text'][:60]}'")

# Look specifically for select elements, even hidden ones
print("\n=== All select elements ===")
all_selects = page.evaluate("""
    const selects = document.querySelectorAll('select');
    return Array.from(selects).map(s => ({
        name: s.name,
        id: s.id,
        className: (s.className || '').substring(0, 60),
        visible: s.offsetParent !== null,
        optionCount: s.options.length,
        firstOptions: Array.from(s.options).slice(0, 5).map(o => o.text.trim() + '=' + o.value)
    }));
""")

for sel in all_selects:
    print(f"  select: name={sel['name']}, visible={sel['visible']}, options={sel['firstOptions']}")

# Look for custom dropdown/combobox near "how long"
print("\n=== Custom dropdowns ===")
custom_dd = page.evaluate("""
    const labels = document.querySelectorAll('label, span, div, h5, h4');
    for (const label of labels) {
        const text = label.textContent.trim().toLowerCase();
        if (text.includes('how long') && text.length < 100) {
            // Found the label - look for nearby interactive elements
            const parent = label.closest('section, div[class*="field"], div[class*="form"], fieldset') || label.parentElement?.parentElement;
            if (parent) {
                const buttons = parent.querySelectorAll('button, [role="combobox"], [role="listbox"], select');
                return Array.from(buttons).map(b => ({
                    tag: b.tagName,
                    text: b.textContent.trim().substring(0, 60),
                    class: (b.className || '').substring(0, 80),
                    role: b.getAttribute('role') || '',
                    ariaExpanded: b.getAttribute('aria-expanded'),
                    dataTest: b.getAttribute('data-test') || '',
                }));
            }
        }
    }
    return [];
""")

for dd in custom_dd:
    print(f"  {dd['tag']}: text='{dd['text']}' role={dd['role']} data-test={dd['dataTest']} class={dd['class'][:40]}")

# Try to find and click the actual duration dropdown button
print("\n=== Clicking duration dropdown ===")

# Method 1: Find button near "how long" text
clicked = page.evaluate("""
    const labels = document.querySelectorAll('label, span, div, h5, h4');
    for (const label of labels) {
        const text = label.textContent.trim().toLowerCase();
        if (text === 'how long will this project take?' || (text.includes('how long') && text.length < 60)) {
            const parent = label.closest('section, div, fieldset')?.parentElement || label.parentElement?.parentElement;
            if (parent) {
                const btn = parent.querySelector('button, [role="combobox"], [role="listbox"]');
                if (btn) {
                    btn.click();
                    return 'clicked: ' + btn.textContent.trim().substring(0, 40);
                }
                const sel = parent.querySelector('select');
                if (sel) {
                    return 'found_select: ' + sel.name;
                }
            }
        }
    }
    return 'not_found';
""")
print(f"  Result: {clicked}")

time.sleep(1)

# Check if dropdown opened - look for menu/listbox
options = page.query_selector_all('[role="option"]:visible, [role="menuitemradio"]:visible')
if options:
    print(f"  Found {len(options)} dropdown options:")
    for opt in options[:10]:
        text = opt.inner_text().strip()
        print(f"    - {text}")
    # Select a reasonable duration
    for opt in options:
        text = opt.inner_text().strip().lower()
        if "1" in text and ("week" in text or "month" in text):
            print(f"  Selecting: {opt.inner_text().strip()}")
            opt.click()
            time.sleep(1)
            break
    else:
        # Just pick the first non-empty option
        for opt in options:
            text = opt.inner_text().strip()
            if text and "select" not in text.lower():
                print(f"  Selecting first valid: {text}")
                opt.click()
                time.sleep(1)
                break
else:
    print("  No dropdown options visible")
    # Try another approach - look for dropdown with data-test or specific class
    dropdown_btn = page.query_selector('[data-test="dropdown-toggle"]:visible, [data-test="duration"]:visible, button[aria-haspopup]:visible')
    if dropdown_btn:
        text = dropdown_btn.inner_text().strip()
        print(f"  Found dropdown button: '{text}'")
        dropdown_btn.click()
        time.sleep(1)
        options = page.query_selector_all('[role="option"]:visible, li:visible')
        for opt in options[:10]:
            print(f"    Option: {opt.inner_text().strip()}")

# Final error check + submit
print("\n=== Final check & submit ===")
time.sleep(1)
errors = page.evaluate("""
    const alerts = document.querySelectorAll('[role="alert"]');
    return Array.from(alerts).map(a => a.textContent.trim()).filter(t => t.length > 3);
""")
print(f"  Errors: {errors}")

if not errors or errors == ['Please fix the errors below']:
    # Check which specific fields have errors
    field_errors = page.evaluate("""
        const errs = document.querySelectorAll('[class*="error"], [class*="Error"], [data-test*="error"]');
        return Array.from(errs).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 3 && t.length < 100);
    """)
    print(f"  Field errors: {field_errors}")

submit = page.query_selector('button:has-text("Submit proposal")')
if submit:
    print(f"  Submit disabled: {submit.get_attribute('disabled')}")

pw.stop()
