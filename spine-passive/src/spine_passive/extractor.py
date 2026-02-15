"""
Extractor module for Spine Passive Learner.
Handles communication with RevitMCPBridge via named pipes.
"""

import json
import subprocess
import sys
import time
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime

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

from .database import Database

logger = logging.getLogger(__name__)


class RevitExtractor:
    """Extract data from Revit projects via MCP Bridge."""

    PIPE_NAME_2026 = r"\\.\pipe\RevitMCPBridge2026"
    PIPE_NAME_2025 = r"\\.\pipe\RevitMCPBridge2025"

    # Timeouts in seconds
    OPEN_TIMEOUT = 300  # 5 minutes to open
    CLOSE_TIMEOUT = 60  # 1 minute to close
    COMMAND_TIMEOUT = 60  # 1 minute for other commands

    def __init__(self, db: Database, revit_version: str = "2026"):
        self.db = db
        self.revit_version = revit_version
        self.pipe_name = self.PIPE_NAME_2026 if revit_version == "2026" else self.PIPE_NAME_2025

    def send_command(self, method: str, params: Optional[Dict] = None,
                     timeout: int = 60) -> Dict:
        """Send a command to Revit via named pipe using PowerShell."""
        request = {"method": method}
        if params:
            request["params"] = params

        # Format JSON for PowerShell single-quoted string (escape single quotes)
        request_json = json.dumps(request).replace("'", "''")
        pipe_name = "RevitMCPBridge" + self.revit_version
        timeout_ms = timeout * 1000

        ps_script = f"""
$pipeName = "{pipe_name}"
$pipe = $null
try {{
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect({timeout_ms})

    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    $reader = New-Object System.IO.StreamReader($pipe)

    $writer.WriteLine('{request_json}')
    $response = $reader.ReadLine()
    Write-Output $response
}} catch {{
    Write-Output ('{{"success": false, "error": "' + $_.Exception.Message + '"}}')
}} finally {{
    if ($pipe) {{ $pipe.Dispose() }}
}}
"""

        try:
            result = _run_ps(ps_script, timeout=timeout + 30)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr or "PowerShell error"}

            response_text = result.stdout.strip()
            if not response_text:
                return {"success": False, "error": "Empty response from Revit"}

            return json.loads(response_text)

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_revit_running(self) -> bool:
        """Check if Revit with MCP Bridge is running."""
        try:
            result = self.send_command("ping", timeout=5)
            return result.get("success", False)
        except Exception:
            return False

    def open_project(self, filepath: str) -> Tuple[bool, str]:
        """Open a Revit project. Returns (success, message)."""
        logger.info(f"Opening: {filepath}")
        result = self.send_command("openProject", {"filePath": filepath}, self.OPEN_TIMEOUT)

        if result.get("success"):
            return True, result.get("result", {}).get("documentTitle", "Opened")
        return False, result.get("error", "Unknown error")

    def close_project(self, save: bool = False) -> Tuple[bool, str]:
        """Close the active project."""
        logger.info(f"Closing project (save={save})")
        result = self.send_command("closeProject", {"save": save}, self.CLOSE_TIMEOUT)

        if result.get("success"):
            return True, "Closed"
        return False, result.get("error", "Unknown error")

    def get_project_info(self) -> Optional[Dict]:
        """Get project information."""
        result = self.send_command("getProjectInfo")
        if result.get("success"):
            return result.get("result", {})
        logger.warning(f"Failed to get project info: {result.get('error')}")
        return None

    def get_levels(self) -> List[Dict]:
        """Get all levels."""
        result = self.send_command("getLevels")
        if result.get("success"):
            return result.get("result", {}).get("levels", [])
        logger.warning(f"Failed to get levels: {result.get('error')}")
        return []

    def get_sheets(self) -> List[Dict]:
        """Get all sheets."""
        result = self.send_command("getAllSheets")
        if result.get("success"):
            return result.get("result", {}).get("sheets", [])
        logger.warning(f"Failed to get sheets: {result.get('error')}")
        return []

    def get_views(self) -> List[Dict]:
        """Get all views."""
        result = self.send_command("getViews")
        if result.get("success"):
            return result.get("result", {}).get("views", [])
        logger.warning(f"Failed to get views: {result.get('error')}")
        return []

    def get_families(self) -> List[Dict]:
        """Get all families."""
        result = self.send_command("getAllFamilies")
        if result.get("success"):
            return result.get("result", {}).get("families", [])
        logger.warning(f"Failed to get families: {result.get('error')}")
        return []

    def get_wall_types(self) -> List[Dict]:
        """Get all wall types."""
        result = self.send_command("getWallTypes")
        if result.get("success"):
            return result.get("result", {}).get("wallTypes", [])
        logger.warning(f"Failed to get wall types: {result.get('error')}")
        return []

    def get_rooms(self) -> List[Dict]:
        """Get all rooms."""
        result = self.send_command("getRooms")
        if result.get("success"):
            return result.get("result", {}).get("rooms", [])
        logger.warning(f"Failed to get rooms: {result.get('error')}")
        return []

    @staticmethod
    def parse_sheet_number(sheet_number: str) -> Tuple[str, str]:
        """Parse sheet number into discipline and series.

        Examples:
            'A001' -> ('A', '000')
            'A-101' -> ('A', '100')
            'S-2.1' -> ('S', '200')
        """
        # Remove common separators
        clean = sheet_number.upper().replace("-", "").replace(".", "").replace(" ", "")

        # Extract discipline (first letter)
        discipline = clean[0] if clean and clean[0].isalpha() else "X"

        # Extract series (first digit after discipline, then add 00)
        series = "000"
        for i, char in enumerate(clean):
            if char.isdigit():
                series = char + "00"
                break

        return discipline, series

    def extract_all(self, project_id: int) -> Dict:
        """Extract all data from currently open project and save to database."""
        start_time = time.time()
        log_id = self.db.log_extraction_start(project_id)

        try:
            # Clear any existing data
            self.db.clear_project_data(project_id)

            # Get project info
            project_info = self.get_project_info() or {}
            logger.info(f"Project: {project_info.get('projectName', 'Unknown')}")

            # Get levels
            levels = self.get_levels()
            for level in levels:
                self.db.add_level(
                    project_id=project_id,
                    level_name=level.get("name", "Unknown"),
                    elevation_ft=level.get("elevation", 0) / 1.0,  # Already in feet
                    is_building_story=level.get("isBuildingStory", True)
                )
            logger.info(f"Extracted {len(levels)} levels")

            # Get sheets
            sheets = self.get_sheets()
            for sheet in sheets:
                sheet_number = sheet.get("sheetNumber", "")
                discipline, series = self.parse_sheet_number(sheet_number)
                self.db.add_sheet(
                    project_id=project_id,
                    sheet_number=sheet_number,
                    sheet_name=sheet.get("sheetName", ""),
                    discipline=discipline,
                    sheet_series=series,
                    viewport_count=sheet.get("viewportCount", 0),
                    titleblock_type=sheet.get("titleblock", None)
                )
            logger.info(f"Extracted {len(sheets)} sheets")

            # Get views
            views = self.get_views()
            for view in views:
                self.db.add_view(
                    project_id=project_id,
                    view_name=view.get("name", "Unknown"),
                    view_type=view.get("viewType", "Unknown"),
                    level_name=view.get("levelName"),
                    is_on_sheet=view.get("isOnSheet", False),
                    detail_level=view.get("detailLevel"),
                    scale=view.get("scale")
                )
            logger.info(f"Extracted {len(views)} views")

            # Get families
            families = self.get_families()
            for family in families:
                self.db.add_family(
                    project_id=project_id,
                    family_name=family.get("familyName", "Unknown"),
                    family_category=family.get("categoryName", "Unknown"),
                    instance_count=family.get("instanceCount", 0),
                    type_count=family.get("typeCount", 1)
                )
            logger.info(f"Extracted {len(families)} families")

            # Get wall types
            wall_types = self.get_wall_types()
            for wt in wall_types:
                self.db.add_wall_type(
                    project_id=project_id,
                    type_name=wt.get("name", "Unknown"),
                    wall_function=wt.get("function"),
                    width_inches=wt.get("width"),
                    instance_count=wt.get("instanceCount", 0)
                )
            logger.info(f"Extracted {len(wall_types)} wall types")

            # Get rooms
            rooms = self.get_rooms()
            for room in rooms:
                self.db.add_room(
                    project_id=project_id,
                    room_name=room.get("name", ""),
                    room_number=room.get("number", ""),
                    level_name=room.get("levelName", ""),
                    area_sqft=room.get("area", 0)
                )
            logger.info(f"Extracted {len(rooms)} rooms")

            # Update project metadata
            self.db.update_project_metadata(project_id, {
                "project_name": project_info.get("projectName"),
                "project_number": project_info.get("projectNumber"),
                "project_address": project_info.get("projectAddress"),
                "client_name": project_info.get("clientName"),
                "project_status": project_info.get("projectStatus"),
                "level_count": len(levels),
                "sheet_count": len(sheets),
                "view_count": len(views),
                "room_count": len(rooms),
                "family_count": len(families),
                "wall_type_count": len(wall_types)
            })

            duration = time.time() - start_time
            self.db.update_project_status(project_id, "complete", duration=duration)
            self.db.log_extraction_complete(log_id, len(sheets), len(views), len(families))

            return {
                "success": True,
                "levels": len(levels),
                "sheets": len(sheets),
                "views": len(views),
                "families": len(families),
                "wall_types": len(wall_types),
                "rooms": len(rooms),
                "duration": duration
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Extraction failed: {error_msg}")
            self.db.update_project_status(project_id, "error", error=error_msg)
            self.db.log_extraction_complete(log_id, 0, 0, 0, status="error", error=error_msg)
            return {"success": False, "error": error_msg}

    @staticmethod
    def convert_wsl_to_windows_path(wsl_path: str) -> str:
        r"""Convert WSL path (/mnt/d/...) to Windows path (D:\...)."""
        if wsl_path.startswith("/mnt/"):
            # Extract drive letter and rest of path
            parts = wsl_path[5:].split("/", 1)  # Skip "/mnt/"
            if len(parts) >= 1:
                drive = parts[0].upper()
                rest = parts[1] if len(parts) > 1 else ""
                return f"{drive}:\\{rest.replace('/', '\\')}"
        return wsl_path

    def run_batch_extraction(self, limit: Optional[int] = None,
                              cooldown: int = 5) -> Dict:
        """Run batch extraction on pending projects."""
        pending = self.db.get_pending_projects(limit)
        logger.info(f"Found {len(pending)} pending projects")

        results = {
            "total": len(pending),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "projects": []
        }

        for i, project in enumerate(pending, 1):
            filepath_raw = project["filepath"]
            # Convert WSL path to Windows path if needed
            filepath = self.convert_wsl_to_windows_path(filepath_raw)
            project_id = project["id"]
            filename = project["filename"]

            logger.info(f"\n[{i}/{len(pending)}] Processing: {filename}")

            # Check if file still exists
            if not Path(filepath).exists():
                logger.warning(f"File not found, skipping: {filepath}")
                self.db.update_project_status(project_id, "error", error="File not found")
                results["skipped"] += 1
                continue

            # Open project
            self.db.update_project_status(project_id, "in_progress")
            success, msg = self.open_project(filepath)
            if not success:
                logger.error(f"Failed to open: {msg}")
                self.db.update_project_status(project_id, "error", error=f"Open failed: {msg}")
                results["failed"] += 1
                results["projects"].append({"file": filename, "status": "open_failed", "error": msg})
                continue

            # Wait for Revit to stabilize
            time.sleep(3)

            # Extract all data
            extraction = self.extract_all(project_id)

            # Close project (no save)
            close_success, close_msg = self.close_project(save=False)
            if not close_success:
                logger.warning(f"Close warning: {close_msg}")

            if extraction.get("success"):
                results["success"] += 1
                results["projects"].append({
                    "file": filename,
                    "status": "success",
                    "sheets": extraction.get("sheets", 0),
                    "views": extraction.get("views", 0),
                    "duration": extraction.get("duration", 0)
                })
            else:
                results["failed"] += 1
                results["projects"].append({
                    "file": filename,
                    "status": "extraction_failed",
                    "error": extraction.get("error")
                })

            # Cooldown between files
            if i < len(pending):
                logger.info(f"Cooldown {cooldown}s before next file...")
                time.sleep(cooldown)

        return results


def scan_for_revit_files(root_path: str, db: Database,
                          recursive: bool = True) -> Dict:
    """Scan a directory for .rvt files and add them to the database."""
    root = Path(root_path)
    if not root.exists():
        return {"error": f"Path does not exist: {root_path}"}

    # Directories to skip
    SKIP_DIRS = {
        '$RECYCLE.BIN', 'System Volume Information', '.git', '__pycache__',
        'node_modules', '.venv', 'venv', 'AppData', '$AV_NLL'
    }

    results = {
        "scanned": 0,
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }

    pattern = "**/*.rvt" if recursive else "*.rvt"

    for rvt_file in root.glob(pattern):
        results["scanned"] += 1

        # Skip backup files
        if ".0001.rvt" in str(rvt_file) or "_backup" in str(rvt_file).lower():
            results["skipped"] += 1
            continue

        # Skip files in skip directories
        if any(skip in rvt_file.parts for skip in SKIP_DIRS):
            results["skipped"] += 1
            continue

        try:
            filepath = str(rvt_file.resolve())
            filename = rvt_file.name
            stat = rvt_file.stat()

            # Check if already in database
            existing = db.get_project_by_path(filepath)

            db.add_project(
                filepath=filepath,
                filename=filename,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime)
            )

            if existing:
                results["updated"] += 1
            else:
                results["added"] += 1
                logger.info(f"Added: {filename}")

        except Exception as e:
            results["errors"].append({"file": str(rvt_file), "error": str(e)})

    return results
