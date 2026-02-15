"""Fix bid amount and resubmit on Upwork proposal page."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Find the proposal page
page = None
for p in context.pages:
    if "proposals" in p.url.lower() or "apply" in p.url.lower():
        page = p
        break

if not page:
    print("No proposal page found. Pages:")
    for p in context.pages:
        print(f"  {p.url}")
    pw.stop()
    exit(1)

print(f"On proposal page: {page.url}")
print(f"Title: {page.title()}")

# Check for error messages
errors = page.query_selector_all('[class*="error"], [class*="Error"], [data-qa*="error"], [role="alert"]')
for err in errors:
    try:
        text = err.inner_text().strip()
        if text:
            print(f"  Error on page: {text[:100]}")
    except:
        pass

# Find the bid/price input - it had placeholder $0.00
print("\nLooking for bid input...")
all_inputs = page.query_selector_all("input:visible")
for i, inp in enumerate(all_inputs):
    ph = inp.get_attribute("placeholder") or ""
    al = inp.get_attribute("aria-label") or ""
    val = ""
    try:
        val = inp.input_value()
    except:
        pass
    itype = inp.get_attribute("type") or ""
    print(f"  [{i}] type={itype}, placeholder='{ph}', aria-label='{al[:30]}', value='{val}'")

    # The $0.00 placeholder input is likely the bid
    if "$0.00" in ph or "$0.00" in val:
        print(f"  >>> Found bid input at index {i}, filling with $65...")
        inp.click()
        time.sleep(0.2)
        # Triple-click to select all, then type
        inp.click(click_count=3)
        time.sleep(0.1)
        page.keyboard.type("65")
        time.sleep(0.5)
        new_val = inp.input_value()
        print(f"  >>> New value: {new_val}")

# Also check if "Description 1" input needs filling (milestone description)
desc_input = page.query_selector('input[aria-label="Description 1"]')
if desc_input:
    val = desc_input.input_value()
    if not val:
        desc_input.fill("Complete Dynamo script for Revit 2021 property updates")
        print(f"  Filled milestone description")

# Now try submitting again
print("\nLooking for Submit button...")
submit_btn = None
for sel in [
    'button:has-text("Submit proposal")',
    'button:has-text("Submit")',
    'button[data-qa="submit-proposal-btn"]',
]:
    try:
        el = page.query_selector(sel)
        if el and el.is_visible():
            submit_btn = el
            text = el.inner_text().strip()
            disabled = el.get_attribute("disabled")
            aria_dis = el.get_attribute("aria-disabled")
            classes = el.get_attribute("class") or ""
            print(f"  Found: '{text}', disabled={disabled}, aria-disabled={aria_dis}")
            break
    except:
        continue

if submit_btn:
    print("  Clicking Submit...")
    submit_btn.click()
    time.sleep(8)
    print(f"  URL after submit: {page.url}")
    print(f"  Title: {page.title()}")

    # Check for success indicators
    success = page.query_selector('[data-qa="proposal-submitted"], [class*="success"]')
    if success:
        print("  SUCCESS indicator found!")

    # Check if we left the apply page
    if "apply" not in page.url.lower():
        print("  Left the apply page - likely submitted!")
else:
    print("  No submit button found")

pw.stop()
