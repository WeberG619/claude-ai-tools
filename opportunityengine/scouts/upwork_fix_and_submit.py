"""Fix the rate-increase dropdowns and submit Upwork proposal."""

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

    # Scroll down to the Terms section where the dropdowns are
    page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
    time.sleep(1)

    # Find all dropdowns with errors
    print("=== Error dropdowns ===")
    error_dropdowns = page.query_selector_all('.has-error.air3-dropdown-toggle')
    for i, dd in enumerate(error_dropdowns):
        try:
            text = dd.inner_text().strip()[:60]
            print(f"  [{i}] '{text}'")
        except:
            pass

    # Find ALL dropdown toggles in the page
    print("\n=== All dropdown toggles ===")
    all_dropdowns = page.query_selector_all('.air3-dropdown-toggle, [data-test*="dropdown"], button[aria-haspopup]')
    for i, dd in enumerate(all_dropdowns):
        try:
            if dd.is_visible():
                text = dd.inner_text().strip()[:60]
                cls = dd.get_attribute("class") or ""
                testid = dd.get_attribute("data-test") or ""
                print(f"  [{i}] '{text}' testid={testid} class={cls[:60]}")
        except:
            pass

    # Click the frequency dropdown (first error dropdown)
    if len(error_dropdowns) >= 1:
        freq_dd = error_dropdowns[0]
        print(f"\nClicking frequency dropdown: '{freq_dd.inner_text().strip()}'")
        freq_dd.click()
        time.sleep(1)

        # Find options
        options = page.query_selector_all('[role="option"], .air3-dropdown-menu-item, li[role="option"]')
        print(f"Found {len(options)} options:")
        for i, opt in enumerate(options):
            try:
                if opt.is_visible():
                    text = opt.inner_text().strip()[:60]
                    print(f"  [{i}] '{text}'")
            except:
                pass

        # Also try menu items
        menu_items = page.query_selector_all('.air3-dropdown-menu li, .air3-dropdown-menu button, [role="menuitem"]')
        if not options:
            print(f"Menu items: {len(menu_items)}")
            for i, mi in enumerate(menu_items):
                try:
                    if mi.is_visible():
                        text = mi.inner_text().strip()[:60]
                        print(f"  [{i}] '{text}'")
                except:
                    pass

        # Try to find any visible list/dropdown content
        visible_items = page.query_selector_all('ul:not([style*="display: none"]) li')
        print(f"\nVisible list items: {len(visible_items)}")
        for i, li in enumerate(visible_items):
            try:
                if li.is_visible():
                    text = li.inner_text().strip()[:60]
                    if text:
                        print(f"  [{i}] '{text}'")
            except:
                pass

        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_freq_dd.png")

        # Try clicking a generic option or use keyboard
        # Press Escape to close if nothing worked
        page.keyboard.press("Escape")
        time.sleep(0.5)

    # Alternative approach: Try to find and interact with the boost/milestone section
    # Look for text around the rate increase
    print("\n=== Rate increase section text ===")
    try:
        section = page.evaluate("""() => {
            const body = document.body.innerText;
            const idx = body.indexOf('rate');
            if (idx >= 0) return body.substring(Math.max(0, idx - 200), idx + 500);
            return 'not found';
        }""")
        print(section[:500])
    except:
        pass

    # Maybe we can just remove the boost/rate-increase by finding a toggle or "no thanks"
    print("\n=== Looking for opt-out of rate increase ===")
    for text in ["No thanks", "Don't boost", "Skip", "None", "Remove"]:
        try:
            el = page.get_by_text(text, exact=False)
            if el and el.is_visible():
                print(f"Found '{text}' option")
                el.click()
                time.sleep(1)
                break
        except:
            pass

    # Check for toggle/checkbox to disable rate increase
    checkboxes = page.query_selector_all('input[type="checkbox"]')
    for cb in checkboxes:
        try:
            if cb.is_visible():
                label = cb.evaluate("e => e.parentElement ? e.parentElement.innerText.substring(0, 60) : ''")
                checked = cb.is_checked()
                print(f"  Checkbox: '{label}' checked={checked}")
        except:
            pass

    # Try selecting the dropdowns via JavaScript
    print("\n=== Trying JS approach on dropdowns ===")
    # Get the HTML around the error dropdowns
    for i, dd in enumerate(error_dropdowns):
        try:
            outer = dd.evaluate("e => e.outerHTML.substring(0, 300)")
            parent = dd.evaluate("e => e.parentElement ? e.parentElement.innerHTML.substring(0, 500) : ''")
            print(f"\nDropdown [{i}] HTML: {outer[:200]}")
            print(f"Parent HTML: {parent[:300]}")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()
