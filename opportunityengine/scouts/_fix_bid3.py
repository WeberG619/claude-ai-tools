"""Fill Upwork proposal form using JS clicks to avoid interception."""
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

# 1. Switch to single payment mode using JS click
print("\n=== Switching to single payment ===")
page.evaluate("""
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const r of radios) {
        if (r.value === 'default') {
            r.click();
        }
    }
""")
time.sleep(2)

# Check which mode is now active
mode = page.evaluate("""
    const checked = document.querySelector('input[type="radio"]:checked');
    checked ? checked.value : 'none';
""")
print(f"  Mode: {mode}")

# 2. Fill bid amount
print("\n=== Filling bid amount ===")
# Find visible text inputs
page.evaluate("""
    const inputs = document.querySelectorAll('input[type="text"]');
    for (const inp of inputs) {
        const ph = inp.placeholder || '';
        if (ph.includes('$') || ph.includes('0.00')) {
            inp.focus();
            inp.value = '';
            inp.dispatchEvent(new Event('input', {bubbles: true}));
            inp.value = '65';
            inp.dispatchEvent(new Event('input', {bubbles: true}));
            inp.dispatchEvent(new Event('change', {bubbles: true}));
            inp.dispatchEvent(new Event('blur', {bubbles: true}));
        }
    }
""")
time.sleep(1)

# Also try the direct approach - find the input and type into it
bid_inputs = page.query_selector_all('input[type="text"]:visible')
for inp in bid_inputs:
    ph = inp.get_attribute("placeholder") or ""
    try:
        val = inp.input_value()
    except:
        val = ""
    if "$" in ph or "$" in val:
        print(f"  Found bid input (ph='{ph}', val='{val}'), typing 65...")
        inp.focus()
        time.sleep(0.2)
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        time.sleep(0.1)
        page.keyboard.type("65", delay=50)
        time.sleep(0.5)
        page.keyboard.press("Tab")
        time.sleep(0.5)
        try:
            print(f"  Value now: {inp.input_value()}")
        except:
            pass
        break

# 3. Fill milestone description if still in milestone mode
print("\n=== Filling description ===")
desc = page.query_selector('input[aria-label="Description 1"]')
if desc and desc.is_visible():
    try:
        val = desc.input_value()
        if not val:
            desc.focus()
            time.sleep(0.1)
            page.keyboard.type("Complete Dynamo script for Revit 2021 property updates", delay=20)
            time.sleep(0.3)
            page.keyboard.press("Tab")
            print("  Filled milestone description")
    except:
        pass
else:
    print("  No description field visible (may be in single-payment mode)")

# 4. Set duration
print("\n=== Setting duration ===")
# Look for native select
selects = page.query_selector_all("select")
for sel in selects:
    vis = sel.is_visible()
    options = sel.query_selector_all("option")
    opt_texts = []
    for opt in options:
        v = opt.get_attribute("value") or ""
        t = opt.inner_text().strip()
        opt_texts.append(f"{v}='{t}'")
    print(f"  Select (visible={vis}): {', '.join(opt_texts[:6])}")
    if vis:
        # Select a reasonable option (not the empty/default)
        for opt in options:
            v = opt.get_attribute("value") or ""
            t = opt.inner_text().strip().lower()
            if v and "select" not in t and v != "":
                print(f"  Selecting: {opt.inner_text().strip()}")
                sel.select_option(value=v)
                time.sleep(1)
                break

# If no native select, look for custom dropdown
if not selects:
    # Look for duration-related buttons/dropdowns
    all_els = page.query_selector_all('[class*="dropdown"], [class*="select"], button:visible')
    for el in all_els:
        try:
            text = el.inner_text().strip()[:60].lower()
            if "duration" in text or "how long" in text or "select" in text:
                print(f"  Duration dropdown: '{el.inner_text().strip()[:60]}'")
                el.click()
                time.sleep(1)
                # Find menu items
                items = page.query_selector_all('[role="option"]:visible, [role="menuitem"]:visible, li:visible')
                for item in items[:10]:
                    it = item.inner_text().strip()
                    print(f"    Item: {it}")
                break
        except:
            continue

# 5. Check errors before submitting
print("\n=== Pre-submit check ===")
time.sleep(1)
errors = page.query_selector_all('[role="alert"]:visible')
err_texts = []
for err in errors:
    try:
        text = err.inner_text().strip()
        if text and len(text) > 3:
            err_texts.append(text[:80])
    except:
        pass
if err_texts:
    print(f"  Errors remaining: {err_texts}")
else:
    print("  No visible errors!")

# 6. Screenshot the current state for debugging
print("\n=== Current form state ===")
# Get all visible non-empty inputs
for inp in page.query_selector_all("input:visible, textarea:visible, select:visible"):
    tag = inp.evaluate("el => el.tagName")
    name = inp.get_attribute("name") or ""
    itype = inp.get_attribute("type") or ""
    try:
        val = inp.input_value()[:50] if tag != "SELECT" else ""
    except:
        val = ""
    if tag == "SELECT":
        val = inp.evaluate("el => el.options[el.selectedIndex]?.text || ''")
    if itype not in ("radio", "hidden", "search", "checkbox"):
        print(f"  {tag}: name={name}, type={itype}, value='{val}'")

# 7. Submit
print("\n=== Submitting ===")
submit = page.query_selector('button:has-text("Submit proposal")')
if submit:
    disabled = submit.get_attribute("disabled")
    print(f"  Submit button disabled={disabled}")
    if disabled is None:
        submit.click()
        time.sleep(8)
        new_url = page.url
        print(f"  URL: {new_url}")
        if "apply" not in new_url.lower():
            print("  SUCCESS - Left apply page!")
        else:
            # Final error check
            errors = page.query_selector_all('[role="alert"]:visible')
            for err in errors:
                try:
                    text = err.inner_text().strip()
                    if text and len(text) > 3:
                        print(f"  Error: {text[:100]}")
                except:
                    pass

pw.stop()
