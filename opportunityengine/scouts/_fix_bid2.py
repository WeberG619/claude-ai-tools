"""Fix all required fields on Upwork proposal form and submit."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Find proposal page
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

# 1. Select "by project" instead of milestones (simpler)
print("\n=== Setting payment type ===")
# Check if there's a "by project" or single payment option
radios = page.query_selector_all('input[type="radio"]:visible')
for r in radios:
    val = r.get_attribute("value") or ""
    name = r.get_attribute("name") or ""
    checked = r.is_checked()
    print(f"  Radio: name={name}, value={val}, checked={checked}")
    if val == "default":
        print(f"  Clicking 'default' (single payment) radio...")
        r.click()
        time.sleep(1)

# 2. After switching to single payment mode, look for new form state
print("\n=== Checking form after mode switch ===")
time.sleep(2)

# Re-examine inputs
inputs = page.query_selector_all("input:visible")
for i, inp in enumerate(inputs):
    ph = inp.get_attribute("placeholder") or ""
    al = inp.get_attribute("aria-label") or ""
    itype = inp.get_attribute("type") or ""
    val = ""
    try:
        val = inp.input_value()
    except:
        pass
    if itype not in ("radio", "hidden", "search", "checkbox"):
        print(f"  [{i}] type={itype}, ph='{ph}', al='{al[:40]}', val='{val}'")

# 3. Fill bid amount - look for currency input
print("\n=== Filling bid amount ===")
bid_filled = False
for inp in inputs:
    ph = inp.get_attribute("placeholder") or ""
    al = inp.get_attribute("aria-label") or ""
    val = ""
    try:
        val = inp.input_value()
    except:
        pass
    itype = inp.get_attribute("type") or ""
    if itype in ("radio", "hidden", "search", "checkbox"):
        continue
    # Look for the amount/bid field
    if "$" in ph or "$" in val or "amount" in al.lower() or "bid" in al.lower() or "price" in al.lower():
        print(f"  Found bid field: ph='{ph}', al='{al}', current='{val}'")
        inp.click()
        time.sleep(0.2)
        # Select all and replace
        page.keyboard.press("Control+a")
        time.sleep(0.1)
        page.keyboard.type("65")
        time.sleep(0.5)
        new_val = inp.input_value()
        print(f"  Set to: {new_val}")
        bid_filled = True
        # Tab out to trigger validation
        page.keyboard.press("Tab")
        time.sleep(0.5)
        break

if not bid_filled:
    # Try filling the $0.00 placeholder input
    for inp in inputs:
        ph = inp.get_attribute("placeholder") or ""
        if "$0.00" in ph:
            print(f"  Trying $0.00 placeholder input...")
            inp.click()
            time.sleep(0.2)
            page.keyboard.press("Control+a")
            page.keyboard.type("65")
            time.sleep(0.5)
            page.keyboard.press("Tab")
            time.sleep(0.5)
            break

# 4. Fill duration dropdown
print("\n=== Setting project duration ===")
# Look for select/dropdown elements
selects = page.query_selector_all("select:visible")
for sel in selects:
    name = sel.get_attribute("name") or ""
    dqa = sel.get_attribute("data-qa") or ""
    print(f"  Select: name={name}, dqa={dqa}")
    # Select first non-empty option
    options = sel.query_selector_all("option")
    for opt in options:
        val = opt.get_attribute("value") or ""
        text = opt.inner_text().strip()
        print(f"    option: value='{val}', text='{text}'")

# Try selecting from dropdown - Upwork might use custom dropdown
# Look for button/div that acts as dropdown
dropdowns = page.query_selector_all('[class*="dropdown"], [class*="select"], [role="listbox"], [role="combobox"]')
for dd in dropdowns:
    text = ""
    try:
        text = dd.inner_text().strip()[:60]
    except:
        pass
    tag = dd.evaluate("el => el.tagName")
    role = dd.get_attribute("role") or ""
    print(f"  Dropdown element: tag={tag}, role={role}, text='{text}'")

# Look for "Select a duration" text and click near it
duration_el = page.query_selector('text="Select a duration"')
if duration_el:
    print("  Found 'Select a duration' text, clicking...")
    duration_el.click()
    time.sleep(1)
    # Look for dropdown options that appeared
    options = page.query_selector_all('[role="option"], li[class*="option"], [class*="menu-item"]')
    for opt in options:
        text = opt.inner_text().strip()
        print(f"    Option: {text}")
    # Click a reasonable duration option
    for opt in options:
        text = opt.inner_text().strip().lower()
        if "1 week" in text or "less than 1 week" in text or "1 to 2 weeks" in text:
            print(f"    Selecting: {opt.inner_text().strip()}")
            opt.click()
            time.sleep(1)
            break
else:
    # Try clicking button that contains duration text
    buttons = page.query_selector_all("button:visible")
    for btn in buttons:
        try:
            text = btn.inner_text().strip().lower()
            if "duration" in text or "select a duration" in text or "how long" in text:
                print(f"  Duration button: '{btn.inner_text().strip()}'")
                btn.click()
                time.sleep(1)
                # Look for options
                options = page.query_selector_all('[role="option"], [role="menuitem"], li:visible')
                for opt in options[:10]:
                    ot = opt.inner_text().strip()
                    if ot:
                        print(f"    Option: {ot}")
                # Select a 1-week-ish option
                for opt in options:
                    ot = opt.inner_text().strip().lower()
                    if "1" in ot and "week" in ot:
                        print(f"    Selecting: {opt.inner_text().strip()}")
                        opt.click()
                        time.sleep(1)
                        break
                break
        except:
            continue

# Also look for native select elements after all
time.sleep(1)
selects = page.query_selector_all("select")
for sel in selects:
    # Try selecting a value
    options = sel.query_selector_all("option")
    for opt in options:
        val = opt.get_attribute("value") or ""
        text = opt.inner_text().strip()
        if val and text and "select" not in text.lower():
            print(f"  Native select - choosing: {text} (value={val})")
            sel.select_option(value=val)
            time.sleep(0.5)
            break
    break

# 5. Check for any remaining errors
print("\n=== Checking errors ===")
time.sleep(1)
errors = page.query_selector_all('[role="alert"]')
for err in errors:
    try:
        text = err.inner_text().strip()
        if text and len(text) > 3:
            print(f"  Error: {text[:100]}")
    except:
        pass

# 6. Try Submit again
print("\n=== Submitting ===")
submit_btn = page.query_selector('button:has-text("Submit proposal")')
if submit_btn:
    print("  Clicking Submit proposal...")
    submit_btn.click()
    time.sleep(8)
    print(f"  URL: {page.url}")
    print(f"  Title: {page.title()}")
    if "apply" not in page.url.lower():
        print("  LEFT apply page - likely SUCCESS!")
    else:
        # Check for remaining errors
        errors = page.query_selector_all('[role="alert"]')
        remaining = []
        for err in errors:
            try:
                text = err.inner_text().strip()
                if text and len(text) > 3:
                    remaining.append(text[:80])
            except:
                pass
        if remaining:
            print(f"  Still has errors: {remaining}")
        else:
            print("  No errors but still on page - check browser")

pw.stop()
