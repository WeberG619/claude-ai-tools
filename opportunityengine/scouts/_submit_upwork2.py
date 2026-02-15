"""Submit proposal for Upwork Opp #144 - Step 2: Click Apply on job page."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"
JOB_URL = "https://www.upwork.com/jobs/Build-Dynamo-Script-Automate-the-updating-properties-Object-instance-Revit-2021_~022017338287448465721"

PROPOSAL = """Hi,

I'm interested in your project: Build a Dynamo Script To Automate the updating of properties of a Object instance in Revit 2021

This is right in my wheelhouse \u2014 I specialize in Revit automation and have built extensive tooling around the Revit API, including 700+ API methods for programmatic model manipulation. I work with Dynamo, Python (via IronPython/CPython nodes), and the Revit API daily.

For your specific need, here's my approach:

1. Clarify the scope \u2014 I'd want to understand which object types (families, walls, doors, etc.) and which parameters (instance, type, shared, project) you're targeting. Are you pulling updated values from an Excel sheet, a database, or another source?

2. Build the Dynamo graph \u2014 I'll create a clean, well-organized Dynamo script that selects the target elements (by category, filter, or selection set), maps the incoming data to the correct parameters, and writes the updates. I'll use Python Script nodes where Dynamo's built-in nodes fall short \u2014 especially for error handling and batch processing.

3. Handle edge cases \u2014 Parameter type mismatches (string vs. integer vs. ElementId), read-only parameters, and elements that may be in groups or design options. I'll build in validation so the script reports what was updated and flags anything it couldn't process.

4. Deliver with documentation \u2014 You'll get the .dyn file, any supporting Python scripts, and a short guide on how to run it and adapt it if your parameter list changes.

Why me over other bidders:

- I've built a full Revit MCP Bridge that exposes the entire Revit API programmatically \u2014 parameter reading/writing, element filtering, family management, the works. A Dynamo property updater is a focused subset of what I do every week.
- I'm comfortable with Revit 2021 specifically, including its IronPython 2.7 environment in Dynamo (no CPython3 in that version without Dynamo 2.13+).
- I deliver fast. For a well-scoped property update script, I can typically turn this around in 2-3 days.

Happy to jump on a quick call or chat to nail down the exact parameters and data source. Once I understand the specifics, I can give you a concrete delivery plan.

