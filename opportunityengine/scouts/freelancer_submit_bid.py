"""Fill and submit Freelancer bid."""

import json
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

    # Scroll to the bid form
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Load proposal
    with open(r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_proposals.json", "r") as f:
        data = json.load(f)

    proposal_text = data["freelancer"]["text"]
    bid_amount = 500

    # Clean proposal for Freelancer
    clean = proposal_text.replace("**", "").replace("- ", "• ")

    # === Fill bid amount ===
    bid_input = page.query_selector('input[placeholder*="bid"]')
    if bid_input and bid_input.is_visible():
        bid_input.click()
        bid_input.fill("")
        bid_input.fill(str(bid_amount))
        print(f"Filled bid amount: ${bid_amount}")
        time.sleep(0.5)
    else:
        print("Could not find bid input")

    # === Fill delivery days (14 days for this scope) ===
    days_input = page.query_selector('input[placeholder*="days"]')
    if days_input and days_input.is_visible():
        days_input.click()
        days_input.fill("")
        days_input.fill("14")
        print("Filled delivery: 14 days")
        time.sleep(0.5)

    # === Fill proposal text ===
    textarea = page.query_selector('textarea[placeholder*="best candidate"]')
    if not textarea:
        textarea = page.query_selector('textarea')

    if textarea and textarea.is_visible():
        textarea.click()
        textarea.fill("")
        textarea.fill(clean)
        print(f"Filled proposal ({len(clean)} chars)")
        time.sleep(0.5)
    else:
        print("Could not find proposal textarea")

    # Update milestone amount to match bid
    milestone_input = page.query_selector('input[placeholder*="milestone"]')
    if not milestone_input:
        # It's the 4th visible number input
        inputs = page.query_selector_all('input[type="number"]')
        for inp in inputs:
            try:
                if inp.is_visible():
                    val = inp.input_value()
                    ph = inp.get_attribute("placeholder") or ""
                    if val == "1125.00" or (not ph and float(val) > 100):
                        inp.click()
                        inp.fill("")
                        inp.fill(str(bid_amount))
                        print(f"Updated milestone amount to ${bid_amount}")
                        break
            except:
                pass

    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_ready.png")

    # === Click Place Bid ===
    place_bid = page.query_selector('button:has-text("Place Bid")')
    if place_bid and place_bid.is_visible():
        print("\n>>> CLICKING PLACE BID <<<")
        place_bid.click()
        time.sleep(6)

        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_result.png")
        print(f"After submit URL: {page.url}")
        body = page.inner_text("body")[:500]
        print(f"Result: {body[:300]}")

        if any(kw in body.lower() for kw in ["bid placed", "success", "submitted", "congratulations"]):
            print("\nSUCCESS - Bid placed!")
        elif "error" in body.lower():
            print("\nError detected - check screenshot")
        else:
            print("\nBid clicked - check screenshot for result")
    else:
        print("Could not find Place Bid button")

    pw.stop()


if __name__ == "__main__":
    main()
