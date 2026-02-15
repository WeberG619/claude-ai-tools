#!/usr/bin/env python3
"""
Revit MCP Client for Python
============================
Named pipe client for communicating with RevitMCPBridge2026.
Provides Python interface to extract schedule data, modify parameters,
and orchestrate compliance checking workflows.

Author: BIM Ops Studio
"""

import json
import os
import sys
import time
import struct
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import logging

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MCPResponse:
    """Response from RevitMCPBridge"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class RevitMCPClient:
    """
    Python client for RevitMCPBridge2026 named pipe communication.

    Provides methods to:
    - Connect to Revit via named pipe
    - Extract schedule data (doors, windows, walls, rooms)
    - Get and set element parameters
    - Query project information

    Example:
        client = RevitMCPClient()
        if client.connect():
            doors = client.get_schedule_data("Door Schedule")
            client.disconnect()
    """

    DEFAULT_PIPE_NAME = "RevitMCPBridge2026"

    def __init__(self, pipe_name: str = None, timeout: float = 30.0):
        """
        Initialize the MCP client.

        Args:
            pipe_name: Named pipe name (default: RevitMCPBridge2026)
            timeout: Request timeout in seconds
        """
        self.pipe_name = pipe_name or self.DEFAULT_PIPE_NAME
        self.timeout = timeout
        self._pipe = None
        self._connected = False
        self._last_error = None

    @property
    def pipe_path(self) -> str:
        """Get the full named pipe path."""
        # For WSL, we need to use Windows path format
        return f"\\\\.\\pipe\\{self.pipe_name}"

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._pipe is not None

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    def connect(self, retry_count: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Connect to the RevitMCPBridge named pipe.

        Args:
            retry_count: Number of connection retries
            retry_delay: Delay between retries in seconds

        Returns:
            True if connected successfully
        """
        for attempt in range(retry_count):
            try:
                # Try to connect via PowerShell/Windows pipe
                self._connected = self._test_connection()
                if self._connected:
                    logger.info(f"Connected to {self.pipe_name}")
                    return True

            except Exception as e:
                self._last_error = str(e)
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

            if attempt < retry_count - 1:
                time.sleep(retry_delay)

        logger.error(f"Failed to connect to {self.pipe_name} after {retry_count} attempts")
        return False

    def _test_connection(self) -> bool:
        """Test the connection with a simple ping command."""
        try:
            result = self._send_raw_command("ping", {})
            return result is not None and result.get("success", False)
        except:
            return False

    def disconnect(self):
        """Disconnect from the named pipe."""
        self._pipe = None
        self._connected = False
        logger.info("Disconnected from RevitMCPBridge")

    def _send_raw_command(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Send a command to Revit via named pipe using PowerShell bridge.

        This uses PowerShell to communicate with the Windows named pipe
        since Python in WSL cannot directly access Windows named pipes.
        """
        import subprocess

        # Build the request JSON
        request = json.dumps({
            "method": method,
            "params": params
        })

        # PowerShell script to send command via named pipe
        ps_script = f'''
$pipeName = "{self.pipe_name}"
$timeout = {int(self.timeout * 1000)}

try {{
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect($timeout)

    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)

    $writer.AutoFlush = $true
    $writer.WriteLine(@'
{request}
'@)

    $response = $reader.ReadLine()

    $pipe.Close()

    Write-Output $response
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
'''

        try:
            # Run PowerShell command
            result = _run_ps(ps_script, timeout=self.timeout + 5)

            if result.returncode != 0:
                self._last_error = result.stderr.strip()
                logger.error(f"PowerShell error: {self._last_error}")
                return None

            response_text = result.stdout.strip()
            if response_text:
                return json.loads(response_text)
            return None

        except subprocess.TimeoutExpired:
            self._last_error = "Command timed out"
            return None
        except json.JSONDecodeError as e:
            self._last_error = f"Invalid JSON response: {e}"
            return None
        except Exception as e:
            self._last_error = str(e)
            return None

    def send_command(self, method: str, params: Dict[str, Any] = None) -> MCPResponse:
        """
        Send a command to RevitMCPBridge.

        Args:
            method: The MCP method name
            params: Parameters for the method

        Returns:
            MCPResponse with success status and data
        """
        params = params or {}

        try:
            result = self._send_raw_command(method, params)

            if result is None:
                return MCPResponse(
                    success=False,
                    error=self._last_error or "No response from Revit"
                )

            return MCPResponse(
                success=result.get("success", False),
                data=result,
                error=result.get("error"),
                raw_response=json.dumps(result)
            )

        except Exception as e:
            return MCPResponse(
                success=False,
                error=str(e)
            )

    # =========================================================================
    # PROJECT INFORMATION
    # =========================================================================

    def get_project_info(self) -> MCPResponse:
        """Get information about the currently open Revit project."""
        return self.send_command("getProjectInfo", {})

    def get_levels(self) -> MCPResponse:
        """Get all levels in the project."""
        return self.send_command("getLevels", {})

    # =========================================================================
    # SCHEDULE METHODS
    # =========================================================================

    def get_all_schedules(self) -> MCPResponse:
        """
        Get a list of all schedules in the project.

        Returns:
            MCPResponse with list of schedule names and IDs
        """
        return self.send_command("getAllSchedules", {})

    def get_schedule_by_name(self, schedule_name: str) -> Optional[Dict]:
        """
        Find a schedule by name.

        Args:
            schedule_name: Name of the schedule to find

        Returns:
            Schedule info dict or None if not found
        """
        response = self.get_all_schedules()
        if not response.success:
            return None

        # getAllSchedules returns 'schedules' array with 'scheduleName' and 'scheduleId'
        schedules = response.data.get("schedules", [])
        for schedule in schedules:
            sched_name = schedule.get("scheduleName", schedule.get("name", ""))
            if sched_name.lower() == schedule_name.lower():
                # Normalize to standard format
                return {
                    "id": schedule.get("scheduleId", schedule.get("id")),
                    "name": sched_name,
                    "category": schedule.get("category"),
                    "fieldCount": schedule.get("fieldCount", 0)
                }

        return None

    def get_schedule_data(self, schedule_id_or_name: Union[int, str],
                          include_headers: bool = True) -> MCPResponse:
        """
        Get data from a schedule.

        Args:
            schedule_id_or_name: Schedule ID (int) or name (str)
            include_headers: Whether to include column headers

        Returns:
            MCPResponse with schedule data as rows/columns
        """
        # If string, look up by name first
        if isinstance(schedule_id_or_name, str):
            schedule = self.get_schedule_by_name(schedule_id_or_name)
            if schedule is None:
                return MCPResponse(
                    success=False,
                    error=f"Schedule '{schedule_id_or_name}' not found"
                )
            schedule_id = schedule.get("id")
        else:
            schedule_id = schedule_id_or_name

        return self.send_command("getScheduleData", {
            "scheduleId": schedule_id,
            "includeHeaders": include_headers
        })

    def get_schedule_fields(self, schedule_id: int) -> MCPResponse:
        """
        Get the field definitions for a schedule.

        Args:
            schedule_id: The schedule element ID

        Returns:
            MCPResponse with field definitions
        """
        return self.send_command("getScheduleFields", {"scheduleId": schedule_id})

    def get_door_schedule(self, schedule_name: str = "Door Schedule") -> List[Dict]:
        """
        Get door schedule data in a structured format.

        Args:
            schedule_name: Name of the door schedule

        Returns:
            List of door dictionaries with normalized field names
        """
        response = self.get_schedule_data(schedule_name)
        if not response.success:
            logger.error(f"Failed to get door schedule: {response.error}")
            return []

        return self._parse_schedule_to_dicts(response.data)

    def get_window_schedule(self, schedule_name: str = "Window Schedule") -> List[Dict]:
        """
        Get window schedule data in a structured format.

        Args:
            schedule_name: Name of the window schedule

        Returns:
            List of window dictionaries with normalized field names
        """
        response = self.get_schedule_data(schedule_name)
        if not response.success:
            logger.error(f"Failed to get window schedule: {response.error}")
            return []

        return self._parse_schedule_to_dicts(response.data)

    def get_wall_schedule(self, schedule_name: str = "Wall Schedule") -> List[Dict]:
        """
        Get wall type schedule data.

        Args:
            schedule_name: Name of the wall schedule

        Returns:
            List of wall type dictionaries
        """
        response = self.get_schedule_data(schedule_name)
        if not response.success:
            logger.error(f"Failed to get wall schedule: {response.error}")
            return []

        return self._parse_schedule_to_dicts(response.data)

    def get_room_schedule(self, schedule_name: str = "Room Schedule") -> List[Dict]:
        """
        Get room schedule data.

        Args:
            schedule_name: Name of the room schedule

        Returns:
            List of room dictionaries
        """
        response = self.get_schedule_data(schedule_name)
        if not response.success:
            logger.error(f"Failed to get room schedule: {response.error}")
            return []

        return self._parse_schedule_to_dicts(response.data)

    def _parse_schedule_to_dicts(self, schedule_data: Dict) -> List[Dict]:
        """
        Parse raw schedule data into list of dictionaries.

        Args:
            schedule_data: Raw schedule data from getScheduleData

        Returns:
            List of dictionaries with column headers as keys
        """
        # Handle both response formats
        # Format 1: response.data = { "rows": [...] }
        # Format 2: response.data = { "result": { "data": [...] } }

        if "result" in schedule_data:
            data = schedule_data.get("result", {}).get("data", [])
        else:
            data = schedule_data.get("rows", schedule_data.get("data", []))

        if not data:
            return []

        # Find the header row - usually first row with actual column names
        # Skip empty rows and schedule title rows
        headers = []
        data_start_idx = 0

        for i, row in enumerate(data):
            # Look for a row that has multiple non-empty values
            non_empty = [v for v in row if v and str(v).strip()]
            if len(non_empty) >= 3:
                # Check if this looks like a header row (contains common header keywords)
                row_str = ' '.join(str(v).upper() for v in row)
                if any(kw in row_str for kw in ['MARK', 'TYPE', 'WIDTH', 'HEIGHT', 'SIZE', 'NAME', 'NUMBER']):
                    headers = row
                    data_start_idx = i + 1
                    break

        if not headers:
            # Fallback: use first row with content
            for i, row in enumerate(data):
                if any(v for v in row if v and str(v).strip()):
                    headers = row
                    data_start_idx = i + 1
                    break

        # Get data rows, skip header and empty/group header rows
        result = []
        for row in data[data_start_idx:]:
            # Skip empty rows and group header rows (rows where first cell has value but rest is empty)
            if not row or not any(str(v).strip() for v in row):
                continue

            non_empty_count = sum(1 for v in row if v and str(v).strip())
            first_val = str(row[0]).strip() if row else ""

            # Skip rows that look like group headers (e.g. "1st Floor" with mostly empty cells)
            if non_empty_count <= 2 and first_val and not any(c.isdigit() for c in first_val[:3]):
                continue

            item = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    header = headers[i] if headers[i] else f"Column_{i}"
                    item[header] = value
                else:
                    item[f"Column_{i}"] = value

            # Only add if we have meaningful data
            if item:
                result.append(item)

        return result

    # =========================================================================
    # ELEMENT METHODS
    # =========================================================================

    def get_element_parameters(self, element_id: int) -> MCPResponse:
        """
        Get all parameters for an element.

        Args:
            element_id: The element ID

        Returns:
            MCPResponse with parameter values
        """
        return self.send_command("getElementParameters", {"elementId": element_id})

    def set_parameter_value(self, element_id: int, parameter_name: str,
                           value: Any) -> MCPResponse:
        """
        Set a parameter value on an element.

        Args:
            element_id: The element ID
            parameter_name: Name of the parameter to set
            value: Value to set

        Returns:
            MCPResponse with result
        """
        return self.send_command("setParameterValue", {
            "elementId": element_id,
            "parameterName": parameter_name,
            "value": value
        })

    def set_multiple_parameters(self, updates: List[Dict[str, Any]]) -> MCPResponse:
        """
        Set multiple parameter values in a batch.

        Args:
            updates: List of dicts with elementId, parameterName, value

        Returns:
            MCPResponse with batch results
        """
        return self.send_command("setMultipleParameters", {"updates": updates})

    def get_elements_by_category(self, category: str) -> MCPResponse:
        """
        Get all elements of a specific category.

        Args:
            category: Category name (e.g., "Doors", "Windows", "Walls", "Rooms")

        Returns:
            MCPResponse with element list
        """
        return self.send_command("getElements", {"category": category})

    # =========================================================================
    # DOOR-SPECIFIC METHODS
    # =========================================================================

    def get_all_doors(self, level_name: str = None) -> MCPResponse:
        """
        Get all doors in the project, optionally filtered by level.

        Args:
            level_name: Optional level name to filter by

        Returns:
            MCPResponse with door data
        """
        params = {}
        if level_name:
            params["levelName"] = level_name
        return self.send_command("getDoors", params)

    # =========================================================================
    # WINDOW-SPECIFIC METHODS
    # =========================================================================

    def get_all_windows(self, level_name: str = None) -> MCPResponse:
        """
        Get all windows in the project, optionally filtered by level.

        Args:
            level_name: Optional level name to filter by

        Returns:
            MCPResponse with window data
        """
        params = {}
        if level_name:
            params["levelName"] = level_name
        return self.send_command("getWindows", params)

    # =========================================================================
    # ROOM-SPECIFIC METHODS
    # =========================================================================

    def get_all_rooms(self, level_name: str = None) -> MCPResponse:
        """
        Get all rooms in the project.

        Args:
            level_name: Optional level name to filter by

        Returns:
            MCPResponse with room data
        """
        params = {}
        if level_name:
            params["levelName"] = level_name
        return self.send_command("getRooms", params)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def ping(self) -> bool:
        """
        Test connection to Revit.

        Returns:
            True if connection is working
        """
        response = self.send_command("ping", {})
        return response.success

    def get_active_view(self) -> MCPResponse:
        """Get the currently active view."""
        return self.send_command("getActiveView", {})


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("REVIT MCP CLIENT TEST")
    print("=" * 70)

    client = RevitMCPClient()

    print("\nConnecting to RevitMCPBridge2026...")
    if client.connect():
        print("✓ Connected!")

        # Test ping
        print("\nTesting ping...")
        if client.ping():
            print("✓ Ping successful")
        else:
            print("✗ Ping failed")

        # Get project info
        print("\nGetting project info...")
        response = client.get_project_info()
        if response.success:
            print(f"✓ Project: {response.data}")
        else:
            print(f"✗ Error: {response.error}")

        # Get schedules
        print("\nGetting schedules...")
        response = client.get_all_schedules()
        if response.success:
            schedules = response.data.get("views", [])
            print(f"✓ Found {len(schedules)} schedules")
            for s in schedules[:5]:
                print(f"  - {s.get('name')}")
        else:
            print(f"✗ Error: {response.error}")

        # Try to get door schedule
        print("\nGetting door schedule...")
        doors = client.get_door_schedule()
        if doors:
            print(f"✓ Found {len(doors)} doors")
            if doors:
                print(f"  First door: {doors[0]}")
        else:
            print("✗ No door schedule found or empty")

        client.disconnect()
    else:
        print(f"✗ Failed to connect: {client.last_error}")

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)
