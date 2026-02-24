#!/usr/bin/env python3
"""
MCP Seatbelt - Security Layer for Claude Code MCP Tools

Exit codes:
  0 = Allow the tool call
  2 = Block the tool call (Claude sees rejection message)

Input: Claude Code passes JSON via stdin with:
  - tool_name: The tool being called (e.g., mcp__whatsapp__send_message)
  - tool_input: Object with tool parameters
  - session_id: Current session ID
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

try:
    from tier_classifier import TierClassifier
    _tier_available = True
except ImportError:
    _tier_available = False

# Fail-open: If seatbelt has internal errors, allow the call rather than break Claude
FAIL_OPEN = True

# Minimum tool prefix to validate
MCP_PREFIX = "mcp__"

DEBUG_LOG = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/seatbelt_debug.log")


def main():
    """Main entry point for the seatbelt hook."""
    # Read JSON from stdin (Claude Code passes tool info this way)
    try:
        stdin_data = sys.stdin.read()
        hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
    except json.JSONDecodeError:
        hook_input = {}

    # Extract tool info from stdin JSON
    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    session_id = hook_input.get('session_id', 'unknown')

    # Debug: Log every invocation
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{tool_name} | {json.dumps(tool_input)[:100]}\n")

    # Only process MCP tools
    if not tool_name.startswith(MCP_PREFIX):
        sys.exit(0)

    try:
        # Initialize components
        policy_engine = PolicyEngine()
        validator = Validator()
        risk_scorer = RiskScorer()
        audit = AuditLogger()

        # ── Tier classification (fast-pass for read-only) ──
        tier_result = None
        if _tier_available:
            try:
                # Load tier overrides from policy YAML if available
                policy_overrides = {}
                tier_classifier = TierClassifier(policy_overrides)
                tier_result = tier_classifier.classify(tool_name)

                # Tier 1 (FREE): Skip full pipeline for read-only ops
                if tier_result.tier == 1:
                    audit.log_fast(tool_name, tier_result, session_id)
                    sys.exit(0)
            except Exception:
                pass  # Tier classifier errors never block

        # Get applicable policy for this tool
        policy = policy_engine.get_policy(tool_name)

        # Validate the call against policy rules
        result = validator.validate(tool_name, tool_input, policy)

        # Calculate final risk score
        risk_score = risk_scorer.calculate(tool_name, tool_input, policy, result)
        result.risk_score = risk_score

        # ── Tier 3 escalation: destructive ops get warn even if log_only ──
        if tier_result and tier_result.tier == 3 and result.action == 'log_only':
            result.action = 'warn'
            result.message = (result.message or "") + f" [Tier 3 escalation: {tier_result.reason}]"

        # Log to audit trail (with tier info)
        audit.log(
            tool_name=tool_name,
            result=result,
            policy=policy,
            tool_input=tool_input,
            session_id=session_id,
            tier_result=tier_result,
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
