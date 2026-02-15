"""
MCP Server Discovery - Auto-discover MCP servers from Claude configurations.

Discovers servers from:
- ~/.claude/settings.local.json (main config)
- ~/.claude/mcp-configs/*.json (modular configs)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from weber_sdk.exceptions import ConfigurationError


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    disabled: bool = False
    comment: Optional[str] = None

    @property
    def is_windows_server(self) -> bool:
        """Check if this server runs on Windows (via powershell.exe)."""
        return "powershell" in self.command.lower()

    @property
    def is_python_server(self) -> bool:
        """Check if this is a Python-based server."""
        return "python" in self.command.lower()

    @property
    def server_path(self) -> Optional[str]:
        """Extract the main server script path if available."""
        for arg in self.args:
            if arg.endswith(".py"):
                return arg
            if arg.endswith((".js", ".ts")):
                return arg
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "cwd": self.cwd,
            "disabled": self.disabled,
            "comment": self.comment,
        }


def get_claude_config_path() -> Path:
    """Get the Claude configuration directory path."""
    # WSL: Check for Windows user home
    if os.path.exists("/mnt/c/Users"):
        wsl_home = Path.home()
        if (wsl_home / ".claude").exists():
            return wsl_home / ".claude"

    # Standard Unix path
    return Path.home() / ".claude"


def parse_server_config(name: str, config: dict) -> MCPServerConfig:
    """Parse a server configuration entry."""
    return MCPServerConfig(
        name=name,
        command=config.get("command", ""),
        args=config.get("args", []),
        env=config.get("env", {}),
        cwd=config.get("cwd"),
        disabled=config.get("disabled", False),
        comment=config.get("_comment"),
    )


def discover_servers(
    include_disabled: bool = False,
    config_path: Optional[Path] = None,
) -> dict[str, MCPServerConfig]:
    """
    Discover all MCP servers from Claude configuration files.

    Args:
        include_disabled: Include disabled servers in results
        config_path: Override the config directory path

    Returns:
        Dictionary mapping server names to their configurations
    """
    config_dir = config_path or get_claude_config_path()
    servers: dict[str, MCPServerConfig] = {}

    # 1. Load from settings.local.json
    settings_file = config_dir / "settings.local.json"
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            mcp_servers = settings.get("mcpServers", {})
            for name, config in mcp_servers.items():
                server = parse_server_config(name, config)
                if include_disabled or not server.disabled:
                    servers[name] = server
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {settings_file}", str(e))
        except Exception as e:
            raise ConfigurationError(f"Error reading {settings_file}", str(e))

    # 2. Load from mcp-configs/*.json
    mcp_configs_dir = config_dir / "mcp-configs"
    if mcp_configs_dir.exists():
        for config_file in mcp_configs_dir.glob("*.json"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                mcp_servers = config_data.get("mcpServers", {})
                for name, config in mcp_servers.items():
                    # Don't override if already exists
                    if name not in servers:
                        server = parse_server_config(name, config)
                        if include_disabled or not server.disabled:
                            servers[name] = server
            except json.JSONDecodeError:
                # Skip invalid JSON files
                continue
            except Exception:
                continue

    return servers


def discover_server_tools(server: MCPServerConfig) -> list[dict]:
    """
    Discover tools exposed by an MCP server by parsing its source.

    This is a best-effort heuristic - actual tool discovery happens
    at runtime when connecting to the server.

    Args:
        server: Server configuration

    Returns:
        List of tool definitions found
    """
    tools = []
    server_path = server.server_path

    if not server_path:
        return tools

    # Convert Windows path to WSL if needed
    if server_path.startswith("D:\\"):
        server_path = server_path.replace("D:\\", "/mnt/d/").replace("\\", "/")
    elif server_path.startswith("C:\\"):
        server_path = server_path.replace("C:\\", "/mnt/c/").replace("\\", "/")

    path = Path(server_path)
    if not path.exists():
        return tools

    try:
        content = path.read_text(encoding="utf-8")

        # Parse Python MCP servers
        if path.suffix == ".py":
            # Look for @mcp.tool() or @server.call_tool() patterns
            import re

            # FastMCP style: @mcp.tool()
            tool_pattern = r'@mcp\.tool\(\)\s*async\s+def\s+(\w+)\([^)]*\)[^:]*:\s*["\']+(.*?)["\']+'
            for match in re.finditer(tool_pattern, content, re.DOTALL):
                tools.append({"name": match.group(1), "description": match.group(2)[:200]})

            # Alternative: def name with docstring
            func_pattern = r'async\s+def\s+(\w+)\([^)]*\).*?:\s*["\']+(.*?)["\']+'
            for match in re.finditer(func_pattern, content, re.DOTALL):
                if match.group(1) not in [t["name"] for t in tools]:
                    tools.append({"name": match.group(1), "description": match.group(2)[:200]})

    except Exception:
        pass

    return tools


def list_server_categories() -> dict[str, list[str]]:
    """
    Categorize discovered servers by their primary function.

    Returns:
        Dictionary mapping category names to server names
    """
    servers = discover_servers(include_disabled=True)

    categories: dict[str, list[str]] = {
        "revit": [],
        "office": [],
        "voice": [],
        "database": [],
        "web": [],
        "automation": [],
        "other": [],
    }

    for name, server in servers.items():
        name_lower = name.lower()
        if "revit" in name_lower:
            categories["revit"].append(name)
        elif any(x in name_lower for x in ["excel", "word", "powerpoint"]):
            categories["office"].append(name)
        elif "voice" in name_lower:
            categories["voice"].append(name)
        elif any(x in name_lower for x in ["sqlite", "postgres", "database"]):
            categories["database"].append(name)
        elif any(x in name_lower for x in ["web", "scraper", "browser"]):
            categories["web"].append(name)
        elif any(x in name_lower for x in ["autocad", "email", "git"]):
            categories["automation"].append(name)
        else:
            categories["other"].append(name)

    return {k: v for k, v in categories.items() if v}


if __name__ == "__main__":
    # CLI tool for discovery
    import sys

    servers = discover_servers(include_disabled=True)
    print(f"Discovered {len(servers)} MCP servers:\n")

    for name, server in sorted(servers.items()):
        status = "DISABLED" if server.disabled else "enabled"
        platform = "Windows" if server.is_windows_server else "Unix"
        print(f"  {name}:")
        print(f"    Status: {status}")
        print(f"    Platform: {platform}")
        print(f"    Command: {server.command}")
        if server.comment:
            print(f"    Description: {server.comment}")
        print()
