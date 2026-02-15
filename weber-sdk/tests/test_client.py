"""Tests for Weber SDK client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from weber_sdk.client import Weber, ServiceProxy, SERVICE_MAP, ALIASES
from weber_sdk.exceptions import ServerNotFoundError


class TestWeber:
    """Tests for the Weber client class."""

    def test_init_with_auto_discover(self):
        """Test initialization with auto-discovery."""
        w = Weber()
        # Should have discovered some servers
        assert isinstance(w._servers, dict)

    def test_init_without_auto_discover(self):
        """Test initialization without auto-discovery."""
        w = Weber(auto_discover=False)
        assert w._servers == {}

    def test_list_servers(self):
        """Test listing servers."""
        w = Weber()
        servers = w.list_servers()
        assert isinstance(servers, list)

    def test_getattr_creates_proxy(self):
        """Test that attribute access creates a ServiceProxy."""
        w = Weber()
        # Access a server name
        proxy = w.voice_input_mcp
        assert isinstance(proxy, ServiceProxy)
        # Should be cached
        assert w.voice_input_mcp is proxy

    def test_getattr_private_raises(self):
        """Test that private attributes raise AttributeError."""
        w = Weber()
        with pytest.raises(AttributeError):
            _ = w._private

    def test_service_map(self):
        """Test service mapping."""
        assert "voice-input-mcp" in SERVICE_MAP
        assert "excel-mcp" in SERVICE_MAP

    def test_aliases(self):
        """Test aliases."""
        assert ALIASES["voice"] == "voice-input-mcp"
        assert ALIASES["excel"] == "excel-mcp"


class TestServiceProxy:
    """Tests for the ServiceProxy class."""

    def test_proxy_creation(self):
        """Test proxy creation."""
        w = Weber()
        from weber_sdk.services.generic import GenericService

        proxy = ServiceProxy(w, "test-server", GenericService)
        assert proxy._server_name == "test-server"
        assert proxy._service_class == GenericService
        assert proxy._service is None
        assert not proxy._connected


class TestAliases:
    """Tests for server aliases."""

    def test_voice_alias(self):
        """Test voice alias resolves correctly."""
        assert ALIASES.get("voice") == "voice-input-mcp"

    def test_excel_alias(self):
        """Test excel alias resolves correctly."""
        assert ALIASES.get("excel") == "excel-mcp"

    def test_revit_aliases(self):
        """Test Revit aliases."""
        assert ALIASES.get("revit2025") == "revit"
        assert ALIASES.get("revit2026") == "revit"
