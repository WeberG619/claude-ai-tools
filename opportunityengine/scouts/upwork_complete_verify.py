"""Complete Upwork verification flow - select Individual, proceed through steps."""

import time
from playwright.sync_api import sync_playwright


def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=8000)
        print(f"Screenshot: {path}")
    except:
        print("Screenshot timed out")


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]

    page = None
    for p in context.pages:
        if "upwork.com" in p.url:
            page = p
            break

    if not page:
        print("No Upwork tab found")
        pw.stop()
        return

    print(f"On: {page.url}")

    # First cancel the "Close without submitting?" dialog if it's showing
    cancel_btn = page.query_selector('button:has-text("Cancel")')
    if cancel_btn and cancel_btn.is_visible():
        cancel_btn.click()
        time.sleep(1)
        print("Cancelled the close dialog")

    # Now we should be back on the verification form
    # Click the dropdown to open it
    dropdown = page.query_selector('[role="combobox"]')
    if dropdown:
        dropdown.click()
        time.sleep(1)

        # Select "Individual"
        individual_opt = page.query_selector('[role="option"]:has-text("Individual")')
        if individual_opt:
            individual_opt.click()
            time.sleep(1)
            print("Selected 'Individual'")
        else:
            print("Could not find Individual option")
            pw.stop()
            return
    else:
        print("No dropdown found")
        pw.stop()
        return

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_v1.png")

    # Click Next
    next_btn = page.query_selector('[data-test="next-button"]')
    if next_btn and next_btn.is_visible():
        print("Clicking Next...")
        next_btn.click()
        time.sleep(3)
    else:
        print("No Next button found")

    # Step 2
    print(f"\nStep 2: {page.url}")
    body = page.inner_text("body")[:600]
    print(f"Page text: {body[:400]}")
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_v2.png")

    # Check what step 2 asks for and list visible inputs
    print("\n=== Visible inputs (step 2) ===")
    inputs = page.query_selector_all("input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_visible():
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                label = inp.get_attribute("aria-label") or ""
                val = inp.input_value()[:30]
                testid = inp.get_attribute("data-test") or ""
                print(f"  [{i}] name={name} type={itype} ph={placeholder[:40]} aria={label} testid={testid} val={val}")
        except:
            pass

    print("\n=== Visible buttons (step 2) ===")
    buttons = page.query_selector_all("button")
    for i, btn in enumerate(buttons):
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:40]
                testid = btn.get_attribute("data-test") or ""
                print(f"  [{i}] '{text}' data-test={testid}")
        except:
            pass

    # Check for dropdowns
    print("\n=== Dropdowns (step 2) ===")
    combos = page.query_selector_all('[role="combobox"], select')
    for i, c in enumerate(combos):
        try:
            if c.is_visible():
                name = c.get_attribute("name") or ""
                aria = c.get_attribute("aria-label") or ""
                print(f"  [{i}] name={name} aria={aria}")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()
