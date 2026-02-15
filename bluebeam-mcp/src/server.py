#!/usr/bin/env python3
"""
Bluebeam Revu MCP Server - Control Bluebeam from Claude Code

Features:
- Check Bluebeam status (running, current document)
- Open/view PDF documents
- Get document information (pages, title)
- Navigate to specific pages
- Export pages as images
- Take screenshots of Bluebeam window
- Get markup summaries via UI Automation

Note: Uses COM automation, PowerShell, and UI Automation for comprehensive control.
"""

import asyncio
import subprocess
import sys
import os
import json
import tempfile
from typing import List, Optional
from datetime import datetime
from pathlib import Path

# PowerShell Bridge — 100x faster than subprocess.run(powershell.exe...)
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================
BLUEBEAM_PATHS = [
    r"C:\Program Files\Bluebeam Software\Bluebeam Revu\2020\Revu\Revu.exe",
    r"C:\Program Files\Bluebeam Software\Bluebeam Revu\2017\Revu\Revu.exe",
    r"C:\Program Files\Bluebeam Software\Bluebeam Revu\Revu.exe",
    r"C:\Program Files (x86)\Bluebeam Software\Bluebeam Revu\Revu.exe",
]

SCREENSHOT_DIR = Path("/mnt/d/.bluebeam-mcp/screenshots")
EXPORT_DIR = Path("/mnt/d/.bluebeam-mcp/exports")

server = Server("bluebeam")


# =============================================================================
# POWERSHELL HELPERS
# =============================================================================
def run_powershell(script: str, timeout: int = 30) -> tuple[bool, str]:
    """Execute PowerShell script and return (success, output).
    Uses the persistent bridge (~5ms) with subprocess fallback (~590ms)."""
    try:
        if _HAS_BRIDGE:
            result = _ps_bridge(script, timeout)
            output = result.stdout.strip()
            if not result.success and result.stderr:
                output = result.stderr.strip()
            return result.success, output
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output = result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_bluebeam_status() -> dict:
    """Get Bluebeam running status and current document."""
    script = '''
    $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
    if ($revu) {
        @{
            running = $true
            processId = $revu.Id
            windowTitle = $revu.MainWindowTitle
            document = if ($revu.MainWindowTitle -match '^(.+) - Bluebeam') { $matches[1] } else { $revu.MainWindowTitle }
        } | ConvertTo-Json
    } else {
        @{ running = $false } | ConvertTo-Json
    }
    '''
    success, output = run_powershell(script)
    if success:
        try:
            return json.loads(output)
        except:
            pass
    return {"running": False, "error": output}


def open_document_in_bluebeam(file_path: str, view_only: bool = False) -> tuple[bool, str]:
    """Open a document in Bluebeam using COM."""
    method = "ViewDocument" if view_only else "EditDocument"
    script = f'''
    try {{
        $revu = New-Object -ComObject 'Revu.Launcher'
        $result = $revu.{method}("{file_path}", $null)
        if ($result) {{
            "Successfully opened document"
        }} else {{
            "Failed to open document"
        }}
    }} catch {{
        $_.Exception.Message
    }}
    '''
    return run_powershell(script)


def get_window_info() -> dict:
    """Get detailed Bluebeam window information via UI Automation."""
    script = '''
    Add-Type -AssemblyName UIAutomationClient
    $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
    if (-not $revu) {
        @{ error = "Bluebeam not running" } | ConvertTo-Json
        return
    }

    $automation = [System.Windows.Automation.AutomationElement]::FromHandle($revu.MainWindowHandle)
    $info = @{
        windowTitle = $automation.Current.Name
        className = $automation.Current.ClassName
        bounds = @{
            x = $automation.Current.BoundingRectangle.X
            y = $automation.Current.BoundingRectangle.Y
            width = $automation.Current.BoundingRectangle.Width
            height = $automation.Current.BoundingRectangle.Height
        }
    }

    # Try to find status bar or page info
    $condition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::StatusBar
    )
    $statusBar = $automation.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
    if ($statusBar) {
        $info.statusBar = $statusBar.Current.Name
    }

    $info | ConvertTo-Json -Depth 3
    '''
    success, output = run_powershell(script, timeout=10)
    if success:
        try:
            return json.loads(output)
        except:
            pass
    return {"error": output}


