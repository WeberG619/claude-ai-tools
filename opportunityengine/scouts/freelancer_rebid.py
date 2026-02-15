"""Fix Freelancer bid amount to $750 (minimum) and resubmit."""

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
        if "freelancer.com" in p.url:
            page = p
            break

    if not page:
        print("No Freelancer tab")
        pw.stop()
        return

    print(f"On: {page.url}")

    # The bid form should still be visible - scroll to it
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)

    # Fix bid amount - change from 500 to 750
    bid_input = page.query_selector('input[placeholder*="bid"]')
    if not bid_input or not bid_input.is_visible():
        # Try by type=number
        inputs = page.query_selector_all('input[type="number"]')
        for inp in inputs:
            try:
                if inp.is_visible():
                    val = inp.input_value()
                    if val == "500" or val == "500.00":
                        bid_input = inp
                        break
            except:
                pass

    if bid_input and bid_input.is_visible():
        bid_input.click()
        bid_input.fill("")
        bid_input.fill("750")
        print("Updated bid to $750")
        # Tab out to trigger validation
        bid_input.press("Tab")
        time.sleep(1)
    else:
        print("Could not find bid input")

    # Fix milestone amount - find the input with 1125.00 and change to 750
    inputs = page.query_selector_all('input[type="number"]')
    for inp in inputs:
        try:
            if inp.is_visible():
                val = inp.input_value()
                if val in ("1125.00", "1125", "500.00", "500"):
                    # Check if this is NOT the main bid input (check placeholder)
                    ph = inp.get_attribute("placeholder") or ""
                    if "bid" not in ph.lower():
                        inp.click()
                        inp.fill("")
                        inp.fill("750")
                        print(f"Updated milestone from {val} to 750")
                        inp.press("Tab")
                        time.sleep(0.5)
        except:
            pass

    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_rebid.png")

    # Check if there are still errors
    body = page.inner_text("body")[:2000]
    if "at least" in body.lower():
        print("Still showing minimum amount error")
    else:
        print("No minimum amount error visible")

    # Scroll down to Place Bid button
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Click Place Bid
    place_bid = page.query_selector('button:has-text("Place Bid")')
    if place_bid and place_bid.is_visible():
        print("\n>>> CLICKING PLACE BID <<<")
        place_bid.click()
        time.sleep(6)

        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_rebid_result.png")
        print(f"URL: {page.url}")
        result_body = page.inner_text("body")[:500]
        print(f"Result: {result_body[:300]}")

        if any(kw in result_body.lower() for kw in ["bid placed", "success", "submitted", "congratulations"]):
            print("\nSUCCESS!")
        elif "failed" in result_body.lower() or "error" in result_body.lower():
            print("\nStill has errors - check screenshot")
        else:
            print("\nCheck screenshot for result")
    else:
        print("Place Bid button not found")

    pw.stop()


if __name__ == "__main__":
    main()
