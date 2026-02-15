"""Check if Freelancer bid form is now available and submit."""

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

    # Reload the project page fresh
    page.goto(
        "https://www.freelancer.com/projects/seo/pSEO-Blog-Network-Automation/details",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    time.sleep(5)

    print(f"On: {page.url}")

    # Scroll down to see the bid form area
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    body = page.inner_text("body")
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_reload.png")

    # Check for "Complete your profile" or bid form
    if "complete your profile" in body.lower():
        idx = body.lower().find("complete your profile")
        section = body[idx:idx+500]
        print(f"Still showing profile steps:\n{section[:400]}")

        # Check which steps are done
        if "verify your email" in section.lower():
            print("\nEmail verification still needed")
            # Look for verify button
            for sel in [
                'button:has-text("Verify")',
                'button:has-text("Send")',
                'button:has-text("Resend")',
                'a:has-text("Verify")',
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        text = el.inner_text().strip()[:60]
                        print(f"  Found: '{text}'")
                except:
                    pass

        if "update your profile" in section.lower():
            print("\nProfile update still needed")
    else:
        print("No 'Complete your profile' section found - bid form may be available!")

    # Look for bid form elements
    print("\n=== Looking for bid form ===")

    # Check for bid amount input
    for sel in [
        'input[name="bid_amount"]',
        'input[data-bid-amount]',
        'input[placeholder*="bid"]',
        'input[placeholder*="amount"]',
        '#bidAmount',
        '.bid-amount input',
        'input[type="number"]',
        'input[fl-currency]',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"  BID INPUT FOUND: {sel}")
        except:
            pass

    # Check for proposal textarea
    for sel in [
        'textarea[name="description"]',
        'textarea[name="proposal"]',
        'textarea',
    ]:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    ph = el.get_attribute("placeholder") or ""
                    name = el.get_attribute("name") or ""
                    print(f"  TEXTAREA FOUND: name={name} ph={ph[:50]}")
        except:
            pass

    # Check for Place Bid button
    for sel in [
        'button:has-text("Place Bid")',
        'button:has-text("Submit")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"  SUBMIT FOUND: {sel}")
        except:
            pass

    # Also list all visible inputs
    print("\n=== All visible inputs ===")
    inputs = page.query_selector_all("input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_visible():
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                ph = inp.get_attribute("placeholder") or ""
                val = inp.input_value()[:30]
                cls = (inp.get_attribute("class") or "")[:50]
                print(f"  [{i}] name={name} type={itype} ph={ph[:30]} val={val} cls={cls}")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()
