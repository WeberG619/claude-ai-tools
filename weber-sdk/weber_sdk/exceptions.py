"""
Weber SDK Exceptions.
"""

from typing import Any


class WeberSDKError(Exception):
    """Base exception for Weber SDK."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConnectionError(WeberSDKError):
    """Failed to connect to MCP server."""

    pass


class ServerNotFoundError(WeberSDKError):
    """MCP server not found in configuration."""

    pass


class ToolNotFoundError(WeberSDKError):
    """Tool not found on MCP server."""

    pass


class ToolExecutionError(WeberSDKError):
    """Tool execution failed."""

    pass


class ConfigurationError(WeberSDKError):
    """Configuration error."""

    pass


class TimeoutError(WeberSDKError):
    """Operation timed out."""

    pass
