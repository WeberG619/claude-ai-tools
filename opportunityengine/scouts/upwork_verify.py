"""Navigate Upwork verification form and get to proposal page."""

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

    # Find the Upwork verification tab
    page = None
    for p in context.pages:
        if "upwork.com" in p.url:
            page = p
            break

    if not page:
        print("No Upwork tab found")
        pw.stop()
        return

    print(f"On: {page.url}")

    # Check if we're on the verification page
    if "verification" in page.url:
        print("On verification page - checking dropdown options...")

        # Find the dropdown and see what options exist
        dropdown = page.query_selector('[role="combobox"], select, [aria-haspopup]')
        if dropdown:
            # Click to open the dropdown
            dropdown.click()
            time.sleep(1)
            safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_dropdown.png")

            # Find all options/listbox items
            options = page.query_selector_all('[role="option"], option, li[role="option"], [data-test*="option"]')
            print(f"Found {len(options)} dropdown options:")
            for i, opt in enumerate(options):
                try:
                    text = opt.inner_text().strip()
                    val = opt.get_attribute("value") or ""
                    print(f"  [{i}] '{text}' value={val}")
                except:
                    pass

            # Also check for any list items that appeared
            list_items = page.query_selector_all('ul li, [role="listbox"] > *')
            if list_items and not options:
                print(f"Found {len(list_items)} list items:")
                for i, li in enumerate(list_items):
                    try:
                        text = li.inner_text().strip()[:60]
                        if text:
                            print(f"  [{i}] '{text}'")
                    except:
                        pass
        else:
            print("No dropdown found, looking for other clickable elements...")
            # Maybe it's a custom dropdown - look for the "Select a type" text
            select_text = page.get_by_text("Select a type")
            if select_text:
                print("Found 'Select a type' element - clicking it")
                select_text.click()
                time.sleep(1)
                safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_dropdown.png")

                # Now look for visible options
                all_visible = page.query_selector_all('[role="option"], [role="menuitem"], li')
                for i, el in enumerate(all_visible):
                    try:
                        if el.is_visible():
                            text = el.inner_text().strip()[:80]
                            if text and text != "Select a type.":
                                print(f"  Option: '{text}'")
                    except:
                        pass

    # Also try: maybe we can close this dialog and go back to the job page
    print("\n--- Trying to close verification and go back ---")
    close_btn = page.query_selector('[data-test="close-button"]')
    if close_btn and close_btn.is_visible():
        print("Found close button")
        close_btn.click()
        time.sleep(3)
        print(f"After close: {page.url}")
        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_after_close.png")

        # Check page text
        body = page.inner_text("body")[:500]
        print(f"Page text: {body[:300]}")

    pw.stop()


if __name__ == "__main__":
    main()
