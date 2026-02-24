#!/usr/bin/env python3
"""
Audit Logger - Logs all MCP tool calls to NDJSON audit trail.

Writes to audit.ndjson with:
- Timestamps
- Tool names and (redacted) parameters
- Risk scores and actions taken
- Policy matches
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from policy_engine import Policy
from validator import ValidationResult


class AuditLogger:
    """Logs MCP tool calls to NDJSON audit file."""

    SCHEMA_VERSION = 1
    DEFAULT_AUDIT_PATH = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson")

    def __init__(self, audit_path: Optional[Path] = None):
        """
        Initialize the audit logger.

        Args:
            audit_path: Path to audit file. Defaults to system-bridge/audit.ndjson
        """
        self.audit_path = audit_path or self.DEFAULT_AUDIT_PATH
        self._ensure_audit_file()

    def _ensure_audit_file(self) -> None:
        """Ensure audit directory and file exist."""
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.audit_path.exists():
            self.audit_path.touch()

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format with timezone."""
        return datetime.now(timezone.utc).isoformat()

    def _get_user(self) -> str:
        """Get current user from environment or default."""
        return os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))

    def log(self, tool_name: str, result: ValidationResult,
            policy: Policy, tool_input: Dict[str, Any],
            session_id: str = "unknown",
            tier_result=None) -> None:
        """
        Log a tool call to the audit trail.

        Args:
            tool_name: The MCP tool that was called
            result: Validation result including action taken
            policy: The policy that was matched
            tool_input: Original parameters (will be redacted)
            session_id: Claude session ID if available
            tier_result: Optional TierResult from tier_classifier
        """
        entry = {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp": self._get_timestamp(),
            "session_id": session_id,
            "user": self._get_user(),
            "tool": tool_name,
            "action": result.action,
            "risk_score": result.risk_score,
            "tier": tier_result.tier if tier_result else None,
            "tier_label": tier_result.label if tier_result else None,
            "parameters": result.redacted_params,
            "policy_matched": result.policy_matched,
            "rules_checked": result.rules_checked,
            "rules_failed": result.rules_failed,
            "reason": result.message or None,
        }

        self._write_entry(entry)

    def log_fast(self, tool_name: str, tier_result, session_id: str = "unknown") -> None:
        """Fast-path logging for Tier 1 (read-only) operations.

        Args:
            tool_name: The MCP tool that was called
            tier_result: TierResult from tier_classifier
            session_id: Claude session ID
        """
        entry = {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp": self._get_timestamp(),
            "session_id": session_id,
            "user": self._get_user(),
            "tool": tool_name,
            "action": "fast_pass",
            "risk_score": 0,
            "tier": tier_result.tier,
            "tier_label": tier_result.label,
            "parameters": {},
            "policy_matched": None,
            "rules_checked": [],
            "rules_failed": [],
            "reason": tier_result.reason,
        }

        self._write_entry(entry)

    def log_error(self, tool_name: str, error: str,
                  session_id: str = "unknown") -> None:
        """
        Log an internal seatbelt error.

        Args:
            tool_name: The tool being processed when error occurred
            error: Error message
            session_id: Claude session ID if available
        """
        entry = {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp": self._get_timestamp(),
            "session_id": session_id,
            "user": self._get_user(),
            "tool": tool_name,
            "action": "error",
            "risk_score": None,
            "parameters": {},
            "policy_matched": None,
            "rules_checked": [],
            "rules_failed": [],
            "reason": f"Seatbelt error: {error}",
        }

        self._write_entry(entry)

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write a single entry to the audit file."""
        try:
            with open(self.audit_path, 'a') as f:
                f.write(json.dumps(entry, default=str) + '\n')
        except Exception as e:
            # Don't crash if we can't log
            print(f"Warning: Failed to write audit log: {e}", file=sys.stderr)

    def query(self, filters: Optional[Dict[str, Any]] = None,
              limit: int = 100) -> list:
        """
        Query the audit log with optional filters.

        Args:
            filters: Dict of field -> value to filter by
            limit: Maximum entries to return

        Returns:
            List of matching audit entries (newest first)
        """
        filters = filters or {}
        results = []

        try:
            with open(self.audit_path, 'r') as f:
                lines = f.readlines()

            # Process newest first
            for line in reversed(lines):
                if len(results) >= limit:
                    break

                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # Check filters
                match = True
                for key, value in filters.items():
                    if key not in entry:
                        match = False
                        break
                    if entry[key] != value:
                        match = False
                        break

                if match:
                    results.append(entry)

        except FileNotFoundError:
            pass

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics from the audit log.

        Returns:
            Dict with counts by action, tool, risk level, etc.
        """
        stats = {
            'total_calls': 0,
            'by_action': {},
            'by_tool': {},
            'by_risk_level': {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0},
            'blocked_count': 0,
            'error_count': 0,
        }

        try:
            with open(self.audit_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    stats['total_calls'] += 1

                    action = entry.get('action', 'unknown')
                    stats['by_action'][action] = stats['by_action'].get(action, 0) + 1

                    if action == 'block':
                        stats['blocked_count'] += 1
                    elif action == 'error':
                        stats['error_count'] += 1

                    tool = entry.get('tool', 'unknown')
                    # Truncate tool name for grouping
                    tool_prefix = '__'.join(tool.split('__')[:2]) if '__' in tool else tool
                    stats['by_tool'][tool_prefix] = stats['by_tool'].get(tool_prefix, 0) + 1

                    risk = entry.get('risk_score')
                    if risk:
                        if risk >= 9:
                            stats['by_risk_level']['CRITICAL'] += 1
                        elif risk >= 7:
                            stats['by_risk_level']['HIGH'] += 1
                        elif risk >= 4:
                            stats['by_risk_level']['MEDIUM'] += 1
                        else:
                            stats['by_risk_level']['LOW'] += 1

        except FileNotFoundError:
            pass

        return stats
