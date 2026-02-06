#!/usr/bin/env python3
"""
Email Watcher Manager - Ensures the email watcher daemon is always running.
Called by SessionStart hook alongside the system bridge daemon manager.
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\email-watcher")
PID_FILE = BASE_DIR / "watcher.pid"
ALERTS_FILE = BASE_DIR / "email_alerts.json"
WATCHER_SCRIPT = BASE_DIR / "email_watcher.py"

HEALTH_TIMEOUT = 300  # 5 minutes - watcher checks every 2 min so allow some slack


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[WatcherMgr {timestamp}] {msg}", file=sys.stderr)


def _pid_alive(pid: int) -> bool:
    """Check if a PID is alive without psutil."""
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    # Fallback: Windows tasklist
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def is_watcher_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        return _pid_alive(pid)
    except Exception:
        return False


def is_watcher_healthy() -> bool:
    if not ALERTS_FILE.exists():
        return False
    try:
        data = json.loads(ALERTS_FILE.read_text())
        last_check = data.get("last_check", "2000-01-01T00:00:00")
        last_dt = datetime.fromisoformat(last_check)
        age = (datetime.now() - last_dt).total_seconds()
        return age < HEALTH_TIMEOUT
    except Exception:
        return False


def kill_stale_watcher():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if _pid_alive(pid):
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True, timeout=5
                )
                log(f"Killed stale watcher (PID {pid})")
        except Exception as e:
            log(f"Could not kill stale watcher: {e}")
        try:
            PID_FILE.unlink()
        except Exception:
            pass


def start_watcher() -> bool:
    log("Starting email watcher...")
    try:
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            ["pythonw", str(WATCHER_SCRIPT)],
            cwd=str(BASE_DIR),
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        log(f"Failed to start watcher: {e}")
        return False


def ensure_watcher_running() -> str:
    if is_watcher_running() and is_watcher_healthy():
        return "running"

    if is_watcher_running():
        log("Watcher running but stale - restarting")
        kill_stale_watcher()
        action = "restarted"
    else:
        log("Watcher not running - starting")
        action = "started"

    for f in [PID_FILE]:
        try:
            if f.exists():
                f.unlink()
        except Exception:
            pass

    if start_watcher():
        time.sleep(3)
        if is_watcher_running():
            return action
        return "start_pending"
    return "failed"


def main():
    result = ensure_watcher_running()
    if result == "running":
        print(f"Email watcher: running")
    else:
        print(f"Email watcher: {result}")
    return 0 if result in ["running", "started", "restarted", "start_pending"] else 1


if __name__ == "__main__":
    sys.exit(main())
