#!/usr/bin/env python3
"""
CDP Browser MCP Server — Reliable browser automation via Chrome DevTools Protocol.
Runs on Windows Python. Supports both Chrome and Edge.
Provides tools for navigation, interaction, screenshots, and more.
"""

import asyncio
import base64
import sys
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Local imports
sys.path.insert(0, os.path.dirname(__file__))
from cdp_client import CDPClient, CDPError, get_client
from chrome_launcher import (
    ensure_chrome_cdp, ensure_edge_cdp, check_cdp_available,
    get_status, CDP_PORT, EDGE_CDP_PORT,
)

mcp = FastMCP("cdp-browser")


# Note: All tools are async since FastMCP runs its own event loop.
# Using _run(loop.run_until_complete()) would fail with "This event loop is already running".


async def _auto_connect(client: CDPClient, tab_index: int = 0) -> None:
    """Ensure client is connected, auto-launching browser if needed."""
    try:
        await client.ensure_connected(tab_index)
        return
    except CDPError:
        pass

    # Try to ensure the browser is running with CDP
    port = client.port
    if port == EDGE_CDP_PORT:
        result = ensure_edge_cdp()
    else:
        result = ensure_chrome_cdp()

    if not result.get("ready") and not result.get("success"):
        raise CDPError(result.get("message", "Failed to connect to browser"))

    # Now connect
    await client.connect(tab_index)


# ── Tool 1: cdp_status ──────────────────────────────────────────────

@mcp.tool()
def cdp_status() -> str:
    """
    Check Chrome and Edge CDP connection status. Lists open tabs for each.
    Auto-launches Chrome with CDP if not running.
    """
    try:
        status = get_status()
        lines = ["CDP Browser Status:"]

        for name, info in status.items():
            if info["available"]:
                lines.append(f"\n{name.upper()} (port {info['port']}): CONNECTED - {info['browser']}")
                try:
                    client = get_client(port=info["port"])
                    tabs = client.get_all_tabs()
                    for tab in tabs:
                        lines.append(f"  [{tab['index']}] {tab['title'][:80]}")
                        lines.append(f"      {tab['url'][:120]}")
                except Exception:
                    pass
            else:
                lines.append(f"\n{name.upper()} (port {info['port']}): NOT CONNECTED")

        return "\n".join(lines)
    except Exception as e:
        return f"CDP Status Error: {e}"


# ── Tool 2: cdp_list_tabs ───────────────────────────────────────────

@mcp.tool()
async def cdp_list_tabs(browser: str = "chrome") -> str:
    """
    List all open tabs with their URLs and titles.

    Args:
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client)
        tabs = client.get_all_tabs()
        if not tabs:
            return f"No tabs open in {browser}."
        lines = [f"Open tabs in {browser} ({len(tabs)}):"]
        for tab in tabs:
            lines.append(f"  [{tab['index']}] {tab['title'][:80]}")
            lines.append(f"      {tab['url'][:120]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tabs: {e}"


# ── Tool 3: cdp_navigate ────────────────────────────────────────────

@mcp.tool()
async def cdp_navigate(url: str, tab_index: int = 0, new_tab: bool = False, browser: str = "chrome") -> str:
    """
    Navigate to a URL in Chrome or Edge.

    Args:
        url: The URL to navigate to
        tab_index: Which tab to navigate (0-based index, default: 0)
        new_tab: If True, open URL in a new tab instead
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)

        if new_tab:
            await _auto_connect(client, tab_index=0)
            target = client.create_new_tab(url)
            return f"Opened new tab in {browser}: {url} (title: {target.get('title', 'loading...')})"

        await _auto_connect(client, tab_index=tab_index)
        await client.navigate(url)

        try:
            title = await client.evaluate("document.title")
            return f"Navigated to: {url}\nTitle: {title}"
        except Exception:
            return f"Navigated to: {url}"
    except Exception as e:
        return f"Navigation error: {e}"


# ── Tool 4: cdp_evaluate ────────────────────────────────────────────

