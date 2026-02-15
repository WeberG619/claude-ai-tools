"""Submit multiple Reddit DMs via Playwright CDP."""

import json
import time
import sys
from playwright.sync_api import sync_playwright


MESSAGES = [
    {
        "recipient": "Penoliya_Haruhi",
        "title": "AI Content Creator - Automation Specialist Application",
        "body": (
            "Hi,\n\n"
            "I'm a full-stack developer and automation specialist with deep experience in "
            "AI/ML pipelines and workflow automation. My background includes building content "
            "pipelines, database systems, and media processing workflows.\n\n"
            "Why I'm a strong fit for Seraphim Management:\n\n"
            "- Content pipeline automation - I've built end-to-end pipelines that process, sort, "
            "and route large volumes of media files programmatically. I can automate your content "
            "organization workflows so your team spends less time on manual sorting.\n"
            "- AI-generated content experience - I work daily with AI image and video generation "
            "tools, prompt engineering, and post-processing pipelines.\n"
            "- Database + workflow systems - I've designed and maintained production databases and "
            "built automation layers on top of them. Content tracking, metadata tagging, and "
            "workflow routing can be systematized.\n"
            "- Technical depth with creative sensibility - My work sits at the intersection of "
            "engineering and visual output.\n\n"
            "What I'd focus on first:\n"
            "1. Audit your current content workflow - tools, file structure, handoff points\n"
            "2. Identify the highest-impact automation opportunities\n"
            "3. Start delivering content while building out systems that make future output faster\n\n"
            "I'm looking for exactly this kind of long-term role. Strong English (native-level), "
            "available immediately, and happy to complete your evaluation tests.\n\n"
            "I'll apply through your Airtable form as well.\n\n"
            "Best,\nWeber Gouin"
        ),
    },
    {
        "recipient": "Reasonable_Salary182",
        "title": "Python SWE Application - Production Systems Expert",
        "body": (
            "Hi,\n\n"
            "I'm a full-stack developer with deep Python expertise and a background building "
            "production-grade systems - exactly the profile you're describing for the Mercor "
            "model-training project.\n\n"
            "Relevant experience:\n\n"
            "- Production Python systems daily: I build and maintain autonomous agent frameworks, "
            "MCP servers, and multi-service pipelines that run 24/7. Full-featured services with "
            "structured error handling, health monitoring, and recovery logic.\n"
            "- Advanced Python fundamentals in practice: async/await (concurrent API orchestration), "
            "decorators (tool registration patterns), context managers (resource lifecycle), "
            "generators (streaming pipelines), and Pydantic models throughout.\n"
            "- AI/ML model training context: I work with Claude API, OpenAI, and tool-use "
            "architectures daily - building structured, evaluable interactions that model-training "
            "projects require.\n"
            "- Modern tooling: FastAPI services, dependency injection, type hints everywhere, "
            "comprehensive test suites. 15+ interconnected repos with CI/CD.\n\n"
            "I come from AEC/engineering (700+ Revit API methods automated, BIM pipelines), "
            "which means complex systems under real constraints - not toy projects.\n\n"
            "Availability: 20+ hours/week, immediately available. Happy to go through the "
            "90-minute technical interview - I write Python without AI IDE assistance regularly.\n\n"
            "Best,\nWeber Gouin"
        ),
    },
]


def send_dm(page, recipient, title, body):
    """Send a single Reddit DM."""
    url = f"https://www.reddit.com/message/compose/?to={recipient}"
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)

    # Check if logged in
    if "login" in page.url.lower() and "compose" not in page.url.lower():
        return {"success": False, "error": "Not logged in"}

    # Fill title
    title_input = page.query_selector('input[name="message-title"]')
    if not title_input:
        # Try alternate selectors
        title_input = page.query_selector('input[placeholder*="Subject"], input[placeholder*="Title"]')
    if not title_input:
        return {"success": False, "error": "Could not find title field"}

    title_input.click()
    time.sleep(0.3)
    title_input.fill(title)
    time.sleep(0.3)

    # Fill message body
    msg_area = page.query_selector('textarea[name="message-content"]')
    if not msg_area:
        msg_area = page.query_selector('textarea#innerTextArea')
    if not msg_area:
        msg_area = page.query_selector('textarea')
    if not msg_area:
        return {"success": False, "error": "Could not find message textarea"}

    msg_area.click()
    time.sleep(0.3)
    msg_area.fill(body)
    time.sleep(0.5)

    # Click Send
    send_btn = None
    buttons = page.query_selector_all('button, faceplate-tracker[action="click"]')
    for btn in buttons:
        try:
            text = btn.inner_text().strip().lower()
            if text == "send" or text == "send message":
                send_btn = btn
                break
        except:
            continue

    if not send_btn:
        return {"success": False, "error": "Could not find Send button"}

    # Check if button is enabled
    disabled = send_btn.get_attribute("disabled")
    if disabled is not None:
        return {"success": False, "error": "Send button is disabled"}

    send_btn.click()
    time.sleep(3)

    # Check if form cleared (indicates success)
    try:
        title_val = title_input.input_value() if title_input.is_visible() else ""
    except:
        title_val = ""

    if not title_val or title_val != title:
        return {"success": True, "message": "DM sent (form cleared)"}
    else:
        return {"success": False, "error": "Form did not clear after clicking Send"}


def main():
    results = []
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.new_page()

        for msg in MESSAGES:
            result = send_dm(page, msg["recipient"], msg["title"], msg["body"])
            result["recipient"] = msg["recipient"]
            results.append(result)
            print(json.dumps(result))
            time.sleep(2)

        page.close()
        pw.stop()
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

    return results


if __name__ == "__main__":
    main()
