#!/usr/bin/env python3
"""
Tests for ComplianceWorkflow
============================
Unit tests for the compliance workflow orchestration.

Author: BIM Ops Studio
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any
from datetime import datetime

import sys
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/site-data-api')

from compliance_workflow import (
    RevitComplianceWorkflow,
    ComplianceReport,
    ExtractedSchedules,
    ValidationResults,
    WriteBackSummary,
    WorkflowStatus
)
from revit_mcp_client import RevitMCPClient, MCPResponse


# Mock the ScheduleValidationResult for testing
class MockScheduleValidationResult:
    """Mock for ScheduleValidationResult from revit_schedule_integration."""
    def __init__(self, total=0, passed=0, failed=0, warnings=0, issues=None):
        self.total_elements = total
        self.passed = passed
        self.failed = failed
        self.warnings = warnings
        self.issues = issues or []


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_workflow_status_values(self):
        """Test all workflow status values exist."""
        assert WorkflowStatus.NOT_STARTED.value == "not_started"
        assert WorkflowStatus.EXTRACTING.value == "extracting"
        assert WorkflowStatus.VALIDATING.value == "validating"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"


class TestExtractedSchedules:
    """Tests for ExtractedSchedules dataclass."""

    def test_create_extracted_schedules(self):
        """Test creating extracted schedules container."""
        schedules = ExtractedSchedules(
            doors=[{"Mark": "D1"}],
            windows=[{"Mark": "W1"}],
            project_name="Test Project"
        )

        assert len(schedules.doors) == 1
        assert len(schedules.windows) == 1
        assert schedules.project_name == "Test Project"

    def test_extracted_schedules_defaults(self):
        """Test extracted schedules default values."""
        schedules = ExtractedSchedules()

        assert schedules.doors == []
        assert schedules.windows == []
        assert schedules.walls == []
        assert schedules.rooms == []


class TestWriteBackSummary:
    """Tests for WriteBackSummary dataclass."""

    def test_create_write_back_summary(self):
        """Test creating write-back summary."""
        summary = WriteBackSummary(
            total_elements=10,
            successful_writes=8,
            failed_writes=2
        )

        assert summary.total_elements == 10
        assert summary.successful_writes == 8
        assert summary.failed_writes == 2


class TestRevitComplianceWorkflowInit:
    """Tests for workflow initialization."""

    @patch('compliance_workflow.RevitMCPClient')
    @patch('compliance_workflow.RevitScheduleValidator')
    @patch('compliance_workflow.NOADatabase')
    def test_init_creates_defaults(self, mock_noa, mock_validator, mock_client):
        """Test initialization creates default instances."""
        workflow = RevitComplianceWorkflow()

        # Should create instances by default
        assert workflow.mcp_client is not None
        assert workflow.validator is not None
        assert workflow.noa_db is not None

    def test_init_with_custom_instances(self):
        """Test initialization with custom dependencies."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_validator = Mock()
        mock_noa_db = Mock()

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=mock_validator,
            noa_db=mock_noa_db
        )

        assert workflow.mcp_client == mock_client
        assert workflow.validator == mock_validator
        assert workflow.noa_db == mock_noa_db

    def test_init_status(self):
        """Test workflow starts with NOT_STARTED status."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_validator = Mock()

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=mock_validator,
            noa_db=Mock()
        )

        assert workflow.status == WorkflowStatus.NOT_STARTED


class TestRevitComplianceWorkflowProgressCallback:
    """Tests for progress callback functionality."""

    def test_set_progress_callback(self):
        """Test setting progress callback."""
        mock_client = Mock(spec=RevitMCPClient)
        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        callback = Mock()
        workflow.set_progress_callback(callback)

        assert workflow._progress_callback == callback

    def test_report_progress_calls_callback(self):
        """Test progress reporting calls the callback."""
        mock_client = Mock(spec=RevitMCPClient)
        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        callback = Mock()
        workflow.set_progress_callback(callback)
        workflow._report_progress("extracting", 0.5, "Test message")

        callback.assert_called_once_with("extracting", 0.5, "Test message")


class TestRevitComplianceWorkflowExtractSchedules:
    """Tests for schedule extraction."""

    def test_extract_schedules_all_types(self):
        """Test extracting all schedule types."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.is_connected = True
        # Mock direct API methods used by the workflow
        mock_client.get_all_doors.return_value = MCPResponse(
            success=True,
            data={"doors": [{"doorId": 123, "mark": "D1", "width": 36, "height": 80}]}
        )
        mock_client.get_all_windows.return_value = MCPResponse(
            success=True,
            data={"windows": [{"windowId": 124, "mark": "W1", "width": 48, "height": 60}]}
        )
        mock_client.get_all_rooms.return_value = MCPResponse(
            success=True,
            data={"rooms": [{"roomId": 125, "number": "101", "name": "Office"}]}
        )
        # Walls fall back to schedule parsing
        mock_client.get_wall_schedule.return_value = []

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        schedules = workflow.extract_schedules(
            check_doors=True,
            check_windows=True,
            check_walls=True,
            check_rooms=True
        )

        assert isinstance(schedules, ExtractedSchedules)
        assert len(schedules.doors) == 1
        assert len(schedules.windows) == 1
        assert len(schedules.rooms) == 1

    def test_extract_schedules_doors_only(self):
        """Test extracting only door schedules."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.is_connected = True
        mock_client.get_all_doors.return_value = MCPResponse(
            success=True,
            data={"doors": [{"doorId": 123, "mark": "D1", "width": 36, "height": 80}]}
        )

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        schedules = workflow.extract_schedules(
            check_doors=True,
            check_windows=False,
            check_walls=False,
            check_rooms=False
        )

        assert isinstance(schedules, ExtractedSchedules)
        assert len(schedules.doors) == 1


class TestRevitComplianceWorkflowValidateAll:
    """Tests for validation."""

    def test_validate_all_creates_results(self):
        """Test validate_all returns ValidationResults."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_validator = Mock()

        # Mock the validation results
        mock_result = MockScheduleValidationResult(total=5, passed=4, failed=1, warnings=0)
        mock_validator.validate_door_schedule.return_value = mock_result
        mock_validator.validate_window_schedule.return_value = mock_result
        mock_validator.validate_wall_schedule.return_value = mock_result
        mock_validator.validate_room_schedule.return_value = mock_result

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=mock_validator,
            noa_db=Mock()
        )

        schedules = ExtractedSchedules(
            doors=[{"Mark": "D1"}],
            windows=[{"Mark": "W1"}]
        )

        results = workflow.validate_all(schedules)

        assert isinstance(results, ValidationResults)


