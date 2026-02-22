"""Get Upwork job listings from Find Work dashboard."""

import time
import json
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    uw = None
    for p in context.pages:
        if "upwork.com" in p.url and "login" not in p.url:
            uw = p
            break

    if not uw:
        uw = context.new_page()

    uw.goto("https://www.upwork.com/nx/find-work/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(6)

    url = uw.url
    print(f"URL: {url}")

    if "login" in url.lower() or "cloudflare" in uw.inner_text("body")[:200].lower():
        print("BLOCKED or logged out")
        uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_blocked.png")
        pw.stop()
        return

    # Extract jobs
    jobs = uw.evaluate("""() => {
        const results = [];
        const links = document.querySelectorAll('a');
        for (const a of links) {
            const text = (a.textContent || '').trim();
            const href = a.href || '';
            if (href.includes('/jobs/') && text.length > 15 && text.length < 200) {
                results.push({title: text, url: href});
            }
        }
        return results.slice(0, 20);
    }""")

    print(f"\nFound {len(jobs)} jobs:\n")
    for j in jobs:
        title = j["title"][:75]
        print(f"  {title}")
        print(f"  {j['url']}")
        print()

    uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_find_work.png")
    pw.stop()


if __name__ == "__main__":
    main()
