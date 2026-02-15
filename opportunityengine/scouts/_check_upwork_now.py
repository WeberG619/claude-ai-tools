# -*- coding: utf-8 -*-
"""Check Upwork proposals status - responses, invites, messages."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

def safe_nav(url, wait=6):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            elif page.title() and "login" not in page.url.lower():
                return True
            else:
                time.sleep(1)
        except:
            time.sleep(1)
    return False

# ============================================================
# Check Proposals Page
# ============================================================
print("=" * 60)
print("UPWORK PROPOSALS STATUS")
print("=" * 60)

safe_nav("https://www.upwork.com/nx/proposals/")
print(f"Title: {page.title()[:60]}")

if "login" in page.url.lower():
    print("NOT LOGGED IN - need to log in first")
    pw.stop()
    exit()

time.sleep(3)

# Get key counters
info = page.evaluate("""(() => {
    const text = document.body.innerText;
    const offers = (text.match(/Offers\\s*\\((\\d+)\\)/) || [null, '0'])[1];
    const invites = (text.match(/Invitations to interview\\s*\\((\\d+)\\)/) || [null, '0'])[1];
    const active = (text.match(/Active proposals\\s*\\((\\d+)\\)/) || [null, '0'])[1];
    const submitted = (text.match(/Submitted proposals\\s*\\((\\d+)\\)/) || [null, '0'])[1];
    return {offers, invites, active, submitted};
})()""")

print(f"\n  Offers: {info['offers']}")
print(f"  Interview Invitations: {info['invites']}")
print(f"  Active Proposals: {info['active']}")
print(f"  Submitted Proposals: {info['submitted']}")

if int(info.get('offers', '0')) > 0 or int(info.get('invites', '0')) > 0 or int(info.get('active', '0')) > 0:
    print("\n  *** RESPONSES DETECTED! ***")

# Get all submitted proposals with details
text = page.evaluate("document.body.innerText.substring(0, 6000)")
print(f"\n{text[:5000]}")

# ============================================================
# Check page 2 if exists
# ============================================================
if "Current page 1 of 2" in text:
    print("\n" + "=" * 60)
    print("PAGE 2")
    print("=" * 60)
    safe_nav("https://www.upwork.com/nx/proposals/?page=2")
    time.sleep(3)
    text2 = page.evaluate("document.body.innerText.substring(0, 4000)")
    print(text2[:3500])

# ============================================================
# Check Messages
# ============================================================
print("\n" + "=" * 60)
print("UPWORK MESSAGES")
print("=" * 60)

safe_nav("https://www.upwork.com/ab/messages")
time.sleep(4)
print(f"Title: {page.title()[:60]}")

msg_text = page.evaluate("document.body.innerText.substring(0, 3000)")
has_conversations = "Conversations will appear here" not in msg_text and "Welcome to Messages" not in msg_text
print(f"Has conversations: {has_conversations}")
if has_conversations:
    print(msg_text[:2500])
else:
    print("No messages yet - inbox empty")

# ============================================================
# Check Notifications
# ============================================================
print("\n" + "=" * 60)
print("UPWORK NOTIFICATIONS")
print("=" * 60)

safe_nav("https://www.upwork.com/nx/notifications")
time.sleep(4)
notif_text = page.evaluate("document.body.innerText.substring(0, 3000)")
print(notif_text[:2500])

pw.stop()
