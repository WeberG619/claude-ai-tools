"""Fix Upwork proposal errors and resubmit."""

import json
import time
from playwright.sync_api import sync_playwright


def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=8000, full_page=True)
        print(f"Screenshot (full page): {path}")
    except:
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

    # Scroll down to see the full form
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    # Get the full page text to find errors
    body = page.inner_text("body")
    print(f"Full page text ({len(body)} chars):")
    # Print relevant sections
    for keyword in ["error", "Error", "required", "Required", "cover letter", "Cover Letter", "Cover letter"]:
        idx = body.lower().find(keyword.lower())
        if idx >= 0:
            snippet = body[max(0, idx-50):idx+150]
            print(f"  Found '{keyword}' at pos {idx}: ...{snippet}...")

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_full.png")

    # Scroll to middle to see the cover letter area
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_mid.png")

    # Check all visible textareas and their content
    print("\n=== All textareas ===")
    textareas = page.query_selector_all("textarea")
    for i, ta in enumerate(textareas):
        try:
            vis = ta.is_visible()
            val = ta.input_value()
            name = ta.get_attribute("name") or ""
            placeholder = ta.get_attribute("placeholder") or ""
            testid = ta.get_attribute("data-test") or ""
            print(f"  [{i}] vis={vis} name={name} ph={placeholder[:40]} testid={testid} len={len(val)} val_start={val[:80]}")
        except Exception as e:
            print(f"  [{i}] error: {e}")

    # Check all error messages on the page
    print("\n=== Error elements ===")
    errors = page.query_selector_all('[class*="error"], [class*="Error"], [data-test*="error"], .text-danger, [role="alert"]')
    for i, err in enumerate(errors):
        try:
            if err.is_visible():
                text = err.inner_text().strip()[:100]
                cls = err.get_attribute("class") or ""
                print(f"  [{i}] '{text}' class={cls[:60]}")
        except:
            pass

    # Check all visible inputs and their values
    print("\n=== All visible inputs ===")
    inputs = page.query_selector_all("input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_visible():
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                testid = inp.get_attribute("data-test") or ""
                val = inp.input_value()[:40]
                aria = inp.get_attribute("aria-label") or ""
                print(f"  [{i}] name={name} type={itype} ph={placeholder[:30]} testid={testid} aria={aria[:30]} val={val}")
        except:
            pass

    # Look for the cover letter section specifically
    print("\n=== Cover letter section ===")
    cl_section = page.query_selector_all('[class*="cover"], [data-test*="cover"], [aria-label*="cover"]')
    for el in cl_section:
        try:
            tag = el.evaluate("e => e.tagName")
            cls = el.get_attribute("class") or ""
            print(f"  <{tag}> class={cls[:80]}")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()