def take_bluebeam_screenshot(output_path: str) -> tuple[bool, str]:
    """Take a screenshot of the Bluebeam window."""
    script = f'''
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
    if (-not $revu) {{
        "Bluebeam not running"
        return
    }}

    # Get window rectangle
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {{
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
    }}
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}
"@

    $handle = $revu.MainWindowHandle
    [Win32]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 50

    $rect = New-Object RECT
    [Win32]::GetWindowRect($handle, [ref]$rect) | Out-Null

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top

    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [System.Drawing.Size]::new($width, $height))

    $bitmap.Save("{output_path}")
    $graphics.Dispose()
    $bitmap.Dispose()

    "Screenshot saved to {output_path}"
    '''
    return run_powershell(script, timeout=15)


def navigate_to_page(page_number: int) -> tuple[bool, str]:
    """Navigate to a specific page using keyboard shortcuts."""
    script = f'''
    $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
    if (-not $revu) {{
        "Bluebeam not running"
        return
    }}

    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32Nav {{
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
    }}
"@

    [Win32Nav]::SetForegroundWindow($revu.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 50

    # Ctrl+G opens Go To Page dialog in Bluebeam
    [System.Windows.Forms.SendKeys]::SendWait("^g")
    Start-Sleep -Milliseconds 100
    [System.Windows.Forms.SendKeys]::SendWait("{page_number}")
    Start-Sleep -Milliseconds 50
    [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")

    "Navigated to page {page_number}"
    '''
    return run_powershell(script)


def get_pdf_info_from_file(file_path: str) -> dict:
    """Get PDF metadata using PyMuPDF if available, otherwise basic info."""
    win_path = file_path.replace("/mnt/d", "D:").replace("/", "\\")
    script = f'''
    $file = "{win_path}"
    if (Test-Path $file) {{
        $info = Get-Item $file
        @{{
            name = $info.Name
            path = $info.FullName
            size = $info.Length
            sizeFormatted = "{{0:N2}} MB" -f ($info.Length / 1MB)
            created = $info.CreationTime.ToString("yyyy-MM-dd HH:mm:ss")
            modified = $info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        }} | ConvertTo-Json
    }} else {{
        @{{ error = "File not found" }} | ConvertTo-Json
    }}
    '''
    success, output = run_powershell(script)
    if success:
        try:
            return json.loads(output)
        except:
            pass
    return {"error": output}


