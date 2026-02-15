"""Navigate to job #143 and check Apply button state."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Navigate to job #143 via JS
job_url = "https://www.upwork.com/jobs/Revit-API-Engineer-Needed-for-Data-Extraction-Tool_~022017942842101097319"
print(f"Navigating to job #143...")
page.evaluate(f"window.location.href = '{job_url}'")

# Wait for navigation
time.sleep(3)
for i in range(30):
    try:
        title = page.title()
        url = page.url
        if "Just a moment" in title:
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        elif "022017942842101097319" in url or "Revit-API" in url:
            break
        else:
            time.sleep(2)
    except:
        time.sleep(2)

time.sleep(3)
print(f"\nTitle: {page.title()}")
print(f"URL: {page.url}")

if "Just a moment" in page.title():
    print("Cloudflare blocked. Check browser manually.")
    pw.stop()
    exit()

# Check Apply button
btn_info = page.evaluate("""(() => {
    const btn = document.querySelector('#submit-proposal-button, button[aria-label="Apply now"]');
    if (!btn) return {found: false};
    return {
        found: true,
        disabled: btn.disabled,
        text: btn.textContent.trim(),
    };
})()""")
print(f"\nApply button: {btn_info}")

# Check for "already submitted" or related text
status_text = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 200);
    const keywords = ['already submitted', 'proposal', 'connect', 'apply', 'send a proposal', 'available connects'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 15);
})()""")
print(f"\nRelevant text:")
for s in status_text:
    print(f"  {s[:120]}")

pw.stop()
