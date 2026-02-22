"""Submit proposal for 'Vibe coding with Claude Code' job on Upwork."""

import time
from playwright.sync_api import sync_playwright

COVER_LETTER = """Hi — I literally build with Claude Code every day as my primary development tool. I don't just "vibe code" — I've built production systems with it, including a 700+ method API bridge, AI rendering pipelines, and autonomous agent frameworks.

For what you're describing (analyzing sites, building brand personas, ad generation with Claude + Gemini), here's what I'd walk you through:

1. **Website analysis** — I'll show you how to use Claude Code to scrape and analyze competitor sites, extract copy patterns, and identify positioning gaps. This is straightforward with Playwright + Claude.

2. **Brand persona + trending ads DB** — We'll build a simple system that stores ad creative data (hooks, angles, CTAs) and uses Claude to generate personas based on brand analysis. I'd use a lightweight stack — Python + SQLite + Claude API.

3. **Claude for copy, Gemini for images** — I work with both APIs daily. I'll set up the workflow where Claude generates ad copy variations (hooks, angles, body copy) and Gemini handles image creation, all triggered from a simple interface.

4. **Feedback loop** — The real value is teaching you how to set up prompt chains that improve based on ad performance data. I've built exactly this kind of iterative AI pipeline.

I can do this as live training sessions where we build together, so you learn the process — not just get a deliverable you can't maintain.

Available to start immediately. What time works for a quick intro call?

— Weber"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    uw = None
    for p in context.pages:
        if "upwork.com" in p.url and "Vibe-coding" in p.url:
            uw = p
            break

    if not uw:
        uw = context.new_page()
        uw.goto(
            "https://www.upwork.com/jobs/Vibe-coding-with-Claude-Code-Codex_~022022952633424216463/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(5)

    print(f"On: {uw.url}")

    # Click "Apply now"
    apply_btn = uw.query_selector('button:has-text("Apply now")')
    if not apply_btn:
        apply_btn = uw.query_selector('a:has-text("Apply now")')
    if not apply_btn:
        # Try link version
        links = uw.query_selector_all("a")
        for link in links:
            if "apply" in (link.inner_text() or "").lower():
                apply_btn = link
                break

    if apply_btn:
        apply_btn.click()
        print("Clicked Apply now")
        time.sleep(5)
        print(f"URL: {uw.url}")
        uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_apply1.png")

        # Look for cover letter textarea
        body_text = uw.inner_text("body")[:1000]
        print(f"Page: {body_text[:300]}")

        # Find and fill cover letter
        textareas = uw.query_selector_all("textarea")
        for ta in textareas:
            try:
                if ta.is_visible():
                    ta.click()
                    ta.fill(COVER_LETTER)
                    print("Cover letter filled!")
                    break
            except:
                pass

        time.sleep(2)
        uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_apply2.png")
        print("Screenshot saved - review before final submit")
    else:
        print("Could not find Apply button")
        uw.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_no_apply.png")

    pw.stop()


if __name__ == "__main__":
    main()
