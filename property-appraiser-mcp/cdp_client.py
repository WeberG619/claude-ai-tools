"""
CDP (Chrome DevTools Protocol) browser client.

Connects to an already-running Chrome/Edge instance via its debugging port.
Provides a simple async API for navigation, JS evaluation, and DOM interaction.

Requirements:
- Chrome/Edge running with --remote-debugging-port=9222
- websockets and aiohttp Python packages
"""

import asyncio
import json
import logging
from typing import Any, Optional

import aiohttp
import websockets

logger = logging.getLogger(__name__)

CDP_HOST = "localhost"
CDP_PORT = 9222


class CDPError(Exception):
    """Error from CDP protocol."""
    pass


class CDPPage:
    """A browser tab controlled via CDP WebSocket."""

    def __init__(self, ws_url: str, target_id: str):
        self._ws_url = ws_url
        self._target_id = target_id
        self._ws = None
        self._msg_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Open WebSocket connection to the tab."""
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=50 * 1024 * 1024,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self._send("Page.enable")
        await self._send("Runtime.enable")

    async def _read_loop(self):
        """Background task reading WebSocket messages."""
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._pending:
                    fut = self._pending[msg_id]
                    if not fut.done():
                        fut.set_result(msg)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.debug(f"CDP read loop error: {e}")
        finally:
            # Resolve any pending futures so callers don't hang
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(CDPError("Connection closed"))

    async def _send(self, method: str, params: Optional[dict] = None, timeout: float = 30.0) -> dict:
        """Send a CDP command and wait for response."""
        self._msg_id += 1
        msg_id = self._msg_id

        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[msg_id] = future

        await self._ws.send(json.dumps(message))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(msg_id, None)

        if "error" in result:
            raise CDPError(result["error"].get("message", "Unknown CDP error"))

        return result.get("result", {})

    async def goto(self, url: str, timeout: float = 30.0):
        """Navigate to a URL and wait for the page to load."""
        await self._send("Page.navigate", {"url": url}, timeout=timeout)
        try:
            await self.wait_for_function(
                "document.readyState === 'complete'",
                timeout_ms=int(timeout * 1000),
            )
        except (asyncio.TimeoutError, CDPError):
            logger.debug(f"Page load wait timed out for {url}, continuing...")
        await asyncio.sleep(1.0)

    async def evaluate(self, expression: str, timeout: float = 30.0) -> Any:
        """Execute JavaScript and return the result."""
        result = await self._send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
            timeout=timeout,
        )

        remote_obj = result.get("result", {})

        if remote_obj.get("subtype") == "error":
            desc = remote_obj.get("description", "Unknown JS error")
            raise CDPError(f"JS Error: {desc}")

        if remote_obj.get("type") == "undefined":
            return None

        return remote_obj.get("value")

    async def wait(self, ms: int):
        """Wait for specified milliseconds."""
        await asyncio.sleep(ms / 1000.0)

    async def wait_for_function(self, js_condition: str, timeout_ms: int = 15000, poll_ms: int = 250):
        """Poll until a JS expression returns truthy."""
        deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
        while asyncio.get_event_loop().time() < deadline:
            try:
                result = await self.evaluate(js_condition, timeout=5.0)
                if result:
                    return result
            except CDPError:
                pass
            await asyncio.sleep(poll_ms / 1000.0)
        raise asyncio.TimeoutError(f"wait_for_function timed out after {timeout_ms}ms")

    async def get_text(self, selector: str = "body") -> str:
        """Get innerText of an element."""
        sel_json = json.dumps(selector)
        result = await self.evaluate(
            f"(document.querySelector({sel_json}) || document.body).innerText || ''"
        )
        return result or ""

    async def get_html(self, selector: str = "html") -> str:
        """Get outerHTML of an element."""
        sel_json = json.dumps(selector)
        result = await self.evaluate(
            f"(document.querySelector({sel_json}) || document.documentElement).outerHTML || ''"
        )
        return result or ""

    async def click(self, selector: str) -> bool:
        """Click an element by CSS selector."""
        sel_json = json.dumps(selector)
        return bool(await self.evaluate(f"""
            (() => {{
                const el = document.querySelector({sel_json});
                if (el) {{ el.click(); return true; }}
                return false;
            }})()
        """))

    async def fill(self, selector: str, value: str) -> bool:
        """Clear and set an input field's value."""
        sel_json = json.dumps(selector)
        val_json = json.dumps(value)
        return bool(await self.evaluate(f"""
            (() => {{
                const el = document.querySelector({sel_json});
                if (!el) return false;
                el.focus();
                el.value = '';
                el.value = {val_json};
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return true;
            }})()
        """))

    async def fill_first_visible(self, selectors: list[str], value: str) -> bool:
        """Try multiple selectors; fill the first visible match."""
        sels_json = json.dumps(selectors)
        val_json = json.dumps(value)
        return bool(await self.evaluate(f"""
            (() => {{
                const sels = {sels_json};
                const val = {val_json};
                for (const sel of sels) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        el.focus();
                        el.value = '';
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }}
                }}
                return false;
            }})()
        """))

    async def click_first_visible(self, selectors: list[str]) -> bool:
        """Try multiple selectors; click the first visible match."""
        sels_json = json.dumps(selectors)
        return bool(await self.evaluate(f"""
            (() => {{
                const sels = {sels_json};
                for (const sel of sels) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }})()
        """))

    async def select_option(self, selector: str, label: str) -> bool:
        """Select a dropdown option by visible text."""
        sel_json = json.dumps(selector)
        lbl_json = json.dumps(label)
        return bool(await self.evaluate(f"""
            (() => {{
                const sel = document.querySelector({sel_json});
                if (!sel) return false;
                for (const opt of sel.options) {{
                    if (opt.text.trim() === {lbl_json} || opt.text.includes({lbl_json})) {{
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }}
                }}
                return false;
            }})()
        """))

    async def press_enter(self):
        """Dispatch Enter key event on the focused element."""
        await self.evaluate("""
            (() => {
                const el = document.activeElement || document.body;
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                // Also try submitting parent form
                const form = el.closest('form');
                if (form) form.submit();
            })()
        """)

    async def close(self):
        """Close this tab and clean up."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        try:
            async with aiohttp.ClientSession() as session:
                await session.get(
                    f"http://{CDP_HOST}:{CDP_PORT}/json/close/{self._target_id}",
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception:
            pass


class CDPBrowser:
    """Manages connection to a Chrome instance via CDP."""

    def __init__(self, host: str = CDP_HOST, port: int = CDP_PORT):
        self.host = host
        self.port = port
        self._pages: list[CDPPage] = []

    async def check_connection(self) -> bool:
        """Check if Chrome is reachable on the debugging port."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.host}:{self.port}/json/version",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"CDP: Connected to {data.get('Browser', 'Chrome')}")
                        return True
        except Exception as e:
            logger.error(f"CDP: Chrome not reachable on port {self.port}: {e}")
        return False

    async def new_page(self) -> CDPPage:
        """Open a new browser tab and return a CDPPage."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{self.host}:{self.port}/json/new?about:blank",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise CDPError(f"Failed to create new tab: HTTP {resp.status}")
                tab_info = await resp.json()

        ws_url = tab_info.get("webSocketDebuggerUrl")
        target_id = tab_info.get("id")

        if not ws_url:
            raise CDPError("No WebSocket URL returned for new tab")

        page = CDPPage(ws_url, target_id)
        await page.connect()
        self._pages.append(page)
        return page

    async def close_all(self):
        """Close all pages opened by this browser instance."""
        for page in self._pages:
            try:
                await page.close()
            except Exception:
                pass
        self._pages.clear()