@mcp.tool()
async def cdp_evaluate(script: str, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Execute JavaScript on the current page and return the result.

    Args:
        script: JavaScript code to execute
        tab_index: Which tab to execute in (0-based index, default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.evaluate(script)
        if isinstance(result, str):
            return result
        import json
        return json.dumps(result, indent=2, default=str)
    except CDPError as e:
        return f"JS Error: {e}"
    except Exception as e:
        return f"Evaluate error: {e}"


# ── Tool 5: cdp_click ───────────────────────────────────────────────

@mcp.tool()
async def cdp_click(selector: str, text: str = None, index: int = 0, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Click an element on the page by CSS selector.

    Args:
        selector: CSS selector (e.g., "button.submit", "#login-btn", "a")
        text: Optional text content to filter elements
        index: If multiple elements match, click the Nth one (0-based)
        tab_index: Which tab to operate in (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.click(selector, text=text, index=index)
        return result
    except CDPError as e:
        return f"Click error: {e}"
    except Exception as e:
        return f"Click error: {e}"


# ── Tool 6: cdp_fill ────────────────────────────────────────────────

@mcp.tool()
async def cdp_fill(selector: str, text: str, clear_first: bool = True, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Fill an input or textarea element with text.

    Args:
        selector: CSS selector for the input (e.g., "#email", "input[name='username']")
        text: The text to type into the field
        clear_first: Whether to clear existing text first (default: True)
        tab_index: Which tab to operate in (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.fill(selector, text, clear_first=clear_first)
        return result
    except CDPError as e:
        return f"Fill error: {e}"
    except Exception as e:
        return f"Fill error: {e}"


# ── Tool 7: cdp_select ──────────────────────────────────────────────

@mcp.tool()
async def cdp_select(selector: str, value: str = None, label: str = None, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Select an option in a dropdown (select element).

    Args:
        selector: CSS selector for the select element
        value: Option value to select (use this OR label)
        label: Visible option text to select (use this OR value)
        tab_index: Which tab to operate in (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.select_option(selector, value=value, label=label)
        return result
    except CDPError as e:
        return f"Select error: {e}"
    except Exception as e:
        return f"Select error: {e}"


# ── Tool 8: cdp_check ───────────────────────────────────────────────

@mcp.tool()
async def cdp_check(selector: str, checked: bool = True, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Check or uncheck a checkbox element.

    Args:
        selector: CSS selector for the checkbox
        checked: True to check, False to uncheck (default: True)
        tab_index: Which tab to operate in (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.check(selector, checked=checked)
        return result
    except CDPError as e:
        return f"Check error: {e}"
    except Exception as e:
        return f"Check error: {e}"


# ── Tool 9: cdp_get_text ────────────────────────────────────────────

@mcp.tool()
async def cdp_get_text(selector: str = "body", max_length: int = 5000, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Get the text content of elements matching a CSS selector.

    Args:
        selector: CSS selector (default: "body" for full page text)
        max_length: Maximum characters to return (default: 5000)
        tab_index: Which tab to read from (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.get_text(selector, max_length=max_length)
        return result
    except CDPError as e:
        return f"Get text error: {e}"
    except Exception as e:
        return f"Get text error: {e}"


# ── Tool 10: cdp_get_html ───────────────────────────────────────────

@mcp.tool()
async def cdp_get_html(selector: str = None, outer: bool = True, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Get the HTML of the page or a specific element.

    Args:
        selector: CSS selector for specific element (default: None for full page)
        outer: If True, outerHTML; if False, innerHTML
        tab_index: Which tab to read from (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.get_html(selector=selector, outer=outer)
        if len(result) > 50000:
            result = result[:50000] + f"\n... (truncated, {len(result)} chars total)"
        return result
    except CDPError as e:
        return f"Get HTML error: {e}"
    except Exception as e:
        return f"Get HTML error: {e}"


# ── Tool 11: cdp_screenshot ─────────────────────────────────────────

@mcp.tool()
async def cdp_screenshot(selector: str = None, full_page: bool = False, tab_index: int = 0, browser: str = "chrome") -> list:
    """
    Take a screenshot of the current page via CDP.
    Returns the image directly (not a file path).

    Args:
        selector: CSS selector to screenshot specific element (default: visible viewport)
        full_page: If True, capture the entire scrollable page
        tab_index: Which tab to screenshot (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        png_bytes = await client.screenshot(selector=selector, full_page=full_page)

        b64 = base64.b64encode(png_bytes).decode("ascii")
        from mcp.types import TextContent, ImageContent
        return [
            TextContent(type="text", text=f"Screenshot captured ({len(png_bytes)} bytes) from {browser}"),
            ImageContent(type="image", data=b64, mimeType="image/png"),
        ]
    except CDPError as e:
        return f"Screenshot error: {e}"
    except Exception as e:
        return f"Screenshot error: {e}"


# ── Tool 12: cdp_wait ───────────────────────────────────────────────

@mcp.tool()
async def cdp_wait(selector: str = None, text: str = None, timeout: float = 10, tab_index: int = 0, browser: str = "chrome") -> str:
    """
    Wait for an element to appear or text to be present on the page.

    Args:
        selector: CSS selector to wait for
        text: Text string to wait for on the page
        timeout: Maximum seconds to wait (default: 10)
        tab_index: Which tab to wait in (default: 0)
        browser: Which browser - "chrome" or "edge" (default: "chrome")
    """
    if not selector and not text:
        await asyncio.sleep(timeout)
        return f"Waited {timeout} seconds"

    try:
        port = EDGE_CDP_PORT if browser.lower() == "edge" else CDP_PORT
        client = get_client(port=port)
        await _auto_connect(client, tab_index=tab_index)
        result = await client.wait_for(selector=selector, text=text, timeout=timeout)
        return result
    except CDPError as e:
        return f"Wait error: {e}"
    except Exception as e:
        return f"Wait error: {e}"


# ── Tool 13: cdp_launch_chrome ───────────────────────────────────────

@mcp.tool()
def cdp_launch_chrome(url: str = None) -> str:
    """
    Launch Chrome with CDP enabled (or confirm it's already running).
    Uses a dedicated profile so it works even if Chrome is already open.

    Args:
        url: Optional URL to open on launch
    """
    result = ensure_chrome_cdp(url=url)
    return result.get("message", str(result))


# ── Tool 14: cdp_launch_edge ────────────────────────────────────────

@mcp.tool()
def cdp_launch_edge(url: str = None) -> str:
    """
    Launch Edge with CDP enabled (or confirm it's already running).
    Uses a dedicated profile so it works even if Edge is already open.

    Args:
        url: Optional URL to open on launch
    """
    result = ensure_edge_cdp(url=url)
    return result.get("message", str(result))


# ── Helpers ──────────────────────────────────────────────────────────

def _js_str(s: str) -> str:
    """Escape a string for safe embedding in JavaScript."""
    import json
    return json.dumps(s)


# ── Entry point ──────────────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
