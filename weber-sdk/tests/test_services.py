"""Tests for service wrappers."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from weber_sdk.services.base import BaseService
from weber_sdk.services.generic import GenericService
from weber_sdk.services.voice import VoiceService
from weber_sdk.services.excel import ExcelService
from weber_sdk.services.revit import RevitService
from weber_sdk.exceptions import ToolNotFoundError


class MockTransport:
    """Mock transport for testing."""

    def __init__(self):
        self.is_connected = True
        self.tools = [
            {"name": "test_tool", "description": "A test tool"},
            {"name": "another_tool", "description": "Another tool"},
        ]
        self.call_history = []

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def list_tools(self):
        return self.tools

    async def call_tool(self, name: str, arguments: dict):
        self.call_history.append((name, arguments))
        return {"content": [{"type": "text", "text": f"Called {name}"}]}


class TestBaseService:
    """Tests for BaseService."""

    @pytest.fixture
    def service(self):
        transport = MockTransport()
        return BaseService(transport, "test-server")

    @pytest.mark.asyncio
    async def test_connect(self, service):
        """Test service connection."""
        await service.connect()
        assert service.is_connected

    @pytest.mark.asyncio
    async def test_list_tools(self, service):
        """Test listing tools."""
        await service.connect()
        tools = service.list_tools()
        assert "test_tool" in tools

    @pytest.mark.asyncio
    async def test_call_tool(self, service):
        """Test calling a tool."""
        await service.connect()
        result = await service.call("test_tool", arg1="value1")
        assert "Called test_tool" in result

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises(self, service):
        """Test calling unknown tool raises error."""
        await service.connect()
        with pytest.raises(ToolNotFoundError):
            await service.call("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        transport = MockTransport()
        async with BaseService(transport, "test") as service:
            assert service.is_connected
        assert not transport.is_connected


class TestGenericService:
    """Tests for GenericService."""

    @pytest.fixture
    def service(self):
        transport = MockTransport()
        svc = GenericService(transport, "test-server")
        svc._tools = {"test_tool": {"name": "test_tool"}}
        return svc

    @pytest.mark.asyncio
    async def test_dynamic_method_access(self, service):
        """Test dynamic method creation."""
        await service.connect()
        # Should create a callable for the tool
        caller = service.test_tool
        assert callable(caller)

    @pytest.mark.asyncio
    async def test_invoke(self, service):
        """Test explicit invoke."""
        await service.connect()
        result = await service.invoke("test_tool", param="value")
        assert result is not None


class TestVoiceService:
    """Tests for VoiceService."""

    @pytest.fixture
    def voice_transport(self):
        transport = MockTransport()
        transport.tools = [
            {"name": "voice_speak", "description": "Speak text"},
            {"name": "voice_listen", "description": "Listen for input"},
            {"name": "voice_conversation", "description": "Converse"},
        ]
        return transport

    @pytest.mark.asyncio
    async def test_speak(self, voice_transport):
        """Test speak method."""
        service = VoiceService(voice_transport, "voice")
        service._tools = {t["name"]: t for t in voice_transport.tools}
        result = await service.speak("Hello")
        assert voice_transport.call_history[-1][0] == "voice_speak"

    @pytest.mark.asyncio
    async def test_listen(self, voice_transport):
        """Test listen method."""
        service = VoiceService(voice_transport, "voice")
        service._tools = {t["name"]: t for t in voice_transport.tools}
        result = await service.listen(max_duration=5)
        assert voice_transport.call_history[-1][0] == "voice_listen"


class TestExcelService:
    """Tests for ExcelService."""

    @pytest.fixture
    def excel_transport(self):
        transport = MockTransport()
        transport.tools = [
            {"name": "get_excel_status", "description": "Get status"},
            {"name": "read_cell", "description": "Read cell"},
            {"name": "write_cell", "description": "Write cell"},
            {"name": "read_range", "description": "Read range"},
        ]
        return transport

    @pytest.mark.asyncio
    async def test_get_status(self, excel_transport):
        """Test get_status method."""
        service = ExcelService(excel_transport, "excel")
        service._tools = {t["name"]: t for t in excel_transport.tools}
        result = await service.get_status()
        assert excel_transport.call_history[-1][0] == "get_excel_status"


class TestRevitService:
    """Tests for RevitService."""

    @pytest.fixture
    def revit_transport(self):
        transport = MockTransport()
        transport.tools = [
            {"name": "get_document_info", "description": "Get doc info"},
            {"name": "get_walls", "description": "Get walls"},
            {"name": "create_wall", "description": "Create wall"},
        ]
        return transport

    @pytest.mark.asyncio
    async def test_get_document_info(self, revit_transport):
        """Test get_document_info method."""
        service = RevitService(revit_transport, "revit", version="2026")
        service._tools = {t["name"]: t for t in revit_transport.tools}
        result = await service.get_document_info()
        assert revit_transport.call_history[-1][0] == "get_document_info"

    def test_version_set(self, revit_transport):
        """Test version is set correctly."""
        service = RevitService(revit_transport, "revit", version="2025")
        assert service.version == "2025"
