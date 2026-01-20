#!/usr/bin/env python3
"""
Master Orchestrator Startup

Initializes all Claude Code enhancement systems:
1. System Bridge (already running via hook)
2. Proactive Memory Surfacing
3. Pre-flight Correction Check
4. Background BIM Validator
5. Voice Command Router
6. Context-Aware Trigger Engine
7. Cross-App Workflow Coordinator

Run this at session start for full intelligent orchestration.
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Tool directories
TOOLS_DIR = Path("/mnt/d/_CLAUDE-TOOLS")


def log(message: str):
    """Print with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def check_system_bridge() -> bool:
    """Verify system bridge is running."""
    state_file = TOOLS_DIR / "system-bridge" / "live_state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            age = (datetime.now() - datetime.fromisoformat(state.get("generated_at", "2000-01-01"))).seconds
            if age < 60:
                return True
        except:
            pass
    return False


def run_proactive_memory():
    """Run proactive memory surfacing."""
    try:
        result = subprocess.run([
            "python3",
            str(TOOLS_DIR / "proactive-memory" / "memory_surfacer.py")
        ], capture_output=True, text=True, timeout=15)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


def run_preflight_check():
    """Run general pre-flight check."""
    try:
        result = subprocess.run([
            "python3",
            str(TOOLS_DIR / "pre-flight-check" / "pre_flight_check.py"),
            "general session startup"
        ], capture_output=True, text=True, timeout=10)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


def get_system_summary() -> dict:
    """Get summary of current system state."""
    try:
        with open(TOOLS_DIR / "system-bridge" / "live_state.json") as f:
            state = json.load(f)

        apps = []
        for app in state.get("applications", []):
            name = app.get("ProcessName", "")
            if name in ["Revit", "Revu", "Code", "chrome", "OUTLOOK"]:
                title = app.get("MainWindowTitle", "")[:40]
                monitor = app.get("Monitor", "unknown")
                apps.append(f"  - {name} ({monitor}): {title}")

        return {
            "active_window": state.get("active_window", "Unknown")[:60],
            "apps": apps,
            "bluebeam": state.get("bluebeam", {}),
        }
    except:
        return {"error": "Could not read system state"}


def main():
    """Master startup sequence."""
    print("=" * 60)
    print("CLAUDE CODE INTELLIGENT ORCHESTRATION SYSTEM")
    print("=" * 60)
    print()

    # Step 1: System Bridge
    log("Checking System Bridge...")
    if check_system_bridge():
        log("✓ System Bridge active")
    else:
        log("✗ System Bridge not responding - check daemon")

    # Step 2: System Summary
    log("Getting system state...")
    summary = get_system_summary()
    if "error" not in summary:
        print(f"\nActive Window: {summary['active_window']}")
        if summary.get("apps"):
            print("\nOpen Applications:")
            for app in summary["apps"][:5]:
                print(app)
        if summary.get("bluebeam", {}).get("running"):
            print(f"\nBluebeam: {summary['bluebeam'].get('document', 'open')}")
    print()

    # Step 3: Proactive Memory
    log("Loading proactive memory...")
    memory_output = run_proactive_memory()
    if memory_output:
        print(memory_output[:500])
    print()

    # Step 4: Pre-flight Check
    log("Running pre-flight check...")
    preflight_output = run_preflight_check()
    if "KNOWN ISSUES" in preflight_output:
        print(preflight_output[:800])
    else:
        print("✓ No critical issues detected")
    print()

    # Step 5: Available Enhancements
    print("=" * 60)
    print("AVAILABLE ENHANCEMENTS")
    print("=" * 60)
    enhancements = [
        ("Pre-flight Check", "/mnt/d/_CLAUDE-TOOLS/pre-flight-check/", "Auto-warns before operations"),
        ("BIM Validator", "/mnt/d/_CLAUDE-TOOLS/bim-validator/", "Validates Revit model"),
        ("Memory Surfacer", "/mnt/d/_CLAUDE-TOOLS/proactive-memory/", "Surfaces relevant corrections"),
        ("Voice Bridge", "/mnt/d/_CLAUDE-TOOLS/voice-bridge/", "Voice command routing"),
        ("Self-Healing", "/mnt/d/_CLAUDE-TOOLS/self-healing/", "Learns from failures"),
        ("Operation Cache", "/mnt/d/_CLAUDE-TOOLS/operation-cache/", "Caches successful patterns"),
        ("Cross-App", "/mnt/d/_CLAUDE-TOOLS/cross-app-automation/", "Orchestrates across apps"),
        ("Triggers", "/mnt/d/_CLAUDE-TOOLS/context-triggers/", "Context-aware automation"),
        ("Floor Plan Pipeline", "/mnt/d/_CLAUDE-TOOLS/floor-plan-pipeline/", "PDF to Revit automation"),
    ]

    for name, path, desc in enhancements:
        exists = Path(path).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {desc}")

    print()
    print("=" * 60)
    print("Ready for intelligent orchestration!")
    print("=" * 60)


if __name__ == "__main__":
    main()
