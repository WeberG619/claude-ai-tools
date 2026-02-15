# -*- coding: utf-8 -*-
"""Find and submit proposals for Claude Code/MCP jobs on Upwork."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CDP_URL = "http://localhost:9222"

JOBS_TO_FIND = [
    {
        "search": "claude+code+expert",
        "match": "claude-code",
        "rate": "15",
        "proposal": """I literally live in Claude Code. I use it daily for production development - AI agents, browser automation, API integrations, and full-stack applications.

What I can teach you:
- Effective prompting patterns for Claude Code (how to get production-quality code, not toy examples)
- MCP server setup and custom tool creation
- Multi-agent workflows and task delegation
- Context management for large codebases
- Integration with git, testing, and CI/CD workflows

I've built MCP servers (Revit API bridge, voice TTS, financial data), autonomous agents, and manage a full workspace through Claude Code.

Happy to do a quick trial session. What's your current experience level?

Best,
Weber Gouin""",
    },
    {
        "search": "improve+claude+code",
        "match": "improve-claude",
        "rate": "35",
        "proposal": """I use Claude Code as my primary development environment daily.

What I've built with Claude Code:
- Custom MCP servers (Revit API bridge with 700+ methods, voice TTS, financial data, memory systems)
- Autonomous agent systems with task queues, browser automation, multi-platform integrations
- Production applications spanning Python, C#, React

I can help improve your Claude Code experience by:
1. Setting up custom MCP servers for your specific tools
2. Configuring CLAUDE.md and project context
3. Building efficient multi-agent workflows
4. Creating custom skills and slash commands
5. Optimizing prompting patterns

What aspects are you trying to improve?

Best,
Weber Gouin""",
    },
    {
        "search": "teach+MCP",
        "match": "teach-mcp",
        "rate": "40",
        "proposal": """I've built multiple production MCP servers and integrate them daily with Claude Code.

MCP servers I've built:
- Revit API Bridge (700+ methods)
- Voice TTS server
- Financial data server (stocks, analysis, portfolio)
- Memory system (semantic search, corrections, patterns)
- Excel automation (full control)
- Browser automation (stealth browsing + credentials)

I can teach your team:
1. MCP architecture (servers, tools, resources, prompts)
2. Building custom MCP servers in Python or TypeScript
3. Connecting MCP to Claude Code, Claude Desktop, custom apps
4. Tool design best practices, error handling, security
5. Real-world patterns: database access, API wrapping, file tools

What's your team's background and what are you building with MCP?

Best,
Weber Gouin""",
    },
    {
        "search": "whatsapp+ai+agent",
        "match": "whatsapp",
        "rate": "40",
        "proposal": """I build AI agent systems professionally. I've created autonomous agents with:

- Claude/GPT API integration with function calling and tool use
- Multi-platform messaging (Telegram, Discord, WhatsApp via Business API)
- Production task queues with scheduling and monitoring
- Web app frontends with real-time updates
- SQLite/PostgreSQL backends for conversation history

For WhatsApp + Web App, I'd approach it as:
1. WhatsApp Business API setup (Twilio/360dialog)
2. AI agent backend with Claude API for conversation + function calling
3. Web dashboard for monitoring and manual override
4. Webhook architecture for real-time messages

What's the agent supposed to do? That'll help me scope the build.

Best,
Weber Gouin""",
    },
    {
        "search": "excel+macro+mac",
        "match": "macro-excel-mac",
        "rate": "30",
        "proposal": """I can build this Excel macro for you. I work with Excel automation regularly - VBA, Python, and Office Scripts.

Note on Mac: Excel for Mac has some VBA limitations vs Windows. I'll work within those constraints or suggest alternatives (Office Scripts, Python via xlwings) if needed.

What does the macro need to do? With a clear spec I can turn this around within a day.

Best,
Weber Gouin""",
    },
    {
        "search": "google+apps+script+fix+debug",
        "match": "apps-script",
        "rate": "30",
        "proposal": """I can fix and debug your Google Apps Script. I work with Sheets automation regularly - Apps Script, custom functions, triggers, API integrations.

Common issues I fix: trigger failures, quota limits, OAuth issues, performance with large datasets, formula/script logic bugs.

What's the script doing (or supposed to do)? Share the error messages and I can diagnose quickly.

