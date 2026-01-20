#!/usr/bin/env python3
"""
Windows Browser MCP Server
Controls Windows browsers from WSL via PowerShell and CDP
"""

import asyncio
import json
import subprocess
import sys
import os
import base64
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.error

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.types import (
        Tool,
        TextContent,
        ImageContent,
    )
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configuration
DEFAULT_MONITOR = "center"  # left, center, right, or primary
CDP_PORT = 9222
SCREENSHOT_DIR = "/mnt/d/.playwright-mcp"

# Monitor positions (will be detected dynamically)
MONITORS = {
    "left": {"x": -5120, "y": 0, "width": 2560, "height": 1440},
    "center": {"x": -2560, "y": 0, "width": 2560, "height": 1440},
    "right": {"x": 0, "y": 0, "width": 2560, "height": 1440},
    "primary": {"x": 0, "y": 0, "width": 2560, "height": 1440},
}

server = Server("windows-browser")

def run_powershell(script: str, capture_output: bool = True) -> tuple[str, str, int]:
    """Execute PowerShell script and return stdout, stderr, returncode"""
    # Escape for PowerShell
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=capture_output,
        text=True
    )
    return result.stdout, result.stderr, result.returncode

def detect_monitors() -> Dict[str, Dict]:
    """Detect monitor configuration from Windows"""
    script = """
    Add-Type -AssemblyName System.Windows.Forms
    $screens = [System.Windows.Forms.Screen]::AllScreens
    $result = @()
    foreach ($screen in $screens) {
        $result += @{
            Name = $screen.DeviceName
            X = $screen.Bounds.X
            Y = $screen.Bounds.Y
            Width = $screen.Bounds.Width
            Height = $screen.Bounds.Height
            Primary = $screen.Primary
        }
    }
    $result | ConvertTo-Json -Compress
    """
    stdout, _, _ = run_powershell(script)
    try:
        screens = json.loads(stdout.strip())
        if not isinstance(screens, list):
            screens = [screens]

        # Sort by X position to determine left/center/right
        screens.sort(key=lambda s: s['X'])

        monitors = {}
        for i, screen in enumerate(screens):
            if screen.get('Primary'):
                monitors['primary'] = screen
            if len(screens) == 3:
                if i == 0:
                    monitors['left'] = screen
                elif i == 1:
                    monitors['center'] = screen
                else:
                    monitors['right'] = screen
            elif len(screens) == 2:
                if i == 0:
                    monitors['left'] = screen
                else:
                    monitors['right'] = screen

        return monitors
    except:
        return MONITORS

def launch_browser_with_cdp(url: str = "about:blank", monitor: str = "center", browser: str = "chrome") -> bool:
    """Launch browser with CDP enabled on specified monitor

    Args:
        url: URL to navigate to
        monitor: Which monitor (left, center, right, primary)
        browser: Browser to use (chrome, edge)
    """
    monitors = detect_monitors()
    mon = monitors.get(monitor, monitors.get('primary', MONITORS['center']))

    # Calculate window position with margins
    x = mon['X'] + 50
    y = mon['Y'] + 50
    width = mon['Width'] - 100
    height = mon['Height'] - 100

    # Browser paths and process names
    browser_config = {
        "chrome": {
            "paths": [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            ],
            "profile_dir": "$env:TEMP\\chrome-cdp-profile",
            "process_name": "chrome"
        },
        "edge": {
            "paths": [
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
            ],
            "profile_dir": "$env:TEMP\\edge-cdp-profile",
            "process_name": "msedge"
        }
    }

    config = browser_config.get(browser.lower(), browser_config["chrome"])
    paths_check = " -or ".join([f'(Test-Path "{p}")' for p in config["paths"]])

    script = f"""
    # Find browser executable
    $browserPath = $null
    $paths = @({', '.join([f'"{p}"' for p in config["paths"]])})
    foreach ($p in $paths) {{
        if (Test-Path $p) {{
            $browserPath = $p
            break
        }}
    }}

    if (-not $browserPath) {{
        Write-Error "{browser} not found"
        exit 1
    }}

    Start-Process $browserPath -ArgumentList @(
        "--remote-debugging-port={CDP_PORT}",
        "--user-data-dir={config['profile_dir']}",
        "--window-position={x},{y}",
        "--window-size={width},{height}",
        "{url}"
    )

    Start-Sleep -Seconds 2

    # Bring window to front
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32Launch {{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);
}}
'@

    $proc = Get-Process {config['process_name']} -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
    if ($proc) {{
        [Win32Launch]::ShowWindow($proc.MainWindowHandle, 9)
        [Win32Launch]::BringWindowToTop($proc.MainWindowHandle)
        [Win32Launch]::SetForegroundWindow($proc.MainWindowHandle)
    }}

    Write-Output "{browser} launched with CDP on port {CDP_PORT}"
    """

    stdout, stderr, code = run_powershell(script)
    return code == 0

