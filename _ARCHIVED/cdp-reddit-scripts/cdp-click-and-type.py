"""Click on body area via CDP mouse events, then insert text"""
import asyncio
import json
import urllib.request

def get_ws_url(port=9222):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")

async def main():
    import websockets

    ws_url = get_ws_url()
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        async def send_cdp(method, params=None):
            nonlocal msg_id
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            msg_id += 1
            await ws.send(json.dumps(msg))
            result = json.loads(await ws.recv())
            return result

        # Step 1: Get the position of the body editor
        pos_js = """
        (function() {
            var bodyComp = document.querySelector('shreddit-composer[name="body"]');
            if (!bodyComp) return JSON.stringify({error: 'no body'});
            var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
            if (!bodyDiv) return JSON.stringify({error: 'no editable'});
            var rect = bodyDiv.getBoundingClientRect();
            return JSON.stringify({x: rect.x + 50, y: rect.y + 30, w: rect.width, h: rect.height});
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": pos_js, "returnByValue": True})
        pos = json.loads(r["result"]["result"]["value"])
        print(f"Body position: {pos}")

        if "error" in pos:
            print(f"Error: {pos['error']}")
            return

        # Step 2: Click on body area using CDP mouse events
        x, y = pos["x"], pos["y"]

        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x, "y": y,
            "button": "left",
            "clickCount": 1
        })
        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x, "y": y,
            "button": "left",
            "clickCount": 1
        })

        await asyncio.sleep(0.3)

        # Step 3: Now try Input.insertText
        body_text = """I kept hitting the same walls with Claude Code:

- It forgets everything between sessions
- It can't touch desktop apps (Excel, Word, browser)
- No way to enforce safety checks before destructive actions
- Sub-agents start from zero context every time

So I built Agent Forge - an open-source framework that plugs into Claude Code using only its native extension points (CLAUDE.md, MCP servers, hooks). No forks, no patches.

What it actually does:

- Persistent memory via SQLite - corrections, decisions, and preferences survive across sessions
- 17 specialized sub-agents (code review, architecture, security, DevOps, etc.)
- Desktop automation - Excel, Word, PowerPoint, browser control
- Common sense engine that checks actions against past mistakes before executing
- 22 slash commands for real workflows

The whole thing installs with `git clone` + `./install.sh` and works immediately.

I built this because I'm a BIM automation specialist, not a software engineer. I needed AI agents that actually work in real professional workflows - not demos, not toys.

I want honest feedback. Tell me it's good or tell me it's garbage. My opinion doesn't count - I built it.

GitHub: https://github.com/WeberG619/agent-forge

Full write-up: https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae

Happy to answer any questions about the implementation."""

        r = await send_cdp("Input.insertText", {"text": body_text})
        print(f"Insert result: {json.dumps(r)}")

        await asyncio.sleep(0.5)

        # Step 4: Verify
        verify_js = """
        (function() {
            var bodyComp = document.querySelector('shreddit-composer[name="body"]');
            if (!bodyComp) return 'no body comp';
            var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
            if (!bodyDiv) return 'no editable';
            return 'len=' + bodyDiv.textContent.length + ' preview=' + bodyDiv.textContent.substring(0, 100);
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": verify_js, "returnByValue": True})
        print(f"Verify: {r.get('result', {}).get('result', {}).get('value', 'unknown')}")

asyncio.run(main())
