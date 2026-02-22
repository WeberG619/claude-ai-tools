#!/usr/bin/env python3
"""
Playwright Browser MCP Server
Element-based web automation - no pixel guessing.

Connects to existing Chrome via CDP or launches a managed browser.
Uses Playwright's locator API for precise, reliable interactions.
"""

import asyncio
import base64
import json
import re
import shutil
import sys
import os
import subprocess
import time
from typing import Optional, Dict, Any, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

# ---------------------------------------------------------------------------
# Playwright imports (async API)
# ---------------------------------------------------------------------------
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------
server = Server("playwright-browser")

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

# Browser paths (Chrome and Edge)
BROWSER_PATHS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
}
# Fallback: check both locations for Edge
if not os.path.exists(BROWSER_PATHS["edge"]):
    BROWSER_PATHS["edge"] = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

CHROME_USER_DATA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
EDGE_USER_DATA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data")
CDP_PROFILE_DIR = os.path.join(os.environ.get("TEMP", ""), "chrome-pw-cdp")

# Global state
_playwright = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None


def _find_chrome_profile() -> str:
    """Detect which Chrome profile is active (Profile 1, Default, etc.)."""
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='chrome.exe'", "get", "commandline"],
            capture_output=True, text=True, timeout=10
        )
        m = re.search(r'--profile-directory="?([^"]+)"?', result.stdout)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    # Check Local State for last used profile
    try:
        local_state = os.path.join(CHROME_USER_DATA, "Local State")
        if os.path.exists(local_state):
            with open(local_state, "r") as f:
                data = json.load(f)
            last = data.get("profile", {}).get("last_used", "Default")
            return last
    except Exception:
        pass
    return "Profile 1"


def _copy_session_to_cdp_profile(source_profile: str):
    """Copy cookies and session data from real Chrome profile to CDP profile."""
    src = os.path.join(CHROME_USER_DATA, source_profile)
    dst = os.path.join(CDP_PROFILE_DIR, "Default")
    os.makedirs(dst, exist_ok=True)

    # Copy Local State (encryption keys)
    ls_src = os.path.join(CHROME_USER_DATA, "Local State")
    if os.path.exists(ls_src):
        shutil.copy2(ls_src, CDP_PROFILE_DIR)

    # Copy profile files
    direct_files = [
        "Login Data", "Login Data-journal",
        "Web Data", "Web Data-journal",
        "Preferences", "Secure Preferences",
        "Extension Cookies", "Extension Cookies-journal",
    ]
    for fname in direct_files:
        fpath = os.path.join(src, fname)
        if os.path.exists(fpath):
            shutil.copy2(fpath, os.path.join(dst, fname))

    # Copy Network/Cookies (Chrome 100+)
    net_src = os.path.join(src, "Network")
    net_dst = os.path.join(dst, "Network")
    os.makedirs(net_dst, exist_ok=True)
    for fname in ["Cookies", "Cookies-journal", "Network Persistent State"]:
        fpath = os.path.join(net_src, fname)
        if os.path.exists(fpath):
            shutil.copy2(fpath, os.path.join(net_dst, fname))


