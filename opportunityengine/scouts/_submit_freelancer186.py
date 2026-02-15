"""Submit proposal on Freelancer.com for Opp #186 - Scrape NSW Transport Contact List."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"
JOB_URL = "https://www.freelancer.com/projects/data-collection/scrape-nsw-transport-contact-list"

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

BID_AMOUNT = "40"


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]

    # Use existing tab
    pages = context.pages
    page = pages[0] if pages else context.new_page()

    print(f"=== Submitting Freelancer Opp #186 ===")
    print(f"Navigating to: {JOB_URL}")

    page.goto(JOB_URL, wait_until="domcontentloaded", timeout=30000)

    # Wait for Cloudflare or loading
    for i in range(15):
        title = page.title()
        if "Just a moment" in title or "Checking" in title:
            print(f"  Waiting for Cloudflare... ({i+1})")
            time.sleep(2)
        else:
            break
    time.sleep(3)

    print(f"Title: {page.title()[:80]}")
    print(f"URL: {page.url[:80]}")

    # Check if we're logged in - look for login redirect or login button
    if "/login" in page.url.lower():
        print("NOT LOGGED IN - redirected to login page")
        print("Please log in to Freelancer.com first")
        pw.stop()
        return False

    # Check if the job page loaded
    if "freelancer.com/projects" not in page.url:
        print(f"Not on job page. Current URL: {page.url}")
        pw.stop()
        return False

    # Look for "Place a Bid" or "Bid on this project" button
    print("\nLooking for bid button...")

    # Freelancer uses different button text
    bid_selectors = [
        'button:has-text("Place a Bid")',
        'button:has-text("Bid on this Project")',
        'a:has-text("Place a Bid")',
        'a:has-text("Bid on this Project")',
        '[data-uitest-target="place-bid-button"]',
        '#place-bid-button',
    ]

    bid_btn = None
    for sel in bid_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                bid_btn = loc
                print(f"  Found bid button: {sel}")
                break
        except:
            continue

    if not bid_btn:
        # Maybe bid form is already on the page (Freelancer often shows it inline)
        print("  No bid button found. Checking if bid form is inline...")

        # Look for bid input field directly
        bid_input = page.locator('input[name="bidAmount"], input[id*="bid"], input[placeholder*="bid"], input[placeholder*="amount"]')
        if bid_input.count() > 0:
            print("  Found inline bid form!")
        else:
            # Dump page info for debugging
            page_info = page.evaluate("""(() => {
                const buttons = document.querySelectorAll('button, a[role="button"], .btn');
                const result = [];
                for (const b of buttons) {
                    const text = b.textContent.trim().substring(0, 60);
                    if (text.length > 2) result.push({tag: b.tagName, text, visible: b.offsetParent !== null});
                }
                return result.slice(0, 20);
            })()""")
            print(f"\n  Page buttons:")
            for b in page_info:
                print(f"    [{b['tag']}] {b['text'][:50]} (visible: {b['visible']})")

            # Also check for any error/restriction messages
            msgs = page.evaluate("""(() => {
                const els = document.querySelectorAll('[role="alert"], .alert, .notice, .message, .error');
                return Array.from(els).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 5);
            })()""")
            if msgs:
                print(f"\n  Alerts/notices:")
                for m in msgs:
                    print(f"    {m[:80]}")

            pw.stop()
            return False

    # Click bid button if found
    if bid_btn:
        try:
            bid_btn.click(timeout=5000)
            time.sleep(3)
            print(f"  Clicked bid button")
        except Exception as e:
            print(f"  Click failed: {e}")

    # Now look for the bid form
    print("\nLooking for bid form fields...")
    time.sleep(2)

    # Find all visible inputs and textareas
    form_info = page.evaluate("""(() => {
        const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
        const result = [];
        for (const inp of inputs) {
            if (inp.offsetParent === null) continue;  // skip hidden
            result.push({
                tag: inp.tagName,
                type: inp.type || '',
                name: inp.name || '',
                id: inp.id || '',
                placeholder: inp.placeholder || '',
                value: inp.value || '',
                label: inp.getAttribute('aria-label') || '',
            });
        }
        return result;
    })()""")

    print(f"  Visible form fields ({len(form_info)}):")
    for f in form_info:
        print(f"    [{f['tag']}] name={f['name']}, id={f['id']}, ph={f['placeholder'][:30]}, val={f['value'][:20]}")

    # Try to fill bid amount
    bid_filled = False
    for f in form_info:
        if any(kw in (f['name'] + f['id'] + f['placeholder'] + f['label']).lower() for kw in ['bid', 'amount', 'price', 'budget']):
            sel = f"#{f['id']}" if f['id'] else f"[name='{f['name']}']" if f['name'] else None
            if sel:
                try:
                    inp = page.locator(sel).first
                    inp.fill(BID_AMOUNT)
                    print(f"  Filled bid amount: ${BID_AMOUNT}")
                    bid_filled = True
                    break
                except Exception as e:
                    print(f"  Failed to fill bid: {e}")

    # Try to fill proposal text
    proposal_filled = False
    for f in form_info:
        if f['tag'] == 'TEXTAREA':
            sel = f"#{f['id']}" if f['id'] else f"textarea[name='{f['name']}']" if f['name'] else "textarea:visible"
            try:
                ta = page.locator(sel).first
                ta.fill(PROPOSAL)
                print(f"  Filled proposal ({len(PROPOSAL)} chars)")
                proposal_filled = True
                break
            except Exception as e:
                print(f"  Failed to fill proposal: {e}")

    if not bid_filled:
        print("  WARNING: Could not find bid amount field")
    if not proposal_filled:
        print("  WARNING: Could not find proposal textarea")

    # Look for submit button
    if bid_filled and proposal_filled:
        time.sleep(1)
        submit_selectors = [
            'button:has-text("Place Bid")',
            'button:has-text("Submit")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]

        for sel in submit_selectors:
            try:
                sub = page.locator(sel).first
                if sub.is_visible(timeout=2000):
                    print(f"\n  Found submit button: {sel}")
                    print(f"  Button text: {sub.text_content()[:50]}")

                    # Submit
                    sub.click(timeout=5000)
                    time.sleep(8)

                    print(f"  After submit URL: {page.url[:80]}")
                    print(f"  After submit title: {page.title()[:80]}")

                    # Check for success
                    if "success" in page.url.lower() or "bid" in page.title().lower():
                        print("  SUCCESS!")
                        pw.stop()
                        return True
                    break
            except:
                continue

        print("  May need manual verification")
    else:
        print("\n  Form not fully filled. Please check the browser.")

    pw.stop()
    return False


if __name__ == "__main__":
    ok = main()
    print(f"\nResult: {'SUCCESS' if ok else 'CHECK BROWSER'}")
