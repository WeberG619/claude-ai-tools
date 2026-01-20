#!/usr/bin/env python3
"""
Claude Daemon - Hardened Persistent Background Service
Runs continuously on Windows, monitoring system state and maintaining
persistent context for Claude Code sessions.

HARDENING FEATURES:
- Crash recovery with automatic restart
- State persistence across restarts
- Health checks and self-healing
- Graceful shutdown with state saving
- Event log rotation
- PID file for process management

Run as: pythonw claude_daemon.py (background)
Or: python claude_daemon.py --console (foreground for testing)
"""

import json
import sqlite3
import subprocess
import os
import sys
import time
import atexit
import signal
import hashlib
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from logging.handlers import RotatingFileHandler

# Optional schema validation (graceful fallback if jsonschema not installed)
try:
    import jsonschema
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False

# Schema versioning constants
SCHEMA_VERSION = 1
DAEMON_VERSION = "2.0.0"  # Hardened version

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")
SCHEMA_DIR = Path(r"D:\agent\schemas")

# State files
STATE_FILE = BASE_DIR / "live_state.json"
PERSISTENT_STATE_FILE = BASE_DIR / "persistent_state.json"  # Survives crashes
PID_FILE = BASE_DIR / "daemon.pid"
HEALTH_FILE = BASE_DIR / "health.json"

# Schema files
LIVE_STATE_SCHEMA_FILE = SCHEMA_DIR / "live_state.schema.json"

# Log files
LOG_FILE = BASE_DIR / "daemon.log"
EVENT_LOG = BASE_DIR / "events.ndjson"  # Newline-delimited JSON (schema-validated events)
EVENT_LOG_LEGACY = BASE_DIR / "events.jsonl"  # Legacy location
AUDIT_LOG = BASE_DIR / "audit.ndjson"  # Security audit trail for tool calls

# Settings
UPDATE_INTERVAL = 10  # seconds between updates
HEALTH_CHECK_INTERVAL = 60  # seconds between health checks
MAX_EVENTS_IN_MEMORY = 100  # keep last N events in memory
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB max log size
LOG_BACKUP_COUNT = 3  # keep 3 rotated logs
MAX_CONSECUTIVE_ERRORS = 10  # restart after this many errors

# Event log rotation settings
EVENT_LOG_MAX_SIZE = 1 * 1024 * 1024  # 1MB max event log size
EVENT_LOG_BACKUP_COUNT = 5  # keep 5 rotated event logs

# Audit log rotation settings
AUDIT_LOG_MAX_SIZE = 2 * 1024 * 1024  # 2MB max audit log size
AUDIT_LOG_BACKUP_COUNT = 10  # keep 10 rotated audit logs (more retention for security)

# Secret redaction patterns (add more as needed)
SECRET_PATTERNS = [
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[email]'),
    (r'password["\']?\s*[:=]\s*["\']?[^"\'}\s]+', 'password=[REDACTED]'),
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'}\s]+', 'api_key=[REDACTED]'),
    (r'secret["\']?\s*[:=]\s*["\']?[^"\'}\s]+', 'secret=[REDACTED]'),
    (r'token["\']?\s*[:=]\s*["\']?[^"\'}\s]+', 'token=[REDACTED]'),
    (r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', 'Bearer [REDACTED]'),
]