Best,
Weber Gouin"""

BID_AMOUNT = "65"


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]

    # Use existing pages - the job page should already be open
    pages = context.pages
    page = None
    for p in pages:
        if "upwork.com/jobs" in p.url:
            page = p
            print(f"Found job page tab: {p.title()[:60]}")
            break

    if not page:
        page = context.new_page()
        print("No job page found, navigating...")
        page.goto(JOB_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(8)

    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")

    # Wait for Cloudflare if needed
    for i in range(15):
        if "Just a moment" in page.title():
            print(f"  Cloudflare challenge... ({i+1}s)")
            time.sleep(2)
        else:
            break

    # Click "Apply now" button on the job page
    print("\n=== Clicking Apply now ===")
    apply_btn = page.query_selector('button:has-text("Apply now")')
    if not apply_btn:
        apply_btn = page.query_selector('a:has-text("Apply now")')
    if not apply_btn:
        # Try data-qa attribute
        apply_btn = page.query_selector('[data-qa="btn-submit-proposal"]')

    if apply_btn:
        print(f"  Found Apply button, clicking...")
        apply_btn.click()
        time.sleep(8)
        print(f"  URL after click: {page.url}")
        print(f"  Title: {page.title()}")
    else:
        print("  ERROR: No Apply button found")
        pw.stop()
        return False

    # Now we should be on the proposal form
    # Wait for form to load
    time.sleep(3)

    # Check if we're on the proposal page
    if "proposals" not in page.url.lower() and "apply" not in page.url.lower():
        print(f"  May not be on proposal page. URL: {page.url}")
        # Maybe it opened in a new way - check all pages
        for p in context.pages:
            if "proposal" in p.url.lower() or "apply" in p.url.lower():
                page = p
                print(f"  Switched to proposal tab: {p.url}")
                break

    print(f"\n=== Filling proposal form ===")
    print(f"Current URL: {page.url}")

    # Dump all form elements for debugging
    print("\nAll inputs:")
    inputs = page.query_selector_all("input:visible")
    for inp in inputs:
        name = inp.get_attribute("name") or ""
        itype = inp.get_attribute("type") or ""
        dqa = inp.get_attribute("data-qa") or ""
        al = inp.get_attribute("aria-label") or ""
        ph = inp.get_attribute("placeholder") or ""
        val = ""
        try:
            val = inp.input_value()[:30]
        except:
            pass
        print(f"  input: name={name}, type={itype}, dqa={dqa}, al={al[:30]}, ph={ph[:30]}, val={val}")

    print("\nAll textareas:")
    textareas = page.query_selector_all("textarea:visible")
    for ta in textareas:
        name = ta.get_attribute("name") or ""
        dqa = ta.get_attribute("data-qa") or ""
        ph = ta.get_attribute("placeholder") or ""
        print(f"  textarea: name={name}, dqa={dqa}, ph={ph[:50]}")

    # Try to fill cover letter
    cover_letter = None
    for sel in [
        'textarea[data-qa="cover-letter"]',
        'textarea[name="coverLetter"]',
        '#cover-letter',
        'textarea[placeholder*="cover letter" i]',
        'textarea[placeholder*="proposal" i]',
        'div[contenteditable="true"]',
        'textarea:visible',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                cover_letter = el
                print(f"\n  Found cover letter: {sel}")
                break
        except:
            continue

    if cover_letter:
        tag = cover_letter.evaluate("el => el.tagName")
        if tag == "DIV":
            # contenteditable div
            cover_letter.click()
            time.sleep(0.3)
            page.keyboard.press("Control+a")
            page.keyboard.type(PROPOSAL, delay=5)
        else:
            cover_letter.click()
            time.sleep(0.3)
            cover_letter.fill(PROPOSAL)
        time.sleep(0.5)
        print(f"  Filled cover letter ({len(PROPOSAL)} chars)")
    else:
        print("  WARNING: No cover letter field found")

    # Try to fill bid amount
    bid_input = None
    for sel in [
        'input[data-qa="bid-input"]',
        'input[data-qa="fixed-price-input"]',
        'input[name="amount"]',
        'input[name="rate"]',
        'input[aria-label*="bid" i]',
        'input[aria-label*="rate" i]',
        'input[aria-label*="amount" i]',
        'input[aria-label*="price" i]',
        'input[data-qa="proposed-bid"]',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                bid_input = el
                print(f"  Found bid input: {sel}")
                break
        except:
            continue

    if bid_input:
        bid_input.click()
        time.sleep(0.2)
        bid_input.fill("")
        time.sleep(0.1)
        bid_input.fill(BID_AMOUNT)
        time.sleep(0.3)
        print(f"  Set bid: ${BID_AMOUNT}")
    else:
        print("  WARNING: No bid input found")

    # Look for submit
    print("\n=== Looking for Submit button ===")
    submit_btn = None
    for sel in [
        'button[data-qa="submit-proposal-btn"]',
        'button[data-qa="btn-submit"]',
        'button:has-text("Submit")',
        'button:has-text("Send")',
        'button:has-text("Submit proposal")',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                submit_btn = el
                print(f"  Found: {sel} -> '{el.inner_text().strip()[:40]}'")
                break
        except:
            continue

    if not submit_btn:
        print("  All visible buttons:")
        for btn in page.query_selector_all("button:visible"):
            try:
                text = btn.inner_text().strip()[:50]
                if text:
                    print(f"    '{text}'")
            except:
                continue

    if submit_btn:
        disabled = submit_btn.get_attribute("disabled")
        aria_disabled = submit_btn.get_attribute("aria-disabled")
        if disabled is not None or aria_disabled == "true":
            print("  Submit button is DISABLED")
        else:
            print("  Clicking Submit...")
            submit_btn.click()
            time.sleep(6)
            print(f"  After submit: {page.url}")
            if "submitted" in page.url.lower() or "success" in page.title().lower():
                print("\n  SUCCESS!")
                pw.stop()
                return True
            print("  Check browser to confirm submission")

    pw.stop()
    return False


if __name__ == "__main__":
    result = main()
    print(f"\n=== RESULT: {'SUCCESS' if result else 'CHECK BROWSER'} ===")
