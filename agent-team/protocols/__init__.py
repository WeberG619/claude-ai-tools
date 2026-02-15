"""
Agent Team Protocols

backstage: Fast internal debate + voice summary only
live_meeting: All agents speak their turns
"""

from .backstage import BackstageProtocol
from .live_meeting import LiveMeetingProtocol

__all__ = ["BackstageProtocol", "LiveMeetingProtocol"]