# Proactive Alert Settings
SPEAK_SCRIPT = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\speak.py")
MEMORY_WARNING_THRESHOLD = 85  # percent
MEMORY_CRITICAL_THRESHOLD = 92  # percent
ALERT_COOLDOWN = 300  # seconds between repeated alerts of same type

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging with rotation."""
    logger = logging.getLogger('claude_daemon')
    logger.setLevel(logging.INFO)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

    # Console handler for --console mode
    if '--console' in sys.argv:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)

    return logger

logger = setup_logging()

# =============================================================================
# SYSTEM STATE CLASS
# =============================================================================

class SystemState:
    """Tracks complete system state with persistence."""

    def __init__(self):
        self.applications: List[Dict] = []
        self.revit_status: Dict = {}
        self.bluebeam_status: Dict = {}
        self.active_window: str = ""
        self.monitors: Dict = {}
        self.system_info: Dict = {}
        self.clipboard: str = ""
        self.recent_files: List[str] = []
        self.last_update: str = ""
        self.events: List[Dict] = []
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "updates": 0,
            "errors": 0,
            "restarts": 0
        }

    def to_dict(self) -> Dict:
        """Convert state to dict with schema versioning."""
        now = datetime.now()
        data = {
            # Schema versioning fields (required)
            "schema_version": SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "source": {
                "daemon_version": DAEMON_VERSION,
                "hostname": socket.gethostname(),
                "pid": os.getpid()
            },
            # Legacy fields (backwards compatible)
            "timestamp": self.last_update,
            "active_window": self.active_window,
            "monitors": self.monitors,
            "system": self.system_info,
            "clipboard_preview": self.clipboard[:100] + "..." if len(self.clipboard) > 100 else self.clipboard,
            "recent_files": self.recent_files,
            "applications": self.applications,
            "revit": self.revit_status,
            "bluebeam": self.bluebeam_status,
            "recent_events": self.events[-20:],
            "daemon_stats": self.stats
        }
        # Add integrity hash (excluding the hash field itself)
        data["hash"] = self._compute_hash(data)
        return data

    def _compute_hash(self, data: Dict) -> str:
        """Compute SHA256 hash of normalized state data."""
        # Create a copy without the hash field for computing
        data_copy = {k: v for k, v in data.items() if k != "hash"}
        # Sort keys for consistent hashing
        normalized = json.dumps(data_copy, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def to_persistent_dict(self) -> Dict:
        """Full state for persistence (includes all events)."""
        return {
            "timestamp": self.last_update,
            "events": self.events[-MAX_EVENTS_IN_MEMORY:],
            "stats": self.stats,
            "previous_apps": list(getattr(self, '_previous_apps', set()))
        }

    def load_from_persistent(self, data: Dict):
        """Restore state from persistent file."""
        self.events = data.get("events", [])
        self.stats = data.get("stats", self.stats)
        self.stats["restarts"] = self.stats.get("restarts", 0) + 1
        return data.get("previous_apps", [])

# =============================================================================
# MAIN DAEMON CLASS
# =============================================================================

class ClaudeDaemon:
    """Main daemon class with hardening features."""

    def __init__(self):
        self.state = SystemState()
        self.previous_apps: set = set()
        self.running = True
        self.consecutive_errors = 0
        self.last_health_check = datetime.now()

        # Proactive alert tracking
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.revit_was_connected = False
        self.previous_memory_state = "normal"  # normal, warning, critical

        # Load persistent state if exists
        self._load_persistent_state()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        # Write PID file
        self._write_pid_file()

        # Register cleanup on exit
        atexit.register(self._cleanup)

    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except Exception as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _write_pid_file(self):
        """Write PID file for process management."""
        try:
            with open(PID_FILE, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"PID file written: {os.getpid()}")
        except Exception as e:
            logger.error(f"Could not write PID file: {e}")

    def _cleanup(self):
        """Cleanup on exit - save state and remove PID file."""
        logger.info("Cleaning up...")
        self._save_persistent_state()
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except Exception as e:
            logger.error(f"Could not remove PID file: {e}")

    def _load_persistent_state(self):
        """Load state from persistent file after crash/restart."""
        if PERSISTENT_STATE_FILE.exists():
            try:
                with open(PERSISTENT_STATE_FILE) as f:
                    data = json.load(f)
                previous = self.state.load_from_persistent(data)
                self.previous_apps = set(tuple(x) if isinstance(x, list) else x for x in previous)
                logger.info(f"Restored persistent state. Restart #{self.state.stats['restarts']}")
            except Exception as e:
                logger.error(f"Could not load persistent state: {e}")

    def _save_persistent_state(self):
        """Save state for recovery after crash."""
        try:
            self.state._previous_apps = self.previous_apps
            with open(PERSISTENT_STATE_FILE, 'w') as f:
                json.dump(self.state.to_persistent_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save persistent state: {e}")

    def _load_schema(self) -> Optional[Dict]:
        """Load JSON schema for validation. Returns None if unavailable."""
        if not SCHEMA_VALIDATION_AVAILABLE:
            return None
        if not LIVE_STATE_SCHEMA_FILE.exists():
            logger.warning(f"Schema file not found: {LIVE_STATE_SCHEMA_FILE}")
            return None
        try:
            with open(LIVE_STATE_SCHEMA_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load schema: {e}")
            return None

    def _validate_state_data(self, data: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate state data against JSON schema.
        Returns: (is_valid, error_message)
        """
        schema = self._load_schema()
        if schema is None:
            # Schema validation not available, pass through
            return True, None
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _run_powershell_hidden(self, cmd: str, timeout: int = 10) -> Optional[str]:
        """Run PowerShell command completely hidden."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                 '-WindowStyle', 'Hidden', '-Command', cmd],
                capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            return result.stdout.strip() if result.stdout else None
        except subprocess.TimeoutExpired:
            logger.warning(f"PowerShell command timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"PowerShell error: {e}")
            return None

    def speak_alert(self, message: str):
        """Speak an alert message using Edge TTS."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            subprocess.Popen(
                ['powershell', '-WindowStyle', 'Hidden', '-Command',
                 f"python '{SPEAK_SCRIPT}' '{message}'"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            logger.info(f"Spoke alert: {message}")
        except Exception as e:
            logger.error(f"Could not speak alert: {e}")

    def can_alert(self, alert_type: str) -> bool:
        """Check if we can send an alert (respects cooldown)."""
        now = datetime.now()
        last_alert = self.alert_cooldowns.get(alert_type)
        if last_alert and (now - last_alert).total_seconds() < ALERT_COOLDOWN:
            return False
        return True

    def record_alert(self, alert_type: str):
        """Record that we sent an alert."""
        self.alert_cooldowns[alert_type] = datetime.now()

    def check_proactive_alerts(self):
        """Check for conditions that should trigger proactive alerts."""
        alerts_sent = []

        # Check memory usage
        mem_percent = self.state.system_info.get("memory_percent", 0)
        if mem_percent >= MEMORY_CRITICAL_THRESHOLD:
            new_state = "critical"
        elif mem_percent >= MEMORY_WARNING_THRESHOLD:
            new_state = "warning"
        else:
            new_state = "normal"

        # Alert on memory state transitions (not every check)
        if new_state != self.previous_memory_state:
            if new_state == "critical" and self.can_alert("memory_critical"):
                self.speak_alert(f"Warning: Memory usage is critical at {mem_percent} percent. Consider closing some applications.")
                self.record_alert("memory_critical")
                self.log_event("alert", f"Memory critical: {mem_percent}%")
                alerts_sent.append("memory_critical")
            elif new_state == "warning" and self.previous_memory_state == "normal" and self.can_alert("memory_warning"):
                self.speak_alert(f"Notice: Memory usage is high at {mem_percent} percent.")
                self.record_alert("memory_warning")
                self.log_event("alert", f"Memory warning: {mem_percent}%")
                alerts_sent.append("memory_warning")
            self.previous_memory_state = new_state

        # Check Revit connection status change
        revit_connected = self.state.revit_status.get("connected", False)
        if self.revit_was_connected and not revit_connected:
            if self.can_alert("revit_disconnected"):
                self.speak_alert("Revit MCP connection lost. The bridge may need restart.")
                self.record_alert("revit_disconnected")
                self.log_event("alert", "Revit MCP disconnected")
                alerts_sent.append("revit_disconnected")
        elif not self.revit_was_connected and revit_connected:
            # Revit just connected - optionally announce
            self.log_event("info", "Revit MCP connected")
        self.revit_was_connected = revit_connected

        # Check for important app crashes (Revit process gone but was there)
        current_process_names = {a.get("ProcessName", "").lower() for a in self.state.applications}
        previous_process_names = {p[0].lower() for p in self.previous_apps if p[0]}

        important_apps = {"revit", "revu", "acad"}  # Apps to watch
        for app in important_apps:
            if app in previous_process_names and app not in current_process_names:
                if self.can_alert(f"{app}_closed"):
                    app_display = {"revit": "Revit", "revu": "Bluebeam", "acad": "AutoCAD"}.get(app, app)
                    self.speak_alert(f"{app_display} has closed unexpectedly.")
                    self.record_alert(f"{app}_closed")
                    self.log_event("alert", f"{app_display} closed unexpectedly")
                    alerts_sent.append(f"{app}_closed")

        return alerts_sent

    def get_open_applications(self) -> List[Dict]:
        """Get all open windows with position and monitor info - runs completely hidden."""
        ps_cmd = '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Window {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

$screens = [System.Windows.Forms.Screen]::AllScreens
$results = @()

Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | ForEach-Object {
    $rect = New-Object Win32Window+RECT
    $hasRect = [Win32Window]::GetWindowRect($_.MainWindowHandle, [ref]$rect)

    $monitor = "unknown"
    $monitorIndex = -1
    if ($hasRect) {
        $centerX = ($rect.Left + $rect.Right) / 2
        $centerY = ($rect.Top + $rect.Bottom) / 2
        for ($i = 0; $i -lt $screens.Count; $i++) {
            $s = $screens[$i]
            if ($centerX -ge $s.Bounds.X -and $centerX -lt ($s.Bounds.X + $s.Bounds.Width) -and
                $centerY -ge $s.Bounds.Y -and $centerY -lt ($s.Bounds.Y + $s.Bounds.Height)) {
                $monitorIndex = $i
                # Weber layout: x=-5120=left, x=-2560=center, x=0=right (primary is rightmost)
                if ($s.Bounds.X -lt -3000) { $monitor = "left" }
                elseif ($s.Bounds.X -lt -1000) { $monitor = "center" }
                else { $monitor = "right" }
                break
            }
        }
    }

    $results += @{
        ProcessName = $_.ProcessName
        Id = $_.Id
        MainWindowTitle = $_.MainWindowTitle
        Monitor = $monitor
        MonitorIndex = $monitorIndex
        Position = @{
            Left = $rect.Left
            Top = $rect.Top
            Right = $rect.Right
            Bottom = $rect.Bottom
            Width = $rect.Right - $rect.Left
            Height = $rect.Bottom - $rect.Top
        }
    }
}
$results | ConvertTo-Json -Depth 3 -Compress
'''
        output = self._run_powershell_hidden(ps_cmd, timeout=15)

        if output:
            try:
                apps = json.loads(output)
                if isinstance(apps, dict):
                    apps = [apps]
                self.consecutive_errors = 0  # Reset on success
                return apps
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                self.consecutive_errors += 1
        else:
            self.consecutive_errors += 1
        return []

    def get_active_window(self) -> str:
        """Get the currently focused window."""
        ps_cmd = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
}
"@
$hwnd = [Win32]::GetForegroundWindow()
$title = New-Object System.Text.StringBuilder 256
[Win32]::GetWindowText($hwnd, $title, 256) | Out-Null
$title.ToString()
'''
        return self._run_powershell_hidden(ps_cmd, timeout=5) or ""

    def get_revit_status(self) -> Dict:
        """Check Revit MCP connection."""
        try:
            import win32file
            PIPE_NAME = r'\\.\pipe\RevitMCPBridge2026'
            handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )

            # Get document info
            request = {"method": "getDocumentInfo", "params": {}}
            message = json.dumps(request) + '\n'
            win32file.WriteFile(handle, message.encode('utf-8'))
            result, response = win32file.ReadFile(handle, 64 * 1024)
            doc_info = json.loads(response.decode('utf-8').strip())

            # Get active view
            request = {"method": "getActiveView", "params": {}}
            message = json.dumps(request) + '\n'
            win32file.WriteFile(handle, message.encode('utf-8'))
            result, response = win32file.ReadFile(handle, 64 * 1024)
            view_info = json.loads(response.decode('utf-8').strip())

            win32file.CloseHandle(handle)

            return {
                "connected": True,
                "document": doc_info.get("title", "Unknown"),
                "view": view_info.get("viewName", "Unknown"),
                "viewType": view_info.get("viewType", "Unknown")
            }
        except Exception as e:
            return {"connected": False, "error": str(e)[:100]}

    def get_bluebeam_status(self) -> Dict:
        """Get Bluebeam status from window title."""
        for app in self.state.applications:
            if app.get("ProcessName", "").lower() == "revu":
                title = app.get("MainWindowTitle", "")
                if " - Bluebeam" in title:
                    doc_name = title.split(" - Bluebeam")[0]
                    return {"running": True, "document": doc_name}
        return {"running": False}

    def get_monitor_info(self) -> Dict:
        """Get monitor count and layout information."""
        ps_cmd = '''
Add-Type -AssemblyName System.Windows.Forms
$monitors = [System.Windows.Forms.Screen]::AllScreens
$result = @{
    count = $monitors.Count
    primary = $null
    screens = @()
}
foreach ($m in $monitors) {
    $screen = @{
        name = $m.DeviceName
        primary = $m.Primary
        width = $m.Bounds.Width
        height = $m.Bounds.Height
        x = $m.Bounds.X
        y = $m.Bounds.Y
        working_width = $m.WorkingArea.Width
        working_height = $m.WorkingArea.Height
    }
    $result.screens += $screen
    if ($m.Primary) {
        $result.primary = $screen
    }
}
$result | ConvertTo-Json -Depth 3 -Compress
'''
        output = self._run_powershell_hidden(ps_cmd, timeout=5)
        if output:
            try:
                return json.loads(output)
            except:
                pass
        return {"count": 0, "error": "Could not detect monitors"}

    def get_system_info(self) -> Dict:
        """Get system resource information."""
        ps_cmd = '''
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue
$mem = Get-CimInstance Win32_OperatingSystem
$memUsed = [math]::Round(($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / 1MB, 1)
$memTotal = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 1)
$memPercent = [math]::Round((($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize) * 100, 0)
@{
    cpu_percent = [math]::Round($cpu, 0)
    memory_used_gb = $memUsed
    memory_total_gb = $memTotal
    memory_percent = $memPercent
} | ConvertTo-Json -Compress
'''
        output = self._run_powershell_hidden(ps_cmd, timeout=15)
        if output:
            try:
                return json.loads(output)
            except:
                pass
        return {}

    def get_clipboard_text(self) -> str:
        """Get current clipboard text content (if text)."""
        ps_cmd = '''
Add-Type -AssemblyName System.Windows.Forms
$clip = [System.Windows.Forms.Clipboard]::GetText()
if ($clip.Length -gt 500) { $clip = $clip.Substring(0, 500) + "..." }
$clip
'''
        output = self._run_powershell_hidden(ps_cmd, timeout=3)
        return output if output else ""

    def get_recent_files(self) -> List[str]:
        """Get recently accessed files from shell Recent folder."""
        ps_cmd = '''
$recent = "C:\\Users\\rick\\AppData\\Roaming\\Microsoft\\Windows\\Recent"
$exists = Test-Path $recent
if ($exists) {
    $files = Get-ChildItem $recent -Filter *.lnk -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 15
    $files | ForEach-Object { $_.BaseName }
} else {
    "PATH_NOT_FOUND: $recent"
}
'''
        output = self._run_powershell_hidden(ps_cmd, timeout=5)
        logger.info(f"Recent files output: {output[:200] if output else 'NONE'}")
        if output:
            if output.startswith("PATH_NOT_FOUND"):
                logger.warning(f"Recent files path issue: {output}")
                return []
            # Filter out system files and return clean names
            files = [f.strip() for f in output.split('\n') if f.strip()]
            return [f for f in files if not f.startswith('$') and not f.startswith('.')]
        return []

    def sanitize_details(self, details: str) -> str:
        """Remove potentially sensitive info from log details."""
        import re
        for pattern, replacement in SECRET_PATTERNS:
            details = re.sub(pattern, replacement, details, flags=re.IGNORECASE)
        return details

    def log_audit(self, tool_name: str, action: str, files_touched: List[str] = None,
                  parameters: Dict = None, result: str = None, success: bool = True):
        """
        Log a tool call to the audit trail for security tracking.

        Args:
            tool_name: Name of the MCP tool or operation
            action: What action was performed (create, edit, delete, etc.)
            files_touched: List of file paths affected
            parameters: Tool parameters (will be redacted)
            result: Result summary (will be redacted)
            success: Whether the operation succeeded
        """
        # Build audit entry
        audit_entry = {
            "ts": datetime.now().isoformat(),
            "event_type": "tool_call",
            "tool": tool_name,
            "action": action,
            "success": success
        }

        # Add optional fields with redaction
        if files_touched:
            audit_entry["files_touched"] = files_touched
        if parameters:
            # Deep redact parameters
            audit_entry["parameters"] = self._redact_dict(parameters)
        if result:
            audit_entry["result"] = self.sanitize_details(str(result)[:500])

        # Rotate audit log if needed
        self._rotate_audit_log()

        # Append to audit log
        try:
            with open(AUDIT_LOG, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception as e:
            logger.error(f"Could not write audit log: {e}")

        logger.debug(f"Audit: {tool_name} - {action} - success={success}")

    def _redact_dict(self, d: Dict) -> Dict:
        """Recursively redact sensitive values in a dictionary."""
        if not isinstance(d, dict):
            return self.sanitize_details(str(d))

        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [self._redact_dict(item) if isinstance(item, dict)
                              else self.sanitize_details(str(item)) for item in value]
            else:
                result[key] = self.sanitize_details(str(value))
        return result

    def _rotate_audit_log(self):
        """Rotate audit log file if it exceeds max size."""
        try:
            if not AUDIT_LOG.exists():
                return

            file_size = AUDIT_LOG.stat().st_size
            if file_size < AUDIT_LOG_MAX_SIZE:
                return

            # Rotate: audit.ndjson -> audit.ndjson.1, etc.
            for i in range(AUDIT_LOG_BACKUP_COUNT - 1, 0, -1):
                old_file = Path(f"{AUDIT_LOG}.{i}")
                new_file = Path(f"{AUDIT_LOG}.{i + 1}")
                if old_file.exists():
                    if new_file.exists():
                        new_file.unlink()
                    old_file.rename(new_file)

            # Rename current to .1
            backup = Path(f"{AUDIT_LOG}.1")
            if backup.exists():
                backup.unlink()
            AUDIT_LOG.rename(backup)

            logger.info(f"Rotated audit log ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Could not rotate audit log: {e}")

    def log_event(self, event_type: str, details: str, app: str = None,
                  window_title: str = None, path: str = None):
        """
        Log an event to the event log with schema-compliant format.

        Args:
            event_type: Type of event (app_opened, app_closed, focus_changed, etc.)
            details: Human-readable event details
            app: Application/process name (optional)
            window_title: Window title (optional)
            path: File path if applicable (optional)
        """
        # Build schema-compliant event
        event = {
            "ts": datetime.now().isoformat(),
            "event_type": event_type,
            "details": self.sanitize_details(details)
        }

        # Add optional fields if provided
        if app:
            event["app"] = app
        if window_title:
            event["window_title"] = window_title
        if path:
            event["path"] = path

        # Also store in legacy format for in-memory state (backwards compatible)
        legacy_event = {
            "timestamp": event["ts"],
            "type": event_type,
            "details": event["details"]
        }
        self.state.events.append(legacy_event)

        # Trim events in memory
        if len(self.state.events) > MAX_EVENTS_IN_MEMORY:
            self.state.events = self.state.events[-MAX_EVENTS_IN_MEMORY:]

        # Rotate event log if needed
        self._rotate_event_log()

        # Append to event log file
        try:
            with open(EVENT_LOG, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Could not write event log: {e}")

        logger.debug(f"Event: {event_type} - {details[:50]}")

    def _rotate_event_log(self):
        """Rotate event log file if it exceeds max size."""
        try:
            if not EVENT_LOG.exists():
                return

            file_size = EVENT_LOG.stat().st_size
            if file_size < EVENT_LOG_MAX_SIZE:
                return

            # Rotate: events.ndjson -> events.ndjson.1, etc.
            for i in range(EVENT_LOG_BACKUP_COUNT - 1, 0, -1):
                old_file = Path(f"{EVENT_LOG}.{i}")
                new_file = Path(f"{EVENT_LOG}.{i + 1}")
                if old_file.exists():
                    if new_file.exists():
                        new_file.unlink()
                    old_file.rename(new_file)

            # Rename current to .1
            backup = Path(f"{EVENT_LOG}.1")
            if backup.exists():
                backup.unlink()
            EVENT_LOG.rename(backup)

            logger.info(f"Rotated event log ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Could not rotate event log: {e}")

    def detect_changes(self, new_apps: List[Dict]):
        """Detect application open/close events."""
        current_apps = {(a.get("ProcessName", ""), a.get("MainWindowTitle", ""))
                       for a in new_apps}

        for app in current_apps - self.previous_apps:
            if app[0] and app[1]:
                self.log_event(
                    "app_opened",
                    f"{app[0]}: {app[1]}",
                    app=app[0],
                    window_title=app[1]
                )

        for app in self.previous_apps - current_apps:
            if app[0] and app[1]:
                self.log_event(
                    "app_closed",
                    f"{app[0]}: {app[1]}",
                    app=app[0],
                    window_title=app[1]
                )

        self.previous_apps = current_apps

    def update_state(self):
        """Update complete system state."""
        self.state.last_update = datetime.now().isoformat()
        self.state.stats["updates"] += 1

        # Get applications
        new_apps = self.get_open_applications()
        self.detect_changes(new_apps)
        self.state.applications = new_apps

        # Get active window
        new_active = self.get_active_window()
        if new_active and new_active != self.state.active_window:
            self.log_event("focus_changed", new_active, window_title=new_active)
            self.state.active_window = new_active

        # Get Revit status (less frequently - every 5 updates = 50 seconds)
        if not hasattr(self, '_revit_counter'):
            self._revit_counter = 0
        self._revit_counter += 1
        if self._revit_counter >= 5:
            self.state.revit_status = self.get_revit_status()
            self._revit_counter = 0

        # Get Bluebeam status
        self.state.bluebeam_status = self.get_bluebeam_status()

        # Get monitor info (less frequently - every 6 updates = 60 seconds)
        # Initialize to 5 so first update triggers collection
        if not hasattr(self, '_monitor_counter'):
            self._monitor_counter = 5
        self._monitor_counter += 1
        if self._monitor_counter >= 6:
            self.state.monitors = self.get_monitor_info()
            self._monitor_counter = 0

        # Get system info (less frequently - every 6 updates = 60 seconds)
        # Initialize to 5 so first update triggers collection
        if not hasattr(self, '_system_counter'):
            self._system_counter = 5
        self._system_counter += 1
        if self._system_counter >= 6:
            self.state.system_info = self.get_system_info()
            self._system_counter = 0

        # Get clipboard (every 3 updates = 30 seconds)
        if not hasattr(self, '_clipboard_counter'):
            self._clipboard_counter = 0
        self._clipboard_counter += 1
        if self._clipboard_counter >= 3:
            self.state.clipboard = self.get_clipboard_text()
            self._clipboard_counter = 0

        # Get recent files (every 6 updates = 60 seconds)
        # Initialize to 5 so first update triggers collection
        if not hasattr(self, '_recent_counter'):
            self._recent_counter = 5
        self._recent_counter += 1
        if self._recent_counter >= 6:
            self.state.recent_files = self.get_recent_files()
            self._recent_counter = 0

        # Check for proactive alerts (every update after system info is fresh)
        if self._system_counter == 0:  # Just updated system info
            self.check_proactive_alerts()

        # Save state to file
        self.save_state()

    def save_state(self):
        """Save current state to JSON file with atomic write and schema validation."""
        try:
            state_data = self.state.to_dict()

            # Validate against schema before writing
            is_valid, error_msg = self._validate_state_data(state_data)
            if not is_valid:
                logger.error(f"State validation failed: {error_msg}")
                logger.info("Falling back to persistent_state.json")
                # Fall back to persistent state - don't crash, just log
                self._save_persistent_state()
                self.state.stats["errors"] += 1
                return

            # Write to temp file first, then rename (atomic)
            temp_file = STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            temp_file.replace(STATE_FILE)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            self.state.stats["errors"] += 1

    def health_check(self):
        """Perform health check and update health file."""
        now = datetime.now()

        health = {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "pid": os.getpid(),
            "uptime_seconds": (now - datetime.fromisoformat(self.state.stats["started_at"])).total_seconds(),
            "updates": self.state.stats["updates"],
            "errors": self.state.stats["errors"],
            "consecutive_errors": self.consecutive_errors,
            "restarts": self.state.stats["restarts"],
            "memory_events": len(self.state.events),
            "tracked_apps": len(self.state.applications)
        }

        # Check for issues
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS // 2:
            health["status"] = "degraded"
            health["issue"] = f"High error rate: {self.consecutive_errors} consecutive errors"

        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            health["status"] = "critical"
            health["issue"] = "Too many consecutive errors, will restart"

        try:
            with open(HEALTH_FILE, 'w') as f:
                json.dump(health, f, indent=2)
        except Exception as e:
            logger.error(f"Could not write health file: {e}")

        self.last_health_check = now
        return health

    def run(self):
        """Main daemon loop with crash recovery."""
        logger.info(f"Claude Daemon starting (PID: {os.getpid()})...")
        logger.info(f"State file: {STATE_FILE}")
        logger.info(f"Update interval: {UPDATE_INTERVAL}s")

        # Initial state capture
        try:
            self.update_state()
            self.health_check()
        except Exception as e:
            logger.error(f"Error in initial update: {e}")

        while self.running:
            try:
                time.sleep(UPDATE_INTERVAL)
                self.update_state()

                # Periodic health check
                if (datetime.now() - self.last_health_check).total_seconds() >= HEALTH_CHECK_INTERVAL:
                    health = self.health_check()
                    if health["status"] == "critical":
                        logger.error("Critical health status, saving state and exiting for restart...")
                        self._save_persistent_state()
                        break

                # Periodic state persistence (every 5 minutes)
                if self.state.stats["updates"] % 30 == 0:
                    self._save_persistent_state()

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.running = False
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.state.stats["errors"] += 1
                self.consecutive_errors += 1
                time.sleep(30)  # Wait longer on error

        logger.info("Claude Daemon stopped")
        self._cleanup()


# =============================================================================
# WATCHDOG LAUNCHER
# =============================================================================

def check_daemon_running() -> Optional[int]:
    """Check if daemon is already running."""
    if PID_FILE.exists():
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            # Check if process exists
            os.kill(pid, 0)
            return pid
        except (ProcessLookupError, ValueError):
            # Process doesn't exist, remove stale PID file
            PID_FILE.unlink()
        except PermissionError:
            # Process exists but we can't signal it
            return pid
    return None


def main():
    """Main entry point with watchdog support."""
    if '--query' in sys.argv:
        # Query mode - read current state file
        try:
            idx = sys.argv.index('--query')
            query_type = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "full"

            if STATE_FILE.exists():
                with open(STATE_FILE) as f:
                    state = json.load(f)
                print(json.dumps(state, indent=2))
            else:
                print('{"error": "No state file found. Is daemon running?"}')
        except Exception as e:
            print(f'{{"error": "{e}"}}')

    elif '--health' in sys.argv:
        # Health check mode
        if HEALTH_FILE.exists():
            with open(HEALTH_FILE) as f:
                print(f.read())
        else:
            print('{"error": "No health file found. Is daemon running?"}')

    elif '--stop' in sys.argv:
        # Stop daemon
        pid = check_daemon_running()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to daemon (PID: {pid})")
            except Exception as e:
                print(f"Could not stop daemon: {e}")
        else:
            print("Daemon is not running")

    elif '--status' in sys.argv:
        # Status check
        pid = check_daemon_running()
        if pid:
            print(f"Daemon is running (PID: {pid})")
            if HEALTH_FILE.exists():
                with open(HEALTH_FILE) as f:
                    health = json.load(f)
                print(f"Status: {health.get('status', 'unknown')}")
                print(f"Uptime: {health.get('uptime_seconds', 0):.0f}s")
                print(f"Updates: {health.get('updates', 0)}")
        else:
            print("Daemon is not running")

    else:
        # Daemon mode - check if already running
        existing_pid = check_daemon_running()
        if existing_pid:
            logger.warning(f"Daemon already running (PID: {existing_pid})")
            print(f"Daemon already running (PID: {existing_pid})")
            sys.exit(1)

        # Start daemon
        daemon = ClaudeDaemon()
        daemon.run()


if __name__ == "__main__":
    main()
