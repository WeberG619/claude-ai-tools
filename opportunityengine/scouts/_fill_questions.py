"""Fill screening questions and submit Automation job proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

print(f"URL: {page.url[:80]}")

# The form has 3 visible textareas:
# [0] Cover letter (already filled)
# [1] Question 1: "Show me something you've built end-to-end..."
# [2] Question 2: "You inherit a Make/n8n workflow..."

Q1_ANSWER = """I built an autonomous agent system that runs 24/7 on my machine. It's a Python daemon that manages a task queue, connects to multiple APIs (Telegram, Google Calendar, voice TTS, browser automation via Playwright), and makes decisions using a rule-based engine with Claude API as the reasoning layer.

It handles: scheduled data scraping, automated notifications, browser-based form submissions, and pipeline management with a SQLite backend. I maintain it daily \u2014 it processes real tasks and I debug/extend it every time something breaks or a new integration is needed. It's not pretty code, but it runs reliably and I've iterated on it for months."""

Q2_ANSWER = """First I'd map what it actually does \u2014 trace every path, identify which nodes are critical vs. decorative. Then I'd prioritize by risk:

1. Add error handling to the nodes that touch external APIs first (these fail most often). Simple try/catch with Slack/email alerts so failures are visible, not silent.

2. Extract hardcoded values into a config node or environment variables. One place to update instead of hunting through 30 nodes.

3. Add logging at key checkpoints so when (not if) something breaks, I know where to look without re-reading the whole flow.

4. I would NOT refactor the entire thing at once. If it works, incremental improvement beats a rewrite. I'd only restructure if the flow has grown to the point where nobody can follow it."""

textareas = page.locator("textarea:visible")
ta_count = textareas.count()
print(f"Visible textareas: {ta_count}")

# Fill question 1 (index 1)
if ta_count >= 2:
    textareas.nth(1).fill(Q1_ANSWER)
    time.sleep(0.5)
    print(f"Filled Q1 ({len(Q1_ANSWER)} chars)")

# Fill question 2 (index 2)
if ta_count >= 3:
    textareas.nth(2).fill(Q2_ANSWER)
    time.sleep(0.5)
    print(f"Filled Q2 ({len(Q2_ANSWER)} chars)")

# Scroll to submit and click
time.sleep(1)
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(1)

# Click Send
print("\nSubmitting...")
page.evaluate("""(() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
        if (btn.textContent.includes('Send for') && btn.offsetParent !== null) {
            btn.click();
            return;
        }
    }
})()""")

time.sleep(10)
print(f"After submit URL: {page.url[:80]}")
print(f"After submit title: {page.title()[:60]}")

if "success" in page.url.lower() or "apply" not in page.url.lower():
    print("SUCCESS!")
else:
    # Check for errors
    errors = page.evaluate("""(() => {
        const errs = document.querySelectorAll('[class*="error"], [class*="invalid"]');
        return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 150)).filter(t => t.length > 3);
    })()""")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e[:100]}")

    # Check for confirm dialog
    cb = page.locator('input[type="checkbox"]:visible')
    if cb.count() > 0:
        print(f"Checkboxes: {cb.count()}")
        for i in range(cb.count()):
            try:
                cb.nth(i).check()
                print(f"  Checked {i}")
            except:
                pass
        time.sleep(1)
        page.evaluate("""(() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if ((btn.textContent.includes('Send') || btn.textContent.includes('Submit') || btn.textContent.includes('Yes'))
                    && btn.offsetParent !== null) {
                    btn.click();
                    return;
                }
            }
        })()""")
        time.sleep(5)
        print(f"After confirm: {page.url[:80]}")
        if "success" in page.url.lower():
            print("SUCCESS after confirm!")

pw.stop()
