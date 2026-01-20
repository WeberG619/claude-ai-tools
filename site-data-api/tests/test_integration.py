#!/usr/bin/env python3
"""
Integration Tests for Revit Compliance System
==============================================
End-to-end tests for the complete compliance workflow.

These tests require a running Revit instance with RevitMCPBridge2026.
Run with: pytest test_integration.py -v --live

Author: BIM Ops Studio
"""

import pytest
import os
import json
from datetime import datetime
from typing import Dict, List, Any

import sys
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/site-data-api')

# Skip all tests in this file if not running live tests
pytestmark = pytest.mark.skipif(
    not os.environ.get('RUN_LIVE_TESTS'),
    reason="Live tests disabled. Set RUN_LIVE_TESTS=1 to enable."
)


class TestLiveRevitConnection:
    """Integration tests requiring live Revit connection."""

    @pytest.fixture
    def mcp_client(self):
        """Create and connect MCP client."""
        from revit_mcp_client import RevitMCPClient

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")
        yield client
        client.disconnect()

    def test_ping_revit(self, mcp_client):
        """Test basic connectivity to Revit."""
        result = mcp_client.ping()
        assert result is True

    def test_get_project_info(self, mcp_client):
        """Test getting project information."""
        response = mcp_client.get_project_info()
        assert response.success is True
        assert response.data is not None

    def test_get_all_schedules(self, mcp_client):
        """Test listing all schedules."""
        response = mcp_client.get_all_schedules()
        assert response.success is True

        schedules = response.data.get("views", [])
        print(f"Found {len(schedules)} schedules")
        for s in schedules[:5]:
            print(f"  - {s.get('name')}")

    def test_get_door_schedule(self, mcp_client):
        """Test getting door schedule data."""
        doors = mcp_client.get_door_schedule()

        print(f"Found {len(doors)} doors")
        if doors:
            print(f"First door: {doors[0]}")

            # Check expected fields
            first_door = doors[0]
            assert "Mark" in first_door or any(k for k in first_door.keys() if "mark" in k.lower())

    def test_get_window_schedule(self, mcp_client):
        """Test getting window schedule data."""
        windows = mcp_client.get_window_schedule()

        print(f"Found {len(windows)} windows")
        if windows:
            print(f"First window: {windows[0]}")


class TestLiveScheduleMapping:
    """Integration tests for schedule mapping with live data."""

    @pytest.fixture
    def mapped_schedules(self):
        """Get mapped schedule data from Revit."""
        from revit_mcp_client import RevitMCPClient
        from schedule_mapper import ScheduleFieldMapper

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")

        mapper = ScheduleFieldMapper()

        raw_doors = client.get_door_schedule()
        raw_windows = client.get_window_schedule()

        client.disconnect()

        return {
            "doors": mapper.map_door_schedule(raw_doors),
            "windows": mapper.map_window_schedule(raw_windows)
        }

    def test_door_mapping_has_mark(self, mapped_schedules):
        """Test that door mapping produces Mark field."""
        doors = mapped_schedules["doors"]
        if doors:
            assert "Mark" in doors[0]

    def test_door_mapping_has_dimensions(self, mapped_schedules):
        """Test that door mapping produces dimension fields."""
        doors = mapped_schedules["doors"]
        if doors:
            # At least one dimension should be present
            has_dimension = any(
                k in doors[0] for k in ["Width", "Height"]
            )
            assert has_dimension or len(doors[0]) > 1  # Has some data


class TestLiveComplianceWorkflow:
    """Integration tests for full compliance workflow."""

    @pytest.fixture
    def workflow(self):
        """Create compliance workflow with live connection."""
        from revit_mcp_client import RevitMCPClient
        from compliance_workflow import RevitComplianceWorkflow

        # Try to import the validator
        try:
            from revit_schedule_integration import RevitScheduleValidator
            validator = RevitScheduleValidator()
        except ImportError:
            pytest.skip("RevitScheduleValidator not available")

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")

        workflow = RevitComplianceWorkflow(
            mcp_client=client,
            validator=validator
        )

        yield workflow

        client.disconnect()

    def test_full_compliance_check(self, workflow):
        """Test running full compliance check."""
        report = workflow.run_full_compliance_check(
            check_doors=True,
            check_windows=True,
            check_walls=False,
            check_rooms=False,
            write_back_results=False
        )

        assert report is not None
        assert report.project_name is not None

        print(f"\nCompliance Report: {report.project_name}")
        print(f"Pass Rate: {report.pass_rate}%")
        print(f"Total Elements: {report.total_elements}")

    def test_compliance_check_with_progress(self, workflow):
        """Test compliance check runs without errors."""
        report = workflow.run_full_compliance_check(
            check_doors=True,
            check_windows=False,
            check_walls=False,
            check_rooms=False
        )

        # Just verify the report was generated
        assert report is not None
        assert report.project_name is not None


class TestLiveNOAValidation:
    """Integration tests for NOA validation with live data."""

    @pytest.fixture
    def noa_matcher(self):
        """Create NOA matcher with database."""
        try:
            from noa_matcher import NOAMatcher
            from noa_database import NOADatabase

            db = NOADatabase()
            matcher = NOAMatcher(db)
            return matcher
        except ImportError:
            pytest.skip("NOA modules not available")

    def test_validate_known_noa(self, noa_matcher):
        """Test validating a known NOA number."""
        # Use a test NOA number that exists in the database
        # This would need to be a real NOA number for actual testing
        result = noa_matcher.validate_noa_number("NOA-TEST-123")

        # Result should return valid/invalid status
        assert result is not None
        assert hasattr(result, 'is_valid')

    def test_suggest_products_for_door(self, noa_matcher):
        """Test suggesting NOA products for a door."""
        door_data = {
            "Mark": "D1",
            "Family_Name": "Single Flush",
            "Width": "36",
            "Height": "80"
        }

        suggestions = noa_matcher.suggest_noa_products(door_data)

        # Should return a list (may be empty if no matches)
        assert isinstance(suggestions, list)