# Backward compatibility alias
def launch_chrome_with_cdp(url: str = "about:blank", monitor: str = "center") -> bool:
    """Launch Chrome with CDP enabled on specified monitor (legacy function)"""
    return launch_browser_with_cdp(url, monitor, "chrome")

def cdp_request(method: str, params: dict = None) -> dict:
    """Send a CDP request to Chrome"""
    try:
        # First get the list of targets
        targets_url = f"http://localhost:{CDP_PORT}/json"
        with urllib.request.urlopen(targets_url, timeout=5) as response:
            targets = json.loads(response.read().decode())

        if not targets:
            return {"error": "No browser targets found"}

        # Find a page target
        page_target = None
        for target in targets:
            if target.get('type') == 'page':
                page_target = target
                break

        if not page_target:
            return {"error": "No page target found"}

        return {"success": True, "target": page_target}
    except Exception as e:
        return {"error": str(e)}

def navigate_browser(url: str) -> dict:
    """Navigate the browser to a URL using CDP"""
    # First check if Chrome with CDP is running
    result = cdp_request("check")

    if "error" in result:
        # Need to launch Chrome
        launch_chrome_with_cdp(url)
        return {"success": True, "message": f"Launched Chrome and navigated to {url}"}

    # Use PowerShell to navigate existing window
    script = f"""
    Add-Type -AssemblyName System.Windows.Forms

    # Find Chrome window and send keys to navigate
    $chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
    if ($chrome) {{
        # Activate window
        Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}}
'@
        [Win32]::SetForegroundWindow($chrome.MainWindowHandle)
        Start-Sleep -Milliseconds 200

        # Send Ctrl+L to focus address bar, then type URL and Enter
        [System.Windows.Forms.SendKeys]::SendWait("^l")
        Start-Sleep -Milliseconds 100
        [System.Windows.Forms.SendKeys]::SendWait("{url}")
        Start-Sleep -Milliseconds 100
        [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")

        Write-Output "Navigated to {url}"
    }} else {{
        Write-Output "Chrome not found, launching..."
    }}
    """

    stdout, stderr, code = run_powershell(script)
    if "Chrome not found" in stdout:
        launch_chrome_with_cdp(url)

    return {"success": True, "url": url}

