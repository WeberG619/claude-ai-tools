# -*- coding: utf-8 -*-
"""Check Upwork messages and proposals for client responses."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = None
for p in context.pages:
    if 'newtab-footer' not in p.url:
        page = p
        break
if not page:
    page = context.pages[0]

def safe_nav(url, wait=6):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            elif page.title():
                return True
        except:
            time.sleep(1)
    return False

# ============================================================
# PART 1: Check Messages
# ============================================================
print("=" * 60)
print("UPWORK MESSAGES")
print("=" * 60)

safe_nav("https://www.upwork.com/ab/messages")
print(f"Title: {page.title()[:60]}")

if "login" not in page.url.lower() and "Just a moment" not in page.title():
    # Get message list
    time.sleep(3)
    messages = page.evaluate("""(() => {
        const text = document.body.innerText;
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        return lines.slice(0, 60).join('\\n');
    })()""")
    print(messages[:2000])
else:
    print(f"Not on messages page: {page.url[:80]}")

# ============================================================
# PART 2: Check Proposals
# ============================================================
print("\n" + "=" * 60)
print("UPWORK PROPOSALS")
print("=" * 60)

safe_nav("https://www.upwork.com/nx/proposals/")
print(f"Title: {page.title()[:60]}")

if "login" not in page.url.lower() and "Just a moment" not in page.title():
    time.sleep(3)

    # Check key counters
    info = page.evaluate("""(() => {
        const text = document.body.innerText;
        const offers = (text.match(/Offers\\s*\\((\\d+)\\)/) || [null, '0'])[1];
        const invites = (text.match(/Invitations to interview\\s*\\((\\d+)\\)/) || [null, '0'])[1];
        const active = (text.match(/Active proposals\\s*\\((\\d+)\\)/) || [null, '0'])[1];
        const submitted = (text.match(/Submitted proposals\\s*\\((\\d+)\\)/) || [null, '0'])[1];
        return {offers, invites, active, submitted};
    })()""")

    print(f"Offers: {info['offers']}")
    print(f"Interview Invitations: {info['invites']}")
    print(f"Active Proposals: {info['active']}")
    print(f"Submitted Proposals: {info['submitted']}")

    # If there are offers or invites, get details
    if int(info.get('offers', '0')) > 0 or int(info.get('invites', '0')) > 0 or int(info.get('active', '0')) > 0:
        print("\n*** RESPONSES DETECTED! ***")

    # Get full page for details
    text = page.evaluate("document.body.innerText.substring(0, 5000)")
    print(f"\nFull proposals:\n{text[:4000]}")
else:
    print(f"Not on proposals page: {page.url[:80]}")

# ============================================================
# PART 3: Check Connects balance
# ============================================================
print("\n" + "=" * 60)
print("CONNECTS BALANCE")
print("=" * 60)

# Navigate to a job to see connects
safe_nav("https://www.upwork.com/nx/find-work/best-matches")
time.sleep(3)

if "login" not in page.url.lower() and "Just a moment" not in page.title():
    connects = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/(\\d+)\\s*Available/i);
        return m ? m[0] : 'not found on page';
    })()""")
    print(f"Connects: {connects}")
else:
    print("Could not check connects")

pw.stop()
