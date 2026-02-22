"""Submit bid on Freelancer for 'Streamlit Ops Control Panel Build' (#1134)."""

import time
from playwright.sync_api import sync_playwright

PROPOSAL = """Hi — this is right in my wheelhouse. I build Python + Streamlit + Redis systems regularly, and I've shipped production control panels with LLM integrations.

Here's what I'd deliver:

1. **Streamlit UI** — Clean, responsive ops dashboard with real-time metrics, customer queue management, and agent workflow views. I'll use Streamlit's session state + caching for snappy performance.

2. **Redis integration** — Fast in-memory state management, job queuing (likely RQ or Celery with Redis broker), and real-time pub/sub for live updates across sessions.

3. **LLM pipeline** — I'll wire in the LLM components for automated response suggestions, ticket classification, or whatever your AI workflow needs. I work with Claude, GPT, and open-source models daily.

4. **Docker deployment** — Everything containerized with docker-compose for easy local dev and deployment.

I can start immediately and typically deliver an MVP within 1-2 weeks for a panel like this.

— Weber"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    # Find or create Freelancer tab
    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        fl = context.new_page()

    # Navigate to the project page
    fl.goto(
        "https://www.freelancer.com/projects/streamlit/streamlit-ops-control-panel-build",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    time.sleep(5)

    print(f"URL: {fl.url}")

    # Check if logged in
    if "login" in fl.url.lower():
        print("NOT LOGGED IN - need to log in first")
        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_not_logged.png")
        pw.stop()
        return

    # Get page content
    body = fl.inner_text("body")[:3000]
    print(f"Page content:\n{body[:1500]}")

    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_project_1134.png")

    # Look for "Place Bid" or "Bid on this project" button
    bid_btn = fl.query_selector('button:has-text("Place Bid")')
    if not bid_btn:
        bid_btn = fl.query_selector('button:has-text("Bid on this")')
    if not bid_btn:
        bid_btn = fl.query_selector('a:has-text("Place Bid")')
    if not bid_btn:
        bid_btn = fl.query_selector('a:has-text("Bid on this")')
    if not bid_btn:
        # Try any element with bid text
        elements = fl.query_selector_all("button, a")
        for el in elements:
            try:
                txt = el.inner_text().lower()
                if "bid" in txt and ("place" in txt or "submit" in txt or "this project" in txt):
                    bid_btn = el
                    break
            except:
                continue

    if bid_btn:
        print(f"Found bid button: {bid_btn.inner_text()}")
        bid_btn.click()
        time.sleep(4)

        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_form_1134.png")

        # Look for bid amount input and description textarea
        body_after = fl.inner_text("body")[:2000]
        print(f"\nAfter clicking bid:\n{body_after[:1000]}")

        # Fill in description/proposal textarea
        textareas = fl.query_selector_all("textarea")
        for ta in textareas:
            try:
                if ta.is_visible():
                    placeholder = ta.get_attribute("placeholder") or ""
                    print(f"Found textarea: placeholder='{placeholder[:50]}'")
                    ta.click()
                    ta.fill(PROPOSAL)
                    print("Proposal filled!")
                    break
            except:
                continue

        # Look for bid amount input - set a competitive rate
        inputs = fl.query_selector_all("input[type='number'], input[type='text']")
        for inp in inputs:
            try:
                if inp.is_visible():
                    placeholder = inp.get_attribute("placeholder") or ""
                    name = inp.get_attribute("name") or ""
                    aria = inp.get_attribute("aria-label") or ""
                    label_text = f"{placeholder} {name} {aria}".lower()
                    if any(w in label_text for w in ["amount", "bid", "budget", "price", "rate"]):
                        inp.click()
                        inp.fill("")
                        inp.type("750")  # Competitive bid
                        print("Bid amount set to $750")
                        break
            except:
                continue

        # Look for delivery days input
        for inp in inputs:
            try:
                if inp.is_visible():
                    placeholder = inp.get_attribute("placeholder") or ""
                    name = inp.get_attribute("name") or ""
                    aria = inp.get_attribute("aria-label") or ""
                    label_text = f"{placeholder} {name} {aria}".lower()
                    if any(w in label_text for w in ["days", "deliver", "period", "duration"]):
                        inp.click()
                        inp.fill("")
                        inp.type("14")  # 2 weeks
                        print("Delivery set to 14 days")
                        break
            except:
                continue

        time.sleep(2)
        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_filled_1134.png")
        print("\nScreenshot saved - review before submitting")
    else:
        print("Could not find Bid button")
        fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_no_bid_1134.png")

    pw.stop()


if __name__ == "__main__":
    main()
