"""Browser Automation Module"""
from .stealth_browser import StealthBrowser, get_browser
from .human_behavior import HumanBehavior
from .session_manager import SessionManager, get_session_manager

__all__ = [
    'StealthBrowser',
    'get_browser',
    'HumanBehavior',
    'SessionManager',
    'get_session_manager'
]
