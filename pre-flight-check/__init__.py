"""
Pre-Flight Check Module
Prevents repeating known mistakes by surfacing corrections before operations.
"""

from .pre_flight_check import check_operation, query_corrections, format_warning_banner
from .context_detector import detect_operation, should_check, get_operation_context

__all__ = [
    "check_operation",
    "query_corrections",
    "format_warning_banner",
    "detect_operation",
    "should_check",
    "get_operation_context",
]
