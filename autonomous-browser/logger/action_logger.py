"""
Action Logger - Complete Audit Trail
Logs all browser actions for accountability and debugging
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import hashlib

LOGGER_DIR = Path(__file__).parent
LOGS_DIR = LOGGER_DIR / "logs"


class ActionLogger:
    """
    Logs all browser automation actions for audit trail.

    Features:
    - Timestamped action logging
    - Credential usage tracking (hashed, not plaintext)
    - Screenshot references
    - Session-based organization
    - Search and replay capabilities
    """

    def __init__(self, session_id: str = None):
        """
        Initialize logger.

        Args:
            session_id: Optional session identifier (auto-generated if not provided)
        """
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = LOGS_DIR / f"session_{self.session_id}.json"

        self._log_data = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "actions": [],
            "credentials_used": [],
            "screenshots": [],
            "errors": [],
            "summary": {}
        }

    def _save_log(self):
        """Save log to file"""
        self.session_file.write_text(json.dumps(self._log_data, indent=2))

    def log_action(self, action_type: str, details: dict = None,
                  success: bool = True) -> dict:
        """
        Log a browser action.

        Args:
            action_type: Type of action (navigate, click, type, etc.)
            details: Action details (selectors, URLs, etc.)
            success: Whether action succeeded
        """
        entry = {
            "id": len(self._log_data["actions"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "details": details or {},
            "success": success
        }

        self._log_data["actions"].append(entry)
        self._save_log()

        return entry

    def log_credential_use(self, site: str, username: str,
                          credential_type: str = "password") -> dict:
        """
        Log credential usage (hashed for security).

        Args:
            site: Website where credential was used
            username: Username (stored as-is, it's not secret)
            credential_type: Type (password, totp, api_key)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "site": site,
            "username": username,
            "type": credential_type,
            # Hash sensitive info
            "credential_hash": hashlib.sha256(f"{site}:{username}".encode()).hexdigest()[:16]
        }

        self._log_data["credentials_used"].append(entry)
        self._save_log()

        return entry

    def log_screenshot(self, filepath: str, context: str = "") -> dict:
        """
        Log a screenshot taken.

        Args:
            filepath: Path to screenshot file
            context: Context/reason for screenshot
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "filepath": filepath,
            "context": context
        }

        self._log_data["screenshots"].append(entry)
        self._save_log()

        return entry

    def log_error(self, error_type: str, message: str,
                 context: dict = None) -> dict:
        """
        Log an error.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "context": context or {}
        }

        self._log_data["errors"].append(entry)
        self._save_log()

        return entry

    def end_session(self, summary: str = ""):
        """
        End the logging session.

        Args:
            summary: Optional summary of what was accomplished
        """
        self._log_data["ended_at"] = datetime.now().isoformat()
        self._log_data["summary"] = {
            "description": summary,
            "total_actions": len(self._log_data["actions"]),
            "credentials_used": len(self._log_data["credentials_used"]),
            "screenshots_taken": len(self._log_data["screenshots"]),
            "errors_encountered": len(self._log_data["errors"]),
            "duration_seconds": (
                datetime.fromisoformat(self._log_data["ended_at"]) -
                datetime.fromisoformat(self._log_data["started_at"])
            ).total_seconds()
        }
        self._save_log()

        return self._log_data["summary"]

    def get_session_log(self) -> dict:
        """Get the current session log"""
        return self._log_data.copy()

    def get_actions(self, action_type: str = None) -> List[dict]:
        """
        Get actions, optionally filtered by type.

        Args:
            action_type: Optional filter by action type
        """
        actions = self._log_data["actions"]
        if action_type:
            actions = [a for a in actions if a["type"] == action_type]
        return actions


class LogBrowser:
    """Static methods for browsing historical logs"""

    @staticmethod
    def list_sessions(days: int = 30) -> List[dict]:
        """
        List recent logging sessions.

        Args:
            days: How many days back to look
        """
        sessions = []
        cutoff = datetime.now() - timedelta(days=days)

        for log_file in LOGS_DIR.glob("session_*.json"):
            try:
                data = json.loads(log_file.read_text())
                started = datetime.fromisoformat(data["started_at"])
                if started >= cutoff:
                    sessions.append({
                        "session_id": data["session_id"],
                        "started_at": data["started_at"],
                        "ended_at": data.get("ended_at"),
                        "action_count": len(data["actions"]),
                        "file": str(log_file)
                    })
            except Exception:
                pass

        # Sort by date, newest first
        sessions.sort(key=lambda x: x["started_at"], reverse=True)
        return sessions

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get a specific session's log"""
        log_file = LOGS_DIR / f"session_{session_id}.json"
        if log_file.exists():
            return json.loads(log_file.read_text())
        return None

    @staticmethod
    def search_actions(keyword: str, days: int = 30) -> List[dict]:
        """
        Search actions across all sessions.

        Args:
            keyword: Keyword to search for
            days: How many days back to search
        """
        results = []
        cutoff = datetime.now() - timedelta(days=days)

        for log_file in LOGS_DIR.glob("session_*.json"):
            try:
                data = json.loads(log_file.read_text())
                started = datetime.fromisoformat(data["started_at"])
                if started < cutoff:
                    continue

                for action in data["actions"]:
                    action_str = json.dumps(action).lower()
                    if keyword.lower() in action_str:
                        results.append({
                            "session_id": data["session_id"],
                            "action": action
                        })
            except Exception:
                pass

        return results

    @staticmethod
    def get_credential_usage(site: str = None, days: int = 30) -> List[dict]:
        """
        Get credential usage history.

        Args:
            site: Optional filter by site
            days: How many days back to search
        """
        usage = []
        cutoff = datetime.now() - timedelta(days=days)

        for log_file in LOGS_DIR.glob("session_*.json"):
            try:
                data = json.loads(log_file.read_text())
                started = datetime.fromisoformat(data["started_at"])
                if started < cutoff:
                    continue

                for cred in data["credentials_used"]:
                    if site is None or site in cred["site"]:
                        usage.append({
                            "session_id": data["session_id"],
                            **cred
                        })
            except Exception:
                pass

        return usage


# Singleton for current session
_current_logger = None

def get_logger(session_id: str = None) -> ActionLogger:
    """Get or create current session logger"""
    global _current_logger
    if _current_logger is None or session_id:
        _current_logger = ActionLogger(session_id)
    return _current_logger


if __name__ == "__main__":
    # Test the logger
    logger = ActionLogger("test_session")

    logger.log_action("navigate", {"url": "https://example.com"})
    logger.log_action("click", {"selector": "#login-button"})
    logger.log_credential_use("example.com", "testuser", "password")
    logger.log_error("timeout", "Element not found", {"selector": "#missing"})

    summary = logger.end_session("Test session completed")
    print(f"Session summary: {json.dumps(summary, indent=2)}")

    # Test log browser
    print("\nRecent sessions:")
    for session in LogBrowser.list_sessions():
        print(f"  {session['session_id']}: {session['action_count']} actions")
