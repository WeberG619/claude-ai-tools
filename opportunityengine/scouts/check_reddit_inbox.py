"""Check Reddit inbox for new messages via Playwright CDP."""

import json
import time
import sys
from playwright.sync_api import sync_playwright


def main():
    results = []
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.new_page()

        page.goto("https://www.reddit.com/message/inbox/", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        # Check if logged in
        if "login" in page.url.lower():
            print(json.dumps([]))
            pw.stop()
            return

        # Get message elements
        messages = page.query_selector_all('[data-testid="message"], .message, .thing.message')
        for msg in messages[:10]:
            try:
                author = ""
                subject = ""
                body = ""
                is_new = False

                # Try to extract author
                author_el = msg.query_selector('a[href*="/user/"]')
                if author_el:
                    author = author_el.inner_text().strip()

                # Try to extract subject
                subject_el = msg.query_selector('.subject, [data-testid="subject"]')
                if subject_el:
                    subject = subject_el.inner_text().strip()

                # Try to extract body
                body_el = msg.query_selector('.md, .message-body, [data-testid="message-body"]')
                if body_el:
                    body = body_el.inner_text().strip()[:300]

                # Check if unread
                cls = msg.get_attribute("class") or ""
                is_new = "unread" in cls or "new" in cls

                if author or subject:
                    results.append({
                        "author": author,
                        "subject": subject,
                        "body": body,
                        "is_new": is_new,
                        "url": "https://www.reddit.com/message/inbox/",
                    })
            except:
                continue

        # Also try the new Reddit UI message list
        if not results:
            # Filter out navigation text that isn't actual messages
            NAV_NOISE = {
                "group chats", "direct chats", "mod mail", "unread",
                "apply", "threads", "messages", "notifications",
                "all", "sent", "compose", "inbox", "settings",
                "log in", "sign up", "get app", "home", "popular",
            }

            # Try new Reddit message containers
            msg_items = page.query_selector_all(
                'div[data-testid="message"], '
                'div[class*="message-thread"], '
                'div[class*="inbox-item"], '
                '.thing.message'
            )
            for item in msg_items[:10]:
                try:
                    text = item.inner_text().strip()
                    # Skip nav elements and very short text
                    if not text or len(text) < 15:
                        continue
                    if text.lower().strip() in NAV_NOISE:
                        continue
                    results.append({
                        "author": "unknown",
                        "subject": text[:80],
                        "body": text[:300],
                        "is_new": True,
                        "url": "https://www.reddit.com/message/inbox/",
                    })
                except:
                    continue

        page.close()
        pw.stop()
    except Exception as e:
        print(json.dumps([]), file=sys.stderr)
        sys.exit(0)

    print(json.dumps(results))


if __name__ == "__main__":
    main()
