# -*- coding: utf-8 -*-
"""Submit Upwork proposals for the best matching jobs."""
from playwright.sync_api import sync_playwright
import time
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CDP_URL = "http://localhost:9222"

# Load job URLs
with open('D:/_CLAUDE-TOOLS/opportunityengine/scouts/_upwork_targets.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
job_urls = data['urls']

# Our top targets with proposals
TARGETS = [
    {
        "title": "Need Claude-Code Expert for Rapid Learning Sessions",
        "rate": "15",
        "proposal": """I literally live in Claude Code. I use it daily for production development - building AI agents, browser automation, API integrations, and full-stack applications.

What I can teach you:
- Effective prompting patterns for Claude Code (how to get it to write production-quality code, not toy examples)
- MCP server setup and custom tool creation
- Multi-agent workflows and task delegation
- Context management for large codebases
- Integration with git, testing, and CI/CD workflows

I've built MCP servers (Revit API bridge, voice TTS, financial data), autonomous agents, and manage a full workspace of interconnected tools all through Claude Code.

Happy to do a quick trial session so you can see my teaching style. What's your current experience level with Claude Code?

Best,
Weber Gouin""",
    },
    {
        "title": "Improve Claude Code Experience",
        "rate": "35",
        "proposal": """I use Claude Code as my primary development environment and have deep experience optimizing the workflow.

What I've built with Claude Code:
- Custom MCP servers (Revit API bridge with 700+ methods, voice TTS, financial data, memory systems)
- Autonomous agent systems with task queues, browser automation, and multi-platform integrations
- Production applications spanning Python, C#, React, and infrastructure

I can help improve your Claude Code experience by:
1. Setting up custom MCP servers for your specific tools and APIs
2. Configuring CLAUDE.md files and project context for optimal code generation
3. Building efficient multi-agent workflows
4. Creating custom skills and slash commands
5. Optimizing prompting patterns for your use cases

What aspects of Claude Code are you trying to improve? I'd love to understand your current pain points.

Best,
Weber Gouin""",
    },
    {
        "title": "Teach us MCP!",
        "rate": "40",
        "proposal": """I've built multiple production MCP servers and integrate them daily with Claude Code. This is my core workflow.

MCP servers I've built:
- **Revit API Bridge** - 700+ methods exposing Autodesk Revit's API through MCP
- **Voice TTS server** - Text-to-speech with multiple voices
- **Financial data server** - Stock quotes, technical analysis, portfolio tracking
- **Memory system** - Persistent memory with semantic search, corrections, and pattern detection
- **Excel automation** - Full Excel control via MCP
- **Browser automation** - Stealth browsing with credential management

I can teach your team:
1. MCP architecture (servers, tools, resources, prompts)
2. Building custom MCP servers in Python or TypeScript
3. Connecting MCP servers to Claude Code, Claude Desktop, and custom applications
4. Best practices for tool design, error handling, and security
5. Real-world patterns: database access, API wrapping, file system tools

What's your team's background and what are you trying to build with MCP?

Best,
Weber Gouin""",
    },
    {
        "title": "AI Agent Developer for WhatsApp and Web App Integration",
        "rate": "40",
        "proposal": """I build AI agent systems professionally. I've created autonomous agents with:

- Claude/GPT API integration with function calling and tool use
- Multi-platform messaging (Telegram, Discord - WhatsApp integration is straightforward with the Business API)
- Production task queues with scheduling, error handling, and monitoring
- Web app frontends with real-time updates
- SQLite/PostgreSQL backends for conversation history and state management

For your WhatsApp + Web App integration, I'd approach it as:
1. WhatsApp Business API setup (or Twilio/360dialog as the provider)
2. AI agent backend with Claude API for natural conversation + function calling
3. Web dashboard for monitoring conversations, analytics, and manual override
4. Webhook-based architecture for real-time message handling

What's the agent supposed to do? (Customer support, lead qualification, appointment booking, etc.) That'll help me scope the build.

Best,
Weber Gouin""",
    },
    {
        "title": "Create a Macro for Excel Mac",
        "rate": "30",
        "proposal": """I can build this Excel macro for you. I work with Excel automation regularly - both VBA macros and Python-based solutions.

Quick note on Mac: Excel for Mac has some VBA limitations compared to Windows. I'll work within those constraints or suggest alternatives (like Office Scripts or Python via xlwings) if needed.

What does the macro need to do? With a clear spec I can usually turn these around within a day.

Best,
Weber Gouin""",
    },
    {
        "title": "Google Apps Script & Google Sheets Expert Needed to Fix and Debug",
        "rate": "30",
        "proposal": """I can fix and debug your Google Apps Script. I work with Google Sheets automation regularly - Apps Script, custom functions, triggers, and API integrations.

Common issues I fix:
- Trigger failures and quota limits
- API authentication issues (OAuth, service accounts)
- Performance problems with large datasets
- Formula/script logic bugs

What's the script doing (or supposed to be doing)? If you can share the error messages or unexpected behavior, I can usually diagnose quickly.

Best,
Weber Gouin""",
    },
]


def submit_proposal(page, job_title, rate, proposal_text):
    """Navigate to job, click Apply, fill form, submit."""
    # Find URL for this job
    url = None
    for title, u in job_urls.items():
        if job_title.lower()[:30] in title.lower():
            url = u
            break

    if not url:
        # Try partial match
        for title, u in job_urls.items():
            words = job_title.lower().split()[:3]
            if all(w in title.lower() for w in words):
                url = u
                break

    if not url:
        print(f"  URL not found for: {job_title[:50]}")
        return False

    print(f"  URL: {url[:80]}")

    # Navigate
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(5)
    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                break
        except:
            time.sleep(2)
    time.sleep(2)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked")
        return False

    # Check if already applied
    already = page.evaluate("document.body.innerText.includes('already submitted')")
    if already:
        print("  Already applied!")
        return "already"

    # Click Apply
    try:
        btn = page.locator('#submit-proposal-button, button:has-text("Apply now")').first
        if btn.is_disabled(timeout=3000):
            print("  Apply button disabled")
            return False
        btn.click(timeout=10000)
        time.sleep(6)
    except Exception as e:
        print(f"  Apply click failed: {e}")
        return False

    if "apply" not in page.url.lower():
        print("  Not on apply page")
        return False

    time.sleep(3)

    # Fill cover letter
    textareas = page.locator("textarea:visible")
    ta_count = textareas.count()
    if ta_count > 0:
        textareas.nth(0).fill(proposal_text)
        time.sleep(0.5)
        print(f"  Cover letter filled ({len(proposal_text)} chars)")

    # Fill any screening questions (textareas after the first)
    for i in range(1, ta_count):
        try:
            val = textareas.nth(i).input_value()
            if not val:
                textareas.nth(i).fill("Happy to discuss in detail. I have extensive experience in this area and can provide specific examples during our conversation.")
                print(f"  Filled screening question {i}")
        except:
            pass

    # Fill rate
    inputs = page.locator('input[type="text"]:visible')
    for i in range(inputs.count()):
        try:
            ph = inputs.nth(i).get_attribute("placeholder") or ""
            val = inputs.nth(i).input_value()
            if "$" in ph or "$" in val:
                inputs.nth(i).focus()
                time.sleep(0.1)
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.type(rate, delay=50)
                page.keyboard.press("Tab")
                time.sleep(1)
                print(f"  Rate: ${rate}")
                break
        except:
            continue

    # Fill rate increase dropdowns
    dds = page.locator('[role="combobox"][data-test="dropdown-toggle"]:visible')
    for i in range(dds.count()):
        try:
            dds.nth(i).click(timeout=3000)
            time.sleep(1)
            opts = page.locator('[role="option"]:visible')
            if opts.count() > 0:
                if i == 0:
                    for j in range(opts.count()):
                        if "6 month" in opts.nth(j).text_content():
                            opts.nth(j).click()
                            break
                    else:
                        opts.nth(min(2, opts.count()-1)).click()
                else:
                    for j in range(opts.count()):
                        if "10%" in opts.nth(j).text_content():
                            opts.nth(j).click()
                            break
                    else:
                        opts.nth(min(1, opts.count()-1)).click()
                time.sleep(1)
        except:
            pass

    # Submit
    time.sleep(2)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Try different submit button texts
    for btn_text in ["Send for", "Submit proposal"]:
        try:
            page.evaluate(f"""(() => {{
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {{
                    if (btn.textContent.includes('{btn_text}') && btn.offsetParent !== null) {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
            }})()""")
            time.sleep(8)
            if "apply" not in page.url.lower() or "success" in page.url.lower():
                print("  SUCCESS!")
                return True
        except:
            pass

    # Check for confirm dialog
    try:
        cb = page.locator('input[type="checkbox"][value="agree"]')
        if cb.count() > 0:
            page.evaluate("document.querySelector('input[type=\"checkbox\"][value=\"agree\"]')?.click()")
            time.sleep(2)
            page.evaluate("""(() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if ((btn.textContent.includes('Submit') || btn.textContent.includes('Send') || btn.textContent.includes('Yes')) && btn.offsetParent) btn.click();
                }
            })()""")
            time.sleep(5)
            if "success" in page.url.lower():
                print("  SUCCESS after confirm!")
                return True
    except:
        pass

    # Final check
    if "success" in page.url.lower() or "Proposals" in page.title():
        print("  SUCCESS!")
        return True

    print(f"  May need manual check. URL: {page.url[:60]}")
    return False


# Main
pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

results = {}
for target in TARGETS:
    print(f"\n{'='*60}")
    print(f"Submitting: {target['title'][:60]}")
    ok = submit_proposal(page, target['title'], target['rate'], target['proposal'])
    results[target['title']] = ok
    time.sleep(3)

print(f"\n\n{'='*60}")
print("RESULTS:")
for title, ok in results.items():
    if ok == True:
        status = "SUBMITTED"
    elif ok == "already":
        status = "ALREADY APPLIED"
    else:
        status = "FAILED"
    print(f"  [{status}] {title[:55]}")

pw.stop()
