#!/usr/bin/env python3
"""
Background BIM Validator Monitor

Runs continuously and monitors Revit model state.
Triggers validation when changes are detected.
Surfaces issues proactively.
"""

import json
import time
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
import socket

# Configuration
CHECK_INTERVAL = 30  # seconds between checks
STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/bim-validator/last_state.json")
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/bim-validator/monitor.log")
REVIT_MCP_PORT = 9001  # RevitMCPBridge default port

# Memory integration
MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")


def log(message: str):
    """Log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)

    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_message + "\n")
    except:
        pass


def check_revit_mcp_available() -> bool:
    """Check if RevitMCPBridge is responding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', REVIT_MCP_PORT))
        sock.close()
        return result == 0
    except:
        return False


def send_mcp_command(method: str, params: dict = None) -> Optional[dict]:
    """Send a command to RevitMCPBridge via HTTP."""
    try:
        import urllib.request
        import urllib.parse

        url = f"http://127.0.0.1:{REVIT_MCP_PORT}/api/{method}"
        data = json.dumps(params or {}).encode('utf-8')

        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None


def get_model_state() -> dict:
    """Get current model state from Revit."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "connected": False,
        "document_name": None,
        "element_counts": {},
        "warning_count": 0,
    }

    if not check_revit_mcp_available():
        return state

    state["connected"] = True

    # Get document info
    doc_info = send_mcp_command("getDocumentInfo")
    if doc_info and doc_info.get("success"):
        state["document_name"] = doc_info.get("title", "Unknown")

    # Get element counts by category
    for category in ["Walls", "Doors", "Windows", "Rooms"]:
        elements = send_mcp_command("getElements", {"category": category})
        if elements and elements.get("success"):
            state["element_counts"][category] = len(elements.get("elements", []))

    # Get warnings count
    warnings = send_mcp_command("getDocumentWarnings")
    if warnings and warnings.get("success"):
        state["warning_count"] = len(warnings.get("warnings", []))

    return state


def load_last_state() -> Optional[dict]:
    """Load the last known model state."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return None


def save_state(state: dict):
    """Save current state for comparison."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass


def detect_changes(old_state: dict, new_state: dict) -> list:
    """Detect significant changes between states."""
    changes = []

    if not old_state or not new_state.get("connected"):
        return changes

    # Document change
    if old_state.get("document_name") != new_state.get("document_name"):
        changes.append({
            "type": "document_changed",
            "old": old_state.get("document_name"),
            "new": new_state.get("document_name")
        })

    # Element count changes
    old_counts = old_state.get("element_counts", {})
    new_counts = new_state.get("element_counts", {})

    for category in set(list(old_counts.keys()) + list(new_counts.keys())):
        old_count = old_counts.get(category, 0)
        new_count = new_counts.get(category, 0)

        if old_count != new_count:
            changes.append({
                "type": "element_count_changed",
                "category": category,
                "old_count": old_count,
                "new_count": new_count,
                "delta": new_count - old_count
            })

    # Warning count changes
    old_warnings = old_state.get("warning_count", 0)
    new_warnings = new_state.get("warning_count", 0)

    if new_warnings > old_warnings:
        changes.append({
            "type": "new_warnings",
            "old_count": old_warnings,
            "new_count": new_warnings,
            "delta": new_warnings - old_warnings
        })

    return changes


def run_quick_validation(state: dict) -> dict:
    """Run quick validation checks on current state."""
    issues = []

    # Check for high warning count
    if state.get("warning_count", 0) > 10:
        issues.append({
            "severity": "warning",
            "message": f"High warning count: {state['warning_count']}"
        })

    # Check for unusual element ratios
    walls = state.get("element_counts", {}).get("Walls", 0)
    doors = state.get("element_counts", {}).get("Doors", 0)
    windows = state.get("element_counts", {}).get("Windows", 0)

    if walls > 0:
        # Typical ratio: 1 door per 2-5 walls
        if doors > 0 and walls / doors < 1:
            issues.append({
                "severity": "info",
                "message": f"Unusual wall/door ratio: {walls} walls, {doors} doors"
            })

    return {
        "status": "issues" if issues else "ok",
        "issues": issues,
        "timestamp": datetime.now().isoformat()
    }


def notify_changes(changes: list, validation: dict):
    """Notify about changes via voice or other means."""
    if not changes and validation["status"] == "ok":
        return

    # Build notification message
    messages = []

    for change in changes:
        if change["type"] == "element_count_changed":
            delta = change["delta"]
            verb = "added" if delta > 0 else "removed"
            messages.append(f"{abs(delta)} {change['category'].lower()} {verb}")
        elif change["type"] == "new_warnings":
            messages.append(f"{change['delta']} new warnings detected")

    for issue in validation.get("issues", []):
        messages.append(issue["message"])

    if messages:
        summary = ". ".join(messages)
        log(f"NOTIFICATION: {summary}")

        # Try to speak via voice MCP
        try:
            subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py",
                f"BIM Monitor: {summary}"
            ], timeout=30, capture_output=True)
        except:
            pass


def monitor_loop():
    """Main monitoring loop."""
    log("BIM Validator Monitor started")
    log(f"Check interval: {CHECK_INTERVAL} seconds")

    last_state = load_last_state()

    while True:
        try:
            # Get current state
            current_state = get_model_state()

            if current_state["connected"]:
                # Detect changes
                changes = detect_changes(last_state, current_state)

                # Run quick validation
                validation = run_quick_validation(current_state)

                # Log status
                if changes:
                    log(f"Changes detected: {json.dumps(changes)}")

                if validation["issues"]:
                    log(f"Validation issues: {json.dumps(validation['issues'])}")

                # Notify if needed
                notify_changes(changes, validation)

                # Save state
                save_state(current_state)
                last_state = current_state

            else:
                log("Revit MCP not available")

        except Exception as e:
            log(f"Error in monitor loop: {e}")

        time.sleep(CHECK_INTERVAL)


def main():
    """Entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            # Single check mode
            state = get_model_state()
            print(json.dumps(state, indent=2))
            return
        elif sys.argv[1] == "--validate":
            # Single validation
            state = get_model_state()
            validation = run_quick_validation(state)
            print(json.dumps(validation, indent=2))
            return

    # Default: run monitor loop
    monitor_loop()


if __name__ == "__main__":
    main()