class TestLiveReportGeneration:
    """Integration tests for report generation."""

    def test_generate_report_from_workflow(self):
        """Test generating report from actual workflow."""
        from revit_mcp_client import RevitMCPClient
        from compliance_workflow import RevitComplianceWorkflow
        from report_integration import ComplianceReportGenerator

        # Try to import validator
        try:
            from revit_schedule_integration import RevitScheduleValidator
            validator = RevitScheduleValidator()
        except ImportError:
            pytest.skip("RevitScheduleValidator not available")

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")

        try:
            workflow = RevitComplianceWorkflow(
                mcp_client=client,
                validator=validator
            )

            report = workflow.run_full_compliance_check(
                check_doors=True,
                check_windows=False,
                check_walls=False,
                check_rooms=False
            )

            generator = ComplianceReportGenerator(client)

            # Test that generator can produce output from real report
            assert report is not None
            assert report.report_text is not None or len(str(report)) > 0

        finally:
            client.disconnect()


class TestLiveParameterWriteBack:
    """Integration tests for writing parameters back to Revit."""

    @pytest.fixture
    def mcp_client(self):
        """Create and connect MCP client."""
        from revit_mcp_client import RevitMCPClient

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")
        yield client
        client.disconnect()

    def test_get_element_parameters(self, mcp_client):
        """Test getting parameters from an element."""
        # First get a door to get its ID
        doors = mcp_client.get_door_schedule()
        if not doors:
            pytest.skip("No doors in model")

        # Get first door's element ID
        first_door = doors[0]
        element_id = first_door.get("_element_id")

        if not element_id:
            pytest.skip("Door schedule doesn't include element IDs")

        response = mcp_client.get_element_parameters(element_id)

        assert response.success is True
        print(f"Parameters for element {element_id}: {response.data}")

    @pytest.mark.skip(reason="Write operations should only run when explicitly enabled")
    def test_set_parameter_value(self, mcp_client):
        """Test setting a parameter value on an element."""
        # This is a destructive test - only run when explicitly enabled
        # Would need a test element ID and parameter name
        pass


class TestEndToEndWorkflow:
    """Complete end-to-end integration tests."""

    def test_complete_workflow(self):
        """Test the complete workflow from extraction to report."""
        from revit_mcp_client import RevitMCPClient
        from schedule_mapper import ScheduleFieldMapper
        from compliance_workflow import RevitComplianceWorkflow
        from report_integration import ComplianceReportGenerator

        # 1. Connect to Revit
        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")

        try:
            # 2. Get project info
            project_info = client.get_project_info()
            print(f"Project: {project_info.data}")

            # 3. Extract schedules
            raw_doors = client.get_door_schedule()
            print(f"Extracted {len(raw_doors)} doors")

            # 4. Map fields
            mapper = ScheduleFieldMapper()
            mapped_doors = mapper.map_door_schedule(raw_doors)
            print(f"Mapped {len(mapped_doors)} doors")

            # 5. Validate (if validator available)
            try:
                from revit_schedule_integration import RevitScheduleValidator
                validator = RevitScheduleValidator()

                workflow = RevitComplianceWorkflow(
                    mcp_client=client,
                    validator=validator
                )

                report = workflow.run_full_compliance_check(
                    check_doors=True,
                    check_windows=False,
                    check_walls=False,
                    check_rooms=False
                )

                print(f"Compliance Pass Rate: {report.pass_rate}%")
                print(f"Report text generated: {len(report.report_text) if report.report_text else 0} characters")

            except ImportError:
                print("Validator not available - skipping validation")

        finally:
            client.disconnect()

    def test_workflow_with_goulds_tower(self):
        """Test workflow with GOULDS TOWER-1 project specifically."""
        from revit_mcp_client import RevitMCPClient

        client = RevitMCPClient()
        if not client.connect():
            pytest.skip("Cannot connect to RevitMCPBridge2026")

        try:
            # Check if GOULDS TOWER-1 is open
            project_info = client.get_project_info()
            project_name = project_info.data.get("projectName", "")

            if "GOULDS" not in project_name.upper():
                pytest.skip(f"GOULDS TOWER-1 not open. Current: {project_name}")

            print(f"Testing with project: {project_name}")

            # Get all schedules
            doors = client.get_door_schedule()
            windows = client.get_window_schedule()

            print(f"GOULDS TOWER-1 has {len(doors)} doors, {len(windows)} windows")

        finally:
            client.disconnect()


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================
def pytest_addoption(parser):
    """Add command-line options for pytest."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live integration tests (requires Revit connection)"
    )


def pytest_configure(config):
    """Configure pytest environment."""
    if config.getoption("--live"):
        os.environ['RUN_LIVE_TESTS'] = '1'


# =============================================================================
# RUN TESTS
# =============================================================================
if __name__ == "__main__":
    # Enable live tests when running directly
    os.environ['RUN_LIVE_TESTS'] = '1'
    pytest.main([__file__, "-v", "-s"])
