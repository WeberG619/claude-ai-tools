"""Select rate-increase dropdowns and submit Upwork proposal."""

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
        print("No Upwork tab")
        pw.stop()
        return

    print(f"On: {page.url}")

    # Scroll to the rate-increase section
    page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
    time.sleep(1)

    # --- Fix Dropdown 1: Frequency ---
    error_dropdowns = page.query_selector_all('.has-error.air3-dropdown-toggle')
    if len(error_dropdowns) >= 1:
        freq_dd = error_dropdowns[0]
        print(f"Opening frequency dropdown: '{freq_dd.inner_text().strip()}'")
        freq_dd.click()
        time.sleep(1)

        # Select "Never"
        never_opt = page.get_by_text("Never", exact=True)
        if never_opt:
            # There may be multiple "Never" texts - find the one in the dropdown
            options = page.query_selector_all('[role="option"]')
            for opt in options:
                try:
                    if opt.is_visible() and "Never" in opt.inner_text():
                        opt.click()
                        print("Selected 'Never' for frequency")
                        time.sleep(1)
                        break
                except:
                    continue
        else:
            print("Could not find 'Never' option")
            page.keyboard.press("Escape")
            time.sleep(0.5)

    # --- Fix Dropdown 2: Percent ---
    # Re-query in case the DOM changed
    error_dropdowns = page.query_selector_all('.has-error.air3-dropdown-toggle')
    if len(error_dropdowns) >= 1:
        pct_dd = error_dropdowns[0]  # Should be the percent one now
        text = pct_dd.inner_text().strip()
        print(f"\nOpening next error dropdown: '{text}'")
        pct_dd.click()
        time.sleep(1)

        # Find and select first option (lowest percent)
        options = page.query_selector_all('[role="option"]')
        selected = False
        for opt in options:
            try:
                if opt.is_visible():
                    opt_text = opt.inner_text().strip()
                    if opt_text and "%" in opt_text:
                        opt.click()
                        print(f"Selected '{opt_text}' for percent")
                        selected = True
                        time.sleep(1)
                        break
            except:
                continue

        if not selected:
            # Try any visible option
            for opt in options:
                try:
                    if opt.is_visible():
                        opt_text = opt.inner_text().strip()
                        if opt_text:
                            opt.click()
                            print(f"Selected '{opt_text}' for percent")
                            time.sleep(1)
                            break
                except:
                    continue

    # Check if errors are resolved
    remaining_errors = page.query_selector_all('.has-error')
    visible_errors = [e for e in remaining_errors if e.is_visible()]
    print(f"\nRemaining visible errors: {len(visible_errors)}")
    for e in visible_errors:
        try:
            print(f"  Error: {e.inner_text().strip()[:60]}")
        except:
            pass

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_fixed.png")

    # Scroll to bottom and click Submit Proposal
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    submit_btn = None
    for sel in [
        'button:has-text("Submit Proposal")',
        'button[data-test="submit-proposal-btn"]',
        'button:has-text("Submit")',
    ]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                submit_btn = btn
                print(f"\nFound submit: {sel}")
                break
        except:
            pass

    if submit_btn:
        print(">>> CLICKING SUBMIT PROPOSAL <<<")
        submit_btn.click()
        time.sleep(8)

        # Check result
        new_url = page.url
        print(f"After submit URL: {new_url}")
        body = page.inner_text("body")[:500]
        print(f"Page text: {body[:300]}")
        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_result.png")

        # Check for success indicators
        if any(kw in body.lower() for kw in ["submitted", "success", "proposal sent", "thank you"]):
            print("\nSUCCESS - Proposal submitted!")
        elif "error" in body.lower() or "fix" in body.lower():
            print("\nStill has errors - check screenshot")
        else:
            print("\nSubmit clicked - check screenshot for result")
    else:
        print("Could not find Submit button")

    pw.stop()


if __name__ == "__main__":
    main()
