"""Check Freelancer membership and bid balance."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Close any modal first
try:
    page.keyboard.press("Escape")
    time.sleep(1)
except:
    pass

# Navigate to membership/settings page
print("Checking membership status...")
page.evaluate("window.location.href = 'https://www.freelancer.com/membership'")
time.sleep(5)

print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Get membership info
membership = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 2 && l.length < 200);
    const keywords = ['bid', 'plan', 'membership', 'free', 'remaining', 'used', 'skill', 'connect',
                       'upgrade', 'monthly', 'basic', 'plus', 'professional', 'premier', 'current'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 30);
})()""")
print(f"\nMembership text:")
for m in membership:
    print(f"  {m[:120]}")

# Check dashboard for bid info
print("\n=== Checking dashboard ===")
page.evaluate("window.location.href = 'https://www.freelancer.com/dashboard'")
time.sleep(5)
print(f"URL: {page.url}")

dash_info = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 2 && l.length < 200);
    const keywords = ['bid', 'remaining', 'available', 'credit', 'balance', 'membership', 'plan'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 15);
})()""")
print(f"\nDashboard bid info:")
for d in dash_info:
    print(f"  {d[:120]}")

# Also check the user's profile/settings
print("\n=== Checking profile completeness ===")
page.evaluate("window.location.href = 'https://www.freelancer.com/u/weberg5'")
time.sleep(5)
print(f"URL: {page.url}")

profile_info = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 2 && l.length < 200);
    const keywords = ['complete', 'verify', 'skill', 'bid', 'portfolio', 'payment', 'email'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 15);
})()""")
print(f"\nProfile info:")
for p in profile_info:
    print(f"  {p[:120]}")

pw.stop()
