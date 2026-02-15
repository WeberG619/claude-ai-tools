# -*- coding: utf-8 -*-
"""Check Upwork and Reddit for responses - use correct tab."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# List all pages and find the right one
print(f"Pages: {len(context.pages)}")
for i, p in enumerate(context.pages):
    try:
        print(f"  [{i}] {p.url[:60]} | {p.title()[:40]}")
    except:
        print(f"  [{i}] (error reading)")

# Use the actual new tab page (not the footer)
page = None
for p in context.pages:
    try:
        if 'newtab-footer' not in p.url:
            page = p
            break
    except:
        continue

if not page:
    # Use first page as fallback
    page = context.pages[0]

print(f"\nUsing page: {page.url[:60]}")

# Try navigating with goto first, fallback to evaluate
def safe_nav(url, wait=6):
    try:
        page.evaluate(f"window.location.href = '{url}'")
    except:
        pass
    time.sleep(wait)
    for i in range(20):
        try:
            title = page.title()
            if "Just a moment" in title:
                time.sleep(2)
            elif title and "newtab" not in page.url:
                return True
            else:
                time.sleep(1)
        except:
            time.sleep(1)
    return False

# ============================================================
# PART 1: Check Upwork Messages
# ============================================================
print("\n" + "=" * 60)
print("UPWORK MESSAGES")
print("=" * 60)

safe_nav("https://www.upwork.com/ab/messages")
print(f"URL: {page.url[:70]}")
print(f"Title: {page.title()[:60]}")

if "Just a moment" not in page.title() and "newtab" not in page.url:
    text = page.evaluate("document.body.innerText.substring(0, 3000)")
    print(text[:2500])
else:
    print("Navigation failed or Cloudflare blocked")

# ============================================================
# PART 2: Check Upwork Proposals
# ============================================================
print("\n" + "=" * 60)
print("UPWORK PROPOSALS")
print("=" * 60)

safe_nav("https://www.upwork.com/nx/proposals/")
print(f"URL: {page.url[:70]}")
print(f"Title: {page.title()[:60]}")

if "Just a moment" not in page.title() and "newtab" not in page.url:
    invites = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Invitations to interview\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    offers = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Offers\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    active = page.evaluate("""(() => {
        const text = document.body.innerText;
        const m = text.match(/Active proposals\\s*\\((\\d+)\\)/);
        return m ? m[1] : '0';
    })()""")
    print(f"Offers: {offers} | Interview invitations: {invites} | Active proposals: {active}")

    text = page.evaluate("document.body.innerText.substring(0, 4000)")
    print(text[:3000])
else:
    print("Navigation failed or Cloudflare blocked")

# ============================================================
# PART 3: Check Reddit Inbox
# ============================================================
print("\n" + "=" * 60)
print("REDDIT INBOX")
print("=" * 60)

safe_nav("https://www.reddit.com/message/inbox/")
print(f"URL: {page.url[:70]}")
print(f"Title: {page.title()[:60]}")

if "newtab" not in page.url:
    text = page.evaluate("document.body.innerText.substring(0, 3000)")
    print(text[:2500])
else:
    print("Navigation failed")

pw.stop()
