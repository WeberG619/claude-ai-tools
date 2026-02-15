"""Submit proposal for '1-Hour Paid Validation Task - Python Playwright'."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"
JOB_URL = "https://www.upwork.com/jobs/Hour-Paid-Validation-Task-Python-Playwright_~022021747431853729876/"

PROPOSAL = """This is exactly what I do. I've spent the last few weeks building production Playwright automation systems \u2014 sequential browser sessions, DOM-based state detection, and clean session lifecycle management.

For your AT&T BYOD validation task, here's my approach:

1. **Single persistent session** \u2014 one browser context, one page, sequential processing. No parallel tabs, no context switching that could degrade state.

2. **DOM-based result detection** \u2014 I'll use explicit element selectors with `wait_for_selector()` and state assertions rather than arbitrary delays. Each step validates the expected DOM state before proceeding.

3. **Immediate abort on unexpected state** \u2014 strict state machine: if any step doesn't match the expected DOM condition (wrong page, missing element, unexpected content), the script raises immediately with a clear error describing what was expected vs. what was found.

4. **Session stability** \u2014 no page reloads between identifiers, careful cleanup of form state between iterations, and timeout guards on every navigation/selector wait.

I can deliver the working script, output from two consecutive runs, and a writeup of the session lifecycle within the hour.

Ready to start immediately.

Best,
Weber Gouin"""

BID = "30"  # $30/hr - competitive mid-range


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page = context.pages[0]

    print(f"Current: {page.title()[:50]}")

    # Navigate to job page
    print(f"\nNavigating to job...")
    page.evaluate(f"window.location.href = '{JOB_URL}'")
    time.sleep(4)
    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                break
        except:
            time.sleep(2)
    time.sleep(3)

    print(f"Title: {page.title()[:60]}")

    if "Just a moment" in page.title():
        print("Cloudflare blocked")
        pw.stop()
        return

    # Click Apply Now
    print("\nClicking Apply Now...")
    apply_btn = page.locator('#submit-proposal-button, button:has-text("Apply now")').first
    try:
        if apply_btn.is_disabled():
            print("Apply button is DISABLED!")
            # Check why
            reason = page.evaluate("document.body.innerText.includes('already submitted') ? 'Already applied' : 'Unknown reason'")
            print(f"Reason: {reason}")
            pw.stop()
            return
        apply_btn.click(timeout=10000)
        time.sleep(6)
    except Exception as e:
        print(f"Apply click failed: {e}")
        pw.stop()
        return

    print(f"URL: {page.url[:80]}")
    if "apply" not in page.url.lower():
        print("Not on apply page!")
        pw.stop()
        return

    # Wait for form to load
    time.sleep(3)
    print("On proposal form page")

    # Dump form state
    form_info = page.evaluate("""(() => {
        const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
        return Array.from(inputs)
            .filter(i => i.offsetParent !== null)
            .map(i => ({
                tag: i.tagName, type: i.type || '', name: i.name || '',
                id: i.id || '', ph: (i.placeholder || '').substring(0, 40),
                val: (i.value || '').substring(0, 20),
            }));
    })()""")
    print(f"\nForm fields ({len(form_info)}):")
    for f in form_info:
        print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, ph={f['ph']}, val={f['val']}")

    # Fill cover letter - find the textarea
    print("\n=== Filling cover letter ===")
    textarea = page.locator("textarea:visible").first
    try:
        textarea.fill(PROPOSAL)
        time.sleep(0.5)
        print(f"  Filled cover letter ({len(PROPOSAL)} chars)")
    except Exception as e:
        print(f"  Cover letter failed: {e}")
        pw.stop()
        return

    # Fill hourly rate
    print("\n=== Setting hourly rate ===")
    rate_filled = False
    for f in form_info:
        if f['type'] == 'text' and ('$' in f['ph'] or '$' in f['val'] or 'rate' in f['name'].lower()):
            selector = f"#{f['id']}" if f['id'] else f"input[name='{f['name']}']" if f['name'] else None
            if selector:
                try:
                    inp = page.locator(selector).first
                    inp.focus()
                    time.sleep(0.2)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(BID, delay=50)
                    page.keyboard.press("Tab")
                    time.sleep(1)
                    print(f"  Set rate: ${BID}/hr")
                    rate_filled = True
                    break
                except Exception as e:
                    print(f"  Rate fill failed: {e}")

    if not rate_filled:
        # Try finding any input with $ placeholder
        inputs = page.locator('input[type="text"]:visible')
        for i in range(inputs.count()):
            inp = inputs.nth(i)
            try:
                ph = inp.get_attribute("placeholder") or ""
                val = inp.input_value()
                if "$" in ph or "$" in val:
                    inp.focus()
                    time.sleep(0.1)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(BID, delay=50)
                    page.keyboard.press("Tab")
                    time.sleep(1)
                    print(f"  Set rate: ${BID}/hr (from $ input)")
                    rate_filled = True
                    break
            except:
                continue

    # Check for questions section
    print("\n=== Checking for screening questions ===")
    questions = page.evaluate("""(() => {
        const body = document.body.innerText;
        const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        const qLines = lines.filter(l => l.includes('?') && l.length > 20 && l.length < 200);
        return qLines.slice(0, 5);
    })()""")
    if questions:
        print(f"  Found {len(questions)} questions:")
        for q in questions:
            print(f"    {q[:100]}")

    # Dump page text to see full form
    page_text = page.evaluate("document.body.innerText.substring(0, 2000)")
    print(f"\n=== Page text ===\n{page_text[:1500]}")

    # Try to submit
    print("\n=== Submitting ===")
    time.sleep(2)
    submit = page.locator('button:has-text("Submit proposal")')
    try:
        submit.scroll_into_view_if_needed()
        time.sleep(1)
        submit.click(timeout=10000)
        time.sleep(8)
        print(f"After submit URL: {page.url[:80]}")
        print(f"After submit title: {page.title()[:60]}")

        if "success" in page.url.lower() or "apply" not in page.url.lower():
            print("SUCCESS!")
        else:
            # Check for confirmation dialog
            checkbox = page.locator('input[type="checkbox"][value="agree"]')
            if checkbox.count() > 0:
                page.evaluate("""(() => {
                    const cb = document.querySelector('input[type="checkbox"][value="agree"]');
                    if (cb) cb.click();
                })()""")
                time.sleep(2)
                # Click confirm
                confirm = page.locator('button:has-text("Submit"), button:has-text("Yes")')
                for i in range(confirm.count()):
                    try:
                        confirm.nth(i).click(timeout=3000)
                        break
                    except:
                        continue
                time.sleep(5)
                if "success" in page.url.lower():
                    print("SUCCESS after confirm!")
                else:
                    print(f"After confirm: {page.url[:80]}")

            # Check for validation errors
            errors = page.evaluate("""(() => {
                const errs = document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]');
                return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 3);
            })()""")
            if errors:
                print(f"Validation errors:")
                for e in errors:
                    print(f"  {e[:80]}")
    except Exception as e:
        if "success" in page.url.lower():
            print(f"SUCCESS (timeout but navigated)")
        else:
            print(f"Submit error: {e}")

    pw.stop()


if __name__ == "__main__":
    main()
