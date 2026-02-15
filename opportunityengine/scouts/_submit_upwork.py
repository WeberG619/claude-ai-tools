"""Submit proposal for Upwork Opp #144 - Revit Dynamo Script."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"
JOB_URL = "https://www.upwork.com/jobs/Build-Dynamo-Script-Automate-the-updating-properties-Object-instance-Revit-2021_~022017338287448465721"

PROPOSAL = """Hi,

I'm interested in your project: Build a Dynamo Script To Automate the updating of properties of a Object instance in Revit 2021

This is right in my wheelhouse — I specialize in Revit automation and have built extensive tooling around the Revit API, including 700+ API methods for programmatic model manipulation. I work with Dynamo, Python (via IronPython/CPython nodes), and the Revit API daily.

For your specific need, here's my approach:

1. Clarify the scope — I'd want to understand which object types (families, walls, doors, etc.) and which parameters (instance, type, shared, project) you're targeting. Are you pulling updated values from an Excel sheet, a database, or another source?

2. Build the Dynamo graph — I'll create a clean, well-organized Dynamo script that selects the target elements (by category, filter, or selection set), maps the incoming data to the correct parameters, and writes the updates. I'll use Python Script nodes where Dynamo's built-in nodes fall short — especially for error handling and batch processing.

3. Handle edge cases — Parameter type mismatches (string vs. integer vs. ElementId), read-only parameters, and elements that may be in groups or design options. I'll build in validation so the script reports what was updated and flags anything it couldn't process.

4. Deliver with documentation — You'll get the .dyn file, any supporting Python scripts, and a short guide on how to run it and adapt it if your parameter list changes.

Why me over other bidders:

