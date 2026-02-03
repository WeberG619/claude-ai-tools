#!/usr/bin/env python3
"""
Unit tests for MCP Seatbelt security layer.

Run with: python -m pytest tests/test_seatbelt.py -v
Or: python tests/test_seatbelt.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from policy_engine import PolicyEngine, Policy
from validator import Validator, ValidationResult
from risk_scorer import RiskScorer
from audit_logger import AuditLogger


class TestPolicyEngine(TestCase):
    """Tests for policy loading and matching."""

    def test_load_default_policies(self):
        """Should load policies from default directory."""
        engine = PolicyEngine()
        policies = engine.list_policies()
        self.assertGreater(len(policies), 0)

    def test_exact_match(self):
        """Should match exact tool names."""
        engine = PolicyEngine()
        policy = engine.get_policy("mcp__whatsapp__whatsapp_send_message")
        self.assertIsNotNone(policy)
        self.assertGreaterEqual(policy.risk, 8)

    def test_wildcard_match(self):
        """Should match wildcard patterns."""
        engine = PolicyEngine()
        policy = engine.get_policy("mcp__voice__speak")
        self.assertIsNotNone(policy)
        self.assertEqual(policy.pattern, "mcp__voice__*")

    def test_default_fallback(self):
        """Should fall back to default for unknown tools."""
        engine = PolicyEngine()
        policy = engine.get_policy("mcp__unknown__tool")
        self.assertIsNotNone(policy)
        self.assertEqual(policy.action, "log_only")

    def test_specificity_ordering(self):
        """More specific patterns should match before less specific."""
        engine = PolicyEngine()

        # Specific tool should match its own policy, not wildcard
        policy = engine.get_policy("mcp__excel-mcp__run_macro_tool")
        self.assertEqual(policy.action, "block")

        # Other excel tools should match wildcard
        policy = engine.get_policy("mcp__excel-mcp__write_cell")
        self.assertNotEqual(policy.action, "block")


class TestValidator(TestCase):
    """Tests for validation rules."""

    def setUp(self):
        self.validator = Validator()

    def test_recipient_whitelist_pass(self):
        """Should allow whitelisted recipients."""
        policy = Policy(
            pattern="test",
            rules=[{
                "type": "recipient_whitelist",
                "config": {"allowed": ["@bdarchitect.net", "test@example.com"]}
            }]
        )
        # Convert to proper format
        from policy_engine import PolicyRule
        policy.rules = [PolicyRule(type="recipient_whitelist",
                                    config={"allowed": ["@bdarchitect.net"]})]

        result = self.validator.validate(
            "test_tool",
            {"to": "bruce@bdarchitect.net"},
            policy
        )
        # Should not block
        self.assertNotEqual(result.action, "block")

    def test_recipient_whitelist_block(self):
        """Should block non-whitelisted recipients."""
        from policy_engine import PolicyRule
        policy = Policy(
            pattern="test",
            action="log_only",
            rules=[PolicyRule(type="recipient_whitelist",
                              config={"allowed": ["@bdarchitect.net"]})]
        )

        result = self.validator.validate(
            "test_tool",
            {"to": "hacker@evil.com"},
            policy
        )
        self.assertEqual(result.action, "block")
        self.assertIn("whitelist", result.message.lower())

    def test_block_patterns(self):
        """Should block dangerous patterns."""
        from policy_engine import PolicyRule
        policy = Policy(
            pattern="test",
            action="log_only",
            rules=[PolicyRule(type="block_patterns",
                              config={"patterns": ["--force", "rm -rf"]})]
        )

        result = self.validator.validate(
            "test_tool",
            {"command": "git push --force origin main"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_path_validation_pass(self):
        """Should allow paths within allowed roots."""
        from policy_engine import PolicyRule
        policy = Policy(
            pattern="test",
            action="log_only",
            rules=[PolicyRule(type="path_validation",
                              config={"allowed_roots": ["D:/", "/mnt/d/"]})]
        )

        result = self.validator.validate(
            "test_tool",
            {"path": "D:/Projects/test.rvt"},
            policy
        )
        self.assertNotEqual(result.action, "block")

    def test_path_validation_block_traversal(self):
        """Should block path traversal attempts."""
        from policy_engine import PolicyRule
        policy = Policy(
            pattern="test",
            action="log_only",
            rules=[PolicyRule(type="path_validation",
                              config={"allowed_roots": ["D:/"],
                                     "block_traversal": True})]
        )

        result = self.validator.validate(
            "test_tool",
            {"path": "D:/Projects/../../../etc/passwd"},
            policy
        )
        self.assertEqual(result.action, "block")
        self.assertIn("traversal", result.message.lower())

    def test_command_sanitize(self):
        """Should block command injection attempts."""
        from policy_engine import PolicyRule
        policy = Policy(
            pattern="test",
            action="log_only",
            rules=[PolicyRule(type="command_sanitize",
                              config={"block_chars": [";", "|", "&"]})]
        )

        result = self.validator.validate(
            "test_tool",
            {"command": "ls; rm -rf /"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_blocks(self):
        """Should block universally dangerous patterns."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"cmd": "rm -rf /"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_ssh_path(self):
        """Should block .ssh directory access."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"file_path": "C:\\Users\\test\\.ssh\\id_rsa"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_ssh_path_unix(self):
        """Should block .ssh directory access (Unix paths)."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"path": "/home/user/.ssh/authorized_keys"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_aws_credentials(self):
        """Should block .aws directory access."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"file": "C:\\Users\\test\\.aws\\credentials"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_credentials_json(self):
        """Should block credentials.json files."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"output": "D:\\backup\\credentials.json"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_pem_files(self):
        """Should block .pem key files."""
        policy = Policy(pattern="test", action="log_only")

        result = self.validator.validate(
            "test_tool",
            {"key_file": "/etc/ssl/private/server.pem"},
            policy
        )
        self.assertEqual(result.action, "block")

    def test_universal_block_private_key_names(self):
        """Should block files named id_rsa, id_ed25519, etc."""
        policy = Policy(pattern="test", action="log_only")

        for key_name in ["id_rsa", "id_ed25519", "id_ecdsa"]:
            result = self.validator.validate(
                "test_tool",
                {"file": f"/tmp/{key_name}"},
                policy
            )
            self.assertEqual(result.action, "block", f"Failed to block {key_name}")

    def test_redact_sensitive(self):
        """Should redact sensitive fields in logs."""
        result = self.validator.validate(
            "test_tool",
            {"user": "test", "password": "secret123", "data": "x" * 100},
            Policy(pattern="test")
        )

        self.assertEqual(result.redacted_params.get("password"), "REDACTED")
        self.assertIn("...", result.redacted_params.get("data", ""))


