"""
STDIO transport for MCP servers.

Spawns an MCP server process and communicates via stdin/stdout using JSON-RPC.
"""

import asyncio
import json
import os
import sys
from typing import Any

from weber_sdk.discovery import MCPServerConfig
from weber_sdk.exceptions import ConnectionError, ToolExecutionError, TimeoutError
from weber_sdk.transports.base import BaseTransport


class StdioTransport(BaseTransport):
    """
    STDIO transport that spawns and communicates with MCP servers.

    Uses JSON-RPC 2.0 protocol over stdin/stdout.
    """

    def __init__(
        self,
        config: MCPServerConfig,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._connected = False
        self._tools: list[dict] = []
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected and self._process is not None

    def _get_next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _build_command(self) -> tuple[str, list[str]]:
        """Build the command and arguments to spawn the server."""
        cmd = self.config.command
        args = self.config.args.copy()

        # Handle Windows-specific commands from WSL
        if self.config.is_windows_server:
            # The command is already powershell.exe with args
            return cmd, args

        # Handle Python commands
        if cmd == "python3":
            cmd = sys.executable
        elif cmd == "python":
            # On Windows via WSL, might need adjustment
            if os.path.exists("/mnt/c/Users"):
                # We're in WSL, but the server might be Windows Python
                pass
            cmd = sys.executable

        return cmd, args

    def _build_env(self) -> dict[str, str]:
        """Build environment variables for the server process."""
        env = os.environ.copy()

        # Add configured environment variables
        for key, value in self.config.env.items():
            # Expand environment variable references
            if value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                env[key] = os.environ.get(var_name, "")
            else:
                env[key] = value

        return env

    async def connect(self) -> None:
        """Spawn the MCP server process and establish connection."""
        if self._connected:
            return

        cmd, args = self._build_command()
        env = self._build_env()
        cwd = self.config.cwd

        try:
            self._process = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )
            self._connected = True

            # Initialize MCP connection
            await self._initialize()

        except FileNotFoundError:
            raise ConnectionError(
                f"Command not found: {cmd}",
                {"command": cmd, "args": args},
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to start server {self.config.name}",
                str(e),
            )

    async def _initialize(self) -> None:
        """Send MCP initialize request."""
        try:
            result = await self.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "clientInfo": {
                        "name": "weber-sdk",
                        "version": "0.1.0",
                    },
                },
            )

            # Send initialized notification
            await self._send_notification("notifications/initialized", {})

            # Cache available tools
            self._tools = await self.list_tools()

        except Exception as e:
            await self.disconnect()
            raise ConnectionError(f"MCP initialization failed for {self.config.name}", str(e))

    async def disconnect(self) -> None:
        """Terminate the server process."""
        self._connected = False

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            except Exception:
                pass
            finally:
                self._process = None

    async def send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC 2.0 request and wait for response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise ConnectionError(f"Not connected to {self.config.name}")

        request_id = self._get_next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        request_line = json.dumps(request) + "\n"

        for attempt in range(self.max_retries):
            try:
                # Send request
                async with self._write_lock:
                    self._process.stdin.write(request_line.encode())
                    await self._process.stdin.drain()

                # Read response
                async with self._read_lock:
                    response_line = await asyncio.wait_for(
                        self._process.stdout.readline(),
                        timeout=self.timeout,
                    )

                if not response_line:
                    raise ConnectionError(f"Server {self.config.name} closed connection")

                response = json.loads(response_line.decode())

                if "error" in response:
                    error = response["error"]
                    raise ToolExecutionError(
                        error.get("message", "Unknown error"),
                        {"code": error.get("code"), "data": error.get("data")},
                    )

                return response.get("result")

            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    continue
                raise TimeoutError(f"Request to {self.config.name} timed out after {self.timeout}s")
            except json.JSONDecodeError as e:
                raise ConnectionError(f"Invalid JSON response from {self.config.name}", str(e))

        raise ConnectionError(f"Max retries exceeded for {self.config.name}")

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._process or not self._process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params

        notification_line = json.dumps(notification) + "\n"

        async with self._write_lock:
            self._process.stdin.write(notification_line.encode())
            await self._process.stdin.drain()

    async def list_tools(self) -> list[dict]:
        """List available tools from the MCP server."""
        result = await self.send_request("tools/list")
        tools = result.get("tools", []) if result else []
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result (typically a list of content items)
        """
        result = await self.send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )
        return result

    def get_cached_tools(self) -> list[dict]:
        """Get cached list of tools (from initialization)."""
        return self._tools.copy()