class TestRevitComplianceWorkflowFullWorkflow:
    """Tests for full compliance workflow."""

    def test_run_full_compliance_check_returns_report(self):
        """Test running full compliance check returns ComplianceReport."""
        # Setup mocks
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.is_connected = True
        mock_client.connect.return_value = True
        # Project info uses nested result format
        mock_client.get_project_info.return_value = MCPResponse(
            success=True,
            data={"result": {"name": "Test Project", "address": "123 Test St"}}
        )
        # Direct API methods return empty data for this test
        mock_client.get_all_doors.return_value = MCPResponse(success=True, data={"doors": []})
        mock_client.get_all_windows.return_value = MCPResponse(success=True, data={"windows": []})
        mock_client.get_all_rooms.return_value = MCPResponse(success=True, data={"rooms": []})
        # Fallback methods also return empty
        mock_client.get_door_schedule.return_value = []
        mock_client.get_window_schedule.return_value = []
        mock_client.get_room_schedule.return_value = []
        mock_client.get_wall_schedule.return_value = []

        mock_validator = Mock()
        mock_validator.validate_door_schedule.return_value = MockScheduleValidationResult()
        mock_validator.validate_window_schedule.return_value = MockScheduleValidationResult()
        mock_validator.validate_wall_schedule.return_value = MockScheduleValidationResult()
        mock_validator.validate_room_schedule.return_value = MockScheduleValidationResult()
        mock_validator.generate_compliance_report.return_value = "Test report"

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=mock_validator,
            noa_db=Mock()
        )

        report = workflow.run_full_compliance_check()

        assert isinstance(report, ComplianceReport)
        assert report.project_name == "Test Project"

    def test_run_compliance_check_with_project_info(self):
        """Test compliance check with provided project info."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.is_connected = True
        # Direct API method for doors
        mock_client.get_all_doors.return_value = MCPResponse(
            success=True,
            data={"doors": [{"doorId": 123, "mark": "D1", "width": 36, "height": 80}]}
        )

        mock_validator = Mock()
        mock_validator.validate_door_schedule.return_value = MockScheduleValidationResult()
        mock_validator.generate_compliance_report.return_value = "Report"

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=mock_validator,
            noa_db=Mock()
        )

        report = workflow.run_full_compliance_check(
            project_info={"name": "Custom Project", "address": "456 Main St"},
            check_doors=True,
            check_windows=False,
            check_walls=False,
            check_rooms=False
        )

        assert report.project_name == "Custom Project"

    def test_run_compliance_check_connection_failure(self):
        """Test compliance check handles connection failure."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.is_connected = False
        mock_client.connect.return_value = False
        mock_client.last_error = "Connection refused"

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        with pytest.raises(ConnectionError):
            workflow.run_full_compliance_check()


class TestRevitComplianceWorkflowWriteBack:
    """Tests for write-back functionality."""

    def test_write_back_results_returns_summary(self):
        """Test write_back_results returns WriteBackSummary."""
        mock_client = Mock(spec=RevitMCPClient)
        mock_client.set_parameter_value.return_value = MCPResponse(success=True)

        workflow = RevitComplianceWorkflow(
            mcp_client=mock_client,
            validator=Mock(),
            noa_db=Mock()
        )

        mock_result = MockScheduleValidationResult(total=1, passed=1, failed=0, issues=[])
        results = ValidationResults(
            door_result=mock_result
        )

        summary = workflow.write_back_results(results)

        assert isinstance(summary, WriteBackSummary)


class TestComplianceReport:
    """Tests for ComplianceReport dataclass."""

    def test_create_compliance_report(self):
        """Test creating compliance report."""
        schedules = ExtractedSchedules()
        results = ValidationResults()

        report = ComplianceReport(
            project_name="Test Project",
            project_address="123 Test St",
            hvhz=True,
            schedules=schedules,
            results=results,
            write_back=None,
            report_text="Test report",
            generated_at=datetime.now().isoformat(),
            total_elements=10,
            total_passed=8,
            total_failed=2,
            total_warnings=0,
            pass_rate=80.0
        )

        assert report.project_name == "Test Project"
        assert report.pass_rate == 80.0

    def test_compliance_report_pass_rate(self):
        """Test compliance report pass rate."""
        report = ComplianceReport(
            project_name="Test",
            project_address="",
            hvhz=True,
            schedules=ExtractedSchedules(),
            results=ValidationResults(),
            write_back=None,
            report_text="",
            generated_at="",
            total_elements=10,
            total_passed=9,
            total_failed=1,
            total_warnings=0,
            pass_rate=90.0
        )

        assert report.pass_rate == 90.0


# =============================================================================
# RUN TESTS
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
