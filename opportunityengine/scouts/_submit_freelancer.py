"""Submit proposal on Freelancer.com for Opp #186 - Scrape NSW Transport Contact List."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:50]} | {page.url[:60]}")

# Navigate to the job page
job_url = "https://www.freelancer.com/projects/data-collection/scrape-nsw-transport-contact-list"
print(f"\nNavigating to job #186...")
page.evaluate(f"window.location.href = '{job_url}'")

time.sleep(3)
for i in range(20):
    try:
        title = page.title()
        if "Just a moment" in title:
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        elif "scrape" in title.lower() or "freelancer" in page.url:
            break
        else:
            time.sleep(2)
    except:
        time.sleep(2)

time.sleep(3)
print(f"Title: {page.title()}")
print(f"URL: {page.url}")

# Check if logged in now
login_state = page.evaluate("""(() => {
    const allEls = document.querySelectorAll('*');
    let hasAvatar = false;
    let hasLoginLink = false;
    for (const el of allEls) {
        const cls = (typeof el.className === 'string') ? el.className : '';
        if (cls.includes('avatar') || cls.includes('user-menu') || cls.includes('UserAvatar')) hasAvatar = true;
        if (el.tagName === 'A' && el.href && el.href.includes('/login') && el.textContent.trim() === 'Log In') hasLoginLink = true;
    }
    return {loggedIn: hasAvatar || !hasLoginLink, hasAvatar, hasLoginLink};
})()""")
print(f"Login state: {login_state}")

if login_state.get('hasLoginLink') and not login_state.get('hasAvatar'):
    print("NOT LOGGED IN - aborting")
    pw.stop()
    exit()

# Look for bid form elements
print("\n=== Checking bid form ===")
form_state = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    const visible = Array.from(inputs).filter(i => i.offsetParent !== null);
    return visible.map(i => ({
        tag: i.tagName,
        type: i.type || '',
        name: i.name || '',
        id: i.id || '',
        ph: (i.placeholder || '').substring(0, 50),
        val: (i.value || '').substring(0, 30),
        cls: (typeof i.className === 'string' ? i.className : '').substring(0, 60),
    }));
})()""")
print(f"Visible form fields ({len(form_state)}):")
for f in form_state:
    print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, id={f['id']}, ph={f['ph']}, val={f['val']}")

# Look for "Bid on this project" or "Place Bid" button
buttons = page.evaluate("""(() => {
    const btns = document.querySelectorAll('button, input[type="submit"]');
    return Array.from(btns)
        .filter(b => b.offsetParent !== null)
        .map(b => ({
            text: b.textContent.trim().substring(0, 60),
            disabled: b.disabled,
            type: b.type || '',
            cls: (typeof b.className === 'string' ? b.className : '').substring(0, 60),
        }))
        .filter(b => b.text.length > 1);
})()""")
print(f"\nVisible buttons:")
for b in buttons:
    d = " [DISABLED]" if b['disabled'] else ""
    print(f"  {b['text'][:50]}{d}")

# Try to fill in the bid amount
print("\n=== Filling bid form ===")

# Find the bid amount input (type=number with placeholder like "50")
bid_filled = False
for f in form_state:
    if f['type'] == 'number' or 'bid' in f['name'].lower() or 'bid' in f['id'].lower() or 'amount' in f['name'].lower():
        selector = None
        if f['id']:
            selector = f"#{f['id']}"
        elif f['name']:
            selector = f"input[name='{f['name']}']"
        else:
            selector = "input[type='number']"

        try:
            inp = page.locator(selector).first
            inp.click()
            time.sleep(0.3)
            inp.fill("40")
            time.sleep(0.5)
            print(f"  Filled bid amount: $40 (selector: {selector})")
            bid_filled = True
            break
        except Exception as e:
            print(f"  Failed to fill bid: {e}")

if not bid_filled:
    # Try generic number input
    try:
        num_input = page.locator("input[type='number']:visible").first
        num_input.click()
        time.sleep(0.3)
        num_input.fill("40")
        print(f"  Filled bid amount: $40 (generic number input)")
        bid_filled = True
    except Exception as e:
        print(f"  No number input found: {e}")

