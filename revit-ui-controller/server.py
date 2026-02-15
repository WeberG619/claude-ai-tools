"""
Revit UI Controller MCP Server

Provides unified control over Revit's UI through:
1. Revit MCP Bridge API (preferred - fastest, most reliable)
2. Windows UI Automation (for elements not exposed via API)
3. Raw click/type fallback (for edge cases)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    import subprocess
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from win_ui_automation import (
    get_revit_window_info,
    get_ui_elements,
    find_element_by_name,
    click_at,
    click_element,
    send_keys_to_revit,
    get_dialog_info,
    click_dialog_button,
)

# Revit MCP Bridge connection
import struct


class RevitMCPClient:
    """Client for communicating with RevitMCPBridge via named pipe."""

    PIPE_NAME = r"\\.\pipe\RevitMCPBridge2026"

    def __init__(self):
        self.connected = False

    def call(self, method: str, params: dict = None) -> dict:
        """Call a method on the Revit MCP Bridge."""
        import subprocess

        request = json.dumps({"method": method, "params": params or {}})

        # Use PowerShell to communicate with named pipe
        script = f"""
        $pipeName = "{self.PIPE_NAME}"
        $request = @'
{request}
'@

        try {{
            $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
            $pipe.Connect(5000)

            $writer = New-Object System.IO.StreamWriter($pipe)
            $writer.AutoFlush = $true
            $reader = New-Object System.IO.StreamReader($pipe)

            $writer.WriteLine($request)
            $response = $reader.ReadLine()

            $pipe.Close()

            Write-Output $response
        }} catch {{
            Write-Output ('{{"success": false, "error": "' + $_.Exception.Message + '"}}')
        }}
        """

        result = _run_ps(script, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"success": False, "error": f"Invalid JSON: {result.stdout}"}

        return {"success": False, "error": result.stderr or "Unknown error"}


# Command aliases - maps friendly names to PostableCommand values
COMMAND_ALIASES = {
    # Architecture tools
    "wall": "Wall",
    "door": "Door",
    "window": "Window",
    "floor": "Floor",
    "ceiling": "Ceiling",
    "roof": "RoofByFootprint",
    "stair": "Stair",
    "railing": "Railing",
    "room": "Room",
    "column": "Column",

    # View tools
    "3dview": "Default3DView",
    "section": "Section",
    "elevation": "Elevation",
    "callout": "Callout",
    "legend": "Legend",

    # Annotate tools
    "dimension": "AlignedDimension",
    "tag": "TagByCategory",
    "text": "Text",
    "keynote": "KeynoteElement",

    # Modify tools
    "move": "Move",
    "copy": "Copy",
    "rotate": "Rotate",
    "mirror": "Mirror",
    "array": "Array",
    "align": "Align",
    "offset": "Offset",
    "trim": "TrimOrExtendToCorner",
    "split": "SplitElement",
    "delete": "Delete",

    # Edit tools
    "undo": "Undo",
    "redo": "Redo",

    # File tools
    "save": "Save",
    "print": "Print",
}

# Initialize
revit_client = RevitMCPClient()
server = Server("revit-ui-controller")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="revit_activate_tool",
            description="Activate a Revit tool by name (e.g., 'Wall', 'Door', 'Section'). Uses ExecuteRevitCommand when possible.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool to activate (e.g., 'Wall', 'Door', 'Section', 'Dimension')",
                    }
                },
                "required": ["tool_name"],
            },
        ),
        Tool(
            name="revit_send_keys",
            description="Send keyboard shortcuts to Revit (e.g., 'Escape', 'Ctrl+Z', 'Tab', 'Enter')",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "Keys to send (e.g., 'Escape', 'Ctrl+Z', 'Ctrl+S', 'Tab')",
                    }
                },
                "required": ["keys"],
            },
        ),
        Tool(
            name="revit_get_selection",
            description="Get information about currently selected elements in Revit",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_clear_selection",
            description="Clear the current selection in Revit",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_get_ui_state",
            description="Get complete Revit UI state including open views, selection, and document info",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_get_properties",
            description="Get properties of selected element(s) or current view",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_get_project_browser",
            description="Get Project Browser structure (views, sheets, families)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_click_ui_element",
            description="Click a named UI element using Windows UI Automation",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_name": {
                        "type": "string",
                        "description": "Name or partial name of UI element to click",
                    }
                },
                "required": ["element_name"],
            },
        ),
        Tool(
            name="revit_get_ui_elements",
            description="Get list of visible UI elements in Revit (buttons, tabs, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_type": {
                        "type": "string",
                        "description": "Type of elements to find: 'all', 'Button', 'TabItem', 'MenuItem', 'Edit'",
                        "default": "all",
                    }
                },
            },
        ),
        Tool(
            name="revit_handle_dialog",
            description="Detect and interact with Revit dialogs",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "'check' to see if dialog is open, 'click' to click a button",
                        "enum": ["check", "click"],
                    },
                    "button_name": {
                        "type": "string",
                        "description": "Name of button to click (required if action='click')",
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="revit_zoom_to_selection",
            description="Zoom the view to fit currently selected elements",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="revit_can_execute_command",
            description="Check if a specific command can be executed in the current context",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command name to check",
                    }
                },
                "required": ["command"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    result = {}

    try:
        if name == "revit_activate_tool":
            tool_name = arguments.get("tool_name", "")

            # Try command alias first
            command = COMMAND_ALIASES.get(tool_name.lower(), tool_name)

            # Call Revit MCP
            result = revit_client.call("executeRevitCommand", {"command": command})

            if not result.get("success"):
                # Try UI Automation as fallback
                ui_result = click_element(tool_name)
                if ui_result.get("success"):
                    result = {
                        "success": True,
                        "method": "ui_automation",
                        "clicked": tool_name,
                        "details": ui_result,
                    }

        elif name == "revit_send_keys":
            keys = arguments.get("keys", "")

            # Try Revit MCP first
            result = revit_client.call("sendKeySequence", {"keys": keys})

            if not result.get("success"):
                # Fallback to direct SendKeys
                success = send_keys_to_revit(keys)
                result = {
                    "success": success,
                    "method": "direct_sendkeys",
                    "keys": keys,
                }

        elif name == "revit_get_selection":
            result = revit_client.call("getSelectionInfo")

        elif name == "revit_clear_selection":
            result = revit_client.call("clearSelection")

        elif name == "revit_get_ui_state":
            # Get multiple pieces of state
            ui_state = revit_client.call("getUIState")
            selection = revit_client.call("getSelectionInfo")
            window_info = get_revit_window_info()

            result = {
                "success": True,
                "revitState": ui_state,
                "selection": selection,
                "windowInfo": window_info,
            }

        elif name == "revit_get_properties":
            result = revit_client.call("getPropertiesPaletteState")

        elif name == "revit_get_project_browser":
            result = revit_client.call("getProjectBrowserState")

        elif name == "revit_click_ui_element":
            element_name = arguments.get("element_name", "")
            result = click_element(element_name)

        elif name == "revit_get_ui_elements":
            element_type = arguments.get("element_type", "all")
            elements = get_ui_elements(element_type)
            result = {
                "success": True,
                "count": len(elements),
                "elements": elements[:50],  # Limit response size
            }

        elif name == "revit_handle_dialog":
            action = arguments.get("action", "check")

            if action == "check":
                result = get_dialog_info()
            elif action == "click":
                button_name = arguments.get("button_name", "")
                if not button_name:
                    result = {"success": False, "error": "button_name required for click action"}
                else:
                    result = click_dialog_button(button_name)

        elif name == "revit_zoom_to_selection":
            result = revit_client.call("zoomToSelected")

        elif name == "revit_can_execute_command":
            command = arguments.get("command", "")
            result = revit_client.call("canExecuteCommand", {"command": command})

        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

    except Exception as e:
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
