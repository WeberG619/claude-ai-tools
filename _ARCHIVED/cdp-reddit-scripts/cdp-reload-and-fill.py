"""Reload Reddit submit page and fill form cleanly via CDP"""
import asyncio
import json
import urllib.request
import base64

def get_ws_url(port=9222):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page" and "reddit" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")

async def main():
    import websockets
    ws_url = get_ws_url()
    msg_id = 1

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        async def send_cdp(method, params=None):
            nonlocal msg_id
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            msg_id += 1
            await ws.send(json.dumps(msg))
            # Wait for matching response (skip events)
            while True:
                result = json.loads(await ws.recv())
                if "id" in result and result["id"] == msg_id - 1:
                    return result
                # It's an event, skip it

        # Step 1: Navigate to fresh submit page
        print("Navigating to fresh submit page...")
        await send_cdp("Page.navigate", {"url": "https://www.reddit.com/r/ClaudeAI/submit/?type=TEXT"})

        # Wait for page to load
        await asyncio.sleep(4)

        # Step 2: Wait for title element to be available
        print("Waiting for form to load...")
        for attempt in range(10):
            check_js = """
            (function() {
                var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
                var bodyComp = document.querySelector('shreddit-composer[name="body"]');
                return JSON.stringify({
                    title: !!(titleComp && titleComp.shadowRoot && titleComp.shadowRoot.querySelector('textarea')),
                    body: !!(bodyComp && bodyComp.querySelector('[contenteditable="true"]'))
                });
            })()
            """
            r = await send_cdp("Runtime.evaluate", {"expression": check_js, "returnByValue": True})
            val = r.get("result", {}).get("result", {}).get("value", "{}")
            state = json.loads(val)
            if state.get("title") and state.get("body"):
                print(f"Form ready on attempt {attempt + 1}")
                break
            await asyncio.sleep(1)
        else:
            print("Form not ready after 10 attempts")
            return

        # Step 3: Set the title
        print("Setting title...")
        title_js = """
        (function() {
            var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
            var textarea = titleComp.shadowRoot.querySelector('textarea');
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeSetter.call(textarea, "I gave Claude Code persistent memory, 17 sub-agents, and desktop automation - here's how");
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            return textarea.value;
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": title_js, "returnByValue": True})
        print(f"Title: {r.get('result', {}).get('result', {}).get('value', 'FAILED')[:60]}")

        # Step 4: Click into body area then use CDP Input.insertText
        print("Setting body...")

        # First, click the body to focus it
        click_js = """
        (function() {
            var bodyComp = document.querySelector('shreddit-composer[name="body"]');
            var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
            bodyDiv.focus();
            bodyDiv.click();
            var rect = bodyDiv.getBoundingClientRect();
            return JSON.stringify({x: rect.x + 20, y: rect.y + 20, focused: document.activeElement === bodyDiv || bodyDiv.contains(document.activeElement)});
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": click_js, "returnByValue": True})
        pos = json.loads(r["result"]["result"]["value"])
        print(f"Body focus: {pos}")

        # Use mouse click via CDP for real focus
        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": int(pos["x"]), "y": int(pos["y"]),
            "button": "left", "clickCount": 1
        })
        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": int(pos["x"]), "y": int(pos["y"]),
            "button": "left", "clickCount": 1
        })
        await asyncio.sleep(0.5)

        # Now type the body text using Input.insertText
        body_text = """I kept hitting the same walls with Claude Code:

\u2022 It forgets everything between sessions
\u2022 It can't touch desktop apps (Excel, Word, browser)
\u2022 No way to enforce safety checks before destructive actions
\u2022 Sub-agents start from zero context every time

So I built Agent Forge - an open-source framework that plugs into Claude Code using only its native extension points (CLAUDE.md, MCP servers, hooks). No forks, no patches.

What it actually does:

\u2022 Persistent memory via SQLite - corrections, decisions, and preferences survive across sessions
\u2022 17 specialized sub-agents (code review, architecture, security, DevOps, etc.)
\u2022 Desktop automation - Excel, Word, PowerPoint, browser control
\u2022 Common sense engine that checks actions against past mistakes before executing
\u2022 22 slash commands for real workflows

The whole thing installs with git clone + ./install.sh and works immediately.

I built this because I'm a BIM automation specialist, not a software engineer. I needed AI agents that actually work in real professional workflows - not demos, not toys.

I want honest feedback. Tell me it's good or tell me it's garbage. My opinion doesn't count - I built it.

GitHub: https://github.com/WeberG619/agent-forge

Full write-up: https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae

Happy to answer any questions about the implementation."""

        r = await send_cdp("Input.insertText", {"text": body_text})
        print(f"Insert: {json.dumps(r)}")

        await asyncio.sleep(1)

        # Verify
        verify_js = """
        (function() {
            var bodyComp = document.querySelector('shreddit-composer[name="body"]');
            var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
            var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
            var textarea = titleComp.shadowRoot.querySelector('textarea');
            return JSON.stringify({
                titleLen: textarea.value.length,
                bodyTextLen: bodyDiv.innerText.length,
                bodyPreview: bodyDiv.innerText.substring(0, 100)
            });
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": verify_js, "returnByValue": True})
        val = json.loads(r["result"]["result"]["value"])
        print(f"Verify - Title len: {val['titleLen']}, Body len: {val['bodyTextLen']}")
        print(f"Body preview: {val['bodyPreview']}")

        # Take screenshot
        await send_cdp("Page.bringToFront")
        scroll_js = "window.scrollTo(0, 0); 'ok';"
        await send_cdp("Runtime.evaluate", {"expression": scroll_js})
        await asyncio.sleep(0.3)

        result = await send_cdp("Page.captureScreenshot", {"format": "png"})
        img_data = base64.b64decode(result["result"]["data"])
        with open(r"D:\_CLAUDE-TOOLS\reddit-screenshot.png", "wb") as f:
            f.write(img_data)
        print("Screenshot saved")

asyncio.run(main())
