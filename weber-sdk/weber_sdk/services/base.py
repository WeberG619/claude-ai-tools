"""
Base service class for MCP server wrappers.
"""

from typing import Any

from weber_sdk.transports.base import BaseTransport
from weber_sdk.exceptions import ToolNotFoundError


class BaseService:
    """
    Base class for service wrappers.

    Provides common functionality for calling MCP tools and managing connections.
    """

    def __init__(self, transport: BaseTransport, server_name: str):
        self._transport = transport
        self._server_name = server_name
        self._tools: dict[str, dict] = {}

    @property
    def server_name(self) -> str:
        """Get the server name."""
        return self._server_name

    @property
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self._transport.is_connected

    async def connect(self) -> None:
        """Connect to the MCP server."""
        await self._transport.connect()
        # Cache tools
        tools = await self._transport.list_tools()
        self._tools = {t["name"]: t for t in tools}

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        await self._transport.disconnect()

    def list_tools(self) -> list[str]:
        """List available tool names."""
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> dict | None:
        """Get tool information by name."""
        return self._tools.get(name)

    async def call(self, tool_name: str, **kwargs: Any) -> Any:
        """
        Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        if tool_name not in self._tools:
            available = ", ".join(self._tools.keys())
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found on {self._server_name}",
                {"available_tools": available},
            )

        result = await self._transport.call_tool(tool_name, kwargs)
        return self._process_result(result)

    def _process_result(self, result: Any) -> Any:
        """
        Process tool result.

        Override in subclasses for custom result processing.
        """
        if result is None:
            return None

        # Extract text content if it's a standard MCP response
        if isinstance(result, dict):
            content = result.get("content", [])
            if content and isinstance(content, list):
                # Return text content if single text response
                if len(content) == 1 and content[0].get("type") == "text":
                    return content[0].get("text", "")
                # Return all content items
                return content
            return result

        return result

    async def __aenter__(self) -> "BaseService":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
