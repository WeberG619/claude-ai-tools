"""Submit bid on Freelancer pSEO project."""

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

    # Navigate to the project page
    project_url = "https://www.freelancer.com/projects/seo/pSEO-Blog-Network-Automation/details"
    page.goto(project_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    print(f"On: {page.url}")
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_project.png")

    body = page.inner_text("body")[:1000]
    print(f"Page text: {body[:500]}")

    # Check if we now have bids available
    if "out of bids" in body.lower() or "0 bids left" in body.lower():
        print("Still showing 0 bids - may need to refresh")
        page.reload(wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)
        body = page.inner_text("body")[:1000]

    # Look for "Place Bid" button
    bid_btn = None
    for sel in [
        'button:has-text("Place Bid")',
        'a:has-text("Place Bid")',
        'button:has-text("Bid on this")',
        'a:has-text("Bid on this")',
        '[data-target="place-bid"]',
        '.PlaceBidBtn',
        'button:has-text("Place a Bid")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                bid_btn = el
                print(f"Found bid button: {sel}")
                break
        except:
            continue

    if not bid_btn:
        # Scroll down to find it
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        for sel in [
            'button:has-text("Place Bid")',
            'a:has-text("Place Bid")',
            'button:has-text("Bid on this")',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    bid_btn = el
                    print(f"Found bid button after scroll: {sel}")
                    break
            except:
                continue

    if bid_btn:
        print("Clicking bid button...")
        bid_btn.click()
        time.sleep(3)
        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bidform.png")
    else:
        print("No bid button found - checking if bid form is already visible")

    # Load proposal
    with open(r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_proposals.json", "r") as f:
        data = json.load(f)

    proposal_text = data["freelancer"]["text"]
    bid_amount = data["freelancer"]["bid"]

    # Clean proposal text for Freelancer (no markdown)
    clean = proposal_text.replace("**", "").replace("- ", "• ")

    print(f"\nBid amount: ${bid_amount}")
    print(f"Proposal ({len(clean)} chars): {clean[:150]}...")

    # Try to find and fill bid amount
    bid_filled = False
    for sel in [
        'input[name="bid_amount"]',
        'input[data-bid-amount]',
        'input[placeholder*="bid"]',
        'input[placeholder*="amount"]',
        'input[placeholder*="Enter"]',
        '#bidAmount',
        '.bid-amount input',
        'input[type="number"]',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                el.fill("")
                el.fill(str(int(bid_amount)))
                print(f"Filled bid amount: ${bid_amount} via {sel}")
                bid_filled = True
                break
        except:
            continue

    if not bid_filled:
        # List all visible inputs
        print("\n=== All visible inputs ===")
        inputs = page.query_selector_all("input")
        for i, inp in enumerate(inputs):
            try:
                if inp.is_visible():
                    name = inp.get_attribute("name") or ""
                    itype = inp.get_attribute("type") or ""
                    placeholder = inp.get_attribute("placeholder") or ""
                    val = inp.input_value()[:30]
                    cls = inp.get_attribute("class") or ""
                    print(f"  [{i}] name={name} type={itype} ph={placeholder[:40]} val={val} class={cls[:40]}")
            except:
                pass

    # Try to find and fill proposal textarea
    proposal_filled = False
    for sel in [
        'textarea[name="description"]',
        'textarea[name="proposal"]',
        'textarea[placeholder*="proposal"]',
        'textarea[placeholder*="describe"]',
        'textarea[placeholder*="Describe"]',
        '.proposal-text textarea',
        'textarea.bid-description',
        '#descriptionTextArea',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                el.fill("")
                el.fill(clean)
                print(f"Filled proposal via {sel}")
                proposal_filled = True
                break
        except:
            continue

    if not proposal_filled:
        # Try any visible textarea
        textareas = page.query_selector_all("textarea")
        for i, ta in enumerate(textareas):
            try:
                if ta.is_visible():
                    name = ta.get_attribute("name") or ""
                    placeholder = ta.get_attribute("placeholder") or ""
                    print(f"  Textarea [{i}]: name={name} ph={placeholder[:50]}")
                    ta.click()
                    ta.fill("")
                    ta.fill(clean)
                    print(f"  Filled textarea [{i}]")
                    proposal_filled = True
                    break
            except:
                pass

    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_filled.png")
    print(f"\nBid filled: {bid_filled}, Proposal filled: {proposal_filled}")

    # Find and click submit
    if bid_filled or proposal_filled:
        for sel in [
            'button[type="submit"]:has-text("Place Bid")',
            'button:has-text("Place Bid")',
            'button:has-text("Submit")',
            'button:has-text("Submit Bid")',
            'button[type="submit"]',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f"\nSubmit button: {sel}")
                    print(">>> CLICKING SUBMIT <<<")
                    btn.click()
                    time.sleep(5)
                    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_submitted.png")
                    print(f"Done! URL: {page.url}")
                    body = page.inner_text("body")[:500]
                    print(f"Result: {body[:300]}")
                    break
            except:
                continue

    pw.stop()


if __name__ == "__main__":
    main()
