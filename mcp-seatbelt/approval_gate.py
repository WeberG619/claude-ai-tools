#!/usr/bin/env python3
"""
Approval Gate - Handles blocking, warning, and approval logic.

In hook mode, interactive approval is not possible due to timeouts.
For now, require_approval falls back to block.

Future: GUI notification system for approval requests.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GateAction(Enum):
    """Possible actions from the approval gate."""
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"
    LOG_ONLY = "log_only"


@dataclass
class GateDecision:
    """Decision from the approval gate."""
    action: GateAction
    reason: str = ""
    user_approved: bool = False


class ApprovalGate:
    """
    Determines final action based on policy and validation results.

    In the current hook-based implementation:
    - block -> Block the call
    - require_approval -> Block (no interactive mode)
    - warn -> Log warning but allow
    - allow/log_only -> Allow the call
    """

    def __init__(self, interactive: bool = False):
        """
        Initialize the approval gate.

        Args:
            interactive: Whether interactive approval is possible.
                        False in hook mode (default).
        """
        self.interactive = interactive

    def decide(self, policy_action: str, require_approval: bool,
               risk_score: int, validation_passed: bool) -> GateDecision:
        """
        Make a gate decision based on policy and validation.

        Args:
            policy_action: Action from policy (block, allow, warn, log_only)
            require_approval: Whether policy requires user approval
            risk_score: Calculated risk score (1-10)
            validation_passed: Whether all validation rules passed

        Returns:
            GateDecision with action and reason
        """
        # Validation failures always block
        if not validation_passed:
            return GateDecision(
                action=GateAction.BLOCK,
                reason="Validation rules failed"
            )

        # Policy says block
        if policy_action == "block":
            return GateDecision(
                action=GateAction.BLOCK,
                reason="Blocked by policy"
            )

        # Requires approval but we can't prompt
        if require_approval and not self.interactive:
            return GateDecision(
                action=GateAction.BLOCK,
                reason="Requires approval (interactive mode not available)"
            )

        # Requires approval and we can prompt (future)
        if require_approval and self.interactive:
            approved = self._prompt_user(risk_score)
            if approved:
                return GateDecision(
                    action=GateAction.ALLOW,
                    reason="User approved",
                    user_approved=True
                )
            else:
                return GateDecision(
                    action=GateAction.BLOCK,
                    reason="User denied"
                )

        # Critical risk auto-blocks
        if risk_score >= 10:
            return GateDecision(
                action=GateAction.BLOCK,
                reason=f"Risk score {risk_score} exceeds maximum"
            )

        # Warn for high risk
        if policy_action == "warn" or risk_score >= 8:
            return GateDecision(
                action=GateAction.WARN,
                reason=f"High risk operation (score: {risk_score})"
            )

        # Default: allow with logging
        if policy_action == "log_only":
            return GateDecision(
                action=GateAction.LOG_ONLY,
                reason="Logged only"
            )

        return GateDecision(
            action=GateAction.ALLOW,
            reason="Allowed by policy"
        )

    def _prompt_user(self, risk_score: int) -> bool:
        """
        Prompt user for approval (future implementation).

        Currently always returns False since we can't prompt in hooks.

        Future: Could use:
        - GUI notification (toast/popup)
        - File-based approval (write to file, wait for response)
        - Webhook to approval service
        """
        # TODO: Implement when we have a notification system
        return False


def format_block_message(tool_name: str, risk_score: int,
                         reason: str, policy: str) -> str:
    """
    Format a user-friendly block message.

    Args:
        tool_name: The blocked tool
        risk_score: Calculated risk
        reason: Why it was blocked
        policy: Which policy matched

    Returns:
        Formatted message string
    """
    return f"""
{'='*60}
🛑 MCP SEATBELT: BLOCKED
{'='*60}
Tool:       {tool_name}
Risk Score: {risk_score}/10
Reason:     {reason}
Policy:     {policy}

To allow this operation, update the policy in:
/mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/policies/
{'='*60}
"""


def format_warning_message(tool_name: str, risk_score: int,
                           reason: str) -> str:
    """
    Format a warning message for high-risk operations.

    Args:
        tool_name: The tool being warned about
        risk_score: Calculated risk
        reason: Why it triggered warning

    Returns:
        Formatted warning string
    """
    return f"⚠️  MCP SEATBELT WARNING [{tool_name}]: {reason} (Risk: {risk_score}/10)"