def take_screenshot(monitor: str = "center", filename: str = None) -> str:
    """Take a screenshot of specified monitor"""
    monitors = detect_monitors()
    mon = monitors.get(monitor, monitors.get('primary', MONITORS['center']))

    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"screenshot_{monitor}_{timestamp}.png"

    filepath = os.path.join(SCREENSHOT_DIR, filename)

    script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $x = {mon['X']}
    $y = {mon['Y']}
    $width = {mon['Width']}
    $height = {mon['Height']}

    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($x, $y, 0, 0, [System.Drawing.Size]::new($width, $height))
    $bitmap.Save('{filepath.replace("/mnt/d", "D:")}')
    $graphics.Dispose()
    $bitmap.Dispose()

    Write-Output "Screenshot saved"
    """

    stdout, stderr, code = run_powershell(script)

    if code == 0:
        return filepath
    else:
        return None

def click_at(x: int, y: int) -> bool:
    """Click at screen coordinates"""
    script = f"""
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class MouseOps {{
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
    public const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP = 0x0004;

    public static void Click(int x, int y) {{
        SetCursorPos(x, y);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }}
}}
'@
    [MouseOps]::Click({x}, {y})
    Write-Output "Clicked at ({x}, {y})"
    """

    stdout, stderr, code = run_powershell(script)
    return code == 0

def type_text(text: str) -> bool:
    """Type text using SendKeys"""
    # Escape special characters for SendKeys
    escaped = text.replace('{', '{{').replace('}', '}}').replace('+', '{+}').replace('^', '{^}').replace('%', '{%}')

    script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait("{escaped}")
    Write-Output "Typed text"
    """

    stdout, stderr, code = run_powershell(script)
    return code == 0

def bring_window_to_front(process_name: str) -> bool:
    """Bring a window to the foreground"""
    script = f"""
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32Front {{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);
}}
'@

    $proc = Get-Process {process_name} -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
    if ($proc) {{
        [Win32Front]::ShowWindow($proc.MainWindowHandle, 9)  # SW_RESTORE
        [Win32Front]::BringWindowToTop($proc.MainWindowHandle)
        [Win32Front]::SetForegroundWindow($proc.MainWindowHandle)
        Write-Output "Window brought to front"
    }} else {{
        Write-Output "Process {process_name} not found"
    }}
    """

    stdout, stderr, code = run_powershell(script)
    return "brought to front" in stdout.lower()

def move_window_to_monitor(process_name: str, monitor: str = "center") -> bool:
    """Move a window to specified monitor"""
    monitors = detect_monitors()
    mon = monitors.get(monitor, monitors.get('primary', MONITORS['center']))

    x = mon['X'] + 50
    y = mon['Y'] + 50
    width = mon['Width'] - 100
    height = mon['Height'] - 100

    script = f"""
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
}}
'@

    $proc = Get-Process {process_name} -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
    if ($proc) {{
        [Win32]::SetWindowPos($proc.MainWindowHandle, [IntPtr]::Zero, {x}, {y}, {width}, {height}, 0x0040)
        Write-Output "Window moved to {monitor} monitor"
    }} else {{
        Write-Output "Process {process_name} not found"
    }}
    """

    stdout, stderr, code = run_powershell(script)
    return "moved" in stdout.lower()

