"""Submit proposal for 'Junior Automation & Tools Engineer'."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"
JOB_URL = "https://www.upwork.com/jobs/Junior-Automation-Tools-Engineer_~022021814713857306179/"

PROPOSAL = """Hi,

Your stack is my daily workflow. I build automation systems with Python, n8n, and APIs \u2014 connecting CRMs, ad platforms, and databases into pipelines that replace manual work.

What I bring that's relevant:

**Automation & integrations:** I've built data pipelines between platforms using Python + REST APIs, including CRM syncs, automated reporting from Google Ads/LinkedIn data, and webhook-driven workflows. I use n8n for orchestration and Python for anything that needs custom logic.

**Tools & applications:** I've built internal dashboards, client portals, and ROI calculators. I work in Python and React, but I'm pragmatic \u2014 if no-code fits, I'll use it. If it needs custom code, I'll build it properly.

**Marketing ops context:** I understand the data model \u2014 campaigns, ad groups, conversions, attribution. I've worked with HubSpot and Google Ads APIs directly, so I know what the data looks like and where the integration pain points are.

I'm especially interested in this because I work best with solo founders who need a technical partner, not just a task executor. I'll suggest improvements proactively, not just build what's specced.

Happy to do a short trial task to show how I work.

Best,
Weber Gouin"""

BID = "25"  # $25/hr - competitive for "Junior" role


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page = context.pages[0]

    print(f"Current: {page.title()[:50]}")

    # Navigate to job
    print(f"Navigating to job...")
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

    # Click Apply
    print("\nClicking Apply Now...")
    apply_btn = page.locator('#submit-proposal-button, button:has-text("Apply now")').first
    try:
        if apply_btn.is_disabled():
            reason = page.evaluate("document.body.innerText.includes('already submitted') ? 'Already applied' : 'Unknown'")
            print(f"Apply DISABLED: {reason}")
            pw.stop()
            return
        apply_btn.click(timeout=10000)
        time.sleep(6)
    except Exception as e:
        print(f"Apply failed: {e}")
        pw.stop()
        return

    print(f"URL: {page.url[:80]}")
    if "apply" not in page.url.lower():
        print("Not on apply page!")
        pw.stop()
        return

    time.sleep(3)
    print("On proposal form")

    # Fill cover letter
    textarea = page.locator("textarea:visible").first
    try:
        textarea.fill(PROPOSAL)
        time.sleep(0.5)
        print(f"Filled cover letter ({len(PROPOSAL)} chars)")
    except Exception as e:
        print(f"Cover letter failed: {e}")
        pw.stop()
        return

    # Fill rate
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
                print(f"Set rate: ${BID}/hr")
                break
        except:
            continue

    # Handle rate-increase dropdowns
    time.sleep(1)
    dd = page.locator('[role="combobox"][data-test="dropdown-toggle"]:visible')
    dd_count = dd.count()
    print(f"Dropdowns: {dd_count}")

    for i in range(dd_count):
        try:
            dd.nth(i).click(timeout=5000)
            time.sleep(1)
            options = page.locator('[role="option"]:visible')
            opt_count = options.count()
            if opt_count > 0:
                # Pick reasonable defaults
                if i == 0:  # frequency
                    for j in range(opt_count):
                        if "6 month" in options.nth(j).text_content():
                            options.nth(j).click()
                            print(f"  Frequency: Every 6 months")
                            break
                    else:
                        if opt_count > 2:
                            options.nth(2).click()
                elif i == 1:  # percent
                    for j in range(opt_count):
                        if "10%" in options.nth(j).text_content():
                            options.nth(j).click()
                            print(f"  Increase: 10%")
                            break
                    else:
                        if opt_count > 1:
                            options.nth(1).click()
                time.sleep(1)
        except Exception as e:
            print(f"  Dropdown {i} error: {e}")

    # Submit
    print("\nSubmitting...")
    time.sleep(2)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    submit = page.locator('button:has-text("Submit proposal")')
    try:
        submit.click(timeout=10000)
        time.sleep(8)
        print(f"After submit: {page.url[:80]}")

        if "success" in page.url.lower() or "apply" not in page.url.lower():
            print("SUCCESS!")
        else:
            # Confirmation dialog?
            checkbox = page.locator('input[type="checkbox"][value="agree"]')
            if checkbox.count() > 0:
                page.evaluate("document.querySelector('input[type=\"checkbox\"][value=\"agree\"]')?.click()")
                time.sleep(2)
                confirm = page.locator('button:has-text("Submit"), button:has-text("Yes")')
                for i in range(confirm.count()):
                    try:
                        confirm.nth(i).click(timeout=3000)
                        break
                    except:
                        continue
                time.sleep(5)
                print(f"Final: {page.url[:80]}")
                if "success" in page.url.lower():
                    print("SUCCESS after confirm!")

            errors = page.evaluate("""(() => {
                const errs = document.querySelectorAll('[class*="error"], [class*="invalid"]');
                return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 3);
            })()""")
            if errors:
                print("Errors:")
                for e in errors:
                    print(f"  {e[:80]}")
    except Exception as e:
        if "success" in page.url.lower():
            print("SUCCESS (timeout)")
        else:
            print(f"Submit error: {e}")

    pw.stop()


if __name__ == "__main__":
    main()
