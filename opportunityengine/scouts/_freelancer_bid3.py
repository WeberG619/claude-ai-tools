"""Navigate to Freelancer project Details tab and find bid form."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Navigate to project details
print("Navigating to project details...")
page.evaluate("window.location.href = 'https://www.freelancer.com/projects/data-collection/Scrape-NSW-Transport-Contact-List/details'")
time.sleep(5)

print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Click "Details" tab explicitly
try:
    details_tab = page.locator("fl-tab-item").filter(has_text="Details").first
    if details_tab.is_visible(timeout=3000):
        details_tab.click()
        time.sleep(2)
        print("Clicked Details tab")
except:
    print("Details tab click failed, trying button...")
    try:
        page.locator("button").filter(has_text="Details").first.click()
        time.sleep(2)
    except:
        pass

# Scroll down to look for bid section
print("\nScrolling through page...")
for scroll_pos in range(0, 5000, 500):
    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
    time.sleep(0.5)

# Now check ENTIRE page for inputs
all_inputs = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input, textarea, select');
    return Array.from(inputs).map(i => ({
        tag: i.tagName,
        type: i.type || '',
        name: i.name || '',
        id: i.id || '',
        ph: (i.placeholder || '').substring(0, 50),
        visible: i.offsetParent !== null,
        rect: i.getBoundingClientRect(),
    })).filter(i => i.type !== 'hidden');
})()""")
print(f"\nAll non-hidden inputs on page ({len(all_inputs)}):")
for inp in all_inputs:
    vis = "VISIBLE" if inp['visible'] else "hidden"
    print(f"  [{inp['tag']}] type={inp['type']}, name={inp['name']}, id={inp['id']}, ph={inp['ph']} ({vis})")

# Check for Angular/React forms that might load dynamically
print("\nChecking for dynamic bid form elements...")
dynamic = page.evaluate("""(() => {
    // Check for Angular/React component tags
    const bidComponents = document.querySelectorAll('[class*="bid"], [class*="Bid"], [id*="bid"], [data-*="bid"]');
    return Array.from(bidComponents).map(e => ({
        tag: e.tagName,
        cls: (typeof e.className === 'string' ? e.className : '').substring(0, 80),
        id: e.id || '',
        visible: e.offsetParent !== null,
        text: e.textContent.trim().substring(0, 100),
    })).slice(0, 15);
})()""")
print(f"Bid-related elements: {len(dynamic)}")
for d in dynamic:
    vis = "VISIBLE" if d['visible'] else "hidden"
    print(f"  [{d['tag']}] cls={d['cls'][:60]} | {d['text'][:50]} ({vis})")

# Check if there's a "Place Bid" or "Bid" link/button anywhere
print("\nSearching for bid buttons/links...")
bid_actions = page.evaluate("""(() => {
    const allEls = document.querySelectorAll('a, button, [role="button"]');
    return Array.from(allEls).filter(el => {
        const text = el.textContent.trim().toLowerCase();
        return (text.includes('bid') || text.includes('place') || text.includes('submit proposal'))
            && text.length < 50;
    }).map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        href: (el.href || '').substring(0, 80),
        visible: el.offsetParent !== null,
        cls: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
    })).slice(0, 10);
})()""")
for b in bid_actions:
    vis = "VISIBLE" if b['visible'] else "hidden"
    print(f"  [{b['tag']}] {b['text'][:40]} | href={b['href'][:50]} ({vis})")

# Check if there's an iframe containing the bid form
iframes = page.evaluate("""(() => {
    return Array.from(document.querySelectorAll('iframe')).map(f => ({
        src: f.src || '',
        id: f.id || '',
        name: f.name || '',
        visible: f.offsetParent !== null,
    }));
})()""")
if iframes:
    print(f"\nIframes: {len(iframes)}")
    for f in iframes:
        print(f"  src={f['src'][:60]}, id={f['id']}, visible={f['visible']}")

# Dump the first 1000 chars of visible page text for context
text = page.evaluate("document.body.innerText.substring(0, 2000)")
print(f"\n=== Page text (first 2000 chars) ===")
print(text[:2000])

pw.stop()
