#!/usr/bin/env python3
"""
RevitMCP Client - Named pipe communication with RevitMCPBridge.

Provides a Python interface to call Revit operations via the MCP bridge.
Works from WSL by spawning PowerShell for named pipe access.

Usage:
    from revit_client import RevitClient

    client = RevitClient("RevitMCPBridge2025")
    result = client.call("getLevels", {})
    print(result)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum


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
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


class RevitVersion(Enum):
    REVIT_2025 = "RevitMCPBridge2025"
    REVIT_2026 = "RevitMCPBridge2026"


@dataclass
class MCPResponse:
    """Response from RevitMCPBridge."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> 'MCPResponse':
        return cls(
            success=d.get("success", False),
            data=d,
            error=d.get("error")
        )


class RevitClient:
    """
    Client for communicating with RevitMCPBridge via named pipes.

    Since named pipes are Windows-only, this uses PowerShell as a bridge
    when running from WSL/Linux.
    """

    # PowerShell script template - method and params are embedded directly
    PS_TEMPLATE = '''
try {{
    $pipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(".", "{pipe_name}", [System.IO.Pipes.PipeDirection]::InOut)
    $pipeClient.Connect({timeout})

    $reader = New-Object System.IO.StreamReader($pipeClient)
    $writer = New-Object System.IO.StreamWriter($pipeClient)
    $writer.AutoFlush = $true

    $request = '{{"method":"{method}","params":{params_json}}}'

    $writer.WriteLine($request)
    $response = $reader.ReadLine()

    $pipeClient.Close()
    Write-Output $response
}}
catch {{
    Write-Output ('{{"success":false,"error":"' + $_.Exception.Message.Replace('"', "'").Replace("`n", " ") + '"}}')
}}
'''

    def __init__(
        self,
        pipe_name: str = "RevitMCPBridge2025",
        timeout_ms: int = 5000,
        verbose: bool = False
    ):
        """
        Initialize RevitMCP client.

        Args:
            pipe_name: Name of the named pipe (RevitMCPBridge2025 or RevitMCPBridge2026)
            timeout_ms: Connection timeout in milliseconds
            verbose: Print debug information
        """
        self.pipe_name = pipe_name
        self.timeout_ms = timeout_ms
        self.verbose = verbose

        # Detect if we're in WSL
        self.is_wsl = "microsoft" in Path("/proc/version").read_text().lower() if Path("/proc/version").exists() else False

    def ping(self) -> bool:
        """Check if RevitMCPBridge is responding."""
        try:
            result = self.call("ping", {})
            return result.success
        except Exception:
            return False

    def call(self, method: str, params: Dict[str, Any]) -> MCPResponse:
        """
        Call a RevitMCPBridge method.

        Args:
            method: MCP method name (e.g., "getLevels", "createWall")
            params: Parameters for the method

        Returns:
            MCPResponse with success status and data
        """
        if self.verbose:
            print(f"[RevitClient] Calling {method} with {json.dumps(params)[:100]}...")

        params_json = json.dumps(params)

        # Build the PowerShell script with embedded values
        ps_script = self.PS_TEMPLATE.format(
            pipe_name=self.pipe_name,
            timeout=self.timeout_ms,
            method=method,
            params_json=params_json
        )

        try:
            # Run PowerShell to access named pipe
            result = _run_ps(ps_script, timeout=max(self.timeout_ms // 1000 + 15, 120))

            # Parse response
            output = result.stdout.strip()

            if self.verbose:
                print(f"[RevitClient] Response: {output[:200]}...")

            if not output:
                return MCPResponse(
                    success=False,
                    data={},
                    error=result.stderr or "No response from RevitMCPBridge"
                )

            # Handle multiple lines (PowerShell may output extra)
            lines = output.split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        data = json.loads(line)
                        return MCPResponse.from_dict(data)
                    except json.JSONDecodeError:
                        continue

            return MCPResponse(
                success=False,
                data={},
                error=f"Invalid JSON response: {output[:100]}"
            )

        except subprocess.TimeoutExpired:
            return MCPResponse(
                success=False,
                data={},
                error="Request timed out"
            )
        except Exception as e:
            return MCPResponse(
                success=False,
                data={},
                error=str(e)
            )

    # ==========================================================================
    # Convenience methods for common operations
    # ==========================================================================

    def get_project_info(self) -> MCPResponse:
        """Get current Revit project information."""
        return self.call("getProjectInfo", {})

    def get_levels(self) -> MCPResponse:
        """Get all levels in the project."""
        return self.call("getLevels", {})

    def get_views(self, view_type: str = None) -> MCPResponse:
        """Get views, optionally filtered by type."""
        params = {}
        if view_type:
            params["viewType"] = view_type
        return self.call("getViews", params)

    def get_sheets(self) -> MCPResponse:
        """Get all sheets in the project."""
        return self.call("getSheets", {})

    def get_elements(self, category: str) -> MCPResponse:
        """Get elements by category."""
        return self.call("getElements", {"category": category})

    def create_wall(
        self,
        start_point: list,
        end_point: list,
        level_id: int,
        height: float = 10.0,
        wall_type_id: int = None
    ) -> MCPResponse:
        """Create a wall."""
        params = {
            "startPoint": start_point,
            "endPoint": end_point,
            "levelId": level_id,
            "height": height
        }
        if wall_type_id:
            params["wallTypeId"] = wall_type_id
        return self.call("createWall", params)

    def create_sheet(
        self,
        sheet_number: str,
        sheet_name: str,
        title_block_id: int = None
    ) -> MCPResponse:
        """Create a new sheet."""
        params = {
            "sheetNumber": sheet_number,
            "sheetName": sheet_name
        }
        if title_block_id:
            params["titleBlockId"] = title_block_id
        return self.call("createSheetAuto", params)

    def place_view_on_sheet(
        self,
        sheet_id: int,
        view_id: int,
        location: list = None
    ) -> MCPResponse:
        """Place a view on a sheet."""
        params = {
            "sheetId": sheet_id,
            "viewId": view_id
        }
        if location:
            params["location"] = location
        return self.call("placeViewOnSheet", params)

    def capture_view(
        self,
        view_id: int = None,
        output_path: str = None,
        width: int = 1920,
        height: int = 1080
    ) -> MCPResponse:
        """Capture a view to image."""
        params = {
            "width": width,
            "height": height
        }
        if view_id:
            params["viewId"] = view_id
        if output_path:
            params["outputPath"] = output_path
        return self.call("captureActiveView", params)


# =============================================================================
# AUTO-DETECT CLIENT
# =============================================================================

def get_active_client(verbose: bool = False) -> Optional[RevitClient]:
    """
    Try to connect to any available RevitMCPBridge.

    Tries 2026 first, then 2025.

    Returns:
        Connected RevitClient or None if no bridge available
    """
    for version in [RevitVersion.REVIT_2026, RevitVersion.REVIT_2025]:
        client = RevitClient(version.value, verbose=verbose)
        if client.ping():
            if verbose:
                print(f"[RevitClient] Connected to {version.value}")
            return client

    return None


# =============================================================================
# CLI TESTING
# =============================================================================

def main():
    """Test RevitMCP connection."""
    import argparse

    parser = argparse.ArgumentParser(description="Test RevitMCPBridge connection")
    parser.add_argument("--pipe", default="RevitMCPBridge2025", help="Pipe name")
    parser.add_argument("--method", default="ping", help="Method to call")
    parser.add_argument("--params", default="{}", help="JSON params")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    print(f"Testing connection to {args.pipe}...")

    client = RevitClient(args.pipe, verbose=args.verbose)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError:
        print(f"Invalid JSON params: {args.params}")
        return 1

    result = client.call(args.method, params)

    print(f"\nSuccess: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Data: {json.dumps(result.data, indent=2)}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
