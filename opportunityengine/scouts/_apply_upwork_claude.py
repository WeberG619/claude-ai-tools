"""Navigate to the 'Vibe coding with Claude Code' Upwork job and grab details."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    # Find Upwork tab
    uw_page = None
    for p in context.pages:
        if "upwork.com" in p.url and "login" not in p.url:
            uw_page = p
            break

    if not uw_page:
        uw_page = context.new_page()

    # Search for the Claude Code job
    uw_page.goto(
        "https://www.upwork.com/nx/search/jobs/?q=claude%20code&sort=recency",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    time.sleep(5)

    # Get job listings text
    body = uw_page.inner_text("body")[:3000]
    print("SEARCH RESULTS:")
    print(body[:2000])

    uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_claude_search.png")

    # Find and click the "Vibe coding" job link
    links = uw_page.query_selector_all("a")
    for link in links:
        try:
            text = link.inner_text()
            if "vibe coding" in text.lower() or "claude code" in text.lower():
                href = link.get_attribute("href")
                print(f"\nFound job link: {text[:80]}")
                print(f"URL: {href}")
                link.click()
                time.sleep(5)

                # Get full job details
                job_body = uw_page.inner_text("body")[:4000]
                print("\nJOB DETAILS:")
                print(job_body[:3000])

                uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_claude_job.png")
                break
        except:
            continue

    pw.stop()


if __name__ == "__main__":
    main()
