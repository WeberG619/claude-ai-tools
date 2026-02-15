"""Check current Upwork page state - no navigation needed."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

pages = context.pages
print(f"Open tabs: {len(pages)}")
for i, p in enumerate(pages):
    try:
        print(f"  [{i}] {p.title()[:60]} | {p.url[:80]}")
    except:
        print(f"  [{i}] (error reading)")

page = pages[0]
time.sleep(2)
print(f"\nCurrent page: {page.title()}")
print(f"URL: {page.url}")

# Check Apply button
btn_info = page.evaluate("""(() => {
    const btn = document.querySelector('#submit-proposal-button, button[aria-label="Apply now"]');
    if (!btn) {
        // List all buttons for debugging
        const buttons = Array.from(document.querySelectorAll('button'))
            .map(b => ({text: b.textContent.trim().substring(0,50), disabled: b.disabled, visible: b.offsetParent !== null}))
            .filter(b => b.text.length > 2 && b.visible);
        return {found: false, visibleButtons: buttons.slice(0, 15)};
    }
    return {
        found: true,
        disabled: btn.disabled,
        text: btn.textContent.trim(),
        title: btn.title || '',
        ariaDisabled: btn.getAttribute('aria-disabled') || '',
        tooltipText: btn.closest('[data-tooltip]') ? btn.closest('[data-tooltip]').getAttribute('data-tooltip') : '',
    };
})()""")
print(f"\nApply button info:")
if btn_info.get('found'):
    print(f"  Found: YES")
    print(f"  Disabled: {btn_info.get('disabled')}")
    print(f"  Text: {btn_info.get('text')}")
    print(f"  Title: {btn_info.get('title')}")
    print(f"  Aria-disabled: {btn_info.get('ariaDisabled')}")
    print(f"  Tooltip: {btn_info.get('tooltipText')}")
else:
    print(f"  Found: NO")
    print(f"  Visible buttons on page:")
    for b in btn_info.get('visibleButtons', []):
        print(f"    [{b['text'][:40]}] disabled={b['disabled']}")

# Scan for Connects-related text
connects_info = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 200);
    const keywords = ['connect', 'proposal', 'require', 'credit', 'available', 'upgrade',
                       'plan', 'membership', 'freelancer plus', 'buy', 'insufficient', 'limit',
                       'apply', 'submit', 'bid'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 25);
})()""")
print(f"\nConnects/proposal-related text on page:")
for c in connects_info:
    print(f"  {c[:120]}")

# Check for any modal or overlay
modal = page.evaluate("""(() => {
    const modals = document.querySelectorAll('[role="dialog"], .modal, [class*="modal"], [class*="overlay"]');
    return Array.from(modals).filter(m => m.offsetParent !== null).map(m => ({
        text: m.textContent.trim().substring(0, 300),
        role: m.getAttribute('role') || '',
        className: m.className.substring(0, 80),
    }));
})()""")
if modal:
    print(f"\nVisible modals/overlays:")
    for m in modal:
        print(f"  {m['text'][:150]}")

# Check for profile completion or verification banners
banners = page.evaluate("""(() => {
    const sels = '[role="alert"], [class*="banner"], [class*="notice"], [class*="warning"], [class*="info-box"], [class*="callout"]';
    return Array.from(document.querySelectorAll(sels))
        .filter(e => e.offsetParent !== null)
        .map(e => e.textContent.trim().substring(0, 200))
        .filter(t => t.length > 5);
})()""")
if banners:
    print(f"\nBanners/alerts:")
    for b in banners:
        print(f"  {b[:120]}")

pw.stop()
