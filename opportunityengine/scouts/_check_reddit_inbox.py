"""Check Reddit inbox for replies to submitted proposals."""
import sys, time
from playwright.sync_api import sync_playwright

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    rd = None
    for p in context.pages:
        if "reddit.com" in p.url:
            rd = p
            break
    if not rd:
        rd = context.new_page()

    rd.goto("https://old.reddit.com/message/inbox/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    print(f"URL: {rd.url}")
    if "login" in rd.url.lower():
        print("NOT LOGGED IN to Reddit")
        pw.stop()
        return

    body = rd.inner_text("body")[:4000]
    safe_print("\n=== REDDIT INBOX ===")
    safe_print(body[:3000])

    rd.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_reddit_inbox.png")

    rd.goto("https://old.reddit.com/message/sent/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    sent = rd.inner_text("body")[:3000]
    safe_print("\n=== SENT MESSAGES ===")
    safe_print(sent[:2000])

    rd.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_reddit_sent.png")
    pw.stop()

if __name__ == "__main__":
    main()
