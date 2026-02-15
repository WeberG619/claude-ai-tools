"""
Agent Team - Multi-Agent Voice Collaboration System

A coding war-room where AI agents debate, build, and validate together.
"""

from .director import Director, Session
from .agent_prompts import get_prompt

__version__ = "1.0.0"
__all__ = ["Director", "Session", "get_prompt"]
