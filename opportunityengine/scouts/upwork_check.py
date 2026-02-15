"""Check Upwork tab state and try to proceed."""

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

    # Find ALL Upwork tabs
    print("\n=== All browser tabs ===")
    upwork_pages = []
    for i, p in enumerate(context.pages):
        url = p.url[:100]
        print(f"  [{i}] {url}")
        if "upwork.com" in p.url:
            upwork_pages.append(p)

    if not upwork_pages:
        print("\nNo Upwork tabs found")
        pw.stop()
        return

    # Use the most relevant Upwork tab
    page = upwork_pages[0]
    print(f"\nUsing Upwork tab: {page.url}")

    # Get current page state
    try:
        body_text = page.inner_text("body")[:800]
        print(f"\nPage text:\n{body_text[:500]}")
    except Exception as e:
        print(f"Could not get body text: {e}")

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_now.png")

    # Check what's on the page
    url = page.url
    print(f"\nCurrent URL: {url}")

    # List all visible buttons
    print("\n=== Visible buttons ===")
    buttons = page.query_selector_all("button")
    for i, btn in enumerate(buttons):
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:60]
                testid = btn.get_attribute("data-test") or ""
                print(f"  [{i}] '{text}' data-test={testid}")
        except:
            pass

    # List all visible links with "apply" or "proposal"
    print("\n=== Relevant links ===")
    links = page.query_selector_all("a")
    for link in links:
        try:
            if link.is_visible():
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()[:60]
                if any(kw in (href + text).lower() for kw in ["apply", "proposal", "submit", "bid"]):
                    print(f"  '{text}' -> {href[:80]}")
        except:
            pass

    # List all dropdowns/selects
    print("\n=== Selects/Dropdowns ===")
    selects = page.query_selector_all("select, [role='listbox'], [role='combobox']")
    for i, sel in enumerate(selects):
        try:
            if sel.is_visible():
                name = sel.get_attribute("name") or ""
                aria = sel.get_attribute("aria-label") or ""
                print(f"  [{i}] name={name} aria={aria}")
        except:
            pass

    # List visible textareas
    print("\n=== Visible textareas ===")
    textareas = page.query_selector_all("textarea")
    for i, ta in enumerate(textareas):
        try:
            if ta.is_visible():
                name = ta.get_attribute("name") or ""
                placeholder = ta.get_attribute("placeholder") or ""
                print(f"  [{i}] name={name} placeholder={placeholder[:50]}")
        except:
            pass

    # List visible inputs
    print("\n=== Visible inputs ===")
    inputs = page.query_selector_all("input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_visible():
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                val = inp.input_value()[:30]
                print(f"  [{i}] name={name} type={itype} placeholder={placeholder[:40]} val={val}")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()
