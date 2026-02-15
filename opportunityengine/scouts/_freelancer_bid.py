"""Navigate Freelancer bid form for Opp #186."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:60]}")
print(f"URL: {page.url}")

# Check current page structure
page_info = page.evaluate("""(() => {
    // Get all clickable elements with meaningful text
    const clickables = document.querySelectorAll('a, button, [role="tab"], [role="button"]');
    const result = [];
    for (const el of clickables) {
        if (el.offsetParent === null) continue;
        const text = el.textContent.trim();
        if (text.length > 1 && text.length < 60) {
            result.push({
                tag: el.tagName,
                text: text,
                href: (el.href || '').substring(0, 80),
                role: el.getAttribute('role') || '',
            });
        }
    }
    return result.slice(0, 30);
})()""")

print(f"\nClickable elements:")
for p in page_info:
    print(f"  [{p['tag']}] {p['text'][:50]} | href={p['href'][:50] if p['href'] else ''}")

# Look for a "Place Bid" or "Bid on this project" link/button
print("\n=== Trying to open bid form ===")

# Try clicking Proposals tab
try:
    proposals_tab = page.locator("text=Proposals").first
    if proposals_tab.is_visible(timeout=3000):
        print("  Clicking 'Proposals' tab...")
        proposals_tab.click()
        time.sleep(3)
        print(f"  URL now: {page.url[:80]}")
except Exception as e:
    print(f"  Proposals tab: {e}")

# Check for bid form after clicking
form_check = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    const visible = Array.from(inputs).filter(i => i.offsetParent !== null);
    return visible.map(i => ({
        tag: i.tagName,
        type: i.type || '',
        name: i.name || '',
        id: i.id || '',
        ph: (i.placeholder || '').substring(0, 50),
    }));
})()""")
print(f"\nVisible inputs after tab click ({len(form_check)}):")
for f in form_check:
    print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, id={f['id']}, ph={f['ph']}")

# Check for "Place Bid" button or link
bid_elements = page.evaluate("""(() => {
    const all = document.querySelectorAll('*');
    const matches = [];
    for (const el of all) {
        if (el.offsetParent === null) continue;
        const text = el.textContent.trim().toLowerCase();
        if ((text.includes('place bid') || text.includes('bid on') || text.includes('submit bid') ||
             text.includes('place a bid') || text === 'bid')
            && el.children.length < 5 && text.length < 50) {
            matches.push({
                tag: el.tagName,
                text: el.textContent.trim(),
                cls: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
                href: (el.href || '').substring(0, 60),
            });
        }
    }
    return matches.slice(0, 10);
})()""")
print(f"\nBid-related elements:")
for b in bid_elements:
    print(f"  [{b['tag']}] {b['text'][:50]} | cls={b['cls'][:40]}")

# Try the direct bid URL pattern on Freelancer
bid_url = page.url.replace('/details', '') + '/proposals'
print(f"\nTrying bid URL: {bid_url}")
page.evaluate(f"window.location.href = '{bid_url}'")
time.sleep(5)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Check again for form
form_check2 = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    const visible = Array.from(inputs).filter(i => i.offsetParent !== null);
    return visible.map(i => ({
        tag: i.tagName,
        type: i.type || '',
        name: i.name || '',
        id: i.id || '',
        ph: (i.placeholder || '').substring(0, 50),
    }));
})()""")
print(f"\nVisible inputs on proposals page ({len(form_check2)}):")
for f in form_check2:
    print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, id={f['id']}, ph={f['ph']}")

# Also check for any body text related to bidding
body_text = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 200);
    const keywords = ['bid', 'amount', 'period', 'deliver', 'proposal', 'describe'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 15);
})()""")
print(f"\nBid-related text:")
for t in body_text:
    print(f"  {t[:100]}")

pw.stop()
