"""Try to open bid form on Freelancer - click Quote or scroll to bid form."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:60]}")
print(f"URL: {page.url}")

# First check: are we out of bids?
membership_text = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 300);
    const keywords = ['bid', 'membership', 'upgrade', 'remaining', 'quota', 'limit', 'free plan', 'out of'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 20);
})()""")
print(f"\nMembership/bid text:")
for m in membership_text:
    print(f"  {m[:150]}")

# Try clicking "Quote" button
print("\n=== Trying 'Quote' button ===")
try:
    quote_btn = page.locator("button").filter(has_text="Quote").first
    if quote_btn.is_visible(timeout=3000):
        print("  Clicking Quote...")
        quote_btn.click()
        time.sleep(3)
        print(f"  URL: {page.url[:80]}")
        print(f"  Title: {page.title()[:60]}")

        # Check for new form fields
        new_fields = page.evaluate("""(() => {
            const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
            return Array.from(inputs)
                .filter(i => i.offsetParent !== null)
                .map(i => ({
                    tag: i.tagName, type: i.type || '', name: i.name || '',
                    id: i.id || '', ph: (i.placeholder || '').substring(0, 50),
                }));
        })()""")
        print(f"  Form fields: {len(new_fields)}")
        for f in new_fields:
            print(f"    [{f['tag']}] type={f['type']}, name={f['name']}, ph={f['ph']}")

        # Check for modal
        modal = page.evaluate("""(() => {
            const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"]');
            return Array.from(modals).filter(m => m.offsetParent !== null).map(m => ({
                text: m.textContent.trim().substring(0, 500),
                cls: (typeof m.className === 'string' ? m.className : '').substring(0, 60),
            }));
        })()""")
        if modal:
            print(f"\n  Modal/dialog found:")
            for m in modal:
                print(f"    {m['text'][:200]}")
except Exception as e:
    print(f"  Quote button error: {e}")

# Try scrolling down to find bid section
print("\n=== Scrolling to find bid section ===")
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(2)

# Check for bid form at bottom of page
bottom_elements = page.evaluate("""(() => {
    const rect = {top: window.scrollY, bottom: window.scrollY + window.innerHeight};
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    return Array.from(inputs)
        .filter(i => {
            const r = i.getBoundingClientRect();
            return r.top >= 0 && r.bottom <= window.innerHeight;
        })
        .map(i => ({
            tag: i.tagName, type: i.type || '', name: i.name || '',
            id: i.id || '', ph: (i.placeholder || '').substring(0, 50),
        }));
})()""")
print(f"Inputs in viewport: {len(bottom_elements)}")
for f in bottom_elements:
    print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, ph={f['ph']}")

# Check the full page for ANY textarea or bid-related input (including hidden ones that may appear)
all_forms = page.evaluate("""(() => {
    const textareas = document.querySelectorAll('textarea');
    const numberInputs = document.querySelectorAll('input[type="number"]');
    return {
        textareas: Array.from(textareas).map(t => ({
            name: t.name || '', id: t.id || '', visible: t.offsetParent !== null,
            ph: (t.placeholder || '').substring(0, 50),
        })),
        numberInputs: Array.from(numberInputs).map(i => ({
            name: i.name || '', id: i.id || '', visible: i.offsetParent !== null,
            ph: (i.placeholder || '').substring(0, 50),
        })),
    };
})()""")
print(f"\nAll textareas (including hidden): {len(all_forms['textareas'])}")
for t in all_forms['textareas']:
    print(f"  name={t['name']}, id={t['id']}, visible={t['visible']}, ph={t['ph']}")
print(f"All number inputs (including hidden): {len(all_forms['numberInputs'])}")
for n in all_forms['numberInputs']:
    print(f"  name={n['name']}, id={n['id']}, visible={n['visible']}, ph={n['ph']}")

# Try the direct place-bid URL
print("\n=== Trying direct bid URL ===")
bid_url = "https://www.freelancer.com/projects/data-collection/Scrape-NSW-Transport-Contact-List/proposals/bid"
page.evaluate(f"window.location.href = '{bid_url}'")
time.sleep(5)
print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Check what's there now
final_fields = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    return Array.from(inputs)
        .filter(i => i.offsetParent !== null)
        .map(i => ({
            tag: i.tagName, type: i.type || '', name: i.name || '',
            id: i.id || '', ph: (i.placeholder || '').substring(0, 50),
        }));
})()""")
print(f"Visible fields: {len(final_fields)}")
for f in final_fields:
    print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, ph={f['ph']}")

pw.stop()