# Look for delivery/period input
period_filled = False
period_inputs = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input[type="number"]:not([type="hidden"])');
    return Array.from(inputs)
        .filter(i => i.offsetParent !== null)
        .map(i => ({
            id: i.id || '',
            name: i.name || '',
            ph: (i.placeholder || ''),
            val: i.value || '',
        }));
})()""")
print(f"\nNumber inputs: {period_inputs}")

# Fill delivery period if there's a second number input
if len(period_inputs) > 1:
    for p in period_inputs:
        ph = p['ph'].lower()
        if 'day' in ph or 'period' in ph or 'deliver' in ph or p['val'] == '':
            selector = f"#{p['id']}" if p['id'] else f"input[name='{p['name']}']"
            try:
                inp = page.locator(selector).first
                if inp.input_value() != "40":  # Don't overwrite bid amount
                    inp.fill("7")
                    print(f"  Set delivery period: 7 days")
                    period_filled = True
                    break
            except:
                pass

# Look for description/proposal textarea
print("\n=== Looking for proposal textarea ===")
textarea_filled = False
textareas = page.locator("textarea:visible")
ta_count = textareas.count()
print(f"  Found {ta_count} visible textareas")

PROPOSAL = """Hi,

I can build this scraper for you. 15,000 transport business contacts across NSW \u2014 I'll pull from public directories, Yellow Pages, ABN Lookup, and transport-specific registries to get you comprehensive coverage.

My approach:
- Python scraper targeting NSW transport directories, business registries, and industry listings
- Automated email extraction and validation (MX record checks to verify deliverability)
- Deduplication by email + business name
- Clean output in Excel/CSV: Business Name, Email, Phone, Address, Category, Source URL

I've built production scraping pipelines that handle rate limiting, retries, and anti-bot detection. I can deliver a first batch of 5,000 contacts within 48 hours so you can verify the quality before I complete the full 15,000.

Deliverables:
1. Clean Excel file with all contacts
2. The Python script itself (so you can re-run it later if needed)
3. Summary report: total found, verified, duplicates removed

Happy to discuss specifics \u2014 do you have preferred source directories, or should I cast a wide net?

Best,
Weber Gouin"""

for i in range(ta_count):
    ta = textareas.nth(i)
    try:
        ta.fill(PROPOSAL)
        print(f"  Filled textarea #{i} with proposal ({len(PROPOSAL)} chars)")
        textarea_filled = True
        break
    except Exception as e:
        print(f"  Textarea #{i} failed: {e}")

if not textarea_filled:
    # Try contenteditable divs
    ce = page.locator("[contenteditable='true']:visible")
    if ce.count() > 0:
        try:
            ce.first.click()
            time.sleep(0.3)
            page.keyboard.type(PROPOSAL, delay=5)
            print(f"  Filled contenteditable with proposal")
            textarea_filled = True
        except Exception as e:
            print(f"  Contenteditable failed: {e}")

print(f"\n=== Form status ===")
print(f"  Bid: {'FILLED' if bid_filled else 'MISSING'}")
print(f"  Period: {'FILLED' if period_filled else 'MISSING/NOT FOUND'}")
print(f"  Proposal: {'FILLED' if textarea_filled else 'MISSING'}")

# If form is filled, look for submit button
if bid_filled and textarea_filled:
    print("\n=== Submitting ===")
    time.sleep(1)

    # Find submit-like button
    submit_btn = None
    submit_selectors = [
        "button:visible:has-text('Place Bid')",
        "button:visible:has-text('Bid on this project')",
        "button:visible:has-text('Submit')",
    ]

    # Use Playwright locators for has-text
    for sel_text in ["Place Bid", "Bid on this project", "Submit Proposal", "Submit"]:
        try:
            loc = page.locator(f"button:visible").filter(has_text=sel_text).first
            if loc.is_visible(timeout=2000):
                submit_btn = loc
                print(f"  Found submit button: '{sel_text}'")
                break
        except:
            continue

    if not submit_btn:
        # Try input[type=submit]
        try:
            submit_btn = page.locator("input[type='submit']:visible").first
            if submit_btn.is_visible(timeout=2000):
                print(f"  Found submit input: {submit_btn.get_attribute('value')}")
        except:
            submit_btn = None

    if submit_btn:
        print("  Clicking submit...")
        submit_btn.click(timeout=10000)
        time.sleep(8)
        print(f"  After submit URL: {page.url[:80]}")
        print(f"  After submit title: {page.title()[:80]}")

        # Check for success indicators
        if "success" in page.url.lower() or "dashboard" in page.url.lower() or "bid" in page.title().lower():
            print("  SUCCESS!")
        else:
            # Check page text for confirmation
            body_text = page.evaluate("document.body.innerText.substring(0, 500)")
            print(f"  Page text: {body_text[:200]}")
    else:
        print("  No submit button found. Check browser manually.")
else:
    print("\nForm not fully filled. Check browser to complete manually.")

pw.stop()
