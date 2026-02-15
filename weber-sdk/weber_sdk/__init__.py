"""
Weber SDK - Unified Python SDK for all MCP servers.

Usage:
    from weber_sdk import Weber

    w = Weber()
    w.voice.speak('Hello')
    w.excel.get_status()
    w.revit2026.get_document_info()

    # Or async:
    async with Weber() as w:
        await w.voice.speak_async('Hello')
"""

from weber_sdk.client import Weber
from weber_sdk.discovery import discover_servers, MCPServerConfig
from weber_sdk.exceptions import (
    WeberSDKError,
    ConnectionError,
    ServerNotFoundError,
    ToolNotFoundError,
    ToolExecutionError,
)

__version__ = "0.1.0"
__all__ = [
    "Weber",
    "discover_servers",
    "MCPServerConfig",
    "WeberSDKError",
    "ConnectionError",
    "ServerNotFoundError",
    "ToolNotFoundError",
    "ToolExecutionError",
]
