#!/usr/bin/env python3
"""
Visual Sync Controller - Real-time dashboard synchronization
============================================================
Extracts files/URLs from agent responses and pushes instant updates
to the dashboard via WebSocket or status file.
"""

import re
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# Status file for fallback (also read by Electron)
STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")

# WebSocket push endpoint
PUSH_ENDPOINT = "http://localhost:8890/api/push"


class VisualSyncController:
    """
    Detects file paths and URLs in agent responses and triggers
    instant visual updates on the dashboard.
    """

    # Patterns for detecting file references
    FILE_PATTERNS = [
        r'`([/\\]?[\w./\\-]+\.\w{1,10})`',           # backtick paths: `path/to/file.py`
        r'"([/\\]?[\w./\\-]+\.\w{1,10})"',           # quoted paths: "path/to/file.py"
        r"'([/\\]?[\w./\\-]+\.\w{1,10})'",           # single quoted: 'path/to/file.py'
        r'(?:editing|writing|reading|creating|opening|looking at)\s+([/\\]?[\w./\\-]+\.\w{1,10})',  # natural language
        r'file:\s*([/\\]?[\w./\\-]+\.\w{1,10})',     # explicit: file: path.py
    ]

    # Patterns for detecting URLs
    URL_PATTERNS = [
        r'(https?://[^\s<>"\'\)]+)',                 # full URLs
        r'(?:navigate to|browsing|opening|visiting)\s+(https?://[^\s<>"\'\)]+)',  # natural language
    ]

    # Patterns for detecting terminal commands
    TERMINAL_PATTERNS = [
        r'(?:running|executing|ran)\s+[`"]?([^`"]+)[`"]?',  # running command
        r'\$\s*(.+)$',                               # shell prompt
        r'(?:npm|pip|python|node|docker|git)\s+\S+', # common CLI tools
    ]

    def __init__(self):
        self.last_activity = None
        self.push_enabled = True

    def extract_files(self, text: str) -> List[str]:
        """Extract file paths from text."""
        files = []
        for pattern in self.FILE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Filter out common false positives
                if not self._is_valid_file_path(match):
                    continue
                files.append(match)
        return list(set(files))  # Deduplicate

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        urls = []
        for pattern in self.URL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
        return list(set(urls))

    def extract_commands(self, text: str) -> List[str]:
        """Extract terminal commands from text."""
        commands = []
        for pattern in self.TERMINAL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            commands.extend(matches)
        return list(set(commands))

    def _is_valid_file_path(self, path: str) -> bool:
        """Check if a string looks like a valid file path."""
        # Filter out version numbers, URLs, etc
        if not path:
            return False
        if path.startswith('http'):
            return False
        if re.match(r'^\d+\.\d+', path):  # Version numbers
            return False
        if len(path) < 3:
            return False
        # Must have a file extension
        if '.' not in path or path.endswith('.'):
            return False
        return True

    def detect_activity_type(self, text: str) -> Tuple[str, Optional[Dict]]:
        """
        Detect what type of activity an agent response describes.

        Returns:
            Tuple of (activity_type, activity_data)
        """
        text_lower = text.lower()

        # Check for URL navigation
        urls = self.extract_urls(text)
        if urls:
            return "browser_navigate", {
                "type": "browser_navigate",
                "url": urls[0],
                "title": self._extract_title(text, urls[0])
            }

        # Check for file operations
        files = self.extract_files(text)
        if files:
            # Determine if reading or writing
            if any(kw in text_lower for kw in ['writing', 'creating', 'editing', 'adding']):
                return "code_write", {
                    "type": "code_write",
                    "file_path": files[0],
                    "content": "",  # Content would need to be passed separately
                    "language": self._detect_language(files[0])
                }
            else:
                return "code_read", {
                    "type": "code_read",
                    "file_path": files[0],
                    "highlight_lines": []
                }

        # Check for terminal commands
        commands = self.extract_commands(text)
        if commands:
            return "terminal_run", {
                "type": "terminal_run",
                "command": commands[0],
                "output": ""
            }

        # Check for thinking/planning
        if any(kw in text_lower for kw in ['thinking', 'analyzing', 'considering', 'planning']):
            return "thinking", {
                "type": "thinking",
                "topic": text[:100]
            }

        return "speech", None

    def _extract_title(self, text: str, url: str) -> str:
        """Extract a title from text for a URL."""
        # Try to find descriptive text near the URL
        words = text.split()
        for i, word in enumerate(words):
            if url in word:
                # Get surrounding words
                start = max(0, i - 3)
                end = min(len(words), i + 1)
                return ' '.join(words[start:end])
        return url[:50]

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.sh': 'bash', '.ps1': 'powershell',
            '.cs': 'csharp', '.cpp': 'cpp', '.go': 'go',
            '.rs': 'rust', '.java': 'java', '.rb': 'ruby',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')

    def sync_from_response(self, agent: str, text: str) -> Optional[Dict]:
        """
        Process an agent response and sync visual state.

        Args:
            agent: The agent name
            text: The response text

        Returns:
            The activity data if detected, None otherwise
        """
        activity_type, activity_data = self.detect_activity_type(text)

        if activity_data:
            self.push_status({
                "agent": agent,
                "speaking": True,
                "text": text[:200],
                "activity": activity_data,
                "timestamp": time.time()
            })
            return activity_data

        # Just update speaking status
        self.push_status({
            "agent": agent,
            "speaking": True,
            "text": text[:200],
            "timestamp": time.time()
        })
        return None

    def push_status(self, status: Dict):
        """
        Push status update to dashboard.
        Tries WebSocket endpoint first, falls back to file.
        """
        self.last_activity = status

        # Try HTTP push first (for WebSocket broadcast)
        if self.push_enabled:
            try:
                response = requests.post(
                    PUSH_ENDPOINT,
                    json=status,
                    timeout=0.5
                )
                if response.status_code == 200:
                    return  # Success
            except Exception:
                pass  # Fall back to file

        # File-based fallback
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Visual sync error: {e}")

    def broadcast_parallel_start(self, agents: List[str]):
        """Broadcast that multiple builders are starting parallel work."""
        self.push_status({
            "type": "parallel_start",
            "agents": agents,
            "timestamp": time.time()
        })

    def broadcast_reasoning(self, agent: str, text: str, status: str = "active"):
        """Broadcast agent reasoning status."""
        self.push_status({
            "type": "reasoning",
            "agent": agent,
            "status": status,
            "text": text[:200],
            "timestamp": time.time()
        })

    def clear_activity(self):
        """Clear the current activity."""
        self.push_status({
            "agent": None,
            "speaking": False,
            "activity": None,
            "timestamp": time.time()
        })

    def push_execution_result(self, agent: str, result):
        """
        Push real execution results to dashboard.

        Args:
            agent: The agent that triggered the execution
            result: ToolResult object from execution_bridge
        """
        activity = {
            "type": "execution_result",
            "agent": agent,
            "action_type": result.action_type,
            "success": result.success,
            "output": result.output[:500] if result.output else "",
            "error": result.error,
            "timestamp": time.time()
        }

        # Add type-specific data
        if result.action_type == "run_command":
            activity["command"] = result.content if hasattr(result, 'content') else ""
        elif result.action_type == "write_file":
            activity["file_path"] = result.path
            activity["content_preview"] = result.content[:200] if result.content else ""
        elif result.action_type == "read_file":
            activity["file_path"] = result.path

        self.push_status(activity)

    def broadcast_execution_mode(self, enabled: bool):
        """Broadcast execution mode change to all clients."""
        self.push_status({
            "type": "execution_mode",
            "enabled": enabled,
            "timestamp": time.time()
        })

    def broadcast_approval_request(self, action_id: str, action_type: str, content: str):
        """
        Broadcast an approval request for a dangerous operation.

        Args:
            action_id: Unique identifier for the action
            action_type: Type of action (e.g., 'run_command', 'git_operation')
            content: The command or operation content
        """
        self.push_status({
            "type": "approval_request",
            "action_id": action_id,
            "action_type": action_type,
            "content": content[:500],
            "timestamp": time.time()
        })


# Convenience functions for direct use
_controller = None


def get_controller() -> VisualSyncController:
    """Get the singleton controller instance."""
    global _controller
    if _controller is None:
        _controller = VisualSyncController()
    return _controller


def sync_response(agent: str, text: str) -> Optional[Dict]:
    """Convenience function to sync from agent response."""
    return get_controller().sync_from_response(agent, text)


def push_activity(activity: Dict):
    """Convenience function to push activity directly."""
    get_controller().push_status(activity)


if __name__ == "__main__":
    # Test the visual sync controller
    controller = VisualSyncController()

    test_texts = [
        "Let me look at `/src/components/App.tsx` to understand the structure.",
        "I'll navigate to https://github.com/anthropics/claude-code for the documentation.",
        "Running `npm install` to install dependencies.",
        "I'm writing the new API endpoint in `api/routes.py`.",
        "Thinking about the best approach for this task...",
    ]

    print("Visual Sync Controller Test")
    print("=" * 50)

    for text in test_texts:
        activity_type, data = controller.detect_activity_type(text)
        print(f"\nText: {text[:60]}...")
        print(f"Type: {activity_type}")
        print(f"Data: {data}")
