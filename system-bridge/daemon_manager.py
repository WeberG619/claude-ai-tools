#!/usr/bin/env python3
"""
Daemon Manager - Bulletproof daemon lifecycle management.
Ensures the Claude system bridge daemon is ALWAYS running.

Called by session_start.py on every Claude Code session.
"""

import json
import os
import sys
import time
import subprocess
import psutil
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION (HARDCODED - ALWAYS WORKS)
# =============================================================================

BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
PID_FILE = BASE_DIR / "daemon.pid"
HEALTH_FILE = BASE_DIR / "health.json"
STATE_FILE = BASE_DIR / "live_state.json"
DAEMON_SCRIPT = BASE_DIR / "claude_daemon.py"

# Timeouts
STARTUP_WAIT = 15  # seconds to wait for daemon to initialize
HEALTH_TIMEOUT = 120  # seconds - daemon is stale if health older than this


def log(msg: str):
    """Simple logging to stderr (visible in hook output)."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[DaemonMgr {timestamp}] {msg}", file=sys.stderr)


def is_daemon_running() -> bool:
    """Check if daemon process is actually running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process exists and is our daemon
        if psutil.pid_exists(pid):
            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline()).lower()
            if "claude_daemon" in cmdline or "python" in cmdline:
                return True
        return False
    except Exception:
        return False


def is_daemon_healthy() -> bool:
    """Check if daemon is healthy (recent health check)."""
    if not HEALTH_FILE.exists():
        return False

    try:
        health = json.loads(HEALTH_FILE.read_text())
        last_check = datetime.fromisoformat(health.get("timestamp", "2000-01-01"))
        age = (datetime.now() - last_check).total_seconds()
        return age < HEALTH_TIMEOUT and health.get("status") == "healthy"
    except Exception:
        return False


def kill_stale_daemon():
    """Kill any stale daemon process."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                log(f"Killed stale daemon (PID {pid})")
        except Exception as e:
            log(f"Could not kill stale daemon: {e}")

        try:
            PID_FILE.unlink()
        except Exception:
            pass


def start_daemon() -> bool:
    """Start the daemon process."""
    log("Starting daemon...")

    try:
        # Use pythonw on Windows for background execution
        if sys.platform == "win32":
            # Start detached process on Windows
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000

            proc = subprocess.Popen(
                ["pythonw", str(DAEMON_SCRIPT)],
                cwd=str(BASE_DIR),
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        else:
            # Linux/WSL - use nohup
            proc = subprocess.Popen(
                ["nohup", "python3", str(DAEMON_SCRIPT)],
                cwd=str(BASE_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )

        log(f"Daemon started (PID {proc.pid})")
        return True
    except Exception as e:
        log(f"Failed to start daemon: {e}")
        return False


def wait_for_daemon(timeout: int = STARTUP_WAIT) -> bool:
    """Wait for daemon to be healthy."""
    log(f"Waiting up to {timeout}s for daemon to initialize...")

    start = time.time()
    while time.time() - start < timeout:
        if is_daemon_healthy() and STATE_FILE.exists():
            try:
                # Verify state file is valid JSON
                state = json.loads(STATE_FILE.read_text())
                if state and isinstance(state, dict):
                    log("Daemon is healthy and state file ready")
                    return True
            except Exception:
                pass
        time.sleep(1)

    log("Daemon did not become healthy in time")
    return False


def ensure_daemon_running() -> dict:
    """
    Main entry point - ensures daemon is running and returns state.

    Returns:
        dict: Current system state, or error dict if failed
    """
    result = {
        "daemon_status": "unknown",
        "action_taken": "none",
        "state": None,
        "error": None
    }

    # Check if already running and healthy
    if is_daemon_running() and is_daemon_healthy():
        result["daemon_status"] = "running"
        result["action_taken"] = "none"
    else:
        # Need to (re)start
        if is_daemon_running():
            log("Daemon running but unhealthy - restarting")
            kill_stale_daemon()
            result["action_taken"] = "restarted"
        else:
            log("Daemon not running - starting")
            result["action_taken"] = "started"

        # Clean up stale files
        for f in [PID_FILE, HEALTH_FILE]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

        # Start daemon
        if start_daemon():
            if wait_for_daemon():
                result["daemon_status"] = "running"
            else:
                result["daemon_status"] = "starting"  # Still initializing
        else:
            result["daemon_status"] = "failed"
            result["error"] = "Could not start daemon"

    # Try to read state
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
            if state and isinstance(state, dict):
                result["state"] = state
    except Exception as e:
        result["error"] = f"Could not read state: {e}"

    return result


def main():
    """CLI entry point."""
    result = ensure_daemon_running()

    # Output minimal status for Claude (full state is read by brain_sync)
    status = result["daemon_status"]
    action = result["action_taken"]

    if action != "none":
        print(f"Daemon {action} - status: {status}")
    else:
        print(f"Daemon status: {status}")

    if result["error"]:
        print(f"Warning: {result['error']}")

    return 0 if status in ["running", "starting"] else 1


if __name__ == "__main__":
    sys.exit(main())