class TestRiskScorer(TestCase):
    """Tests for risk scoring."""

    def setUp(self):
        self.scorer = RiskScorer()

    def test_base_risk(self):
        """Should use policy base risk."""
        policy = Policy(pattern="test", risk=5)
        result = ValidationResult()

        score = self.scorer.calculate(
            "mcp__test__tool",
            {},
            policy,
            result
        )
        self.assertGreaterEqual(score, 5)

    def test_external_comm_modifier(self):
        """Should increase risk for external communication."""
        policy = Policy(pattern="test", risk=3)
        result = ValidationResult()

        score = self.scorer.calculate(
            "mcp__whatsapp__send_message",
            {},
            policy,
            result
        )
        # Should be higher than base due to external comm modifier
        self.assertGreater(score, 3)

    def test_sensitive_path_modifier(self):
        """Should increase risk for sensitive paths."""
        policy = Policy(pattern="test", risk=3)
        result = ValidationResult()

        score = self.scorer.calculate(
            "mcp__test__tool",
            {"path": "/etc/passwd"},
            policy,
            result
        )
        self.assertGreater(score, 3)

    def test_irreversible_modifier(self):
        """Should increase risk for irreversible operations."""
        policy = Policy(pattern="test", risk=3)
        result = ValidationResult()

        score = self.scorer.calculate(
            "mcp__test__tool",
            {"command": "git push --force"},
            policy,
            result
        )
        self.assertGreater(score, 3)

    def test_max_score_cap(self):
        """Risk should never exceed 10."""
        policy = Policy(pattern="test", risk=9)
        result = ValidationResult(rules_failed=["a", "b", "c"])

        score = self.scorer.calculate(
            "mcp__whatsapp__send_message",
            {"path": "/etc/passwd", "cmd": "delete --force"},
            policy,
            result
        )
        self.assertLessEqual(score, 10)


