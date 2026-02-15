"""Check Freelancer messages/notifications via Playwright CDP."""

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

        page.goto("https://www.freelancer.com/messages", wait_until="domcontentloaded", timeout=20000)
        time.sleep(4)

        url = page.url
        if "login" in url.lower():
            print(json.dumps([]))
            pw.stop()
            return

        # Look for message threads
        threads = page.query_selector_all('.thread, .conversation, [class*="message-thread"]')
        for thread in threads[:10]:
            try:
                client = ""
                project = ""
                message = ""
                is_new = False

                name_el = thread.query_selector('.username, .name, [class*="name"]')
                if name_el:
                    client = name_el.inner_text().strip()

                project_el = thread.query_selector('.project-name, .subject, [class*="project"]')
                if project_el:
                    project = project_el.inner_text().strip()

                preview_el = thread.query_selector('.preview, .last-message, [class*="preview"]')
                if preview_el:
                    message = preview_el.inner_text().strip()[:300]

                cls = thread.get_attribute("class") or ""
                if "unread" in cls or "new" in cls:
                    is_new = True

                if client or project:
                    results.append({
                        "client": client,
                        "project": project,
                        "message": message,
                        "is_new": is_new,
                        "url": "https://www.freelancer.com/messages",
                    })
            except:
                continue

        # Check notification count from the nav
        if not results:
            body_text = page.inner_text("body")[:500]
            # Look for notification badges
            badges = page.query_selector_all('[class*="badge"], [class*="count"], [class*="notification"]')
            for badge in badges:
                try:
                    if badge.is_visible():
                        text = badge.inner_text().strip()
                        if text.isdigit() and int(text) > 0:
                            results.append({
                                "client": "unknown",
                                "project": f"{text} notifications",
                                "message": "Check Freelancer messages",
                                "is_new": True,
                                "url": "https://www.freelancer.com/messages",
                            })
                            break
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
