"""
CDP WebSocket Client — connects to Chrome/Edge DevTools Protocol via WebSocket.
Handles connection, reconnection, and all CDP commands.
Runs on Windows Python — connects to localhost directly.
"""

import asyncio
import base64
import json
import os
import urllib.request
import urllib.error
from typing import Any, Optional

import websockets
from websockets.exceptions import ConnectionClosed


class CDPError(Exception):
    """Error from CDP protocol."""
    pass


class CDPClient:
    """Chrome/Edge DevTools Protocol client over WebSocket."""

    def __init__(self, port: int = None):
        self._ws = None
        self._msg_id = 0
        self._host = "127.0.0.1"
        self._port = port or int(os.environ.get("CDP_PORT", "9222"))

    @property
    def port(self):
        return self._port

    # ── Connection management ────────────────────────────────────────

    async def connect(self, tab_index: int = 0) -> str:
        """Connect to a browser tab. Returns tab title."""
        if self._ws and not self._ws.close_code:
            await self._ws.close()

        targets = self._get_targets()

        if not targets:
            raise CDPError(
                f"No page targets found on {self._host}:{self._port}. "
                "Is the browser running with --remote-debugging-port?"
            )

        if tab_index >= len(targets):
            tab_index = 0

        target = targets[tab_index]
        ws_url = target["webSocketDebuggerUrl"]

        self._ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)
        return target.get("title", "Unknown")

    async def ensure_connected(self, tab_index: int = 0) -> None:
        """Ensure we have a live connection, reconnecting if needed."""
        if self._ws and not self._ws.close_code:
            try:
                await self._ws.ping()
                return
            except Exception:
                pass

        await self.connect(tab_index)

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    def _get_targets(self) -> list[dict]:
        """Get page targets from CDP HTTP endpoint."""
        url = f"http://{self._host}:{self._port}/json"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                targets = json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise CDPError(
                f"Cannot reach browser CDP at {self._host}:{self._port}. "
                f"Error: {e}. "
                f"Make sure the browser is running with --remote-debugging-port={self._port}"
            )

        return [t for t in targets if t.get("type") == "page"]

    def get_all_tabs(self) -> list[dict]:
        """Get all open tabs (page targets) from CDP."""
        targets = self._get_targets()
        return [
            {
                "index": i,
                "title": t.get("title", ""),
                "url": t.get("url", ""),
            }
            for i, t in enumerate(targets)
        ]

    # ── CDP command execution ────────────────────────────────────────

    async def send(self, method: str, params: dict = None, timeout: float = 30) -> dict:
        """Send a CDP command and wait for response."""
        if not self._ws or self._ws.close_code is not None:
            raise CDPError("Not connected. Call connect() first.")

        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        await self._ws.send(json.dumps(msg))

        # Wait for response with matching id
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise CDPError(f"Timeout waiting for response to {method}")

            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                raise CDPError(f"Timeout waiting for response to {method}")
            except ConnectionClosed:
                raise CDPError("WebSocket connection closed unexpectedly")

            response = json.loads(raw)
            if response.get("id") == self._msg_id:
                if "error" in response:
                    err = response["error"]
                    raise CDPError(f"CDP error: {err.get('message', err)}")
                return response.get("result", {})

    # ── High-level operations ────────────────────────────────────────

    async def evaluate(self, expression: str, return_by_value: bool = True) -> Any:
        """Execute JavaScript and return the result."""
        await self.ensure_connected()
        result = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        })

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            text = exc.get("text", "")
            if "exception" in exc:
                text = exc["exception"].get("description", text)
            raise CDPError(f"JS error: {text}")

        val = result.get("result", {})
        if "value" in val:
            return val["value"]
        return val.get("description", str(val))

    def create_new_tab(self, url: str = "about:blank") -> dict:
        """Create a new tab via CDP HTTP API. Falls back to PUT method for newer Chrome."""
        import urllib.parse
        api_url = f"http://{self._host}:{self._port}/json/new?{urllib.parse.quote(url, safe='')}"

        # Try GET first (older Chrome), then PUT (newer Chrome)
        for method in ["GET", "PUT"]:
            try:
                req = urllib.request.Request(api_url, method=method)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code == 405:
                    continue  # Try next method
                raise CDPError(f"Failed to create new tab: {e}")
            except Exception as e:
                raise CDPError(f"Failed to create new tab: {e}")

        raise CDPError("Failed to create new tab: all HTTP methods returned 405")

    async def navigate(self, url: str) -> dict:
        """Navigate to a URL. Returns frame info."""
        await self.ensure_connected()
        result = await self.send("Page.navigate", {"url": url})
        # Wait for load
        try:
            await self.send("Page.enable")
            await asyncio.sleep(1)
        except Exception:
            pass
        return result

    async def click(self, selector: str, text: str = None, index: int = 0) -> str:
        """Click an element by CSS selector, optionally filtering by text content."""
        await self.ensure_connected()

        if text:
            js = f"""
            (() => {{
                const els = [...document.querySelectorAll({json.dumps(selector)})];
                const match = els.filter(e => e.textContent.includes({json.dumps(text)}))[{index}];
                if (!match) return 'ERROR: No element matching selector ' + {json.dumps(selector)} + ' with text ' + {json.dumps(text)};
                match.scrollIntoView({{block: 'center'}});
                match.click();
                return 'Clicked: ' + match.tagName + ' "' + match.textContent.trim().substring(0, 80) + '"';
            }})()
            """
        else:
            js = f"""
            (() => {{
                const els = document.querySelectorAll({json.dumps(selector)});
                const el = els[{index}];
                if (!el) return 'ERROR: No element matching selector ' + {json.dumps(selector)} + ' (found ' + els.length + ' elements)';
                el.scrollIntoView({{block: 'center'}});
                el.click();
                return 'Clicked: ' + el.tagName + ' "' + el.textContent.trim().substring(0, 80) + '"';
            }})()
            """

        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def fill(self, selector: str, text: str, clear_first: bool = True) -> str:
        """Fill an input or textarea element."""
        await self.ensure_connected()

        clear_js = "el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true}));" if clear_first else ""

        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return 'ERROR: No element matching selector ' + {json.dumps(selector)};
            el.scrollIntoView({{block: 'center'}});
            el.focus();
            {clear_js}
            el.value = {json.dumps(text)};
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return 'Filled: ' + el.tagName + '[' + (el.name || el.id || el.type) + '] with ' + {json.dumps(text)}.substring(0, 50);
        }})()
        """
        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def select_option(self, selector: str, value: str = None, label: str = None) -> str:
        """Select a dropdown option by value or visible label."""
        await self.ensure_connected()

        if label:
            match_js = f"""
            const opt = [...el.options].find(o => o.textContent.trim() === {json.dumps(label)});
            if (!opt) return 'ERROR: No option with label ' + {json.dumps(label)};
            el.value = opt.value;
            """
        elif value:
            match_js = f"el.value = {json.dumps(value)};"
        else:
            raise CDPError("Must provide either value or label")

        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return 'ERROR: No element matching selector ' + {json.dumps(selector)};
            if (el.tagName !== 'SELECT') return 'ERROR: Element is not a SELECT';
            {match_js}
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return 'Selected: ' + el.options[el.selectedIndex].textContent.trim();
        }})()
        """
        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def check(self, selector: str, checked: bool = True) -> str:
        """Check or uncheck a checkbox."""
        await self.ensure_connected()

        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return 'ERROR: No element matching selector ' + {json.dumps(selector)};
            if (el.type !== 'checkbox' && el.type !== 'radio') return 'ERROR: Element is not a checkbox/radio';
            if (el.checked !== {json.dumps(checked)}) {{
                el.checked = {json.dumps(checked)};
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                el.dispatchEvent(new Event('click', {{bubbles: true}}));
            }}
            return 'Checkbox ' + (el.name || el.id) + ' is now ' + (el.checked ? 'checked' : 'unchecked');
        }})()
        """
        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def get_text(self, selector: str = "body", max_length: int = 5000) -> str:
        """Get text content of elements matching selector."""
        await self.ensure_connected()

        js = f"""
        (() => {{
            const els = document.querySelectorAll({json.dumps(selector)});
            if (els.length === 0) return 'ERROR: No elements matching ' + {json.dumps(selector)};
            const texts = [...els].map(el => el.textContent.trim()).filter(t => t);
            return texts.join('\\n').substring(0, {max_length});
        }})()
        """
        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def get_html(self, selector: str = None, outer: bool = True) -> str:
        """Get HTML of page or specific element."""
        await self.ensure_connected()

        if selector:
            prop = "outerHTML" if outer else "innerHTML"
            js = f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return 'ERROR: No element matching ' + {json.dumps(selector)};
                return el.{prop};
            }})()
            """
        else:
            js = "document.documentElement.outerHTML"

        result = await self.evaluate(js)
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise CDPError(result)
        return result

    async def screenshot(self, selector: str = None, full_page: bool = False) -> bytes:
        """Take a screenshot via CDP. Returns PNG bytes."""
        await self.ensure_connected()

        if selector:
            js = f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {{x: rect.x, y: rect.y, width: rect.width, height: rect.height}};
            }})()
            """
            box = await self.evaluate(js)
            if box is None:
                raise CDPError(f"No element matching {selector}")

            result = await self.send("Page.captureScreenshot", {
                "format": "png",
                "clip": {
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                    "scale": 1,
                },
            })
        elif full_page:
            metrics = await self.evaluate(
                "({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})"
            )
            result = await self.send("Page.captureScreenshot", {
                "format": "png",
                "clip": {
                    "x": 0,
                    "y": 0,
                    "width": metrics["width"],
                    "height": metrics["height"],
                    "scale": 1,
                },
            })
        else:
            result = await self.send("Page.captureScreenshot", {"format": "png"})

        return base64.b64decode(result["data"])

    async def wait_for(self, selector: str = None, text: str = None, timeout: float = 10) -> str:
        """Wait for element to appear or text to be present on page."""
        await self.ensure_connected()

        deadline = asyncio.get_event_loop().time() + timeout
        poll_interval = 0.3

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                target = selector or text
                raise CDPError(f"Timeout waiting for: {target}")

            if selector:
                js = f"!!document.querySelector({json.dumps(selector)})"
                found = await self.evaluate(js)
                if found:
                    return f"Found element: {selector}"

            if text:
                js = f"document.body.textContent.includes({json.dumps(text)})"
                found = await self.evaluate(js)
                if found:
                    return f"Found text: {text}"

            await asyncio.sleep(min(poll_interval, remaining))


# Singleton clients per port
_clients: dict[int, CDPClient] = {}


def get_client(port: int = None) -> CDPClient:
    """Get or create a CDP client for the given port."""
    port = port or int(os.environ.get("CDP_PORT", "9222"))
    if port not in _clients:
        _clients[port] = CDPClient(port=port)
    return _clients[port]
