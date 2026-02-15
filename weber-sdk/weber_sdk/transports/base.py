"""
Base transport interface for MCP communication.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    """Abstract base class for MCP transports."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        pass

    @abstractmethod
    async def send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request to the server."""
        pass

    @abstractmethod
    async def list_tools(self) -> list[dict]:
        """List available tools from the server."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the server."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        pass
