"""Fix bid amount and resubmit for Streamlit Ops Control Panel (#1134)."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    # Find Freelancer tab
    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        print("No Freelancer tab found")
        pw.stop()
        return

    print(f"URL: {fl.url}")

    # Fix bid amount - clear and set to $300 (within $250-350 range)
    bid_input = fl.query_selector('input[flmarker="bidAmountInput"]')
    if not bid_input:
        # Try finding by looking at all visible number/text inputs near "Bid Amount"
        inputs = fl.query_selector_all("input")
        for inp in inputs:
            try:
                if inp.is_visible():
                    val = inp.input_value()
                    if val == "750.00" or val == "750":
                        bid_input = inp
                        print(f"Found bid input with value: {val}")
                        break
            except:
                continue

    if bid_input:
        bid_input.click(click_count=3)  # Select all
        time.sleep(0.3)
        bid_input.fill("300")
        print("Bid amount changed to $300")
        time.sleep(1)
    else:
        print("Could not find bid amount input - trying JavaScript")
        fl.evaluate("""() => {
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                if (inp.value === '750.00' || inp.value === '750') {
                    inp.value = '300';
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    return true;
                }
            }
            return false;
        }""")
        print("Set via JS")

    time.sleep(1)

    # Also fix milestone amount if present
    fl.evaluate("""() => {
        const inputs = document.querySelectorAll('input');
        for (const inp of inputs) {
            if (inp.value === '750.00' || inp.value === '750') {
                inp.value = '300';
                inp.dispatchEvent(new Event('input', {bubbles: true}));
                inp.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }
    }""")

    time.sleep(1)
    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_fixed_1134.png")

    # Now click "Place Bid" / "Write my bid" button
    submit_btn = fl.query_selector('button:has-text("Write my bid")')
    if not submit_btn:
        submit_btn = fl.query_selector('button:has-text("Place Bid")')
    if not submit_btn:
        submit_btn = fl.query_selector('button:has-text("Submit")')
    if not submit_btn:
        buttons = fl.query_selector_all("button")
        for btn in buttons:
            try:
                txt = btn.inner_text().lower()
                if "bid" in txt or "submit" in txt:
                    print(f"Found button: '{btn.inner_text()}'")
                    submit_btn = btn
                    break
            except:
                continue

    if submit_btn:
        print(f"Clicking: '{submit_btn.inner_text()}'")
        submit_btn.click()
        time.sleep(5)
        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_submitted_1134.png")
        body = fl.inner_text("body")[:1500]
        print(f"\nAfter submit:\n{body[:800]}")
    else:
        print("Could not find submit button")

    pw.stop()


if __name__ == "__main__":
    main()
