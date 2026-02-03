#!/usr/bin/env python3
"""
MCP Seatbelt - Security Layer for Claude Code MCP Tools

Exit codes:
  0 = Allow the tool call
  2 = Block the tool call (Claude sees rejection message)

Environment variables (set by Claude Code):
  CLAUDE_TOOL_NAME  - The tool being called (e.g., mcp__whatsapp__send_message)
  CLAUDE_TOOL_INPUT - JSON string of parameters
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from policy_engine import PolicyEngine
from validator import Validator, ValidationResult
from risk_scorer import RiskScorer
from audit_logger import AuditLogger

# Fail-open: If seatbelt has internal errors, allow the call rather than break Claude
FAIL_OPEN = True

# Minimum tool prefix to validate
MCP_PREFIX = "mcp__"


def main():
    """Main entry point for the seatbelt hook."""
    tool_name = os.environ.get('CLAUDE_TOOL_NAME', '')
    tool_input_raw = os.environ.get('CLAUDE_TOOL_INPUT', '{}')
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')

    # Only process MCP tools
    if not tool_name.startswith(MCP_PREFIX):
        sys.exit(0)

    # Parse tool input
    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        tool_input = {"_raw": tool_input_raw}

    try:
        # Initialize components
        policy_engine = PolicyEngine()
        validator = Validator()
        risk_scorer = RiskScorer()
        audit = AuditLogger()

        # Get applicable policy for this tool
        policy = policy_engine.get_policy(tool_name)

        # Validate the call against policy rules
        result = validator.validate(tool_name, tool_input, policy)

        # Calculate final risk score
        risk_score = risk_scorer.calculate(tool_name, tool_input, policy, result)
        result.risk_score = risk_score

        # Log to audit trail
        audit.log(
            tool_name=tool_name,
            result=result,
            policy=policy,
            tool_input=tool_input,
            session_id=session_id
        )

        # Determine action based on result
        if result.action == 'block':
            # Print rejection message to stderr so Claude sees it
            print(f"\n{'='*60}", file=sys.stderr)
            print("🛑 MCP SEATBELT: BLOCKED", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(f"Tool: {tool_name}", file=sys.stderr)
            print(f"Risk Score: {risk_score}/10", file=sys.stderr)
            print(f"Reason: {result.message}", file=sys.stderr)
            if result.policy_matched:
                print(f"Policy: {result.policy_matched}", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)
            sys.exit(2)

        elif result.action == 'warn':
            # Log warning but allow
            print(f"\n⚠️  MCP SEATBELT WARNING: {result.message}", file=sys.stderr)
            sys.exit(0)

        else:  # 'allow' or 'log_only'
            sys.exit(0)

    except Exception as e:
        # Log the error
        try:
            audit = AuditLogger()
            audit.log_error(tool_name, str(e))
        except:
            pass

        if FAIL_OPEN:
            # Allow the call rather than break Claude Code
            print(f"⚠️  MCP Seatbelt error (fail-open): {e}", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"🛑 MCP Seatbelt error: {e}", file=sys.stderr)
            sys.exit(2)


if __name__ == '__main__':
    main()
