#!/usr/bin/env python3
"""
Voice Command Router for Claude Code

Bridges Wispr Flow voice input to Claude Code operations.
Monitors a watch file/clipboard for voice commands and routes to appropriate actions.

Voice Command Patterns:
- "Claude, [command]" - Direct Claude instruction
- "Verify the model" - Triggers BIM validation
- "Check for issues" - Runs pre-flight check
- "Create walls from..." - Triggers floor plan pipeline
- "What's open" - Reports system state
"""

import json
import os
import sys
import time
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# Configuration
WATCH_FILE = Path("/mnt/d/_CLAUDE-TOOLS/voice-bridge/voice_input.txt")
RESPONSE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/voice-bridge/voice_response.txt")
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/voice-bridge/router.log")
CHECK_INTERVAL = 1  # seconds


class VoiceCommandRouter:
    """Routes voice commands to appropriate handlers."""

    def __init__(self):
        self.commands = {}
        self.last_input = ""
        self.register_default_commands()

    def log(self, message: str):
        """Log router activity."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + "\n")
        except:
            pass

    def speak(self, text: str):
        """Speak response using voice MCP."""
        try:
            subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py",
                text
            ], timeout=30, capture_output=True)
        except:
            pass

    def register(self, pattern: str, handler: Callable, description: str = ""):
        """Register a command pattern and handler."""
        self.commands[pattern] = {
            "handler": handler,
            "description": description
        }

    def register_default_commands(self):
        """Register built-in voice commands."""

        # System state
        self.register(
            r"what'?s? open|system status|what are you seeing",
            self.cmd_system_status,
            "Report current system state"
        )

        # BIM Validation
        self.register(
            r"verify|validate|check model|bim check",
            self.cmd_verify_bim,
            "Run BIM validation"
        )

        # Pre-flight check
        self.register(
            r"check for issues|pre-?flight|known issues",
            self.cmd_preflight,
            "Run pre-flight correction check"
        )

        # Memory recall
        self.register(
            r"what did we learn|corrections|past mistakes",
            self.cmd_memory_recall,
            "Surface relevant memories"
        )

        # Floor plan
        self.register(
            r"create walls|floor plan|extract walls",
            self.cmd_floor_plan_info,
            "Floor plan processing info"
        )

        # Help
        self.register(
            r"help|commands|what can you do",
            self.cmd_help,
            "List available commands"
        )

    # =========================================================================
    # Command Handlers
    # =========================================================================

    def cmd_system_status(self, text: str) -> str:
        """Report current system state."""
        try:
            state_file = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)

                apps = []
                for app in state.get("applications", []):
                    name = app.get("ProcessName", "")
                    if name in ["Revit", "Revu", "Code", "chrome"]:
                        title = app.get("MainWindowTitle", "")[:50]
                        apps.append(f"{name}: {title}")

                if apps:
                    return "Currently open: " + ". ".join(apps[:3])
                else:
                    return "No major applications detected."
            return "System state not available."
        except Exception as e:
            return f"Error getting system state: {e}"

    def cmd_verify_bim(self, text: str) -> str:
        """Run BIM validation."""
        try:
            result = subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/bim-validator/background_monitor.py",
                "--validate"
            ], capture_output=True, text=True, timeout=30)

            if result.stdout:
                validation = json.loads(result.stdout)
                status = validation.get("status", "unknown")
                issues = validation.get("issues", [])

                if status == "ok":
                    return "BIM validation passed. No issues detected."
                else:
                    return f"Validation found {len(issues)} issues. " + ". ".join([i["message"] for i in issues[:2]])
            return "Validation completed but no results returned."
        except Exception as e:
            return f"Validation error: {e}"

    def cmd_preflight(self, text: str) -> str:
        """Run pre-flight correction check."""
        try:
            result = subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/pre-flight-check/pre_flight_check.py",
                "general check"
            ], capture_output=True, text=True, timeout=10)

            if "No known issues" in result.stdout:
                return "Pre-flight check clear. No known issues for current context."
            elif "KNOWN ISSUES DETECTED" in result.stdout:
                # Count issues
                count = result.stdout.count("importance:")
                return f"Pre-flight check found {count} relevant corrections. Review before proceeding."
            return "Pre-flight check completed."
        except Exception as e:
            return f"Pre-flight error: {e}"

    def cmd_memory_recall(self, text: str) -> str:
        """Surface relevant memories."""
        try:
            result = subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/proactive-memory/memory_surfacer.py"
            ], capture_output=True, text=True, timeout=10)

            if result.stdout:
                # Extract key points
                lines = result.stdout.split("\n")
                corrections = [l for l in lines if l.startswith("- [")][:2]

                if corrections:
                    return "Recent corrections: " + ". ".join([c.split("]")[1].strip() for c in corrections])
                return "No critical corrections found for current context."
            return "Memory check completed."
        except Exception as e:
            return f"Memory error: {e}"

    def cmd_floor_plan_info(self, text: str) -> str:
        """Provide floor plan processing info."""
        return ("To process a floor plan, I need a PDF file path. "
                "Use the slash command pdf-to-revit with the PDF location. "
                "For example: slash pdf-to-revit path-to-your-file.pdf")

    def cmd_help(self, text: str) -> str:
        """List available commands."""
        commands = [
            "what's open - shows current apps",
            "verify model - runs BIM validation",
            "check for issues - pre-flight check",
            "what did we learn - shows past corrections",
            "help - this message"
        ]
        return "Available commands: " + ". ".join(commands)

    # =========================================================================
    # Command Processing
    # =========================================================================

    def process_command(self, text: str) -> Optional[str]:
        """Process a voice command and return response."""
        text_lower = text.lower().strip()

        # Skip if empty or too short
        if len(text_lower) < 3:
            return None

        # Try to match each registered command
        for pattern, config in self.commands.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                self.log(f"Matched pattern: {pattern}")
                try:
                    response = config["handler"](text)
                    return response
                except Exception as e:
                    self.log(f"Handler error: {e}")
                    return f"Error processing command: {e}"

        # No match - could forward to Claude
        return None

    def watch_loop(self):
        """Main loop: watch for voice input and process."""
        self.log("Voice Command Router started")
        self.log(f"Watching: {WATCH_FILE}")

        WATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        WATCH_FILE.touch()

        while True:
            try:
                # Check for new input
                if WATCH_FILE.exists():
                    with open(WATCH_FILE) as f:
                        current_input = f.read().strip()

                    if current_input and current_input != self.last_input:
                        self.last_input = current_input
                        self.log(f"Received: {current_input[:100]}")

                        # Process command
                        response = self.process_command(current_input)

                        if response:
                            self.log(f"Response: {response[:100]}")

                            # Write response file
                            with open(RESPONSE_FILE, 'w') as f:
                                f.write(response)

                            # Speak response
                            self.speak(response)

                        # Clear input file
                        with open(WATCH_FILE, 'w') as f:
                            f.write("")

            except Exception as e:
                self.log(f"Loop error: {e}")

            time.sleep(CHECK_INTERVAL)


def main():
    """Entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # Test mode: process single command
            router = VoiceCommandRouter()
            command = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "help"
            response = router.process_command(command)
            print(response or "No matching command")
        elif sys.argv[1] == "--commands":
            # List commands
            router = VoiceCommandRouter()
            for pattern, config in router.commands.items():
                print(f"{pattern}: {config['description']}")
    else:
        # Default: run watch loop
        router = VoiceCommandRouter()
        router.watch_loop()


if __name__ == "__main__":
    main()