class TestAuditLogger(TestCase):
    """Tests for audit logging."""

    def setUp(self):
        # Use temp file for tests
        self.temp_dir = tempfile.mkdtemp()
        self.audit_path = Path(self.temp_dir) / "test_audit.ndjson"
        self.logger = AuditLogger(audit_path=self.audit_path)

    def test_log_entry(self):
        """Should write valid NDJSON entries."""
        result = ValidationResult(
            action="allow",
            risk_score=5,
            policy_matched="test_policy",
            redacted_params={"to": "test@example.com"}
        )
        policy = Policy(pattern="test")

        self.logger.log(
            tool_name="mcp__test__tool",
            result=result,
            policy=policy,
            tool_input={"to": "test@example.com"}
        )

        # Read and verify
        with open(self.audit_path) as f:
            line = f.readline()
            entry = json.loads(line)

        self.assertEqual(entry["tool"], "mcp__test__tool")
        self.assertEqual(entry["action"], "allow")
        self.assertEqual(entry["risk_score"], 5)

    def test_log_error(self):
        """Should log errors separately."""
        self.logger.log_error("mcp__test__tool", "Test error")

        with open(self.audit_path) as f:
            line = f.readline()
            entry = json.loads(line)

        self.assertEqual(entry["action"], "error")
        self.assertIn("Test error", entry["reason"])

    def test_query_with_filters(self):
        """Should filter query results."""
        # Add some entries
        for action in ["allow", "block", "allow"]:
            result = ValidationResult(action=action, risk_score=5)
            self.logger.log("mcp__test", result, Policy(pattern="test"), {})

        # Query for blocks only
        blocked = self.logger.query(filters={"action": "block"})
        self.assertEqual(len(blocked), 1)

    def test_get_stats(self):
        """Should compute correct statistics."""
        actions = ["allow", "block", "allow", "warn"]
        for action in actions:
            result = ValidationResult(action=action, risk_score=5)
            self.logger.log("mcp__test", result, Policy(pattern="test"), {})

        stats = self.logger.get_stats()
        self.assertEqual(stats["total_calls"], 4)
        self.assertEqual(stats["blocked_count"], 1)


class TestIntegration(TestCase):
    """Integration tests for full seatbelt flow."""

    def test_whatsapp_to_unknown_blocked(self):
        """WhatsApp to unknown recipient should warn/block."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__whatsapp__whatsapp_send_message")
        result = validator.validate(
            "mcp__whatsapp__whatsapp_send_message",
            {"contact": "hacker@evil.com", "message": "test"},
            policy
        )

        # Should either block or warn based on policy
        self.assertIn(result.action, ["block", "warn"])

    def test_voice_allowed(self):
        """Voice operations should always be allowed."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__voice__speak")
        result = validator.validate(
            "mcp__voice__speak",
            {"text": "Hello world", "voice": "andrew"},
            policy
        )

        self.assertNotEqual(result.action, "block")

    def test_vba_macro_blocked(self):
        """Excel VBA macros should always be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__excel-mcp__run_macro_tool")
        result = validator.validate(
            "mcp__excel-mcp__run_macro_tool",
            {"macro_name": "MyMacro"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_git_force_push_blocked(self):
        """Git force push should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__git__execute")
        result = validator.validate(
            "mcp__git__execute",
            {"command": "push --force origin main"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_sql_set_password_blocked(self):
        """SQL SET password should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__sqlite-server__write_query")
        result = validator.validate(
            "mcp__sqlite-server__write_query",
            {"query": "UPDATE users SET password = 'hacked'"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_sql_set_api_key_blocked(self):
        """SQL SET api_key should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__sqlite-server__write_query")
        result = validator.validate(
            "mcp__sqlite-server__write_query",
            {"query": "UPDATE config SET api_key = 'stolen'"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_sql_set_token_blocked(self):
        """SQL SET token should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__sqlite-server__write_query")
        result = validator.validate(
            "mcp__sqlite-server__write_query",
            {"query": "UPDATE sessions SET token = 'hijacked'"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_sql_normal_update_allowed(self):
        """Normal SQL UPDATE should be allowed."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__sqlite-server__write_query")
        result = validator.validate(
            "mcp__sqlite-server__write_query",
            {"query": "UPDATE users SET name = 'John'"},
            policy
        )

        # Should not be blocked (log_only is the default)
        self.assertNotEqual(result.action, "block")

    def test_ssh_path_in_excel_blocked(self):
        """SSH path in Excel import should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__excel-mcp__import_csv")
        result = validator.validate(
            "mcp__excel-mcp__import_csv",
            {"file_path": "C:\\Users\\test\\.ssh\\id_rsa"},
            policy
        )

        self.assertEqual(result.action, "block")

    def test_credentials_file_in_excel_blocked(self):
        """credentials.json in Excel export should be blocked."""
        engine = PolicyEngine()
        validator = Validator()

        policy = engine.get_policy("mcp__excel-mcp__export_csv")
        result = validator.validate(
            "mcp__excel-mcp__export_csv",
            {"file_path": "D:\\backup\\credentials.json"},
            policy
        )

        self.assertEqual(result.action, "block")


if __name__ == '__main__':
    main(verbosity=2)
