"""Tests for Permission Scoping v1.0 — per-agent tool/directory/access control."""

import json
import pytest
from permissions import (
    PermissionScope, ComplianceResult, DEFAULT_SCOPES,
    get_scope_for_agent, compile_permission_prompt,
    verify_output_compliance, merge_scopes, _tool_matches,
)


# ─── PERMISSION SCOPE TESTS ──────────────────────────────────

class TestPermissionScope:
    def test_default_construction(self):
        scope = PermissionScope()
        assert scope.allowed_tools == []
        assert scope.write_access is False
        assert scope.execute_access is False
        assert scope.network_access is False

    def test_to_dict(self):
        scope = PermissionScope(
            allowed_tools=["Read", "Grep"],
            write_access=True,
        )
        d = scope.to_dict()
        assert d["allowed_tools"] == ["Read", "Grep"]
        assert d["write_access"] is True
        assert d["execute_access"] is False

    def test_from_dict(self):
        d = {
            "allowed_tools": ["Read"],
            "write_access": True,
            "network_access": False,
        }
        scope = PermissionScope.from_dict(d)
        assert scope.allowed_tools == ["Read"]
        assert scope.write_access is True

    def test_from_dict_ignores_unknown_keys(self):
        d = {
            "allowed_tools": ["Read"],
            "unknown_field": "ignored",
        }
        scope = PermissionScope.from_dict(d)
        assert scope.allowed_tools == ["Read"]

    def test_roundtrip_serialization(self):
        scope = PermissionScope(
            allowed_tools=["Read", "Grep", "Glob"],
            denied_tools=["Bash"],
            write_access=False,
            custom_constraints=["No email"],
        )
        d = scope.to_dict()
        restored = PermissionScope.from_dict(d)
        assert restored.to_dict() == d

    def test_all_agents_have_scopes(self):
        expected_agents = [
            "tech-scout", "market-analyst", "code-architect",
            "floor-plan-processor", "excel-reporter", "revit-builder",
            "bim-validator", "client-liaison", "invoice-tracker",
            "proposal-writer", "python-engineer",
        ]
        for agent in expected_agents:
            assert agent in DEFAULT_SCOPES, f"Agent '{agent}' missing from DEFAULT_SCOPES"

    def test_research_agents_read_only(self):
        research_agents = ["tech-scout", "market-analyst", "code-architect"]
        for agent in research_agents:
            scope = DEFAULT_SCOPES[agent]
            assert scope.write_access is False, f"{agent} should not have write access"
            assert scope.execute_access is False, f"{agent} should not have execute access"

    def test_dev_agents_have_write(self):
        dev_agents = ["python-engineer", "revit-builder"]
        for agent in dev_agents:
            scope = DEFAULT_SCOPES[agent]
            assert scope.write_access is True, f"{agent} should have write access"


# ─── COMPILE PERMISSION PROMPT TESTS ─────────────────────────

class TestCompilePermissionPrompt:
    def test_prompt_mentions_tools(self):
        scope = PermissionScope(allowed_tools=["Read", "Grep"])
        prompt = compile_permission_prompt(scope, "test")
        assert "Read" in prompt
        assert "Grep" in prompt

    def test_denied_access_shows_denied(self):
        scope = PermissionScope(write_access=False, execute_access=False)
        prompt = compile_permission_prompt(scope)
        assert "DENIED" in prompt

    def test_directories_included(self):
        scope = PermissionScope(allowed_directories=["/mnt/d/Projects"])
        prompt = compile_permission_prompt(scope)
        assert "/mnt/d/Projects" in prompt

    def test_custom_constraints_included(self):
        scope = PermissionScope(custom_constraints=["Never send emails without approval"])
        prompt = compile_permission_prompt(scope)
        assert "Never send emails without approval" in prompt

    def test_agent_name_in_prompt(self):
        scope = PermissionScope()
        prompt = compile_permission_prompt(scope, "test-agent")
        assert "test-agent" in prompt

    def test_file_patterns_included(self):
        scope = PermissionScope(allowed_file_patterns=["*.md", "*.txt"])
        prompt = compile_permission_prompt(scope)
        assert "*.md" in prompt
        assert "*.txt" in prompt


# ─── VERIFY OUTPUT COMPLIANCE TESTS ───────────────────────────

