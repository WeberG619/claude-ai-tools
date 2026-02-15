"""Complete all 3 Freelancer profile steps and then bid."""

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

    # Scroll to the profile completion section
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # === STEP 1: Select All Skills ===
    print("=== STEP 1: Skills ===")
    select_all = page.query_selector('button:has-text("Select All")')
    if select_all and select_all.is_visible():
        select_all.click()
        time.sleep(1)
        print("Clicked 'Select All'")

    # Click Next
    next_btn = page.query_selector('button:has-text("Next")')
    if next_btn and next_btn.is_visible():
        next_btn.click()
        time.sleep(3)
        print("Clicked 'Next'")
    else:
        print("No Next button found")

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_step2.png")

    # === STEP 2: Verify Email ===
    print("\n=== STEP 2: Verify Email ===")
    body = page.inner_text("body")
    idx = body.lower().find("verify")
    if idx >= 0:
        print(f"Verify section: {body[idx:idx+300]}")

    # Look for verify/resend button
    for sel in [
        'button:has-text("Verify")',
        'button:has-text("Send")',
        'button:has-text("Resend")',
        'a:has-text("Verify")',
        'a:has-text("verify")',
        'button:has-text("Next")',
        'button:has-text("Skip")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                text = el.inner_text().strip()[:60]
                print(f"Found: '{text}' via {sel}")
                # If it's Next or Skip, click it
                if "next" in text.lower() or "skip" in text.lower():
                    el.click()
                    time.sleep(3)
                    print("Clicked to proceed")
                    break
                # If it's verify/send, click it
                if "verify" in text.lower() or "send" in text.lower() or "resend" in text.lower():
                    el.click()
                    time.sleep(3)
                    print("Clicked verify/send")
                    break
        except:
            pass

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_step2b.png")

    # Check what's on screen now
    body2 = page.inner_text("body")
    # Find current step info
    for kw in ["step", "Step", "verify", "Verify", "email", "Email", "profile", "Profile", "complete", "Complete"]:
        idx = body2.lower().find(kw.lower())
        if idx >= 0:
            snippet = body2[max(0,idx-20):idx+200]
            if "complete your profile" in snippet.lower() or "step" in snippet.lower()[:30]:
                print(f"Context: ...{snippet[:150]}...")
                break

    # === STEP 3: Update Profile ===
    print("\n=== STEP 3: Update Profile ===")
    # Look for profile-related elements
    for sel in [
        'button:has-text("Update")',
        'button:has-text("Save")',
        'button:has-text("Next")',
        'button:has-text("Complete")',
        'button:has-text("Done")',
        'button:has-text("Finish")',
        'a:has-text("Update your profile")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                text = el.inner_text().strip()[:60]
                print(f"Found: '{text}' via {sel}")
        except:
            pass

    # Check all visible buttons now
    print("\n=== All visible buttons ===")
    buttons = page.query_selector_all("button")
    for btn in buttons:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:60]
                if text and len(text) > 1 and len(text) < 50:
                    print(f"  '{text}'")
        except:
            pass

    # Check if bid form appeared
    print("\n=== Checking for bid form ===")
    bid_inputs = page.query_selector_all('input[type="number"], input[placeholder*="bid"], input[placeholder*="amount"]')
    for inp in bid_inputs:
        try:
            if inp.is_visible():
                print(f"  Found bid input!")
        except:
            pass

    textareas = page.query_selector_all("textarea")
    for ta in textareas:
        try:
            if ta.is_visible():
                name = ta.get_attribute("name") or ""
                ph = ta.get_attribute("placeholder") or ""
                print(f"  Found textarea: name={name} ph={ph[:50]}")
        except:
            pass

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_step3.png")

    pw.stop()


if __name__ == "__main__":
    main()
