"""Submit 3 proposals: 2 Reddit DMs + 1 Upwork via CDP."""
import json
import time
import sys
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"

# Reddit DM #1: AI Content Creator to Penoliya_Haruhi
DM1 = {
    "recipient": "Penoliya_Haruhi",
    "title": "AI Content Creator - Automation Specialist Application",
    "body": """Hi,

I'm a full-stack developer and automation specialist with deep experience in AI/ML pipelines and workflow automation.

Why I'm a strong fit for Seraphim Management:

- Content pipeline automation - I've built end-to-end pipelines that process, sort, and route large volumes of media files programmatically. I can automate your content organization workflows so your team spends less time on manual sorting.
- AI-generated content experience - I work daily with AI image and video generation tools, prompt engineering, and post-processing pipelines.
- Database + workflow systems - I've designed and maintained production databases and built automation layers on top of them. Content tracking, metadata tagging, and workflow routing can be systematized.
- Technical depth with creative sensibility - My work sits at the intersection of engineering and visual output.

What I'd focus on first:
1. Audit your current content workflow - tools, file structure, handoff points
2. Identify the highest-impact automation opportunities
3. Start delivering content while building out systems that make future output faster

I'm looking for exactly this kind of long-term role. Strong English (native-level), available immediately, and happy to complete your evaluation tests.

I'll apply through your Airtable form as well.

Best,
Weber Gouin""",
}

# Reddit DM #2: Python SWE to Reasonable_Salary182
DM2 = {
    "recipient": "Reasonable_Salary182",
    "title": "Python SWE Application - Production Systems Expert",
    "body": """Hi,

I'm a full-stack developer with deep Python expertise building production-grade systems - exactly the profile described for the Mercor model-training project.

Relevant experience:

- Production Python systems daily: autonomous agent frameworks, MCP servers, and multi-service pipelines running 24/7. Full-featured services with structured error handling, health monitoring, and recovery logic.
- Advanced Python fundamentals: async/await (concurrent API orchestration), decorators (tool registration patterns), context managers (resource lifecycle), generators (streaming pipelines), Pydantic models throughout.
- AI/ML model training context: Claude API, OpenAI, and tool-use architectures daily - building structured, evaluable interactions that model-training projects require.
- Modern tooling: FastAPI services, dependency injection, type hints everywhere, comprehensive test suites. 15+ interconnected repos with CI/CD.

I come from AEC/engineering (700+ Revit API methods automated, BIM pipelines) - complex systems under real constraints, not toy projects.

Availability: 20+ hours/week, immediately available. Happy to go through the 90-minute technical interview.

Best,
Weber Gouin""",
}


def send_reddit_dm(page, dm):
    """Send a Reddit DM via compose page."""
    recipient = dm["recipient"]
    url = f"https://www.reddit.com/message/compose/?to={recipient}"

    print(f"\n--- Sending DM to {recipient} ---")
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    time.sleep(4)

    # Check if logged in
    current_url = page.url
    if "login" in current_url.lower() and "compose" not in current_url.lower():
        print(f"  NOT LOGGED IN (url: {current_url})")
        return False

    # Fill title
    title_input = page.query_selector('input[name="message-title"]')
    if not title_input:
        # Try fallback
        title_input = page.query_selector('input[placeholder*="Title"], input[placeholder*="Subject"]')
    if not title_input:
        # Dump what's on page for debugging
        inputs = page.query_selector_all("input")
        for inp in inputs:
            name = inp.get_attribute("name") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            print(f"  Input: name={name}, placeholder={placeholder}")
        print("  ERROR: Could not find title field")
        return False

    title_input.click()
    time.sleep(0.3)
    title_input.fill(dm["title"])
    time.sleep(0.3)
    print(f"  Filled title: {dm['title'][:50]}")

    # Fill message
    msg_area = page.query_selector('textarea[name="message-content"]')
    if not msg_area:
        msg_area = page.query_selector('textarea#innerTextArea')
    if not msg_area:
        msg_area = page.query_selector('textarea')
    if not msg_area:
        print("  ERROR: Could not find message textarea")
        return False

    msg_area.click()
    time.sleep(0.3)
    msg_area.fill(dm["body"])
    time.sleep(0.5)
    print(f"  Filled message ({len(dm['body'])} chars)")

    # Click Send
    send_btn = None
    buttons = page.query_selector_all('button')
    for btn in buttons:
        try:
            text = btn.inner_text().strip().lower()
            if text in ("send", "send message"):
                send_btn = btn
                break
        except:
            continue

    if not send_btn:
        # Try faceplate-tracker elements
        trackers = page.query_selector_all('faceplate-tracker[action="click"]')
        for t in trackers:
            try:
                text = t.inner_text().strip().lower()
                if "send" in text:
                    send_btn = t
                    break
            except:
                continue

    if not send_btn:
        print("  ERROR: Could not find Send button")
        return False

    disabled = send_btn.get_attribute("disabled")
    if disabled is not None:
        print("  ERROR: Send button is disabled")
        return False

    print("  Clicking Send...")
    send_btn.click()
    time.sleep(3)

    # Check if form cleared (success indicator)
    try:
        title_val = title_input.input_value() if title_input.is_visible() else ""
    except:
        title_val = ""

    if not title_val or title_val != dm["title"]:
        print(f"  SUCCESS - DM sent to {recipient}!")
        return True
    else:
        print(f"  UNCERTAIN - form may not have submitted")
        return False


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page = context.new_page()

    results = {}

    # Send Reddit DM #1
    ok1 = send_reddit_dm(page, DM1)
    results["dm1_penoliya"] = ok1
    time.sleep(2)

    # Send Reddit DM #2
    ok2 = send_reddit_dm(page, DM2)
    results["dm2_mercor"] = ok2

    page.close()
    pw.stop()

    print(f"\n=== RESULTS ===")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