# MCP Tool Definitions
@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="browser_open",
            description="Open a web browser (Chrome or Edge) on a specific monitor and navigate to a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to"
                    },
                    "monitor": {
                        "type": "string",
                        "enum": ["left", "center", "right", "primary"],
                        "description": "Which monitor to open the browser on",
                        "default": "center"
                    },
                    "browser": {
                        "type": "string",
                        "enum": ["chrome", "edge"],
                        "description": "Which browser to use (chrome or edge)",
                        "default": "chrome"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_navigate",
            description="Navigate the browser to a new URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_screenshot",
            description="Take a screenshot of a monitor to see what's displayed",
            inputSchema={
                "type": "object",
                "properties": {
                    "monitor": {
                        "type": "string",
                        "enum": ["left", "center", "right", "primary"],
                        "description": "Which monitor to screenshot",
                        "default": "center"
                    }
                }
            }
        ),
        Tool(
            name="browser_click",
            description="Click at specific screen coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate (screen position)"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate (screen position)"
                    }
                },
                "required": ["x", "y"]
            }
        ),
        Tool(
            name="browser_type",
            description="Type text using keyboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to type"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="browser_search",
            description="Open browser and perform a Google search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "monitor": {
                        "type": "string",
                        "enum": ["left", "center", "right", "primary"],
                        "default": "center"
                    },
                    "browser": {
                        "type": "string",
                        "enum": ["chrome", "edge"],
                        "description": "Which browser to use",
                        "default": "chrome"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="window_move",
            description="Move an application window to a specific monitor",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "Name of the process (e.g., 'chrome', 'msedge', 'notepad')"
                    },
                    "monitor": {
                        "type": "string",
                        "enum": ["left", "center", "right", "primary"],
                        "default": "center"
                    }
                },
                "required": ["process_name"]
            }
        ),
        Tool(
            name="get_monitors",
            description="Get information about connected monitors",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    """Handle tool calls - returns list of content items for MCP SDK 1.12.x compatibility"""
    try:
        if name == "browser_open":
            url = arguments.get("url", "https://google.com")
            monitor = arguments.get("monitor", "center")
            browser = arguments.get("browser", "chrome")

            success = launch_browser_with_cdp(url, monitor, browser)

            # Take a screenshot to show result
            await asyncio.sleep(2)
            screenshot_path = take_screenshot(monitor)

            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()

                return [
                    TextContent(type="text", text=f"{browser.capitalize()} opened on {monitor} monitor, navigated to {url}"),
                    ImageContent(type="image", data=image_data, mimeType="image/png")
                ]
            else:
                return [TextContent(type="text", text=f"{browser.capitalize()} opened on {monitor} monitor, navigated to {url}")]

        elif name == "browser_navigate":
            url = arguments.get("url")
            result = navigate_browser(url)

            await asyncio.sleep(1)
            screenshot_path = take_screenshot("center")

            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()

                return [
                    TextContent(type="text", text=f"Navigated to {url}"),
                    ImageContent(type="image", data=image_data, mimeType="image/png")
                ]
            else:
                return [TextContent(type="text", text=f"Navigated to {url}")]

        elif name == "browser_screenshot":
            monitor = arguments.get("monitor", "center")
            screenshot_path = take_screenshot(monitor)

            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()

                return [
                    TextContent(type="text", text=f"Screenshot of {monitor} monitor"),
                    ImageContent(type="image", data=image_data, mimeType="image/png")
                ]
            else:
                raise Exception("Failed to take screenshot")

        elif name == "browser_click":
            x = arguments.get("x")
            y = arguments.get("y")
            success = click_at(x, y)

            return [TextContent(type="text", text=f"Clicked at ({x}, {y})" if success else "Click failed")]

        elif name == "browser_type":
            text = arguments.get("text")
            success = type_text(text)

            return [TextContent(type="text", text=f"Typed: {text}" if success else "Type failed")]

        elif name == "browser_search":
            query = arguments.get("query")
            monitor = arguments.get("monitor", "center")
            browser = arguments.get("browser", "chrome")

            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            launch_browser_with_cdp(search_url, monitor, browser)

            await asyncio.sleep(2)
            screenshot_path = take_screenshot(monitor)

            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()

                return [
                    TextContent(type="text", text=f"Searched for: {query}"),
                    ImageContent(type="image", data=image_data, mimeType="image/png")
                ]
            else:
                return [TextContent(type="text", text=f"Searched for: {query}")]

        elif name == "window_move":
            process_name = arguments.get("process_name")
            monitor = arguments.get("monitor", "center")

            success = move_window_to_monitor(process_name, monitor)

            return [TextContent(type="text", text=f"Moved {process_name} to {monitor} monitor" if success else f"Failed to move {process_name}")]

        elif name == "get_monitors":
            monitors = detect_monitors()

            return [TextContent(type="text", text=json.dumps(monitors, indent=2))]

        else:
            raise Exception(f"Unknown tool: {name}")

    except Exception as e:
        raise Exception(f"Error: {str(e)}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import urllib.parse
    asyncio.run(main())
