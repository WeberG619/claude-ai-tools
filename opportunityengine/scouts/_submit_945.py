"""Submit Reddit DM to FonziAI for opportunity #945 via Edge CDP."""

import time
import sys
from playwright.sync_api import sync_playwright

PROPOSAL_TITLE = "Re: Full Stack Software Engineer - Experienced Builder"

PROPOSAL_MSG = """Hi there,

Saw your post on r/forhire. I'm a full-stack engineer with 3+ years building production apps across Python, TypeScript, and C#.

What I bring:
- Full stack: React, Node.js, TypeScript, Python - comfortable owning features end-to-end
- AI/ML integration: Built AI rendering pipelines, LLM-powered automation workflows, and ML document analysis tools in production
- System design: Real-time state sync, event-driven architectures, multi-service platforms with CI/CD
- API design: REST, WebSockets, named pipes - built inter-process communication layers and MCP servers

I've spent years in fast-paced ship-it environments building the product, not just contributing. Used to collaborating directly with founders, making architectural decisions, and owning the full lifecycle.

Based in US-friendly timezone, available for long-term engagement. Happy to do a technical conversation or short trial task.

Best,
Weber Gouin"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]

    # Find existing DM tab or open new one
    page = None
    for p in context.pages:
        if "message/compose" in p.url and "FonziAI" in p.url:
            page = p
            break

    if not page:
        page = context.new_page()
        page.goto(
            "https://www.reddit.com/message/compose/?to=FonziAI",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(5)

    print(f"On page: {page.url}")

    # Fill Title
    title_filled = False
    title_selectors = [
        'input[name="title"]',
        'input[placeholder*="Title"]',
        "#title",
    ]
    for sel in title_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                el.fill(PROPOSAL_TITLE)
                title_filled = True
                print(f"Title filled via {sel}")
                break
        except Exception as e:
            print(f"Title {sel}: {e}")

    # Fallback: find any input that looks like title
    if not title_filled:
        inputs = page.query_selector_all("input")
        for inp in inputs:
            try:
                ph = inp.get_attribute("placeholder") or ""
                nm = inp.get_attribute("name") or ""
                if "title" in ph.lower() or "title" in nm.lower() or "subject" in ph.lower():
                    inp.click()
                    inp.fill(PROPOSAL_TITLE)
                    title_filled = True
                    print(f"Title filled via fallback input (placeholder={ph}, name={nm})")
                    break
            except:
                pass

    # Fill Message
    msg_filled = False
    msg_selectors = [
        'textarea[name="message"]',
        'textarea[name="body"]',
        'textarea[placeholder*="Message"]',
        "textarea",
    ]
    for sel in msg_selectors:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    el.click()
                    el.fill(PROPOSAL_MSG)
                    msg_filled = True
                    print(f"Message filled via {sel}")
                    break
            if msg_filled:
                break
        except Exception as e:
            print(f"Message {sel}: {e}")

    time.sleep(1)
    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_945_filled.png")
    print(f"\nTitle filled: {title_filled}")
    print(f"Message filled: {msg_filled}")
    print("Screenshot saved: .screenshot_945_filled.png")

    if title_filled and msg_filled:
        # Click Send
        send_selectors = [
            'button:has-text("Send")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]
        for sel in send_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f"\n>>> CLICKING SEND via {sel} <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(
                        path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_945_sent.png"
                    )
                    print("SENT! Screenshot saved: .screenshot_945_sent.png")
                    break
            except Exception as e:
                print(f"Send {sel}: {e}")
    else:
        print("\nCould not fill all fields - check screenshot")

    pw.stop()


if __name__ == "__main__":
    main()
