"""Continue through Upwork verification steps 2-5."""

import time
from playwright.sync_api import sync_playwright


def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=8000)
        print(f"Screenshot: {path}")
    except:
        print("Screenshot timed out")


def click_next(page):
    next_btn = page.query_selector('[data-test="next-button"]')
    if next_btn and next_btn.is_visible():
        next_btn.click()
        time.sleep(3)
        return True
    return False


def dump_page(page, step):
    """Print page state for debugging."""
    print(f"\n{'='*50}")
    print(f"STEP {step}: {page.url}")
    body = page.inner_text("body")[:600]
    print(f"Page text:\n{body[:500]}")

    safe_screenshot(page, rf"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_v{step}.png")

    # Visible inputs
    inputs = page.query_selector_all("input")
    visible_inputs = []
    for inp in inputs:
        try:
            if inp.is_visible():
                info = {
                    "name": inp.get_attribute("name") or "",
                    "type": inp.get_attribute("type") or "",
                    "placeholder": (inp.get_attribute("placeholder") or "")[:40],
                    "value": inp.input_value()[:30],
                    "testid": inp.get_attribute("data-test") or "",
                }
                visible_inputs.append(info)
                print(f"  Input: {info}")
        except:
            pass

    # Visible dropdowns
    combos = page.query_selector_all('[role="combobox"], select')
    for c in combos:
        try:
            if c.is_visible():
                print(f"  Dropdown: name={c.get_attribute('name')} aria={c.get_attribute('aria-label')}")
        except:
            pass

    return visible_inputs


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

    # We should be on step 2 - US tax status
    # Select "Yes" radio (value=true)
    yes_radio = page.query_selector('input[type="radio"][value="true"]')
    if yes_radio:
        yes_radio.click()
        time.sleep(0.5)
        print("Selected 'Yes' for US tax status")

    # Click Next to go to step 3
    print("Going to step 3...")
    if not click_next(page):
        print("No Next button")
        pw.stop()
        return

    # Step 3
    inputs3 = dump_page(page, 3)

    # Step 3 likely asks for name/SSN/TIN info
    # Check what's needed and try to fill what we can
    body = page.inner_text("body")[:1000]

    # If this asks for personal info like SSN, we stop and tell the user
    if any(kw in body.lower() for kw in ["ssn", "social security", "tax identification", "tin", "ein"]):
        print("\n>>> STOP: This step requires SSN/TIN - needs manual input <<<")
        print("Please complete the remaining verification steps in the browser.")
        pw.stop()
        return

    # Check if there are form fields to fill
    # Try to click Next if it's just informational
    if not inputs3:
        print("No input fields - trying Next...")
        click_next(page)
        dump_page(page, 4)

        body4 = page.inner_text("body")[:1000]
        if any(kw in body4.lower() for kw in ["ssn", "social security", "tax identification", "tin", "ein"]):
            print("\n>>> STOP: This step requires SSN/TIN <<<")
            pw.stop()
            return

        click_next(page)
        dump_page(page, 5)
    else:
        print(f"\nStep 3 has {len(inputs3)} input fields - checking what they need...")

    pw.stop()


if __name__ == "__main__":
    main()
