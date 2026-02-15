# -*- coding: utf-8 -*-
"""Check Upwork messages and proposals for any client responses."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# ============================================================
# PART 1: Check Upwork Messages
# ============================================================
print("=" * 60)
print("UPWORK MESSAGES")
print("=" * 60)

page.evaluate("window.location.href = 'https://www.upwork.com/ab/messages'")
time.sleep(6)
for i in range(20):
    try:
        if "Just a moment" in page.title():
            time.sleep(2)
        else:
            break
    except:
        time.sleep(1)
time.sleep(3)

print(f"URL: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

if "Just a moment" not in page.title():
    text = page.evaluate("document.body.innerText.substring(0, 3000)")
    print(f"\n{text[:2500]}")
else:
    print("Cloudflare blocked")

# ============================================================
# PART 2: Check Upwork Proposals for interview invitations
# ============================================================
print("\n" + "=" * 60)
print("UPWORK PROPOSALS - CHECKING FOR RESPONSES")
print("=" * 60)

page.evaluate("window.location.href = 'https://www.upwork.com/nx/proposals/'")
time.sleep(6)
for i in range(20):
    try:
        if "Just a moment" in page.title():
            time.sleep(2)
        else:
            break
    except:
        time.sleep(1)
time.sleep(3)

if "Just a moment" not in page.title():
    # Check for interview invitations
    invites = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Invitations to interview\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    print(f"Interview invitations: {invites}")

    # Check for offers
    offers = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Offers\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    print(f"Offers: {offers}")

    # Check active proposals (means client is engaging)
    active = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Active proposals\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    print(f"Active proposals: {active}")

    # Get all submitted proposals with any status changes
    text = page.evaluate("document.body.innerText.substring(0, 4000)")
    print(f"\nFull proposals page:\n{text[:3000]}")
else:
    print("Cloudflare blocked")

# ============================================================
# PART 3: Check Reddit Inbox
# ============================================================
print("\n" + "=" * 60)
print("REDDIT INBOX")
print("=" * 60)

page.evaluate("window.location.href = 'https://www.reddit.com/message/inbox/'")
time.sleep(6)
for i in range(15):
    try:
        if "Just a moment" not in page.title():
            break
        time.sleep(2)
    except:
        time.sleep(1)
time.sleep(3)

print(f"URL: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\n{text[:2500]}")

# Also check sent messages to confirm what we sent
print("\n" + "=" * 60)
print("REDDIT SENT MESSAGES")
print("=" * 60)

page.evaluate("window.location.href = 'https://www.reddit.com/message/sent/'")
time.sleep(5)
for i in range(10):
    try:
        if "Just a moment" not in page.title():
            break
        time.sleep(2)
    except:
        time.sleep(1)
time.sleep(2)

text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(f"\n{text[:2500]}")

pw.stop()