class TestVerifyOutputCompliance:
    def test_clean_output_passes(self):
        scope = PermissionScope(
            allowed_tools=["Read", "Grep", "Glob"],
            write_access=False,
            execute_access=False,
        )
        output = "I read the file and found 10 wall segments. The data looks correct."
        result = verify_output_compliance(output, scope)
        assert result.compliant is True
        assert len(result.violations) == 0

    def test_write_detection(self):
        scope = PermissionScope(write_access=False)
        output = "I created the file at /tmp/output.txt with the analysis results."
        result = verify_output_compliance(output, scope)
        assert result.compliant is False
        assert any(v["type"] == "unauthorized_write" for v in result.violations)

    def test_write_detection_modified(self):
        scope = PermissionScope(write_access=False)
        output = "I modified the file to fix the issue."
        result = verify_output_compliance(output, scope)
        assert result.compliant is False

    def test_bash_detection(self):
        scope = PermissionScope(execute_access=False)
        output = "I ran the bash command to check the system status."
        result = verify_output_compliance(output, scope)
        assert result.compliant is False
        assert any(v["type"] == "unauthorized_execute" for v in result.violations)

    def test_denied_tool_detection(self):
        scope = PermissionScope(
            allowed_tools=["Read", "Grep"],
            denied_tools=["Edit", "Write", "Bash"],
        )
        output = "I used the Edit tool to fix the typo in the config."
        result = verify_output_compliance(output, scope)
        assert result.compliant is False
        assert any(v["type"] == "denied_tool_usage" for v in result.violations)

    def test_path_outside_scope(self):
        scope = PermissionScope(
            allowed_directories=["/mnt/d/Projects"],
        )
        output = "I accessed the data at /mnt/d/SecretData/passwords.txt"
        result = verify_output_compliance(output, scope)
        assert result.compliant is False
        assert any(v["type"] == "directory_outside_scope" for v in result.violations)

    def test_path_inside_scope_passes(self):
        scope = PermissionScope(
            allowed_directories=["/mnt/d/Projects"],
        )
        output = "I read the floor plan at /mnt/d/Projects/client/plan.pdf"
        result = verify_output_compliance(output, scope)
        # Should be compliant — path is within allowed directory
        outside = [v for v in result.violations if v["type"] == "directory_outside_scope"]
        assert len(outside) == 0

    def test_false_positive_tolerance(self):
        """Normal prose mentioning 'edit' shouldn't trigger violation."""
        scope = PermissionScope(
            allowed_tools=["Read", "Grep"],
            denied_tools=["Edit"],
        )
        output = "You may want to edit the configuration later."
        result = verify_output_compliance(output, scope)
        # Casual mention of "edit" in prose shouldn't match tool usage pattern
        assert result.compliant is True

    def test_empty_output_passes(self):
        scope = PermissionScope(write_access=False)
        result = verify_output_compliance("", scope)
        assert result.compliant is True

    def test_none_output_passes(self):
        scope = PermissionScope()
        result = verify_output_compliance(None, scope)
        assert result.compliant is True

    def test_write_allowed_no_violation(self):
        scope = PermissionScope(write_access=True)
        output = "I created the file with the report data."
        result = verify_output_compliance(output, scope)
        # Write is allowed, so no unauthorized_write violation
        write_violations = [v for v in result.violations if v["type"] == "unauthorized_write"]
        assert len(write_violations) == 0

    def test_checked_patterns_count(self):
        scope = PermissionScope(write_access=False, execute_access=False)
        output = "Some normal output text here."
        result = verify_output_compliance(output, scope)
        assert result.checked_patterns > 0


# ─── TOOL MATCHING TESTS ─────────────────────────────────────

class TestToolMatching:
    def test_exact_match(self):
        assert _tool_matches("Read", ["Read", "Grep"]) is True
        assert _tool_matches("Write", ["Read", "Grep"]) is False

    def test_wildcard_match(self):
        assert _tool_matches("mcp__excel-mcp__read_cell", ["mcp__excel-mcp__*"]) is True
        assert _tool_matches("mcp__revit-mcp__create", ["mcp__excel-mcp__*"]) is False

    def test_empty_patterns(self):
        assert _tool_matches("Read", []) is False


# ─── MERGE SCOPES TESTS ──────────────────────────────────────

class TestMergeScopes:
    def test_tool_intersection(self):
        base = PermissionScope(allowed_tools=["Read", "Grep", "Write"])
        override = PermissionScope(allowed_tools=["Read", "Grep", "Bash"])
        merged = merge_scopes(base, override)
        assert "Read" in merged.allowed_tools
        assert "Grep" in merged.allowed_tools
        assert "Write" not in merged.allowed_tools
        assert "Bash" not in merged.allowed_tools

    def test_write_denied_if_either_denies(self):
        base = PermissionScope(write_access=True)
        override = PermissionScope(write_access=False)
        merged = merge_scopes(base, override)
        assert merged.write_access is False

    def test_execute_denied_if_either_denies(self):
        base = PermissionScope(execute_access=True)
        override = PermissionScope(execute_access=False)
        merged = merge_scopes(base, override)
        assert merged.execute_access is False

    def test_directory_intersection(self):
        base = PermissionScope(allowed_directories=["/mnt/d/Projects", "/mnt/d/Data"])
        override = PermissionScope(allowed_directories=["/mnt/d/Projects"])
        merged = merge_scopes(base, override)
        assert "/mnt/d/Projects" in merged.allowed_directories

    def test_denied_tools_union(self):
        base = PermissionScope(denied_tools=["Bash"])
        override = PermissionScope(denied_tools=["Write"])
        merged = merge_scopes(base, override)
        assert "Bash" in merged.denied_tools
        assert "Write" in merged.denied_tools

    def test_custom_constraints_union(self):
        base = PermissionScope(custom_constraints=["No email"])
        override = PermissionScope(custom_constraints=["No delete"])
        merged = merge_scopes(base, override)
        assert "No email" in merged.custom_constraints
        assert "No delete" in merged.custom_constraints


# ─── GRACEFUL DEGRADATION TESTS ──────────────────────────────

class TestGracefulDegradation:
    def test_unknown_agent_gets_restrictive_default(self):
        scope = get_scope_for_agent("totally-unknown-agent")
        assert scope.write_access is False
        assert scope.execute_access is False
        assert "Read" in scope.allowed_tools

    def test_empty_agent_name(self):
        scope = get_scope_for_agent("")
        assert scope.write_access is False

    def test_none_agent_name(self):
        scope = get_scope_for_agent(None)
        assert scope.write_access is False

    def test_garbage_input_no_crash(self):
        scope = get_scope_for_agent(123)
        assert isinstance(scope, PermissionScope)
        result = verify_output_compliance(12345, scope)
        assert isinstance(result, ComplianceResult)
