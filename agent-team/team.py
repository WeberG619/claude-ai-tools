#!/usr/bin/env python3
"""
Agent Team CLI - Simple entry point for the coding war-room.

Usage:
    python team.py "Build a REST API for user management"
    python team.py --live "Create authentication middleware"
    python team.py --test-voices
    python team.py --status

This is the main interface for launching team sessions.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "turn_state.json"
LOGS_DIR = SCRIPT_DIR / "logs"


def test_voices():
    """Run voice test for all agents."""
    test_script = SCRIPT_DIR / "test_voices.py"
    subprocess.run(["python3", str(test_script)], check=True)


def show_status():
    """Show current session status."""
    if not STATE_FILE.exists():
        print("No active session.")
        return

    with open(STATE_FILE) as f:
        state = json.load(f)

    print("\n" + "="*50)
    print("AGENT TEAM STATUS")
    print("="*50)
    print(f"Session ID: {state.get('session_id', 'N/A')}")
    print(f"Status: {state.get('status', 'unknown')}")
    print(f"Mode: {state.get('mode', 'unknown')}")
    print(f"Current Speaker: {state.get('current_speaker', 'none')}")
    print(f"Turns: {state.get('turn_number', 0)} / {state.get('max_turns', 8)}")

    if state.get('task'):
        print(f"Task: {state['task'][:60]}...")

    print("="*50)


def list_logs():
    """List recent session logs."""
    if not LOGS_DIR.exists():
        print("No session logs yet.")
        return

    logs = sorted(LOGS_DIR.glob("session_*.json"), reverse=True)[:10]

    print("\n" + "="*50)
    print("RECENT SESSIONS")
    print("="*50)

    for log in logs:
        with open(log) as f:
            data = json.load(f)
        task = data.get("task", "Unknown")[:40]
        turns = data.get("turn_number", 0)
        status = data.get("status", "unknown")
        print(f"  {log.stem}: {task}... ({turns} turns, {status})")

    print("="*50)


def run_team(task: str, mode: str = "backstage", max_turns: int = 8):
    """Run a team session."""
    from director import Director

    director = Director(mode=mode)
    result = director.run_session(task)

    return result


def quick_demo():
    """Run a quick demo to see the system in action."""
    print("\n" + "="*60)
    print("🚀 AGENT TEAM QUICK DEMO")
    print("="*60)
    print("\nThis demo will:")
    print("1. Test all agent voices")
    print("2. Run a sample backstage session")
    print("3. Show the summary\n")

    input("Press Enter to start...")

    # Test voices
    print("\n[1/3] Testing voices...")
    test_voices()

    # Run sample task
    print("\n[2/3] Running sample task...")
    from protocols.backstage import BackstageProtocol

    protocol = BackstageProtocol(max_internal_turns=4)
    result = protocol.run("Create a simple hello world function in Python")

    # Show results
    print("\n[3/3] Results:")
    print(f"  Turns: {result['turns']}")
    print(f"  Status: {result['status']}")
    print(f"  Mode: {result['mode']}")

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Team - Coding War-Room",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python team.py "Build a user authentication system"
  python team.py --live "Create a REST API"
  python team.py --test-voices
  python team.py --demo

Modes:
  backstage (default): Fast internal debate, only summary spoken
  live: All agents speak their turns out loud
        """
    )

    parser.add_argument("task", nargs="?", help="Task for the team to work on")
    parser.add_argument("--live", action="store_true",
                        help="Live mode - all agents speak")
    parser.add_argument("--max-turns", type=int, default=8,
                        help="Maximum turns (default: 8)")
    parser.add_argument("--test-voices", action="store_true",
                        help="Test all agent voices")
    parser.add_argument("--status", action="store_true",
                        help="Show current session status")
    parser.add_argument("--logs", action="store_true",
                        help="List recent session logs")
    parser.add_argument("--demo", action="store_true",
                        help="Run a quick demo")

    args = parser.parse_args()

    # Handle flag commands
    if args.test_voices:
        test_voices()
        return

    if args.status:
        show_status()
        return

    if args.logs:
        list_logs()
        return

    if args.demo:
        quick_demo()
        return

    # Require task for main operation
    if not args.task:
        parser.print_help()
        print("\n❌ Error: Please provide a task or use --demo")
        sys.exit(1)

    # Determine mode
    mode = "live" if args.live else "backstage"

    # Run the team
    print(f"\n🚀 Starting Agent Team ({mode} mode)...")
    result = run_team(args.task, mode=mode, max_turns=args.max_turns)

    print(f"\n✅ Session complete!")
    print(f"   Session ID: {result.get('session_id', 'N/A')}")
    print(f"   Turns: {result.get('turn_number', 0)}")


if __name__ == "__main__":
    main()
