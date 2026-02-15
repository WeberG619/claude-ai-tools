"""Final fix and submit for Upwork proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = None
for p in context.pages:
    if "apply" in p.url.lower():
        page = p
        break

if not page:
    print("No proposal page found")
    pw.stop()
    exit(1)

print(f"On: {page.url}")

# Fix duration - change to "Less than 1 month"
print("\n=== Fixing duration ===")
# Click the dropdown (it should show current selection now)
dropdown = page.locator('[role="combobox"][data-test="dropdown-toggle"]').first
try:
    dropdown.click(timeout=5000)
    time.sleep(1)
    # Select "Less than 1 month"
    less_month = page.locator('[role="option"]:has-text("Less than 1 month")')
    if less_month.is_visible():
        less_month.click()
        print("  Selected: Less than 1 month")
        time.sleep(1)
except Exception as e:
    print(f"  Duration fix failed: {e}")

# Get ALL form error details
print("\n=== Detailed error analysis ===")
page.evaluate("window.scrollTo(0, 0)")
time.sleep(0.5)

# Get full form HTML structure for debugging
form_state = page.evaluate("""(() => {
    const errors = [];
    // Find all elements with error-related classes or attributes
    const errorEls = document.querySelectorAll(
        '[class*="error"], [class*="invalid"], [aria-invalid="true"], [data-test*="error"]'
    );
    for (const el of errorEls) {
        const text = el.textContent?.trim()?.substring(0, 100);
        if (text && text.length > 2 && text.length < 100) {
            const parent = el.closest('[class*="field"], [class*="section"], label');
            const parentText = parent?.textContent?.trim()?.substring(0, 50) || '';
            errors.push({text, context: parentText});
        }
    }
    return errors;
})()""")

seen = set()
for e in form_state:
    key = e['text'][:50]
    if key not in seen:
        seen.add(key)
        print(f"  Error: '{e['text']}'")
        if e['context'] != e['text']:
            print(f"    Near: '{e['context'][:60]}'")

# Check if cover letter is still filled
print("\n=== Verifying fields ===")
textarea = page.locator("textarea:visible").first
if textarea.is_visible():
    val = textarea.input_value()
    print(f"  Cover letter: {len(val)} chars - {'OK' if len(val) > 100 else 'EMPTY!'}")
    if len(val) < 10:
        print("  RE-FILLING cover letter...")
        # Need to re-read the proposal
        proposal = """Hi,

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
        textarea.fill(proposal)
        time.sleep(0.5)

# Check bid
bid_inputs = page.locator('input[type="text"]:visible')
for i in range(bid_inputs.count()):
    try:
        val = bid_inputs.nth(i).input_value()
        if "$" in val:
            print(f"  Bid field [{i}]: {val}")
    except:
        pass

# Check duration
duration_text = page.evaluate("""(() => {
    const dd = document.querySelector('[role="combobox"][data-test="dropdown-toggle"]');
    return dd ? dd.textContent.trim() : 'not found';
})()""")
print(f"  Duration: {duration_text}")

# Scroll to bottom to check for any remaining required fields
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(1)

# Check for checkboxes that need to be checked
checkboxes = page.locator('input[type="checkbox"]:visible')
for i in range(checkboxes.count()):
    cb = checkboxes.nth(i)
    checked = cb.is_checked()
    label = ""
    try:
        parent = cb.locator("xpath=..")
        label = parent.inner_text().strip()[:60]
    except:
        pass
    print(f"  Checkbox [{i}]: checked={checked}, label='{label}'")
    if not checked and label:
        print(f"    Checking it...")
        cb.check()
        time.sleep(0.5)

# Now try to submit
print("\n=== Final Submit ===")
time.sleep(1)

# Clear any stale error state by scrolling
page.evaluate("window.scrollTo(0, 0)")
time.sleep(0.5)
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(0.5)

submit = page.locator('button:has-text("Submit proposal")')
if submit.is_visible():
    print("  Clicking Submit proposal...")
    submit.click()
    time.sleep(10)
    print(f"  URL: {page.url}")
    print(f"  Title: {page.title()}")
    if "apply" not in page.url.lower():
        print("\n  SUCCESS - Proposal submitted!")
    else:
        # Check what errors remain
        remaining = page.evaluate("""(() => {
            const alerts = document.querySelectorAll('[role="alert"]');
            const fieldErrors = document.querySelectorAll('[class*="error"]:not([role="alert"])');
            const all = [...alerts, ...fieldErrors];
            return Array.from(new Set(
                all.map(a => a.textContent.trim().substring(0, 100)).filter(t => t.length > 3 && t.length < 100)
            ));
        })()""")
        print(f"  Remaining errors: {remaining}")

pw.stop()
