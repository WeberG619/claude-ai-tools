"""Tests for MCP server discovery."""

import pytest
from pathlib import Path
import json
import tempfile

from weber_sdk.discovery import (
    discover_servers,
    MCPServerConfig,
    parse_server_config,
    list_server_categories,
)


class TestMCPServerConfig:
    """Tests for MCPServerConfig dataclass."""

    def test_basic_config(self):
        """Test basic configuration."""
        config = MCPServerConfig(
            name="test-server",
            command="python3",
            args=["server.py"],
        )
        assert config.name == "test-server"
        assert config.command == "python3"
        assert config.args == ["server.py"]
        assert not config.disabled

    def test_is_windows_server(self):
        """Test Windows server detection."""
        windows = MCPServerConfig(
            name="win",
            command="powershell.exe",
            args=["-Command", "python server.py"],
        )
        unix = MCPServerConfig(name="unix", command="python3", args=["server.py"])

        assert windows.is_windows_server
        assert not unix.is_windows_server

    def test_is_python_server(self):
        """Test Python server detection."""
        python = MCPServerConfig(name="py", command="python3", args=["server.py"])
        node = MCPServerConfig(name="node", command="npx", args=["server"])

        assert python.is_python_server
        assert not node.is_python_server

    def test_server_path(self):
        """Test server path extraction."""
        config = MCPServerConfig(
            name="test",
            command="python3",
            args=["/path/to/server.py"],
        )
        assert config.server_path == "/path/to/server.py"

    def test_to_dict(self):
        """Test dictionary conversion."""
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["server.py"],
            env={"KEY": "value"},
            disabled=True,
            comment="Test server",
        )
        d = config.to_dict()
        assert d["name"] == "test"
        assert d["disabled"] is True
        assert d["env"] == {"KEY": "value"}


class TestParseServerConfig:
    """Tests for parse_server_config function."""

    def test_parse_basic(self):
        """Test parsing basic config."""
        raw = {
            "command": "python3",
            "args": ["server.py"],
        }
        config = parse_server_config("test", raw)
        assert config.name == "test"
        assert config.command == "python3"

    def test_parse_with_all_fields(self):
        """Test parsing config with all fields."""
        raw = {
            "command": "python3",
            "args": ["server.py"],
            "env": {"KEY": "value"},
            "cwd": "/path/to/cwd",
            "disabled": True,
            "_comment": "Test comment",
        }
        config = parse_server_config("test", raw)
        assert config.cwd == "/path/to/cwd"
        assert config.disabled is True
        assert config.comment == "Test comment"


class TestDiscoverServers:
    """Tests for discover_servers function."""

    def test_discover_from_temp_config(self):
        """Test discovery from temporary config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)

            # Create settings.local.json
            settings = {
                "mcpServers": {
                    "test-server": {
                        "command": "python3",
                        "args": ["server.py"],
                        "disabled": False,
                    },
                    "disabled-server": {
                        "command": "python3",
                        "args": ["other.py"],
                        "disabled": True,
                    },
                }
            }
            with open(config_path / "settings.local.json", "w") as f:
                json.dump(settings, f)

            # Test without disabled
            servers = discover_servers(config_path=config_path)
            assert "test-server" in servers
            assert "disabled-server" not in servers

            # Test with disabled
            servers = discover_servers(include_disabled=True, config_path=config_path)
            assert "test-server" in servers
            assert "disabled-server" in servers

    def test_discover_from_mcp_configs(self):
        """Test discovery from mcp-configs folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)

            # Create mcp-configs directory
            mcp_configs = config_path / "mcp-configs"
            mcp_configs.mkdir()

            # Create a config file
            revit_config = {
                "mcpServers": {
                    "revit": {
                        "command": "python",
                        "args": ["revit_server.py"],
                    }
                }
            }
            with open(mcp_configs / "revit.json", "w") as f:
                json.dump(revit_config, f)

            servers = discover_servers(config_path=config_path)
            assert "revit" in servers


class TestListServerCategories:
    """Tests for list_server_categories function."""

    def test_categorization(self):
        """Test that servers are categorized correctly."""
        # This test depends on actual config, so we just verify structure
        categories = list_server_categories()
        assert isinstance(categories, dict)
        # At minimum, these categories exist
        for cat in categories.keys():
            assert isinstance(categories[cat], list)
