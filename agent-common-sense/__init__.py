try:
    from .sense import CommonSense, ActionCheck
except ImportError:
    from sense import CommonSense, ActionCheck

__all__ = ["CommonSense", "ActionCheck"]
__version__ = "1.0.0"