def _detect_running_browser() -> str:
    """Detect which browser is currently running (chrome or edge)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        if "chrome.exe" in result.stdout.lower():
            return "chrome"
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq msedge.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        if "msedge.exe" in result.stdout.lower():
            return "edge"
    except Exception:
        pass
    return "chrome"  # default


def _get_browser_process_name(browser: str) -> str:
    return "msedge.exe" if browser == "edge" else "chrome.exe"


def _get_user_data_dir(browser: str) -> str:
    return EDGE_USER_DATA if browser == "edge" else CHROME_USER_DATA


def _launch_browser_cdp(browser: str = None):
    """Launch Chrome or Edge with CDP using a dedicated profile directory."""
    if browser is None:
        browser = _detect_running_browser()

    browser_path = BROWSER_PATHS.get(browser, BROWSER_PATHS["chrome"])
    if not os.path.exists(browser_path):
        # Fallback to whichever exists
        for name, path in BROWSER_PATHS.items():
            if os.path.exists(path):
                browser_path = path
                browser = name
                break

    # Ensure CDP profile has current session cookies
    user_data = _get_user_data_dir(browser)
    if os.path.exists(user_data):
        try:
            profile = _find_chrome_profile()
            _copy_session_to_cdp_profile(profile)
        except Exception:
            pass  # Non-fatal: proceed without session copy

    subprocess.Popen([
        browser_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={CDP_PROFILE_DIR}",
        "about:blank",
    ])


async def _ensure_browser() -> Page:
    """Connect to Chrome/Edge via CDP, starting browser with CDP if needed.

    Handles reconnection if the browser was closed or CDP dropped.
    """
    global _playwright, _browser, _context, _page

    # Fast path: existing page is still alive
    if _page and not _page.is_closed():
        try:
            await _page.title()  # Quick liveness check
            return _page
        except Exception:
            _page = None  # Page died, fall through to reconnect

    if _playwright is None:
        _playwright = await async_playwright().start()

    # Try connecting to existing CDP endpoint
    for attempt in range(2):
        try:
            if _browser:
                try:
                    _browser.close()
                except Exception:
                    pass
            _browser = await _playwright.chromium.connect_over_cdp(CDP_URL, timeout=5000)
            contexts = _browser.contexts
            if contexts:
                _context = contexts[0]
                pages = _context.pages
                if pages:
                    _page = pages[0]
                    return _page
            if _context is None:
                _context = await _browser.new_context()
            _page = await _context.new_page()
            return _page
        except Exception:
            if attempt == 0:
                await asyncio.sleep(1)

    # CDP not available — need to launch a browser with CDP
    browser_type = _detect_running_browser()
    proc_name = _get_browser_process_name(browser_type)

    # Kill existing browser (it's running without CDP)
    try:
        subprocess.run(["taskkill", "/F", "/IM", proc_name],
                       capture_output=True, timeout=10)
    except Exception:
        pass
    await asyncio.sleep(3)

    # Launch with CDP
    _launch_browser_cdp(browser_type)
    await asyncio.sleep(5)

    # Connect with retries
    last_error = None
    for attempt in range(10):
        try:
            _browser = await _playwright.chromium.connect_over_cdp(CDP_URL, timeout=5000)
            contexts = _browser.contexts
            if contexts:
                _context = contexts[0]
                pages = _context.pages
                if pages:
                    _page = pages[0]
                    return _page
            if _context is None:
                _context = await _browser.new_context()
            _page = await _context.new_page()
            return _page
        except Exception as e:
            last_error = e
            await asyncio.sleep(1)

    raise RuntimeError(f"Failed to connect to {browser_type} via CDP after 10 retries: {last_error}")


async def _get_page_by_url_or_title(url_pattern: str = None, title_pattern: str = None) -> Optional[Page]:
    """Find a page matching URL or title pattern across all contexts."""
    if _browser is None:
        return None
    for ctx in _browser.contexts:
        for page in ctx.pages:
            if url_pattern and url_pattern.lower() in page.url.lower():
                return page
            if title_pattern:
                title = await page.title()
                if title_pattern.lower() in title.lower():
                    return page
    return None


async def _get_interactable_elements(page: Page, filter_role: str = None, filter_visible: bool = True, max_count: int = 50) -> List[Dict]:
    """Extract interactable elements from the page using accessibility tree."""
    js_code = """
    (opts) => {
        const {filterRole, filterVisible, maxCount} = opts;
        const roles = ['button', 'link', 'textbox', 'checkbox', 'radio',
                       'combobox', 'menuitem', 'tab', 'switch', 'option',
                       'searchbox', 'slider', 'spinbutton'];
        const selector = filterRole
            ? `[role="${filterRole}"], ${filterRole}`
            : roles.map(r => `[role="${r}"]`).join(', ')
              + ', button, a, input, textarea, select, [contenteditable="true"]';

        const elements = document.querySelectorAll(selector);
        const results = [];

        for (const el of elements) {
            if (results.length >= maxCount) break;

            if (filterVisible) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
            }

            const rect = el.getBoundingClientRect();
            const role = el.getAttribute('role') || el.tagName.toLowerCase();
            const name = el.getAttribute('aria-label')
                || el.getAttribute('aria-labelledby')
                || el.getAttribute('name')
                || el.getAttribute('placeholder')
                || el.innerText?.slice(0, 80)
                || '';
            const type = el.getAttribute('type') || '';
            const id = el.id || '';
            const classes = el.className?.toString()?.slice(0, 100) || '';
            const enabled = !el.disabled && el.getAttribute('aria-disabled') !== 'true';
            const value = el.value || el.getAttribute('aria-checked') || '';
            const contentEditable = el.isContentEditable;

            // Build a stable selector
            let cssSelector = '';
            if (id) {
                cssSelector = `#${CSS.escape(id)}`;
            } else if (el.getAttribute('aria-label')) {
                const tag = el.tagName.toLowerCase();
                cssSelector = `${tag}[aria-label="${el.getAttribute('aria-label').replace(/"/g, '\\\\"')}"]`;
            } else if (el.getAttribute('data-testid')) {
                cssSelector = `[data-testid="${el.getAttribute('data-testid')}"]`;
            } else if (el.getAttribute('name')) {
                const tag = el.tagName.toLowerCase();
                cssSelector = `${tag}[name="${el.getAttribute('name')}"]`;
            }

            results.push({
                index: results.length,
                role: role,
                name: name.trim().slice(0, 80),
                type: type,
                enabled: enabled,
                contentEditable: contentEditable,
                selector: cssSelector,
                bbox: {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                },
                value: value?.toString()?.slice(0, 50) || ''
            });
        }
        return results;
    }
    """
    return await page.evaluate(js_code, {
        "filterRole": filter_role,
        "filterVisible": filter_visible,
        "maxCount": max_count
    })


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="pw_connect",
            description="Connect to Chrome browser via CDP. Restarts Chrome with debug port if needed. Preserves tabs/session.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="pw_navigate",
            description="Navigate to a URL. Can target a specific tab by URL/title pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "tab_url": {"type": "string", "description": "Switch to tab matching this URL pattern first"},
                    "tab_title": {"type": "string", "description": "Switch to tab matching this title pattern first"},
                    "wait_for": {"type": "string", "description": "Wait for this selector after navigation", "default": ""},
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="pw_list_tabs",
            description="List all open browser tabs with their URLs and titles.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="pw_switch_tab",
            description="Switch to a specific tab by index, URL pattern, or title pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Tab index (from pw_list_tabs)"},
                    "url": {"type": "string", "description": "URL pattern to match"},
                    "title": {"type": "string", "description": "Title pattern to match"},
                }
            }
        ),
        Tool(
            name="pw_get_elements",
            description="List interactable elements on the page: buttons, links, inputs, textboxes, etc. Returns role, name, enabled state, and CSS selector for each.",
            inputSchema={
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "Filter by role (button, link, textbox, etc.)"},
                    "name_filter": {"type": "string", "description": "Filter elements whose name contains this text"},
                    "max_count": {"type": "integer", "description": "Max elements to return", "default": 50}
                }
            }
        ),
        Tool(
            name="pw_click",
            description="Click an element. Use selector, role+name, or text content to target it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to click"},
                    "role": {"type": "string", "description": "ARIA role (button, link, textbox, etc.)"},
                    "name": {"type": "string", "description": "Accessible name / label (used with role)"},
                    "text": {"type": "string", "description": "Visible text content to match"},
                    "index": {"type": "integer", "description": "Element index from pw_get_elements result"},
                }
            }
        ),
        Tool(
            name="pw_fill",
            description="Fill text into an input/textarea/contenteditable. Clears existing content first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input"},
                    "role": {"type": "string", "description": "ARIA role (textbox, searchbox, etc.)"},
                    "name": {"type": "string", "description": "Accessible name / label (used with role)"},
                    "text": {"type": "string", "description": "Text to type into the field"},
                    "press_enter": {"type": "boolean", "description": "Press Enter after filling", "default": False},
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="pw_type",
            description="Type text character-by-character into the currently focused element. Useful for contenteditable fields that don't support fill().",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to focus first (optional)"},
                    "text": {"type": "string", "description": "Text to type"},
                    "delay": {"type": "integer", "description": "Delay between keystrokes in ms", "default": 10},
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="pw_press_key",
            description="Press a keyboard key or shortcut (Enter, Tab, Escape, Control+a, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press (Enter, Tab, Escape, Control+a, Control+v, etc.)"},
                    "selector": {"type": "string", "description": "Focus this element first (optional)"},
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="pw_get_state",
            description="Get current page state: URL, title, and optionally focused element info.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="pw_screenshot",
            description="Take a screenshot of the page. Only use when element list isn't sufficient.",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full scrollable page", "default": False},
                    "selector": {"type": "string", "description": "Screenshot a specific element only"},
                }
            }
        ),
        Tool(
            name="pw_evaluate",
            description="Execute JavaScript in the page context. Use as fallback when element-based tools aren't enough.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript to execute. Use 'return' for values."},
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="pw_wait",
            description="Wait for an element to appear, or a fixed delay.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to wait for"},
                    "state": {"type": "string", "description": "State to wait for: visible, hidden, attached, detached", "default": "visible"},
                    "timeout": {"type": "integer", "description": "Timeout in ms", "default": 10000},
                    "delay": {"type": "integer", "description": "Fixed delay in ms (if no selector)"},
                }
            }
        ),
        Tool(
            name="pw_scroll",
            description="Scroll the page or a specific element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "description": "up or down", "default": "down"},
                    "amount": {"type": "integer", "description": "Pixels to scroll", "default": 500},
                    "selector": {"type": "string", "description": "Scroll within this element"},
                }
            }
        ),
        Tool(
            name="pw_set_clipboard",
            description="Set the clipboard content and paste it into the focused element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to put in clipboard and paste"},
                    "selector": {"type": "string", "description": "Focus this element before pasting (optional)"},
                },
                "required": ["text"]
            }
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    global _page, _context

    try:
        if name == "pw_connect":
            page = await _ensure_browser()
            tabs = []
            for ctx in _browser.contexts:
                for p in ctx.pages:
                    tabs.append({"url": p.url, "title": await p.title()})
            return [TextContent(type="text", text=json.dumps({
                "status": "connected",
                "current_url": page.url,
                "current_title": await page.title(),
                "tabs": tabs
            }, indent=2))]

        if name == "pw_navigate":
            page = await _ensure_browser()
            tab_url = arguments.get("tab_url")
            tab_title = arguments.get("tab_title")

            # Switch tab if requested
            if tab_url or tab_title:
                for ctx in _browser.contexts:
                    for p in ctx.pages:
                        if tab_url and tab_url.lower() in p.url.lower():
                            _page = p
                            page = p
                            break
                        if tab_title:
                            t = await p.title()
                            if tab_title.lower() in t.lower():
                                _page = p
                                page = p
                                break

            await page.bring_to_front()
            url = arguments["url"]
            wait_for = arguments.get("wait_for", "")
            response = None
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                err_str = str(nav_err)
                # Handle HTTP error codes (404, 500, etc.) — page still loaded
                if "net::ERR_HTTP_RESPONSE_CODE_FAILURE" in err_str:
                    pass  # Page loaded but returned error status — that's OK
                elif "net::ERR_ABORTED" in err_str:
                    pass  # Download or redirect interruption — page may still be usable
                else:
                    raise
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            status = response.status if response else "unknown"
            return [TextContent(type="text", text=json.dumps({
                "url": page.url,
                "title": await page.title(),
                "status": status
            }))]

        if name == "pw_list_tabs":
            page = await _ensure_browser()
            tabs = []
            for ctx in _browser.contexts:
                for i, p in enumerate(ctx.pages):
                    tabs.append({
                        "index": i,
                        "url": p.url,
                        "title": await p.title(),
                        "active": p == _page
                    })
            return [TextContent(type="text", text=json.dumps(tabs, indent=2))]

        if name == "pw_switch_tab":
            page = await _ensure_browser()
            idx = arguments.get("index")
            url_pat = arguments.get("url")
            title_pat = arguments.get("title")

            for ctx in _browser.contexts:
                for i, p in enumerate(ctx.pages):
                    if idx is not None and i == idx:
                        _page = p
                        await p.bring_to_front()
                        return [TextContent(type="text", text=f"Switched to tab {i}: {p.url}")]
                    if url_pat and url_pat.lower() in p.url.lower():
                        _page = p
                        await p.bring_to_front()
                        return [TextContent(type="text", text=f"Switched to tab: {p.url}")]
                    if title_pat:
                        t = await p.title()
                        if title_pat.lower() in t.lower():
                            _page = p
                            await p.bring_to_front()
                            return [TextContent(type="text", text=f"Switched to tab: {t}")]
            return [TextContent(type="text", text="No matching tab found")]

        if name == "pw_get_elements":
            page = await _ensure_browser()
            role = arguments.get("role")
            name_filter = arguments.get("name_filter", "")
            max_count = arguments.get("max_count", 50)

            elements = await _get_interactable_elements(page, filter_role=role, max_count=max_count)

            if name_filter:
                elements = [e for e in elements if name_filter.lower() in e["name"].lower()]

            # Compact display
            lines = []
            for e in elements:
                tag = f"[{e['role']}]"
                label = e['name'][:60] if e['name'] else '(no label)'
                sel = e['selector'] or '(no selector)'
                state = 'enabled' if e['enabled'] else 'disabled'
                ce = ' contentEditable' if e.get('contentEditable') else ''
                lines.append(f"  {e['index']:3d}. {tag:20s} {label:60s} | {state}{ce} | {sel}")

            header = f"Found {len(elements)} elements on {page.url}"
            return [TextContent(type="text", text=header + "\n" + "\n".join(lines))]

        if name == "pw_click":
            page = await _ensure_browser()
            selector = arguments.get("selector")
            role = arguments.get("role")
            aname = arguments.get("name")
            text = arguments.get("text")
            index = arguments.get("index")

            if index is not None:
                elements = await _get_interactable_elements(page, max_count=index + 1)
                if index < len(elements):
                    el = elements[index]
                    if el["selector"]:
                        await page.click(el["selector"], timeout=5000)
                    else:
                        bbox = el["bbox"]
                        await page.mouse.click(bbox["x"] + bbox["w"]//2, bbox["y"] + bbox["h"]//2)
                    return [TextContent(type="text", text=f"Clicked element {index}: [{el['role']}] {el['name']}")]
                return [TextContent(type="text", text=f"Element index {index} not found")]

            if role and aname:
                locator = page.get_by_role(role, name=aname)
                await locator.click(timeout=5000)
                return [TextContent(type="text", text=f"Clicked [{role}] '{aname}'")]

            if text:
                locator = page.get_by_text(text, exact=False)
                await locator.first.click(timeout=5000)
                return [TextContent(type="text", text=f"Clicked text '{text}'")]

            if selector:
                await page.click(selector, timeout=5000)
                return [TextContent(type="text", text=f"Clicked '{selector}'")]

            return [TextContent(type="text", text="No target specified. Use selector, role+name, text, or index.")]

        if name == "pw_fill":
            page = await _ensure_browser()
            selector = arguments.get("selector")
            role = arguments.get("role")
            aname = arguments.get("name")
            text = arguments["text"]
            press_enter = arguments.get("press_enter", False)

            if role and aname:
                locator = page.get_by_role(role, name=aname)
            elif selector:
                locator = page.locator(selector)
            else:
                # Try focused element
                locator = page.locator(":focus")

            await locator.fill(text, timeout=5000)
            if press_enter:
                await locator.press("Enter")
            return [TextContent(type="text", text=f"Filled text ({len(text)} chars)")]

        if name == "pw_type":
            page = await _ensure_browser()
            selector = arguments.get("selector")
            text = arguments["text"]
            delay = arguments.get("delay", 10)

            if selector:
                await page.click(selector, timeout=5000)
            await page.keyboard.type(text, delay=delay)
            return [TextContent(type="text", text=f"Typed {len(text)} chars")]

        if name == "pw_press_key":
            page = await _ensure_browser()
            key = arguments["key"]
            selector = arguments.get("selector")

            if selector:
                await page.press(selector, key, timeout=5000)
            else:
                await page.keyboard.press(key)
            return [TextContent(type="text", text=f"Pressed '{key}'")]

        if name == "pw_get_state":
            page = await _ensure_browser()
            focused = await page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    return {
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        name: el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || '',
                        id: el.id || '',
                        contentEditable: el.isContentEditable
                    };
                }
            """)
            return [TextContent(type="text", text=json.dumps({
                "url": page.url,
                "title": await page.title(),
                "focused_element": focused
            }, indent=2))]

        if name == "pw_screenshot":
            page = await _ensure_browser()
            full_page = arguments.get("full_page", False)
            selector = arguments.get("selector")
            # Full-page screenshots of large pages need more time
            ss_timeout = 60000 if full_page else 30000

            if selector:
                el = page.locator(selector)
                screenshot_bytes = await el.screenshot(timeout=ss_timeout)
            else:
                screenshot_bytes = await page.screenshot(full_page=full_page, timeout=ss_timeout)

            b64 = base64.b64encode(screenshot_bytes).decode()
            return [ImageContent(type="image", data=b64, mimeType="image/png")]

        if name == "pw_evaluate":
            page = await _ensure_browser()
            script = arguments["script"]
            result = await page.evaluate(script)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        if name == "pw_wait":
            page = await _ensure_browser()
            selector = arguments.get("selector")
            delay = arguments.get("delay")

            if delay:
                await asyncio.sleep(delay / 1000)
                return [TextContent(type="text", text=f"Waited {delay}ms")]

            if selector:
                state = arguments.get("state", "visible")
                timeout = arguments.get("timeout", 10000)
                await page.wait_for_selector(selector, state=state, timeout=timeout)
                return [TextContent(type="text", text=f"Element '{selector}' is {state}")]

            return [TextContent(type="text", text="Specify selector or delay")]

        if name == "pw_scroll":
            page = await _ensure_browser()
            direction = arguments.get("direction", "down")
            amount = arguments.get("amount", 500)
            selector = arguments.get("selector")

            delta = amount if direction == "down" else -amount
            if selector:
                el = page.locator(selector)
                await el.evaluate(f"el => el.scrollBy(0, {delta})")
            else:
                await page.mouse.wheel(0, delta)
            return [TextContent(type="text", text=f"Scrolled {direction} {amount}px")]

        if name == "pw_set_clipboard":
            page = await _ensure_browser()
            text = arguments["text"]
            selector = arguments.get("selector")

            if selector:
                await page.click(selector, timeout=5000)
                await asyncio.sleep(0.2)

            # Strategy 1: Use CDP to set clipboard directly (works in CDP mode)
            method = "unknown"
            try:
                cdp = await page.context.new_cdp_session(page)
                await cdp.send("Browser.setPermission", {
                    "permission": {"name": "clipboard-read-write"},
                    "setting": "granted",
                    "origin": page.url.split("?")[0].rsplit("/", 1)[0] if "://" in page.url else page.url,
                })
            except Exception:
                pass  # Permission grant may not be needed or may fail; continue anyway

            try:
                # Try navigator.clipboard with granted permission
                await page.evaluate("""
                    async (text) => {
                        await navigator.clipboard.writeText(text);
                    }
                """, text)
                await page.keyboard.press("Control+v")
                await asyncio.sleep(0.3)
                method = "clipboard API + Ctrl+V"
            except Exception:
                # Strategy 2: Synthetic paste via DataTransfer / input event
                try:
                    pasted = await page.evaluate("""
                        (text) => {
                            const el = document.activeElement;
                            if (!el) return false;

                            // For input/textarea elements
                            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                                const start = el.selectionStart || 0;
                                const end = el.selectionEnd || 0;
                                el.value = el.value.slice(0, start) + text + el.value.slice(end);
                                el.selectionStart = el.selectionEnd = start + text.length;
                                el.dispatchEvent(new Event('input', {bubbles: true}));
                                el.dispatchEvent(new Event('change', {bubbles: true}));
                                return true;
                            }

                            // For contenteditable elements
                            if (el.isContentEditable) {
                                document.execCommand('insertText', false, text);
                                return true;
                            }

                            return false;
                        }
                    """, text)
                    if pasted:
                        method = "execCommand/value injection"
                    else:
                        raise RuntimeError("No active editable element")
                except Exception:
                    # Strategy 3: Fall back to Playwright keyboard.type
                    await page.keyboard.type(text, delay=2)
                    method = "keyboard.type fallback"

            return [TextContent(type="text", text=f"Pasted {len(text)} chars via {method}")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {str(e)}")]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
