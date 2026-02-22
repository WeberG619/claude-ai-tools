"""Fix proposal length and resubmit bid for Streamlit Ops Control Panel (#1134)."""

import time
from playwright.sync_api import sync_playwright

# Under 1500 chars
PROPOSAL = """Here's what I'd deliver:

1. Streamlit UI - Clean ops dashboard with real-time queue, customer context sidebar, and agent workflow views using session state + caching.

2. Redis integration - In-memory state for chat presence, typing indicators, and job queuing with pub/sub for instant updates across agents.

3. Postgres data layer - Customer context hydration, chat transcript archival, and role-based access for support vs. ops leaders.

4. WebSocket/realtime - Live chat integration with your existing gateway, instant queue updates pushed to all connected agents.

5. Docker deployment - Everything containerized with docker-compose.

I build Python + Streamlit + Redis systems regularly and have shipped production dashboards with LLM integrations. MVP in 2 weeks.

- Weber"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        print("No Freelancer tab found")
        pw.stop()
        return

    print(f"URL: {fl.url}")
    print(f"Proposal length: {len(PROPOSAL)} chars")

    # Clear and refill the textarea with shorter proposal
    textareas = fl.query_selector_all("textarea")
    for ta in textareas:
        try:
            if ta.is_visible():
                ta.click()
                ta.fill("")
                time.sleep(0.3)
                ta.fill(PROPOSAL)
                print("Proposal replaced with shorter version!")
                break
        except:
            continue

    time.sleep(1)

    # Click submit button
    submit_btn = fl.query_selector('button:has-text("All Done")')
    if not submit_btn:
        submit_btn = fl.query_selector('button:has-text("Write my bid")')
    if not submit_btn:
        submit_btn = fl.query_selector('button:has-text("Place Bid")')

    if submit_btn:
        print(f"Clicking: '{submit_btn.inner_text()}'")
        submit_btn.click()
        time.sleep(5)

        # Check result
        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_result_1134.png")
        body = fl.inner_text("body")[:2000]

        if "failed" in body.lower()[:500]:
            print("STILL FAILING")
            print(body[:500])
        elif "success" in body.lower()[:500] or "your bid" in body.lower()[:500]:
            print("BID SUBMITTED SUCCESSFULLY!")
        else:
            print(f"Result page:\n{body[:800]}")
    else:
        print("No submit button found")

    pw.stop()


if __name__ == "__main__":
    main()
