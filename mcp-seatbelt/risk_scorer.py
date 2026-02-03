#!/usr/bin/env python3
"""
Risk Scorer - Calculates risk scores for MCP tool calls.

Risk is scored 1-10:
  1-3:  Low risk (read operations, internal tools)
  4-6:  Medium risk (write operations, local changes)
  7-8:  High risk (external communication, system changes)
  9-10: Critical risk (mass operations, irreversible actions)
"""

import re
from typing import Any, Dict, Optional

from policy_engine import Policy
from validator import ValidationResult


class RiskScorer:
    """Calculates risk scores for tool calls."""

    # Risk multipliers for different characteristics
    RISK_MODIFIERS = {
        # External communication adds risk
        'external_comm': 3,
        # File system writes add risk
        'fs_write': 2,
        # Sensitive paths add risk
        'sensitive_path': 2,
        # Unknown/new recipient adds risk
        'new_recipient': 2,
        # Bulk operations add risk
        'bulk_operation': 2,
        # Irreversible actions add risk
        'irreversible': 3,
    }

    # Tools that communicate externally
    EXTERNAL_COMM_PATTERNS = [
        r'mcp__whatsapp__',
        r'mcp__email',
        r'mcp__.*send',
        r'mcp__.*post',
        r'mcp__.*upload',
    ]

    # Tools that write to filesystem
    FS_WRITE_PATTERNS = [
        r'mcp__.*write',
        r'mcp__.*create',
        r'mcp__.*delete',
        r'mcp__.*save',
        r'mcp__excel.*',  # Excel modifications
        r'mcp__revit.*place',
        r'mcp__revit.*create',
    ]

    # Sensitive paths that increase risk
    SENSITIVE_PATHS = [
        '/etc/', '/var/', '/usr/', '/boot/',
        'C:\\Windows', 'C:\\Program Files',
        '.ssh', '.aws', '.config', '.env',
        'credentials', 'secrets', 'tokens',
    ]

    # Patterns indicating bulk/mass operations
    BULK_PATTERNS = [
        r'all', r'batch', r'bulk', r'mass', r'every',
        r'\*',  # Wildcards
    ]

    # Irreversible action patterns
    IRREVERSIBLE_PATTERNS = [
        r'delete', r'remove', r'drop', r'truncate',
        r'--force', r'--hard', r'-rf',
        r'push', r'publish', r'deploy',
    ]

    def calculate(self, tool_name: str, tool_input: Dict[str, Any],
                  policy: Policy, validation_result: ValidationResult) -> int:
        """
        Calculate final risk score for a tool call.

        Args:
            tool_name: The MCP tool name
            tool_input: Parameters passed to the tool
            policy: The matched policy
            validation_result: Result from validator

        Returns:
            Risk score from 1-10
        """
        # Start with base risk from policy
        score = policy.risk

        # Apply modifiers
        input_str = str(tool_input).lower()
        tool_lower = tool_name.lower()

        # External communication
        if any(re.search(p, tool_lower) for p in self.EXTERNAL_COMM_PATTERNS):
            score += self.RISK_MODIFIERS['external_comm']

        # File system writes
        if any(re.search(p, tool_lower) for p in self.FS_WRITE_PATTERNS):
            score += self.RISK_MODIFIERS['fs_write']

        # Sensitive paths
        if any(path.lower() in input_str for path in self.SENSITIVE_PATHS):
            score += self.RISK_MODIFIERS['sensitive_path']

        # Bulk operations
        if any(re.search(p, input_str) for p in self.BULK_PATTERNS):
            score += self.RISK_MODIFIERS['bulk_operation']

        # Irreversible actions
        if any(re.search(p, input_str) for p in self.IRREVERSIBLE_PATTERNS):
            score += self.RISK_MODIFIERS['irreversible']

        # Validation failures increase risk
        score += len(validation_result.rules_failed)

        # Clamp to 1-10 range
        return max(1, min(10, score))

    def get_risk_level(self, score: int) -> str:
        """Convert numeric score to risk level string."""
        if score >= 9:
            return "CRITICAL"
        elif score >= 7:
            return "HIGH"
        elif score >= 4:
            return "MEDIUM"
        else:
            return "LOW"

    def explain_score(self, tool_name: str, tool_input: Dict[str, Any],
                      policy: Policy) -> Dict[str, Any]:
        """
        Explain how a risk score was calculated.

        Returns:
            Dict with base score, modifiers applied, and final score
        """
        explanation = {
            'base_score': policy.risk,
            'modifiers': [],
            'final_score': policy.risk
        }

        input_str = str(tool_input).lower()
        tool_lower = tool_name.lower()
        score = policy.risk

        if any(re.search(p, tool_lower) for p in self.EXTERNAL_COMM_PATTERNS):
            explanation['modifiers'].append(
                ('external_comm', self.RISK_MODIFIERS['external_comm'])
            )
            score += self.RISK_MODIFIERS['external_comm']

        if any(re.search(p, tool_lower) for p in self.FS_WRITE_PATTERNS):
            explanation['modifiers'].append(
                ('fs_write', self.RISK_MODIFIERS['fs_write'])
            )
            score += self.RISK_MODIFIERS['fs_write']

        if any(path.lower() in input_str for path in self.SENSITIVE_PATHS):
            explanation['modifiers'].append(
                ('sensitive_path', self.RISK_MODIFIERS['sensitive_path'])
            )
            score += self.RISK_MODIFIERS['sensitive_path']

        if any(re.search(p, input_str) for p in self.BULK_PATTERNS):
            explanation['modifiers'].append(
                ('bulk_operation', self.RISK_MODIFIERS['bulk_operation'])
            )
            score += self.RISK_MODIFIERS['bulk_operation']

        if any(re.search(p, input_str) for p in self.IRREVERSIBLE_PATTERNS):
            explanation['modifiers'].append(
                ('irreversible', self.RISK_MODIFIERS['irreversible'])
            )
            score += self.RISK_MODIFIERS['irreversible']

        explanation['final_score'] = max(1, min(10, score))
        explanation['level'] = self.get_risk_level(explanation['final_score'])

        return explanation
