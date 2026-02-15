"""Check Upwork messages for new client responses via Playwright CDP."""

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

        page.goto("https://www.upwork.com/ab/messages", wait_until="domcontentloaded", timeout=20000)
        time.sleep(4)

        url = page.url
        if "login" in url.lower():
            print(json.dumps([]))
            pw.stop()
            return

        # Look for message threads with unread indicators
        threads = page.query_selector_all('[data-test="message-thread"], .thread-list-item, [class*="thread"]')
        for thread in threads[:10]:
            try:
                client = ""
                job_title = ""
                message = ""
                is_new = False

                # Client name
                name_el = thread.query_selector('[data-test="thread-name"], .name, .thread-name')
                if name_el:
                    client = name_el.inner_text().strip()

                # Job title or subject
                title_el = thread.query_selector('[data-test="thread-title"], .thread-title, .subject')
                if title_el:
                    job_title = title_el.inner_text().strip()

                # Last message preview
                preview_el = thread.query_selector('[data-test="thread-preview"], .preview, .last-message')
                if preview_el:
                    message = preview_el.inner_text().strip()[:300]

                # Unread indicator
                unread_el = thread.query_selector('.unread-count, .badge, [class*="unread"]')
                if unread_el:
                    is_new = True

                cls = thread.get_attribute("class") or ""
                if "unread" in cls:
                    is_new = True

                if client or job_title:
                    results.append({
                        "client": client,
                        "job_title": job_title,
                        "message": message,
                        "is_new": is_new,
                        "url": "https://www.upwork.com/ab/messages",
                    })
            except:
                continue

        # If no structured results, check notification badge
        if not results:
            badge = page.query_selector('[data-test="messages-count"], .nav-badge, [class*="badge"]')
            if badge:
                try:
                    count = badge.inner_text().strip()
                    if count and count.isdigit() and int(count) > 0:
                        results.append({
                            "client": "unknown",
                            "job_title": f"{count} unread messages",
                            "message": "Check Upwork messages",
                            "is_new": True,
                            "url": "https://www.upwork.com/ab/messages",
                        })
                except:
                    pass

        page.close()
        pw.stop()
    except Exception as e:
        print(json.dumps([]), file=sys.stderr)
        sys.exit(0)

    print(json.dumps(results))


if __name__ == "__main__":
    main()
