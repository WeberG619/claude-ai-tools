#!/usr/bin/env python3
"""
Tests for RevitMCPClient
========================
Unit tests for the named pipe client for RevitMCPBridge2026.

Author: BIM Ops Studio
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import sys
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/site-data-api')

from revit_mcp_client import RevitMCPClient, MCPResponse


class TestMCPResponse:
    """Tests for MCPResponse dataclass."""

    def test_success_response(self):
        """Test successful response creation."""
        response = MCPResponse(
            success=True,
            data={"test": "data"},
            error=None
        )
        assert response.success is True
        assert response.data == {"test": "data"}
        assert response.error is None

    def test_error_response(self):
        """Test error response creation."""
        response = MCPResponse(
            success=False,
            error="Connection failed"
        )
        assert response.success is False
        assert response.data is None
        assert response.error == "Connection failed"


class TestRevitMCPClientInit:
    """Tests for RevitMCPClient initialization."""

    def test_default_pipe_name(self):
        """Test default pipe name."""
        client = RevitMCPClient()
        assert client.pipe_name == "RevitMCPBridge2026"

    def test_custom_pipe_name(self):
        """Test custom pipe name."""
        client = RevitMCPClient(pipe_name="CustomPipe")
        assert client.pipe_name == "CustomPipe"

    def test_default_timeout(self):
        """Test default timeout."""
        client = RevitMCPClient()
        assert client.timeout == 30.0

    def test_custom_timeout(self):
        """Test custom timeout."""
        client = RevitMCPClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_pipe_path_format(self):
        """Test pipe path is correctly formatted."""
        client = RevitMCPClient()
        assert client.pipe_path == "\\\\.\\pipe\\RevitMCPBridge2026"

    def test_initial_state(self):
        """Test initial connection state."""
        client = RevitMCPClient()
        assert client.is_connected is False
        assert client.last_error is None


class TestRevitMCPClientConnection:
    """Tests for connection methods."""

    @patch.object(RevitMCPClient, '_test_connection')
    def test_connect_success(self, mock_test):
        """Test successful connection."""
        mock_test.return_value = True

        client = RevitMCPClient()
        result = client.connect()

        assert result is True
        # Note: is_connected also checks _pipe, so we check _connected directly
        assert client._connected is True

    @patch.object(RevitMCPClient, '_send_raw_command')
    def test_connect_failure(self, mock_send):
        """Test connection failure."""
        mock_send.return_value = None

        client = RevitMCPClient()
        result = client.connect(retry_count=1)

        assert result is False
        assert client.is_connected is False

    @patch.object(RevitMCPClient, '_send_raw_command')
    def test_connect_retry(self, mock_send):
        """Test connection retries."""
        # Fail first two attempts, succeed on third
        mock_send.side_effect = [None, None, {"success": True}]

        client = RevitMCPClient()
        result = client.connect(retry_count=3, retry_delay=0.01)

        assert result is True
        assert mock_send.call_count == 3

    def test_disconnect(self):
        """Test disconnection."""
        client = RevitMCPClient()
        client._connected = True

        client.disconnect()

        assert client.is_connected is False


class TestRevitMCPClientCommands:
    """Tests for send_command method."""

    @patch.object(RevitMCPClient, '_send_raw_command')
    def test_send_command_success(self, mock_send):
        """Test successful command."""
        mock_send.return_value = {"success": True, "data": {"value": 123}}

        client = RevitMCPClient()
        response = client.send_command("testMethod", {"param": "value"})

        assert response.success is True
        assert response.data["data"]["value"] == 123

    @patch.object(RevitMCPClient, '_send_raw_command')
    def test_send_command_no_response(self, mock_send):
        """Test command with no response."""
        mock_send.return_value = None

        client = RevitMCPClient()
        client._last_error = "Timeout"
        response = client.send_command("testMethod", {})

        assert response.success is False
        assert "Timeout" in response.error or "No response" in response.error

    @patch.object(RevitMCPClient, '_send_raw_command')
    def test_send_command_exception(self, mock_send):
        """Test command that raises exception."""
        mock_send.side_effect = Exception("Test error")

        client = RevitMCPClient()
        response = client.send_command("testMethod", {})

        assert response.success is False
        assert "Test error" in response.error


class TestRevitMCPClientScheduleMethods:
    """Tests for schedule-related methods."""

    @patch.object(RevitMCPClient, 'send_command')
    def test_get_all_schedules(self, mock_send):
        """Test getting all schedules."""
        mock_send.return_value = MCPResponse(
            success=True,
            data={"schedules": [
                {"scheduleId": 1, "scheduleName": "Door Schedule"},
                {"scheduleId": 2, "scheduleName": "Window Schedule"}
            ]}
        )

        client = RevitMCPClient()
        response = client.get_all_schedules()

        assert response.success is True
        mock_send.assert_called_once_with("getAllSchedules", {})

    @patch.object(RevitMCPClient, 'get_all_schedules')
    def test_get_schedule_by_name_found(self, mock_get):
        """Test finding schedule by name."""
        mock_get.return_value = MCPResponse(
            success=True,
            data={"schedules": [
                {"scheduleId": 1, "scheduleName": "Door Schedule"},
                {"scheduleId": 2, "scheduleName": "Window Schedule"}
            ]}
        )

        client = RevitMCPClient()
        schedule = client.get_schedule_by_name("Door Schedule")

        assert schedule is not None
        assert schedule["id"] == 1
        assert schedule["name"] == "Door Schedule"

    @patch.object(RevitMCPClient, 'get_all_schedules')
    def test_get_schedule_by_name_not_found(self, mock_get):
        """Test schedule not found."""
        mock_get.return_value = MCPResponse(
            success=True,
            data={"schedules": [{"scheduleId": 1, "scheduleName": "Door Schedule"}]}
        )

        client = RevitMCPClient()
        schedule = client.get_schedule_by_name("Nonexistent Schedule")

        assert schedule is None

    @patch.object(RevitMCPClient, 'send_command')
    def test_get_schedule_data_by_id(self, mock_send):
        """Test getting schedule data by ID."""
        mock_send.return_value = MCPResponse(
            success=True,
            data={"rows": [["Mark", "Width"], ["D1", "36"]]}
        )

        client = RevitMCPClient()
        response = client.get_schedule_data(12345)

        mock_send.assert_called_once_with("getScheduleData", {
            "scheduleId": 12345,
            "includeHeaders": True
        })

    @patch.object(RevitMCPClient, 'get_schedule_by_name')
    @patch.object(RevitMCPClient, 'send_command')
    def test_get_schedule_data_by_name(self, mock_send, mock_get_schedule):
        """Test getting schedule data by name."""
        mock_get_schedule.return_value = {"id": 12345, "name": "Door Schedule"}
        mock_send.return_value = MCPResponse(
            success=True,
            data={"rows": [["Mark", "Width"], ["D1", "36"]]}
        )

        client = RevitMCPClient()
        response = client.get_schedule_data("Door Schedule")

        assert response.success is True


class TestRevitMCPClientScheduleParsing:
    """Tests for schedule data parsing."""

    def test_parse_schedule_to_dicts(self):
        """Test parsing schedule data to dictionaries."""
        client = RevitMCPClient()

        schedule_data = {
            "rows": [
                ["Mark", "Width", "Height"],
                ["D1", "36", "80"],
                ["D2", "32", "80"]
            ],
            "includeHeaders": True
        }

        result = client._parse_schedule_to_dicts(schedule_data)

        assert len(result) == 2
        assert result[0]["Mark"] == "D1"
        assert result[0]["Width"] == "36"
        assert result[1]["Mark"] == "D2"

    def test_parse_schedule_empty(self):
        """Test parsing empty schedule."""
        client = RevitMCPClient()

        result = client._parse_schedule_to_dicts({"rows": []})

        assert result == []

    def test_parse_schedule_headers_only(self):
        """Test parsing schedule with headers only."""
        client = RevitMCPClient()

        schedule_data = {
            "rows": [["Mark", "Width", "Height"]],
            "includeHeaders": True
        }

        result = client._parse_schedule_to_dicts(schedule_data)

        assert result == []


class TestRevitMCPClientElementMethods:
    """Tests for element-related methods."""

    @patch.object(RevitMCPClient, 'send_command')
    def test_get_element_parameters(self, mock_send):
        """Test getting element parameters."""
        mock_send.return_value = MCPResponse(
            success=True,
            data={"parameters": {"Mark": "D1", "Width": "36"}}
        )

        client = RevitMCPClient()
        response = client.get_element_parameters(12345)

        mock_send.assert_called_once_with("getElementParameters", {"elementId": 12345})

    @patch.object(RevitMCPClient, 'send_command')
    def test_set_parameter_value(self, mock_send):
        """Test setting parameter value."""
        mock_send.return_value = MCPResponse(success=True)

        client = RevitMCPClient()
        response = client.set_parameter_value(12345, "Mark", "D1-NEW")

        mock_send.assert_called_once_with("setParameterValue", {
            "elementId": 12345,
            "parameterName": "Mark",
            "value": "D1-NEW"
        })

    @patch.object(RevitMCPClient, 'send_command')
    def test_set_multiple_parameters(self, mock_send):
        """Test setting multiple parameters."""
        mock_send.return_value = MCPResponse(success=True)

        updates = [
            {"elementId": 1, "parameterName": "Mark", "value": "D1"},
            {"elementId": 2, "parameterName": "Mark", "value": "D2"}
        ]

        client = RevitMCPClient()
        response = client.set_multiple_parameters(updates)

        mock_send.assert_called_once_with("setMultipleParameters", {"updates": updates})


class TestRevitMCPClientUtilityMethods:
    """Tests for utility methods."""

    @patch.object(RevitMCPClient, 'send_command')
    def test_ping_success(self, mock_send):
        """Test successful ping."""
        mock_send.return_value = MCPResponse(success=True)

        client = RevitMCPClient()
        result = client.ping()

        assert result is True

    @patch.object(RevitMCPClient, 'send_command')
    def test_ping_failure(self, mock_send):
        """Test failed ping."""
        mock_send.return_value = MCPResponse(success=False)

        client = RevitMCPClient()
        result = client.ping()

        assert result is False

    @patch.object(RevitMCPClient, 'send_command')
    def test_get_project_info(self, mock_send):
        """Test getting project info."""
        mock_send.return_value = MCPResponse(
            success=True,
            data={"projectName": "Test Project"}
        )

        client = RevitMCPClient()
        response = client.get_project_info()

        mock_send.assert_called_once_with("getProjectInfo", {})

    @patch.object(RevitMCPClient, 'send_command')
    def test_get_active_view(self, mock_send):
        """Test getting active view."""
        mock_send.return_value = MCPResponse(
            success=True,
            data={"viewName": "Level 1"}
        )

        client = RevitMCPClient()
        response = client.get_active_view()

        mock_send.assert_called_once_with("getActiveView", {})


# =============================================================================
# RUN TESTS
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
