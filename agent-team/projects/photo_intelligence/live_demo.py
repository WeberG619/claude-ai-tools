"""
Photo Intelligence - Live Demo Module
=====================================

This file demonstrates the live code view functionality.
Watch the monitor auto-switch between projects!

Features being built:
- AI-powered photo analysis
- Construction site tagging
- Issue detection
- Project organization
"""

from datetime import datetime
from typing import List, Dict

class LiveDemoWidget:
    """A widget to demonstrate live coding for OBS recording."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.created_at = datetime.now()
        self.messages: List[str] = []

    def add_message(self, msg: str) -> None:
        """Add a message to the demo log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {msg}")

    def get_status(self) -> Dict:
        """Get the current demo status."""
        return {
            "project": self.project_name,
            "created": self.created_at.isoformat(),
            "message_count": len(self.messages),
            "messages": self.messages[-5:]  # Last 5 messages
        }

def main():
    """Main entry point for live demo."""
    demo = LiveDemoWidget("Photo Intelligence")
    demo.add_message("Live monitor is working!")
    demo.add_message("Auto-switching between projects!")
    demo.add_message("Ready for OBS recording!")

    print(f"Demo Status: {demo.get_status()}")
    return demo

if __name__ == "__main__":
    main()
