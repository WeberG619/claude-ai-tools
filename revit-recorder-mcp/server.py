#!/usr/bin/env python3
"""
Revit Recorder MCP Server

Records screen when working in Revit + Claude Code, logs MCP calls,
and enables AI-assisted editing with voice narration.

Uses FFmpeg for recording - no OBS required, runs in background.
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple
import sqlite3
import threading

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP library not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
RECORDINGS_DIR = BASE_DIR / "recordings"
DB_PATH = BASE_DIR / "sessions.db"
SYSTEM_STATE_PATH = Path(r"D:\_CLAUDE-TOOLS\system-bridge\live_state.json")
FFMPEG_PATH = r"C:\Program Files\ffmpeg-2025-03-20-git-76f09ab647-full_build\bin\ffmpeg.exe"

# Ensure directories exist
RECORDINGS_DIR.mkdir(exist_ok=True)


def init_db():
    """Initialize SQLite database for session tracking."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            recording_file TEXT,
            revit_project TEXT,
            status TEXT DEFAULT 'recording',
            duration_seconds REAL,
            file_size_mb REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mcp_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT NOT NULL,
            method TEXT NOT NULL,
            params TEXT,
            result_preview TEXT,
            duration_ms INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS markers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT NOT NULL,
            marker_type TEXT,
            description TEXT,
            video_timestamp_sec REAL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()


