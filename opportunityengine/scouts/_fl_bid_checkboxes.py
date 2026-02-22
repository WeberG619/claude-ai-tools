"""Find and check the hidden checkboxes, then submit the bid."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        print("No Freelancer tab found")
        pw.stop()
        return

    # Scroll up to bid form area first
    fl.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)

    # Find the checkboxes and their surrounding context
    cb_info = fl.evaluate("""() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        const results = [];
        for (const cb of checkboxes) {
            // Get parent and sibling text for context
            let context = '';
            let el = cb.parentElement;
            for (let i = 0; i < 5 && el; i++) {
                context = el.textContent.trim().substring(0, 200);
                if (context.length > 10) break;
                el = el.parentElement;
            }
            results.push({
                id: cb.id,
                checked: cb.checked,
                context: context,
                rect: cb.getBoundingClientRect(),
            });
        }
        return results;
    }""")

    print("=== CHECKBOXES WITH CONTEXT ===")
    for cb in cb_info:
        print(f"\n  ID: {cb['id']}")
        print(f"  Checked: {cb['checked']}")
        print(f"  Position: top={cb['rect']['top']:.0f}")
        print(f"  Context: {cb['context'][:150]}")

    # Scroll to the checkbox area - they're likely in the "Optional Upgrades" section
    # Let me take a screenshot at the midpoint of the form
    fl.evaluate("window.scrollTo(0, 800)")
    time.sleep(1)
    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_mid1.png")

    fl.evaluate("window.scrollTo(0, 1200)")
    time.sleep(1)
    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_mid2.png")

    fl.evaluate("window.scrollTo(0, 1600)")
    time.sleep(1)
    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_mid3.png")

    # Check ALL checkboxes via JavaScript
    checked = fl.evaluate("""() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        let count = 0;
        for (const cb of checkboxes) {
            if (!cb.checked) {
                cb.click();
                count++;
            }
        }
        return count;
    }""")
    print(f"\nChecked {checked} checkboxes")
    time.sleep(1)

    # Now scroll back to top and click submit via the "All Done" / "Write my bid" button
    fl.evaluate("window.scrollTo(0, 400)")
    time.sleep(1)

    submit_btn = fl.query_selector('button:has-text("All Done")')
    if not submit_btn:
        submit_btn = fl.query_selector('button:has-text("Write my bid")')
    if not submit_btn:
        # Try the bottom Place Bid button
        fl.evaluate("window.scrollTo(0, document.body.scrollHeight - 400)")
        time.sleep(1)
        submit_btn = fl.query_selector('button:has-text("Place Bid")')

    if submit_btn:
        btn_text = submit_btn.inner_text()
        print(f"Clicking: '{btn_text}'")
        submit_btn.click()
        time.sleep(6)

        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_final.png")

        # Check if the URL changed or if we got a success message
        new_url = fl.url
        print(f"URL after submit: {new_url}")

        body = fl.inner_text("body")[:1500]
        if "failed" in body.lower()[:500]:
            print("STILL FAILING")
            # Look for specific error messages
            errors = fl.evaluate("""() => {
                const errorEls = document.querySelectorAll('[class*="error"], [class*="alert"], [role="alert"]');
                return Array.from(errorEls).map(e => e.textContent.trim().substring(0, 200)).filter(t => t.length > 0);
            }""")
            print("Errors found:")
            for e in errors:
                print(f"  - {e}")
        elif "congratulations" in body.lower() or "bid placed" in body.lower() or "success" in body.lower():
            print("BID SUBMITTED SUCCESSFULLY!")
        else:
            print(f"Page content:\n{body[:800]}")
    else:
        print("No submit button found")

    pw.stop()


if __name__ == "__main__":
    main()