- I've built a full Revit MCP Bridge that exposes the entire Revit API programmatically — parameter reading/writing, element filtering, family management, the works. A Dynamo property updater is a focused subset of what I do every week.
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
    page = context.new_page()

    # Step 1: Navigate to job page
    print("=== Step 1: Navigate to job page ===")
    page.goto(JOB_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    url = page.url
    title = page.title()
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Check if redirected to login
    if "login" in url.lower() or "signup" in url.lower():
        print("NOT LOGGED IN to Upwork - redirected to login page")
        print("Please log in to Upwork in the CDP Chrome browser, then re-run this script.")
        page.close()
        pw.stop()
        return False

    # Step 2: Find and click "Submit a Proposal" or "Apply Now" button
    print("\n=== Step 2: Looking for Apply/Proposal button ===")
    time.sleep(2)

    # Try multiple selectors for the apply button
    apply_btn = None
    selectors = [
        'a[data-qa="btn-submit-proposal"]',
        'button[data-qa="btn-submit-proposal"]',
        'a:has-text("Submit a Proposal")',
        'a:has-text("Apply Now")',
        'button:has-text("Submit a Proposal")',
        'button:has-text("Apply Now")',
        'a[href*="proposals/job"]',
    ]

    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                apply_btn = el
                print(f"  Found apply button: {sel}")
                break
        except:
            continue

    if not apply_btn:
        # List all links/buttons for debugging
        print("  Could not find apply button. Scanning page elements...")
        links = page.query_selector_all("a")
        for link in links:
            try:
                text = link.inner_text().strip()[:60]
                href = link.get_attribute("href") or ""
                if any(kw in text.lower() for kw in ["submit", "apply", "proposal", "bid"]):
                    print(f"  Link: '{text}' -> {href[:80]}")
            except:
                continue
        buttons = page.query_selector_all("button")
        for btn in buttons:
            try:
                text = btn.inner_text().strip()[:60]
                if any(kw in text.lower() for kw in ["submit", "apply", "proposal", "bid"]):
                    print(f"  Button: '{text}'")
            except:
                continue

        # Try clicking any link with "proposal" in href
        proposal_link = page.query_selector('a[href*="proposal"]')
        if proposal_link:
            apply_btn = proposal_link
            print(f"  Found proposal link by href")

    if not apply_btn:
        print("  ERROR: No apply button found on page")
        # Take note of page state
        h1 = page.query_selector("h1")
        if h1:
            print(f"  Page heading: {h1.inner_text()[:100]}")
        page.close()
        pw.stop()
        return False

    # Click the apply button
    print("  Clicking apply button...")
    apply_btn.click()
    time.sleep(5)

    print(f"  Now at: {page.url}")
    print(f"  Title: {page.title()}")

    # Step 3: Fill in the proposal form
    print("\n=== Step 3: Filling proposal form ===")

    # Look for cover letter textarea
    cover_letter = None
    cl_selectors = [
        'textarea[data-qa="cover-letter"]',
        'textarea[name="coverLetter"]',
        '#cover-letter',
        'textarea[placeholder*="cover letter"]',
        'textarea[placeholder*="Cover Letter"]',
        'textarea',
    ]

    for sel in cl_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                cover_letter = el
                print(f"  Found cover letter field: {sel}")
                break
        except:
            continue

    if cover_letter:
        cover_letter.click()
        time.sleep(0.5)
        cover_letter.fill(PROPOSAL)
        time.sleep(0.5)
        print(f"  Filled cover letter ({len(PROPOSAL)} chars)")
    else:
        print("  WARNING: Could not find cover letter field")
        # List all textareas
        tas = page.query_selector_all("textarea")
        for ta in tas:
            name = ta.get_attribute("name") or ""
            ph = ta.get_attribute("placeholder") or ""
            dqa = ta.get_attribute("data-qa") or ""
            print(f"    textarea: name={name}, placeholder={ph[:40]}, data-qa={dqa}")

    # Look for bid/rate input
    bid_input = None
    bid_selectors = [
        'input[data-qa="bid-input"]',
        'input[data-qa="fixed-price-input"]',
        'input[name="amount"]',
        'input[name="rate"]',
        'input[aria-label*="bid"]',
        'input[aria-label*="rate"]',
        'input[aria-label*="amount"]',
    ]

    for sel in bid_selectors:
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
        time.sleep(0.3)
        bid_input.fill("")
        time.sleep(0.2)
        bid_input.fill(BID_AMOUNT)
        time.sleep(0.3)
        print(f"  Set bid to ${BID_AMOUNT}")
    else:
        print("  WARNING: Could not find bid input")
        inputs = page.query_selector_all("input")
        for inp in inputs:
            name = inp.get_attribute("name") or ""
            itype = inp.get_attribute("type") or ""
            dqa = inp.get_attribute("data-qa") or ""
            al = inp.get_attribute("aria-label") or ""
            if itype not in ("hidden", "checkbox", "radio"):
                print(f"    input: name={name}, type={itype}, data-qa={dqa}, aria-label={al[:40]}")

    # Step 4: Submit
    print("\n=== Step 4: Looking for submit button ===")
    submit_btn = None
    submit_selectors = [
        'button[data-qa="submit-proposal-btn"]',
        'button[data-qa="btn-submit"]',
        'button:has-text("Submit")',
        'button:has-text("Send")',
    ]

    for sel in submit_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                submit_btn = el
                print(f"  Found submit button: {sel}")
                break
        except:
            continue

    if submit_btn:
        disabled = submit_btn.get_attribute("disabled")
        if disabled is not None:
            print("  WARNING: Submit button is disabled - form may have validation errors")
        else:
            print("  Clicking Submit...")
            submit_btn.click()
            time.sleep(5)
            print(f"  After submit URL: {page.url}")
            print(f"  After submit title: {page.title()}")

            # Check for success
            if "proposals" in page.url.lower() or "submitted" in page.url.lower():
                print("\n  SUCCESS - Proposal submitted on Upwork!")
                page.close()
                pw.stop()
                return True
            else:
                print(f"  UNCERTAIN - check the browser to confirm")
    else:
        print("  Could not find submit button")
        buttons = page.query_selector_all("button")
        for btn in buttons:
            try:
                text = btn.inner_text().strip()[:60]
                if text:
                    print(f"    button: '{text}'")
            except:
                continue

    page.close()
    pw.stop()
    return False


if __name__ == "__main__":
    result = main()
    print(f"\n=== FINAL RESULT: {'SUCCESS' if result else 'NEEDS ATTENTION'} ===")