Best,
Weber Gouin""",
    },
]

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]


def find_and_apply(search_term, match_key, rate, proposal):
    """Search Upwork, find the job, click through to apply."""
    url = f"https://www.upwork.com/nx/search/jobs/?q={search_term}&sort=recency&proposals=0-4&payment_verified=1"
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(5)

    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            elif page.evaluate("document.querySelectorAll('a[href*=\"/jobs/\"]').length") > 2:
                break
            else:
                time.sleep(1)
        except:
            time.sleep(1)
    time.sleep(2)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked search")
        return False

    # Find the first job link
    job_link = page.evaluate("""(() => {
        const links = document.querySelectorAll('a[href*="/jobs/"]');
        for (const a of links) {
            const text = a.textContent.trim();
            if (text.length > 10 && text.length < 150 && a.href.includes('/jobs/')) {
                return {title: text, url: a.href.split('?')[0]};
            }
        }
        return null;
    })()""")

    if not job_link:
        print("  No job found in search results")
        return False

    print(f"  Found: {job_link['title'][:60]}")
    print(f"  URL: {job_link['url'][:80]}")

    # Navigate to job page
    page.evaluate(f"window.location.href = '{job_link['url']}'")
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
        print("  Cloudflare on job page")
        return False

    # Check already applied
    already = page.evaluate("document.body.innerText.includes('already submitted')")
    if already:
        print("  Already applied!")
        return "already"

    # Click Apply
    try:
        btn = page.locator('#submit-proposal-button').first
        if btn.is_disabled(timeout=3000):
            print("  Apply disabled")
            return False
        btn.click(timeout=10000)
        time.sleep(6)
    except:
        try:
            page.locator('button:has-text("Apply now")').first.click(timeout=5000)
            time.sleep(6)
        except Exception as e:
            print(f"  Apply failed: {e}")
            return False

    if "apply" not in page.url.lower():
        print(f"  Not on apply page: {page.url[:60]}")
        return False

    time.sleep(3)
    print("  On apply page")

    # Fill cover letter (first textarea)
    textareas = page.locator("textarea:visible")
    ta_count = textareas.count()
    if ta_count > 0:
        textareas.nth(0).fill(proposal)
        print(f"  Cover letter filled")

    # Fill screening questions
    for i in range(1, ta_count):
        try:
            val = textareas.nth(i).input_value()
            if not val:
                textareas.nth(i).fill("Happy to discuss in detail. I have hands-on production experience with this and can share specific examples.")
                print(f"  Screening Q{i} filled")
        except:
            pass

    # Set rate
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

    # Rate increase dropdowns
    dds = page.locator('[role="combobox"][data-test="dropdown-toggle"]:visible')
    for i in range(dds.count()):
        try:
            dds.nth(i).click(timeout=3000)
            time.sleep(1)
            opts = page.locator('[role="option"]:visible')
            if opts.count() > 0:
                target_text = "6 month" if i == 0 else "10%"
                for j in range(opts.count()):
                    if target_text in opts.nth(j).text_content():
                        opts.nth(j).click()
                        break
                else:
                    opts.nth(min(i+1, opts.count()-1)).click()
                time.sleep(1)
        except:
            pass

    # Submit
    time.sleep(2)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    submitted = page.evaluate("""(() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent;
            if ((text.includes('Send for') || text.includes('Submit proposal')) && btn.offsetParent) {
                btn.click();
                return true;
            }
        }
        return false;
    })()""")

    if submitted:
        time.sleep(10)
        url_now = page.url.lower()
        title_now = page.title()

        if "success" in url_now or "apply" not in url_now or "Proposals" in title_now:
            print("  SUCCESS!")
            return True

        # Confirmation dialog?
        try:
            page.evaluate("""(() => {
                const cb = document.querySelector('input[type="checkbox"][value="agree"]');
                if (cb) cb.click();
            })()""")
            time.sleep(2)
            page.evaluate("""(() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if ((btn.textContent.includes('Submit') || btn.textContent.includes('Send') || btn.textContent.includes('Yes')) && btn.offsetParent) {
                        btn.click();
                        return;
                    }
                }
            })()""")
            time.sleep(5)
            if "success" in page.url.lower():
                print("  SUCCESS after confirm!")
                return True
        except:
            pass

        # Check for errors
        errors = page.evaluate("""(() => {
            const errs = document.querySelectorAll('[class*="error"]');
            return Array.from(errs).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 3);
        })()""")
        if errors:
            print(f"  Errors: {errors[:3]}")

    print(f"  Final URL: {page.url[:60]}")
    return False


results = {}
for job in JOBS_TO_FIND:
    print(f"\n{'='*60}")
    print(f"TARGET: {job['search'].replace('+', ' ')}")
    ok = find_and_apply(job['search'], job['match'], job['rate'], job['proposal'])
    results[job['search']] = ok
    time.sleep(3)

print(f"\n\n{'='*60}")
print("RESULTS:")
for search, ok in results.items():
    status = "SUBMITTED" if ok == True else ("ALREADY" if ok == "already" else "FAILED")
    print(f"  [{status}] {search.replace('+', ' ')}")

pw.stop()
