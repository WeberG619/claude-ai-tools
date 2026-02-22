"""Open the 'Vibe coding with Claude Code' job on Upwork and get details."""

import time
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

    # Go directly to the job
    job_url = "https://www.upwork.com/jobs/Vibe-coding-with-Claude-Code-Codex_~022022952633424216463/"
    uw.goto(job_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    print(f"URL: {uw.url}")

    # Get full job text
    body = uw.inner_text("body")[:5000]
    print("\n=== JOB DETAILS ===")
    print(body[:4000])

    uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_claude_job.png")
    print("\nScreenshot saved")

    pw.stop()


if __name__ == "__main__":
    main()
