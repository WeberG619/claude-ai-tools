"""
Weber SDK Client - Unified interface to all MCP servers.

Usage:
    from weber_sdk import Weber

    # Sync usage
    w = Weber()
    w.voice.speak_sync('Hello')

    # Async usage
    async with Weber() as w:
        await w.voice.speak('Hello')
        await w.excel.get_status()
        walls = await w.revit2026.get_walls()
"""

from typing import Any

from weber_sdk.discovery import discover_servers, MCPServerConfig
from weber_sdk.transports.stdio import StdioTransport
from weber_sdk.services.base import BaseService
from weber_sdk.services.generic import GenericService
from weber_sdk.services.voice import VoiceService
from weber_sdk.services.excel import ExcelService
from weber_sdk.services.revit import RevitService
from weber_sdk.exceptions import ServerNotFoundError


# Mapping of server names to service classes
SERVICE_MAP: dict[str, type[BaseService]] = {
    "voice-input-mcp": VoiceService,
    "voice": VoiceService,
    "excel-mcp": ExcelService,
    "excel": ExcelService,
    "revit": RevitService,
    "revit-mcp": RevitService,
}


# Alias mappings for convenience
ALIASES: dict[str, str] = {
    "voice": "voice-input-mcp",
    "excel": "excel-mcp",
    "word": "word-mcp",
    "powerpoint": "powerpoint-mcp",
    "autocad": "autocad-mcp",
    "revit2025": "revit",  # Uses the revit.json config
    "revit2026": "revit",  # Also revit.json but with different pipe
}


class ServiceProxy:
    """
    Lazy service proxy that connects on first use.

    Allows accessing services without explicitly connecting first.
    """

    def __init__(
        self,
        client: "Weber",
        server_name: str,
        service_class: type[BaseService],
    ):
        self._client = client
        self._server_name = server_name
        self._service_class = service_class
        self._service: BaseService | None = None
        self._connected = False

    async def _ensure_connected(self) -> BaseService:
        """Ensure the service is connected."""
        if self._service is None or not self._connected:
            config = self._client._get_server_config(self._server_name)
            transport = StdioTransport(config)
            self._service = self._service_class(transport, self._server_name)
            await self._service.connect()
            self._connected = True
        return self._service

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying service."""
        # Return async wrapper for service methods
        async def async_proxy(*args: Any, **kwargs: Any) -> Any:
            service = await self._ensure_connected()
            method = getattr(service, name)
            if callable(method):
                result = method(*args, **kwargs)
                # Await if coroutine
                if hasattr(result, "__await__"):
                    return await result
                return result
            return method

        # Check if this is a sync method
        if name.endswith("_sync"):
            def sync_proxy(*args: Any, **kwargs: Any) -> Any:
                import asyncio

                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(async_proxy(*args, **kwargs))
                finally:
                    loop.close()

            return sync_proxy

        return async_proxy


class Weber:
    """
    Unified SDK client for all MCP servers.

    Provides access to all MCP servers through a single interface:
        w = Weber()
        w.voice.speak('Hello')
        w.excel.get_status()
        w.revit2026.get_walls()

    Services are connected lazily on first use.
    """

    def __init__(
        self,
        auto_discover: bool = True,
        config_path: str | None = None,
    ):
        """
        Initialize the Weber SDK.

        Args:
            auto_discover: Automatically discover MCP servers from config files
            config_path: Optional override for config directory path
        """
        self._servers: dict[str, MCPServerConfig] = {}
        self._services: dict[str, BaseService] = {}
        self._proxies: dict[str, ServiceProxy] = {}

        if auto_discover:
            self._discover_servers(config_path)

    def _discover_servers(self, config_path: str | None = None) -> None:
        """Discover available MCP servers."""
        from pathlib import Path

        path = Path(config_path) if config_path else None
        self._servers = discover_servers(include_disabled=False, config_path=path)

    def _get_server_config(self, name: str) -> MCPServerConfig:
        """Get server configuration by name, handling aliases."""
        # Check aliases
        actual_name = ALIASES.get(name, name)

        if actual_name in self._servers:
            return self._servers[actual_name]

        # Try finding by partial match
        for server_name, config in self._servers.items():
            if name.lower() in server_name.lower():
                return config

        available = ", ".join(self._servers.keys())
        raise ServerNotFoundError(
            f"Server '{name}' not found",
            {"available_servers": available},
        )

    def __getattr__(self, name: str) -> ServiceProxy:
        """
        Dynamically create service proxies for server access.

        Allows accessing servers as attributes:
            w.voice.speak('Hello')
            w.excel.get_status()
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if proxy already exists
        if name in self._proxies:
            return self._proxies[name]

        # Determine service class
        actual_name = ALIASES.get(name, name)
        service_class = SERVICE_MAP.get(actual_name, GenericService)

        # Create and cache proxy
        proxy = ServiceProxy(self, name, service_class)
        self._proxies[name] = proxy
        return proxy

    def list_servers(self) -> list[str]:
        """
        List all discovered servers.

        Returns:
            List of server names
        """
        return list(self._servers.keys())

    def get_server_info(self, name: str) -> dict[str, Any]:
        """
        Get information about a specific server.

        Args:
            name: Server name

        Returns:
            Server configuration dictionary
        """
        config = self._get_server_config(name)
        return config.to_dict()

    async def connect_all(self) -> None:
        """Connect to all discovered servers."""
        for name in self._servers:
            proxy = getattr(self, name.replace("-", "_"))
            await proxy._ensure_connected()

    async def disconnect_all(self) -> None:
        """Disconnect from all connected services."""
        for service in self._services.values():
            if service.is_connected:
                await service.disconnect()
        self._services.clear()

        for proxy in self._proxies.values():
            if proxy._service and proxy._connected:
                await proxy._service.disconnect()
                proxy._connected = False

    async def __aenter__(self) -> "Weber":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect_all()

    # Note: Service access is via __getattr__, e.g.:
    #   w.voice.speak("Hello")
    #   w.excel.get_status()
    #   w.revit2026.get_walls()
    # No explicit properties needed - they're created dynamically.