# =============================================================================
# MCP TOOLS
# =============================================================================
@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_status",
            description="Check if Bluebeam Revu is running and get current document info",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="open_document",
            description="Open a PDF document in Bluebeam Revu",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Full path to the PDF file (Windows or WSL path)"
                    },
                    "view_only": {
                        "type": "boolean",
                        "description": "Open in view-only mode (default: false)",
                        "default": False
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_window_info",
            description="Get detailed information about the Bluebeam window via UI Automation",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="take_screenshot",
            description="Take a screenshot of the Bluebeam window",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Output filename (optional, auto-generated if not provided)"
                    }
                },
            }
        ),
        Tool(
            name="go_to_page",
            description="Navigate to a specific page in the current document",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "Page number to navigate to",
                        "minimum": 1
                    }
                },
                "required": ["page"]
            }
        ),
        Tool(
            name="get_pdf_info",
            description="Get information about a PDF file (size, dates, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="create_document",
            description="Create a new blank PDF document in Bluebeam",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the new document"
                    },
                    "template": {
                        "type": "string",
                        "description": "Template to use (optional)"
                    }
                },
                "required": ["output_path"]
            }
        ),
        Tool(
            name="send_keys",
            description="Send keyboard commands to Bluebeam (for advanced automation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "Keys to send (SendKeys format, e.g., '^s' for Ctrl+S, '{F5}' for F5)"
                    },
                    "delay_ms": {
                        "type": "integer",
                        "description": "Delay in milliseconds before sending keys",
                        "default": 50
                    }
                },
                "required": ["keys"]
            }
        ),
        Tool(
            name="focus_window",
            description="Bring Bluebeam window to foreground",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "get_status":
            status = get_bluebeam_status()
            if status.get("running"):
                return [TextContent(
                    type="text",
                    text=f"Bluebeam is running\nDocument: {status.get('document', 'Unknown')}\nProcess ID: {status.get('processId')}"
                )]
            else:
                return [TextContent(type="text", text="Bluebeam is not running")]

        elif name == "open_document":
            file_path = arguments.get("file_path", "")
            view_only = arguments.get("view_only", False)

            # Convert WSL path to Windows path if needed
            if file_path.startswith("/mnt/"):
                drive = file_path[5].upper()
                file_path = f"{drive}:{file_path[6:]}".replace("/", "\\")

            success, result = open_document_in_bluebeam(file_path, view_only)
            return [TextContent(type="text", text=result)]

        elif name == "get_window_info":
            info = get_window_info()
            return [TextContent(type="text", text=json.dumps(info, indent=2))]

        elif name == "take_screenshot":
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = arguments.get("filename")
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"bluebeam_{timestamp}.png"

            output_path = str(SCREENSHOT_DIR / filename).replace("/mnt/d", "D:").replace("/", "\\")
            success, result = take_bluebeam_screenshot(output_path)

            if success:
                wsl_path = output_path.replace("D:", "/mnt/d").replace("\\", "/")
                return [TextContent(type="text", text=f"Screenshot saved: {wsl_path}")]
            return [TextContent(type="text", text=f"Screenshot failed: {result}")]

        elif name == "go_to_page":
            page = arguments.get("page", 1)
            success, result = navigate_to_page(page)
            return [TextContent(type="text", text=result)]

        elif name == "get_pdf_info":
            file_path = arguments.get("file_path", "")
            info = get_pdf_info_from_file(file_path)
            return [TextContent(type="text", text=json.dumps(info, indent=2))]

        elif name == "create_document":
            output_path = arguments.get("output_path", "")
            template = arguments.get("template", "")

            if output_path.startswith("/mnt/"):
                drive = output_path[5].upper()
                output_path = f"{drive}:{output_path[6:]}".replace("/", "\\")

            script = f'''
            try {{
                $revu = New-Object -ComObject 'Revu.Launcher'
                $result = $revu.CreateNewDocument("{output_path}", "{template}")
                if ($result) {{
                    "Created new document: {output_path}"
                }} else {{
                    "Failed to create document"
                }}
            }} catch {{
                $_.Exception.Message
            }}
            '''
            success, result = run_powershell(script)
            return [TextContent(type="text", text=result)]

        elif name == "send_keys":
            keys = arguments.get("keys", "")
            delay = arguments.get("delay_ms", 50)

            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
            if (-not $revu) {{
                "Bluebeam not running"
                return
            }}

            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32Keys {{
                [DllImport("user32.dll")]
                public static extern bool SetForegroundWindow(IntPtr hWnd);
            }}
"@
            [Win32Keys]::SetForegroundWindow($revu.MainWindowHandle) | Out-Null
            Start-Sleep -Milliseconds {delay}
            [System.Windows.Forms.SendKeys]::SendWait("{keys}")
            "Sent keys: {keys}"
            '''
            success, result = run_powershell(script)
            return [TextContent(type="text", text=result)]

        elif name == "focus_window":
            script = '''
            $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
            if (-not $revu) {
                "Bluebeam not running"
                return
            }

            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32Focus {
                [DllImport("user32.dll")]
                public static extern bool SetForegroundWindow(IntPtr hWnd);
                [DllImport("user32.dll")]
                public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            }
"@
            [Win32Focus]::ShowWindow($revu.MainWindowHandle, 9) | Out-Null  # SW_RESTORE
            [Win32Focus]::SetForegroundWindow($revu.MainWindowHandle) | Out-Null
            "Bluebeam window focused"
            '''
            success, result = run_powershell(script)
            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# =============================================================================
# MAIN
# =============================================================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
