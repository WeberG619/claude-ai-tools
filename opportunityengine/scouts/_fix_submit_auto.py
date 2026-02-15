"""Fix and submit Automation job proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:50]}")
print(f"URL: {page.url[:80]}")

# Check if we're still on the apply page
if "apply" in page.url.lower():
    # Find all buttons
    buttons = page.evaluate("""(() => {
        const btns = document.querySelectorAll('button');
        return Array.from(btns)
            .map(b => ({
                text: b.textContent.trim().substring(0, 60),
                visible: b.offsetParent !== null,
                disabled: b.disabled,
                type: b.type || '',
            }))
            .filter(b => b.text.length > 2);
    })()""")
    print(f"\nAll buttons:")
    for b in buttons:
        vis = "VIS" if b['visible'] else "hid"
        dis = " [DIS]" if b['disabled'] else ""
        print(f"  [{vis}] {b['text'][:50]}{dis}")

    # Look for errors
    errors = page.evaluate("""(() => {
        const errs = document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]');
        return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 200)).filter(t => t.length > 3);
    })()""")
    if errors:
        print(f"\nErrors:")
        for e in errors:
            print(f"  {e[:120]}")

    # Scroll down to make submit visible
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    # Try different submit button selectors
    submit_selectors = [
        'button:has-text("Submit")',
        'button[type="submit"]',
        'button:has-text("Send")',
        'button:has-text("Place")',
    ]

    for sel in submit_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                text = btn.text_content().strip()
                print(f"\nFound submit: '{text}' via {sel}")
                btn.click(timeout=10000)
                time.sleep(8)
                print(f"After click: {page.url[:80]}")
                if "success" in page.url.lower() or "apply" not in page.url.lower():
                    print("SUCCESS!")
                    break
        except Exception as e:
            print(f"  {sel}: {e}")
            continue

    # If still on apply page, check for confirm dialog
    if "apply" in page.url.lower():
        checkbox = page.locator('input[type="checkbox"]')
        if checkbox.count() > 0:
            for i in range(checkbox.count()):
                try:
                    if checkbox.nth(i).is_visible(timeout=1000):
                        checkbox.nth(i).check()
                        print(f"  Checked checkbox {i}")
                except:
                    pass
            time.sleep(2)
            # Try submit again
            try:
                page.locator('button:has-text("Submit")').first.click(timeout=5000)
                time.sleep(5)
                print(f"After resubmit: {page.url[:80]}")
                if "success" in page.url.lower():
                    print("SUCCESS!")
            except:
                pass

    print(f"\nFinal URL: {page.url[:80]}")
    print(f"Final title: {page.title()[:60]}")
else:
    print("Not on apply page - may have already submitted")
    if "success" in page.url.lower() or "proposals" in page.url.lower():
        print("Looks like SUCCESS")

pw.stop()
