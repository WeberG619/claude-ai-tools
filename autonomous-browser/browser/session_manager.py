"""
Session Manager - Persistent Login Sessions
Manages cookies and authentication state across browser sessions
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


class SessionManager:
    """
    Manages browser sessions for persistent authentication.

    Features:
    - Save/restore cookies
    - Track session validity
    - Auto-refresh expired sessions
    """

    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.sessions_file = SESSIONS_DIR / "sessions.json"
        self._sessions = self._load_sessions()

    def _load_sessions(self) -> dict:
        """Load sessions from file"""
        if self.sessions_file.exists():
            return json.loads(self.sessions_file.read_text())
        return {}

    def _save_sessions(self):
        """Save sessions to file"""
        self.sessions_file.write_text(json.dumps(self._sessions, indent=2))

    def save_session(self, site: str, cookies: List[dict],
                    local_storage: dict = None,
                    session_storage: dict = None) -> dict:
        """
        Save a session for a site.

        Args:
            site: Website domain
            cookies: List of cookies from browser
            local_storage: Optional localStorage data
            session_storage: Optional sessionStorage data
        """
        self._sessions[site] = {
            "cookies": cookies,
            "local_storage": local_storage or {},
            "session_storage": session_storage or {},
            "saved_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        self._save_sessions()

        return {
            "status": "saved",
            "site": site,
            "cookie_count": len(cookies)
        }

    def get_session(self, site: str) -> dict:
        """
        Get a saved session for a site.

        Returns cookies and storage data if available.
        """
        session = self._sessions.get(site)

        if not session:
            # Try partial match
            for stored_site, stored_session in self._sessions.items():
                if site in stored_site or stored_site in site:
                    session = stored_session
                    site = stored_site
                    break

        if not session:
            return {"status": "not_found", "site": site}

        # Update last used
        session["last_used"] = datetime.now().isoformat()
        self._save_sessions()

        return {
            "status": "success",
            "site": site,
            "cookies": session["cookies"],
            "local_storage": session.get("local_storage", {}),
            "session_storage": session.get("session_storage", {}),
            "saved_at": session["saved_at"]
        }

    def has_session(self, site: str) -> bool:
        """Check if a session exists for a site"""
        if site in self._sessions:
            return True
        # Try partial match
        for stored_site in self._sessions.keys():
            if site in stored_site or stored_site in site:
                return True
        return False

    def delete_session(self, site: str) -> dict:
        """Delete a saved session"""
        if site in self._sessions:
            del self._sessions[site]
            self._save_sessions()
            return {"status": "deleted", "site": site}
        return {"status": "not_found", "site": site}

    def list_sessions(self) -> List[dict]:
        """List all saved sessions"""
        return [
            {
                "site": site,
                "cookie_count": len(data["cookies"]),
                "saved_at": data["saved_at"],
                "last_used": data.get("last_used")
            }
            for site, data in self._sessions.items()
        ]

    def clear_all_sessions(self) -> dict:
        """Clear all saved sessions"""
        count = len(self._sessions)
        self._sessions = {}
        self._save_sessions()
        return {"status": "cleared", "count": count}


# Singleton instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get or create session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


if __name__ == "__main__":
    sm = get_session_manager()
    print(f"Sessions loaded: {len(sm.list_sessions())}")
    for session in sm.list_sessions():
        print(f"  - {session['site']}: {session['cookie_count']} cookies")