class RevitRecorder:
    """Records Revit sessions using FFmpeg - no OBS required."""

    def __init__(self):
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.current_session_id: Optional[int] = None
        self.session_start_time: Optional[datetime] = None
        self.recording_file: Optional[str] = None

    def get_system_state(self) -> Optional[Dict]:
        """Read live system state from daemon."""
        try:
            if SYSTEM_STATE_PATH.exists():
                with open(SYSTEM_STATE_PATH) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not read system state: {e}")
        return None

    def get_revit_info(self) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Get Revit status and monitor info.
        Returns: (is_running, project_name, monitor_info)
        """
        state = self.get_system_state()
        if not state:
            return False, None, None

        apps = state.get("applications", [])
        monitors = state.get("monitors", {}).get("screens", [])

        for app in apps:
            if app.get("ProcessName") == "Revit":
                title = app.get("MainWindowTitle", "")
                monitor_idx = app.get("MonitorIndex", 0)

                # Extract project name
                project = None
                if " - [" in title:
                    project = title.split(" - [")[1].split(" - ")[0]

                # Get monitor info
                monitor_info = None
                if 0 <= monitor_idx < len(monitors):
                    m = monitors[monitor_idx]
                    monitor_info = {
                        "index": monitor_idx,
                        "x": m.get("x", 0),
                        "y": m.get("y", 0),
                        "width": m.get("width", 1920),
                        "height": m.get("height", 1080)
                    }

                return True, project, monitor_info

        return False, None, None

    def is_claude_code_running(self) -> bool:
        """Check if Claude Code (VS Code) is running."""
        state = self.get_system_state()
        if not state:
            return False

        for app in state.get("applications", []):
            if app.get("ProcessName") == "Code":
                return True
        return False

    @property
    def is_recording(self) -> bool:
        return self.ffmpeg_process is not None and self.ffmpeg_process.poll() is None

    def start_recording(self, project_name: str = None, fps: int = 30, quality: str = "medium") -> Dict:
        """Start FFmpeg screen recording."""
        if self.is_recording:
            return {
                "success": False,
                "error": "Already recording",
                "session_id": self.current_session_id
            }

        # Auto-detect Revit project and monitor
        is_revit, detected_project, monitor_info = self.get_revit_info()

        if project_name is None:
            project_name = detected_project or "Unknown"

        # Default monitor if Revit not detected
        if monitor_info is None:
            monitor_info = {"index": 0, "x": 0, "y": 0, "width": 2560, "height": 1440}

        # Quality presets
        quality_presets = {
            "low": {"crf": 28, "preset": "ultrafast"},
            "medium": {"crf": 23, "preset": "fast"},
            "high": {"crf": 18, "preset": "medium"}
        }
        q = quality_presets.get(quality, quality_presets["medium"])

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:50]
        self.recording_file = f"revit_{safe_name}_{timestamp}.mp4"
        output_path = RECORDINGS_DIR / self.recording_file

        # Build FFmpeg command
        cmd = [
            FFMPEG_PATH,
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-offset_x", str(abs(monitor_info["x"])),
            "-offset_y", str(monitor_info["y"]),
            "-video_size", f"{monitor_info['width']}x{monitor_info['height']}",
            "-i", "desktop",
            "-c:v", "libx264",
            "-crf", str(q["crf"]),
            "-preset", q["preset"],
            "-pix_fmt", "yuv420p",
            "-y",
            str(output_path)
        ]

        try:
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.session_start_time = datetime.now()

            # Create database session
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (start_time, recording_file, revit_project, status)
                VALUES (?, ?, ?, 'recording')
            ''', (self.session_start_time.isoformat(), self.recording_file, project_name))
            self.current_session_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Started recording session {self.current_session_id}: {self.recording_file}")

            return {
                "success": True,
                "session_id": self.current_session_id,
                "recording_file": self.recording_file,
                "output_path": str(output_path),
                "project": project_name,
                "monitor": monitor_info["index"],
                "resolution": f"{monitor_info['width']}x{monitor_info['height']}",
                "fps": fps,
                "quality": quality
            }

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return {"success": False, "error": str(e)}

    def stop_recording(self) -> Dict:
        """Stop FFmpeg recording."""
        if not self.is_recording:
            return {"success": False, "error": "Not recording"}

        try:
            # Send 'q' to FFmpeg for graceful stop
            self.ffmpeg_process.stdin.write(b'q')
            self.ffmpeg_process.stdin.flush()

            try:
                self.ffmpeg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)

            end_time = datetime.now()
            duration = (end_time - self.session_start_time).total_seconds() if self.session_start_time else 0

            # Get file size
            output_path = RECORDINGS_DIR / self.recording_file if self.recording_file else None
            file_size_mb = 0
            if output_path and output_path.exists():
                file_size_mb = round(output_path.stat().st_size / (1024*1024), 2)

            # Update database
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions SET end_time = ?, status = 'completed',
                duration_seconds = ?, file_size_mb = ?
                WHERE id = ?
            ''', (end_time.isoformat(), duration, file_size_mb, self.current_session_id))
            conn.commit()
            conn.close()

            session_id = self.current_session_id
            recording_file = self.recording_file

            self.ffmpeg_process = None
            self.current_session_id = None
            self.session_start_time = None
            self.recording_file = None

            logger.info(f"Stopped recording session {session_id}, duration: {duration:.1f}s, size: {file_size_mb}MB")

            return {
                "success": True,
                "session_id": session_id,
                "recording_file": recording_file,
                "duration_seconds": round(duration, 1),
                "file_size_mb": file_size_mb
            }

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return {"success": False, "error": str(e)}

    def log_mcp_call(self, method: str, params: Dict = None, result_preview: str = None, duration_ms: int = None) -> Dict:
        """Log an MCP call during recording."""
        if not self.current_session_id:
            return {"success": False, "error": "No active recording session"}

        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mcp_calls (session_id, timestamp, method, params, result_preview, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.current_session_id,
                datetime.now().isoformat(),
                method,
                json.dumps(params) if params else None,
                result_preview[:500] if result_preview else None,
                duration_ms
            ))
            call_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return {"success": True, "call_id": call_id}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_marker(self, marker_type: str, description: str) -> Dict:
        """Add a marker to the current recording."""
        if not self.current_session_id:
            return {"success": False, "error": "No active recording session"}

        try:
            video_timestamp = (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0

            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO markers (session_id, timestamp, marker_type, description, video_timestamp_sec)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.current_session_id,
                datetime.now().isoformat(),
                marker_type,
                description,
                video_timestamp
            ))
            marker_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return {"success": True, "marker_id": marker_id, "video_timestamp_sec": round(video_timestamp, 1)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session_info(self, session_id: int = None) -> Dict:
        """Get information about a recording session."""
        sid = session_id or self.current_session_id
        if not sid:
            return {"success": False, "error": "No session specified"}

        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM sessions WHERE id = ?', (sid,))
            session = cursor.fetchone()

            if not session:
                return {"success": False, "error": "Session not found"}

            cursor.execute('SELECT COUNT(*) FROM mcp_calls WHERE session_id = ?', (sid,))
            mcp_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM markers WHERE session_id = ?', (sid,))
            marker_count = cursor.fetchone()[0]

            conn.close()

            return {
                "success": True,
                "session": {
                    "id": session[0],
                    "start_time": session[1],
                    "end_time": session[2],
                    "recording_file": session[3],
                    "revit_project": session[4],
                    "status": session[5],
                    "duration_seconds": session[6],
                    "file_size_mb": session[7],
                    "mcp_calls": mcp_count,
                    "markers": marker_count
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_sessions(self, limit: int = 20) -> Dict:
        """List recent recording sessions."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, start_time, end_time, recording_file, revit_project, status, duration_seconds, file_size_mb
                FROM sessions ORDER BY start_time DESC LIMIT ?
            ''', (limit,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row[0],
                    "start_time": row[1],
                    "end_time": row[2],
                    "recording_file": row[3],
                    "revit_project": row[4],
                    "status": row[5],
                    "duration_seconds": row[6],
                    "file_size_mb": row[7]
                })

            conn.close()
            return {"success": True, "sessions": sessions}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session_mcp_calls(self, session_id: int) -> Dict:
        """Get all MCP calls for a session."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, method, params, result_preview, duration_ms
                FROM mcp_calls WHERE session_id = ? ORDER BY timestamp
            ''', (session_id,))

            calls = []
            for row in cursor.fetchall():
                calls.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "method": row[2],
                    "params": json.loads(row[3]) if row[3] else None,
                    "result_preview": row[4],
                    "duration_ms": row[5]
                })

            conn.close()
            return {"success": True, "calls": calls}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session_markers(self, session_id: int) -> Dict:
        """Get all markers for a session."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, marker_type, description, video_timestamp_sec
                FROM markers WHERE session_id = ? ORDER BY video_timestamp_sec
            ''', (session_id,))

            markers = []
            for row in cursor.fetchall():
                markers.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "marker_type": row[2],
                    "description": row[3],
                    "video_timestamp_sec": row[4]
                })

            conn.close()
            return {"success": True, "markers": markers}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Global recorder instance
recorder = RevitRecorder()


# MCP Server
server = Server("revit-recorder-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="recorder_start",
            description="Start recording the Revit session (uses FFmpeg, no OBS needed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Name of the project (auto-detected from Revit if not specified)"},
                    "fps": {"type": "integer", "default": 30, "enum": [15, 30, 60]},
                    "quality": {"type": "string", "default": "medium", "enum": ["low", "medium", "high"]}
                }
            }
        ),
        Tool(
            name="recorder_stop",
            description="Stop the current recording",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="recorder_status",
            description="Get current recording status and system state",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="recorder_log_mcp",
            description="Log an MCP call during recording (for creating narration script later)",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "MCP method name"},
                    "params": {"type": "object", "description": "Method parameters"},
                    "result_preview": {"type": "string", "description": "Brief preview of result"},
                    "duration_ms": {"type": "integer", "description": "Call duration in milliseconds"}
                },
                "required": ["method"]
            }
        ),
        Tool(
            name="recorder_add_marker",
            description="Add a marker/bookmark to the recording for later editing",
            inputSchema={
                "type": "object",
                "properties": {
                    "marker_type": {"type": "string", "enum": ["highlight", "cut", "narrate", "important", "error"]},
                    "description": {"type": "string", "description": "Description of what happened at this point"}
                },
                "required": ["marker_type", "description"]
            }
        ),
        Tool(
            name="recorder_list_sessions",
            description="List recent recording sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="recorder_get_session",
            description="Get detailed info about a recording session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID (current if not specified)"}
                }
            }
        ),
        Tool(
            name="recorder_get_mcp_calls",
            description="Get all MCP calls logged in a session (for generating narration)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="recorder_get_markers",
            description="Get all markers in a session (for editing)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="recorder_generate_narration",
            description="Generate a narration script from session MCP calls for Andrew voice TTS",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID"},
                    "generate_audio": {"type": "boolean", "default": False, "description": "Also generate audio files"}
                },
                "required": ["session_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "recorder_start":
        result = recorder.start_recording(
            project_name=arguments.get("project_name"),
            fps=arguments.get("fps", 30),
            quality=arguments.get("quality", "medium")
        )
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_stop":
        result = recorder.stop_recording()
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_status":
        is_revit, project, monitor = recorder.get_revit_info()
        is_claude = recorder.is_claude_code_running()

        duration = None
        if recorder.is_recording and recorder.session_start_time:
            duration = round((datetime.now() - recorder.session_start_time).total_seconds(), 1)

        status = {
            "is_recording": recorder.is_recording,
            "current_session_id": recorder.current_session_id,
            "recording_file": recorder.recording_file,
            "duration_seconds": duration,
            "revit_running": is_revit,
            "revit_project": project,
            "revit_monitor": monitor.get("index") if monitor else None,
            "claude_code_running": is_claude,
            "ready_for_recording": is_revit
        }
        return [TextContent(type="text", text=json.dumps(status))]

    elif name == "recorder_log_mcp":
        result = recorder.log_mcp_call(
            method=arguments["method"],
            params=arguments.get("params"),
            result_preview=arguments.get("result_preview"),
            duration_ms=arguments.get("duration_ms")
        )
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_add_marker":
        result = recorder.add_marker(
            marker_type=arguments["marker_type"],
            description=arguments["description"]
        )
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_list_sessions":
        result = recorder.list_sessions(limit=arguments.get("limit", 20))
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_get_session":
        result = recorder.get_session_info(session_id=arguments.get("session_id"))
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_get_mcp_calls":
        result = recorder.get_session_mcp_calls(session_id=arguments["session_id"])
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_get_markers":
        result = recorder.get_session_markers(session_id=arguments["session_id"])
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "recorder_generate_narration":
        # Get session data
        session_result = recorder.get_session_info(arguments["session_id"])
        if not session_result.get("success"):
            return [TextContent(type="text", text=json.dumps(session_result))]

        calls_result = recorder.get_session_mcp_calls(arguments["session_id"])
        markers_result = recorder.get_session_markers(arguments["session_id"])

        session = session_result["session"]
        calls = calls_result.get("calls", [])
        markers = markers_result.get("markers", [])

        # Generate narration script
        script_lines = [
            f"# Narration Script: {session['revit_project']}",
            f"# Recorded: {session['start_time']}",
            f"# Duration: {session.get('duration_seconds', 0):.0f} seconds",
            f"# MCP Calls: {len(calls)}",
            "",
            "## Introduction",
            f"In this session, we're working with {session['revit_project']} in Revit.",
            ""
        ]

        # Group calls by time for narrative flow
        for call in calls:
            method = call['method']
            params = call.get('params', {})

            # Generate human-readable description
            if method.startswith("create"):
                action = f"Creating {method.replace('create', '').replace('_', ' ').lower()}"
            elif method.startswith("get"):
                action = f"Retrieving {method.replace('get', '').replace('_', ' ').lower()}"
            elif method.startswith("set"):
                action = f"Setting {method.replace('set', '').replace('_', ' ').lower()}"
            elif method.startswith("place"):
                action = f"Placing {method.replace('place', '').replace('_', ' ').lower()}"
            elif method.startswith("delete"):
                action = f"Removing {method.replace('delete', '').replace('_', ' ').lower()}"
            else:
                action = f"Executing {method.replace('_', ' ')}"

            # Extract timestamp for video reference
            ts = call['timestamp'].split('T')[1][:8] if 'T' in call['timestamp'] else ""
            script_lines.append(f"[{ts}] {action}")

            if params and len(params) > 0:
                param_items = list(params.items())[:3]
                param_str = ", ".join(f"{k}={v}" for k, v in param_items)
                if len(param_str) > 80:
                    param_str = param_str[:77] + "..."
                script_lines.append(f"  with {param_str}")
            script_lines.append("")

        # Add markers section
        if markers:
            script_lines.append("\n## Key Moments")
            for marker in markers:
                script_lines.append(f"[{marker['video_timestamp_sec']:.1f}s] {marker['marker_type'].upper()}: {marker['description']}")

        script = "\n".join(script_lines)

        # Save script to file
        script_file = RECORDINGS_DIR / f"narration_session_{arguments['session_id']}.txt"
        with open(script_file, 'w') as f:
            f.write(script)

        result = {
            "success": True,
            "script_file": str(script_file),
            "script_preview": script[:1500] if len(script) > 1500 else script,
            "total_calls": len(calls),
            "total_markers": len(markers)
        }

        # Optionally generate audio
        if arguments.get("generate_audio", False):
            try:
                from narrator import generate_narration_audio
                audio_result = asyncio.get_event_loop().run_until_complete(
                    generate_narration_audio(str(script_file), voice="andrew")
                )
                result["audio"] = audio_result
            except Exception as e:
                result["audio_error"] = str(e)

        return [TextContent(type="text", text=json.dumps(result))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
