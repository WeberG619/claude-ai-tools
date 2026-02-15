"""
Generic service wrapper for any MCP server.

Provides dynamic tool access without typed methods.
"""

from typing import Any

from weber_sdk.services.base import BaseService
from weber_sdk.transports.base import BaseTransport


class GenericService(BaseService):
    """
    Generic service wrapper that provides dynamic tool access.

    Allows calling any tool on the server without predefined methods:
        service.some_tool(arg1="value1", arg2="value2")
    """

    def __init__(self, transport: BaseTransport, server_name: str):
        super().__init__(transport, server_name)
        self._method_cache: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        """
        Dynamically create tool caller methods.

        This allows calling tools as if they were methods:
            service.voice_speak(text="Hello")
            service.get_excel_status()
        """
        # Avoid recursion for internal attributes
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if it's a known tool
        if name in self._tools:
            return self._create_tool_caller(name)

        # Create a potential tool caller (might fail at call time if tool doesn't exist)
        return self._create_tool_caller(name)

    def _create_tool_caller(self, tool_name: str) -> Any:
        """Create a callable that invokes the tool."""

        async def caller(**kwargs: Any) -> Any:
            return await self.call(tool_name, **kwargs)

        # Also provide sync version via run_sync
        def sync_caller(**kwargs: Any) -> Any:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context
                import concurrent.futures
                import threading

                result: Any = None
                exception: Exception | None = None

                def run_in_thread() -> None:
                    nonlocal result, exception
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(caller(**kwargs))
                        new_loop.close()
                    except Exception as e:
                        exception = e

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception:
                    raise exception
                return result
            else:
                return loop.run_until_complete(caller(**kwargs))

        # Attach both versions
        caller.sync = sync_caller  # type: ignore
        return caller

    async def invoke(self, tool_name: str, **kwargs: Any) -> Any:
        """
        Explicitly invoke a tool by name.

        This is equivalent to calling the tool as a method but more explicit:
            await service.invoke("voice_speak", text="Hello")
        """
        return await self.call(tool_name, **kwargs)
