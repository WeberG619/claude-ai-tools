"""Click Send for 17 Connects button."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"URL: {page.url[:80]}")

# Close any modal first
try:
    page.keyboard.press("Escape")
    time.sleep(1)
except:
    pass

# Scroll to the button
page.evaluate("""(() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
        if (btn.textContent.includes('Send for')) {
            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
            return btn.textContent.trim();
        }
    }
    return 'not found';
})()""")
time.sleep(2)

# Click via JS to avoid any overlay issues
result = page.evaluate("""(() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
        if (btn.textContent.includes('Send for') && btn.offsetParent !== null) {
            btn.click();
            return 'clicked: ' + btn.textContent.trim();
        }
    }
    return 'button not found';
})()""")
print(f"Click result: {result}")

time.sleep(10)
print(f"After click URL: {page.url[:80]}")
print(f"After click title: {page.title()[:60]}")

if "success" in page.url.lower() or "apply" not in page.url.lower():
    print("SUCCESS!")
else:
    # Check for confirmation dialog or error
    text = page.evaluate("document.body.innerText.substring(0, 500)")
    print(f"\nPage text: {text[:300]}")

    # Check for modal
    modal = page.evaluate("""(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        const visible = Array.from(modals).filter(m => m.offsetParent !== null);
        return visible.map(m => m.textContent.trim().substring(0, 300));
    })()""")
    if modal:
        print(f"\nModal: {modal}")

    # Check for checkboxes
    cb = page.locator('input[type="checkbox"]:visible')
    if cb.count() > 0:
        print(f"\nCheckboxes found: {cb.count()}")
        for i in range(cb.count()):
            try:
                cb.nth(i).check()
                print(f"  Checked {i}")
            except:
                pass
        time.sleep(1)
        # Try send again
        page.evaluate("""(() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.includes('Send') || btn.textContent.includes('Submit') || btn.textContent.includes('Yes')) {
                    if (btn.offsetParent !== null) { btn.click(); return; }
                }
            }
        })()""")
        time.sleep(5)
        print(f"After resubmit: {page.url[:80]}")

pw.stop()
