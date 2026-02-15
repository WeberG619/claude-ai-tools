"""Debug current state of Automation proposal page."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:50]}")

# Check for modal/dialog
modals = page.evaluate("""(() => {
    const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"], [class*="overlay"]');
    return Array.from(modals).filter(m => m.offsetParent !== null).map(m => ({
        text: m.textContent.trim().substring(0, 500),
        cls: (typeof m.className === 'string' ? m.className : '').substring(0, 80),
    }));
})()""")

if modals:
    print(f"\nModals/dialogs ({len(modals)}):")
    for m in modals:
        print(f"  {m['text'][:300]}")
else:
    print("\nNo modals")

# Dump page text
text = page.evaluate("document.body.innerText")
# Find the bottom portion (where errors/confirmations would be)
print(f"\nPage text (last 1000 chars):")
print(text[-1000:])

# Check all visible interactive elements
interactive = page.evaluate("""(() => {
    const els = document.querySelectorAll('button:not([disabled]), input[type="checkbox"], input[type="radio"], a[href]');
    return Array.from(els)
        .filter(e => e.offsetParent !== null)
        .map(e => ({
            tag: e.tagName,
            type: e.type || '',
            text: e.textContent.trim().substring(0, 60),
            checked: e.checked || false,
            href: (e.href || '').substring(0, 60),
        }))
        .filter(e => e.text.length > 1 || e.href)
        .slice(0, 30);
})()""")
print(f"\nVisible interactive elements:")
for e in interactive:
    chk = " [CHECKED]" if e['checked'] else ""
    print(f"  [{e['tag']}] {e['text'][:50]}{chk}")

pw.stop()
