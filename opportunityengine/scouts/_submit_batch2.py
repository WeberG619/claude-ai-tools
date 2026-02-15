"""Submit 2 Upwork proposals (#139, #143) and 1 Freelancer proposal (#186)."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"

PROPOSALS = {
    139: {
        "url": "https://www.upwork.com/jobs/Dynamo-Revit-Script-Review-and-Parameter-Value-Adjustment_~022019521479826811508",
        "bid": "35",
        "content": """Hi,

I specialize in exactly this \u2014 Dynamo scripts and the Revit API. I've built 700+ Revit API methods including parameter reading/writing, element filtering, and batch operations. Reviewing and adjusting Dynamo scripts is something I do weekly.

What I'll deliver:

1. Full review of your existing Dynamo script \u2014 I'll identify any nodes that are inefficient, deprecated, or error-prone. If you're using Python Script nodes, I'll review the code for proper error handling and Revit API best practices.

2. Parameter value adjustments \u2014 Whether it's instance parameters, type parameters, or shared parameters, I'll make sure the values are being read and written correctly. I'll handle edge cases like read-only parameters, parameter type mismatches, and elements in groups.

3. A short write-up of what I changed and why, so you can maintain it going forward.

Quick question: which version of Revit are you running? (Important because Dynamo's Python environment differs between versions \u2014 IronPython 2.7 in older versions vs CPython3 in newer ones.)

I can start today and turn this around fast.

Best,
Weber Gouin""",
    },
    143: {
        "url": "https://www.upwork.com/jobs/Revit-API-Engineer-Needed-for-Data-Extraction-Tool_~022017942842101097319",
        "bid": "10",
        "content": """Hi,

This is right in my wheelhouse. I've built a full Revit API bridge with 700+ methods \u2014 parameter extraction, element queries, family data, schedule data, you name it. Building a focused data extraction tool is a subset of what I already have running.

What I bring:
- Deep Revit API experience (C# and Python) \u2014 I know the difference between extracting from the model database vs. the Revit UI
- ETL pipeline experience \u2014 I can output to CSV, JSON, Excel, or pipe directly into a database
- Handles edge cases: linked models, workshared files, design options, parameter types (string, int, double, ElementId)

To scope this right, a few questions:
1. What data are you extracting? (Element parameters, quantities, schedules, geometry, spatial data?)
2. Output format preference? (Excel, CSV, JSON, database?)
3. Does this need to run as a Revit add-in, a Dynamo script, or a standalone tool using Revit's headless API?

I can start immediately and show you a working prototype within the first few hours so you can see the approach before we go deeper.

Best,
Weber Gouin""",
    },
}


def submit_upwork(page, opp_id, data):
    """Submit an Upwork proposal."""
    print(f"\n{'='*60}")
    print(f"=== Submitting Upwork Opp #{opp_id} ===")
    print(f"{'='*60}")

    # Navigate to job page
    page.goto(data["url"], wait_until="domcontentloaded", timeout=30000)

    # Wait for Cloudflare
    for i in range(20):
        if "Just a moment" in page.title():
            time.sleep(2)
        else:
            break
    time.sleep(3)

    print(f"  Title: {page.title()[:60]}")

    # Click Apply now
    apply_btn = page.locator('button:has-text("Apply now")').first
    try:
        apply_btn.click(timeout=10000)
        time.sleep(6)
    except Exception as e:
        print(f"  No Apply button: {e}")
        return False

    print(f"  On: {page.url[:60]}")

    if "apply" not in page.url.lower():
        print(f"  Not on apply page")
        return False

    # Switch to single payment mode
    page.evaluate("""(() => {
        const radios = document.querySelectorAll('input[type="radio"]');
        for (const r of radios) {
            if (r.value === 'default') r.click();
        }
    })()""")
    time.sleep(2)

    # Fill cover letter
    textarea = page.locator("textarea:visible").first
    try:
        textarea.fill(data["content"])
        time.sleep(0.5)
        print(f"  Filled cover letter ({len(data['content'])} chars)")
    except Exception as e:
        print(f"  Cover letter failed: {e}")
        return False

    # Fill bid amount
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
                page.keyboard.type(data["bid"], delay=50)
                page.keyboard.press("Tab")
                time.sleep(0.5)
                print(f"  Set bid: ${data['bid']}")
                break
        except:
            continue

    # Set duration - click the dropdown
    time.sleep(1)
    try:
        dd = page.locator('[role="combobox"][data-test="dropdown-toggle"]').first
        dd.click(timeout=5000)
        time.sleep(1)
        # Select "Less than 1 month"
        opt = page.locator('[role="option"]:has-text("Less than 1 month")')
        if opt.is_visible():
            opt.click()
            time.sleep(1)
            print(f"  Set duration: Less than 1 month")
    except Exception as e:
        print(f"  Duration dropdown: {e}")

    # Submit
    time.sleep(1)
    submit = page.locator('button:has-text("Submit proposal")')
    try:
        submit.click(timeout=10000)
        time.sleep(8)
        print(f"  After submit: {page.url[:60]}")
        if "apply" not in page.url.lower() or "success" in page.url.lower():
            print(f"  SUCCESS!")
            return True

        # May have confirmation dialog - check for checkbox
        checkbox = page.locator('input[type="checkbox"][value="agree"]')
        if checkbox.count() > 0:
            page.evaluate("""(() => {
                const cb = document.querySelector('input[type="checkbox"][value="agree"]');
                if (cb) cb.click();
            })()""")
            time.sleep(2)
            # Click submit again in dialog
            confirm_btns = page.locator('button:has-text("Submit"), button:has-text("Yes")')
            for i in range(confirm_btns.count()):
                try:
                    confirm_btns.nth(i).click(timeout=3000)
                    break
                except:
                    continue
            time.sleep(5)
            if "success" in page.url.lower() or "apply" not in page.url.lower():
                print(f"  SUCCESS after confirm!")
                return True

        print(f"  May need manual check")
        return False
    except Exception as e:
        # Check if navigated away (success)
        if "success" in page.url.lower():
            print(f"  SUCCESS (timeout but navigated)")
            return True
        print(f"  Submit error: {e}")
        return False


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page = context.new_page()

    results = {}

    # Submit Upwork #139
    ok = submit_upwork(page, 139, PROPOSALS[139])
    results[139] = ok
    time.sleep(3)

    # Submit Upwork #143
    ok = submit_upwork(page, 143, PROPOSALS[143])
    results[143] = ok

    page.close()
    pw.stop()

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    for k, v in results.items():
        print(f"  Opp #{k}: {'SUCCESS' if v else 'CHECK BROWSER'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
