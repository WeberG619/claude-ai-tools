"""Complete Freelancer profile steps to unlock bidding."""

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

    # Scroll down to see the "Complete your profile" section
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_profile_steps.png")

    body = page.inner_text("body")
    # Find the complete your profile section
    idx = body.lower().find("complete your profile")
    if idx >= 0:
        print(f"Profile section:\n{body[idx:idx+500]}")

    # Step 1: "Update your skills" - click on it
    print("\n=== Looking for Step 1: Update skills ===")
    step1 = None
    for sel in [
        'a:has-text("Update your skills")',
        'button:has-text("Update your skills")',
        ':has-text("Update your skills")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                step1 = el
                print(f"Found: {sel}")
                break
        except:
            pass

    if step1:
        step1.click()
        time.sleep(3)
        print(f"After click: {page.url}")
        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_step1.png")

        body_after = page.inner_text("body")[:1500]
        print(f"Page text: {body_after[:800]}")

        # If we're on a skills page, add relevant skills
        # Look for skill input
        skill_input = None
        for sel in [
            'input[placeholder*="skill"]',
            'input[placeholder*="Skill"]',
            'input[placeholder*="search"]',
            'input[type="text"]',
        ]:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        placeholder = el.get_attribute("placeholder") or ""
                        print(f"  Found input: ph={placeholder}")
                        skill_input = el
                        break
                if skill_input:
                    break
            except:
                pass

        # Check for checkboxes (skills to select)
        print("\n=== Visible checkboxes ===")
        checkboxes = page.query_selector_all('input[type="checkbox"]')
        for i, cb in enumerate(checkboxes):
            try:
                if cb.is_visible():
                    checked = cb.is_checked()
                    label = cb.evaluate("e => { const l = e.closest('label') || e.parentElement; return l ? l.innerText.substring(0, 60) : ''; }")
                    print(f"  [{i}] checked={checked} label='{label}'")
            except:
                pass

        # Look for any buttons to proceed
        print("\n=== Buttons ===")
        buttons = page.query_selector_all("button")
        for btn in buttons:
            try:
                if btn.is_visible():
                    text = btn.inner_text().strip()[:60]
                    if text and len(text) > 1:
                        print(f"  '{text}'")
            except:
                pass
    else:
        print("Could not find 'Update your skills' link")

        # Try clicking step numbers
        for sel in ['text=1', '.step-1', '[data-step="1"]']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    time.sleep(2)
                    print(f"Clicked {sel}, now on: {page.url}")
                    break
            except:
                pass

    pw.stop()


if __name__ == "__main__":
    main()
