"""Uncheck paid upgrades and submit the bid cleanly."""

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

    print(f"URL: {fl.url}")

    # UNCHECK all paid upgrade checkboxes
    unchecked = fl.evaluate("""() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        let count = 0;
        for (const cb of checkboxes) {
            if (cb.checked) {
                cb.click();
                count++;
            }
        }
        return count;
    }""")
    print(f"Unchecked {unchecked} checkboxes")
    time.sleep(1)

    # Verify state
    state = fl.evaluate("""() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        return Array.from(checkboxes).map(cb => ({id: cb.id, checked: cb.checked}));
    }""")
    for s in state:
        print(f"  Checkbox {s['id'][:15]}: checked={s['checked']}")

    # Scroll to and click the bottom "Place Bid" button
    fl.evaluate("window.scrollTo(0, document.body.scrollHeight - 300)")
    time.sleep(1)

    # Click Place Bid button at bottom
    place_bid = fl.query_selector('button.BtnPrimary:has-text("Place Bid")')
    if not place_bid:
        # Try finding the pink/red button at bottom
        buttons = fl.query_selector_all("button")
        for btn in buttons:
            try:
                text = btn.inner_text().strip()
                if text == "Place Bid":
                    rect = btn.evaluate("el => el.getBoundingClientRect()")
                    if rect["top"] > 1000:  # Bottom button
                        place_bid = btn
                        print(f"Found bottom Place Bid at y={rect['top']:.0f}")
                        break
            except:
                continue

    if not place_bid:
        # Use the "All Done" / "Write my bid" button instead
        fl.evaluate("window.scrollTo(0, 400)")
        time.sleep(0.5)
        place_bid = fl.query_selector('button:has-text("All Done")')
        if not place_bid:
            place_bid = fl.query_selector('button:has-text("Write my bid")')

    if place_bid:
        print(f"Clicking: '{place_bid.inner_text().strip()[:30]}'")
        place_bid.click()
        time.sleep(6)

        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_clean_result.png")

        new_url = fl.url
        print(f"URL: {new_url}")

        body = fl.inner_text("body")[:1500]
        if "failed" in body.lower()[:600]:
            print("STILL FAILING")
            # Get precise error
            errors = fl.evaluate("""() => {
                const alerts = document.querySelectorAll('[role="alert"], .alert, [class*="error-message"], [class*="ErrorMessage"]');
                return Array.from(alerts).map(e => e.textContent.trim().substring(0, 300));
            }""")
            for e in errors:
                print(f"  ERROR: {e}")

            # Check if it's an Angular form - get validation state
            val_state = fl.evaluate("""() => {
                const invalids = document.querySelectorAll('.ng-invalid, [aria-invalid="true"]');
                return Array.from(invalids).map(el => ({
                    tag: el.tagName,
                    id: el.id || '',
                    name: el.name || '',
                    class: el.className.substring(0, 100),
                    value: el.value || '',
                }));
            }""")
            if val_state:
                print("\nInvalid fields:")
                for v in val_state:
                    print(f"  {v['tag']} id='{v['id']}' name='{v['name']}' value='{v['value'][:30]}' class='{v['class'][:50]}'")
        else:
            print("RESULT:")
            print(body[:500])
    else:
        print("No submit button found")

    pw.stop()


if __name__ == "__main__":
    main()
