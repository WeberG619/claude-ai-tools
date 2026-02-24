#!/usr/bin/env python3
"""
Tier Classifier — Classifies MCP tool calls into reversibility tiers.

Tier 1 (FREE):    Read-only ops — fast-pass, skip full pipeline
Tier 2 (CONFIRM): Create/modify — default, normal pipeline
Tier 3 (BLOCK):   Destructive — escalate from log_only to warn

Usage:
    from tier_classifier import TierClassifier
    c = TierClassifier()
    result = c.classify("mcp__excel-mcp__read_cell")
    # TierResult(tier=1, label='FREE', reason='Pattern: read_*')
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TierResult:
    tier: int           # 1, 2, or 3
    label: str          # FREE, CONFIRM, BLOCK
    reason: str         # Why this classification
    override: bool = False  # True if policy YAML overrode pattern

    def __repr__(self):
        return f"TierResult(tier={self.tier}, label='{self.label}', reason='{self.reason}')"


# Tier 1: Read-only patterns (prefixes and suffixes of the tool method name)
TIER1_PREFIXES = (
    "get_", "list_", "read_", "search_", "describe_", "find_",
    "check_", "query_", "fetch_", "browse_", "lookup_", "show_",
    "view_", "count_", "inspect_", "analyze_", "detect_",
    "recall_", "status", "info", "stats", "memory_search",
    "memory_recall", "memory_smart", "memory_check",
)

# Full tool names that are always Tier 1
TIER1_TOOLS = {
    "mcp__voice__speak", "mcp__voice__speak_summary",
    "mcp__voice__list_voices", "mcp__voice__stop_speaking",
    "mcp__visual-memory__memory_status", "mcp__visual-memory__memory_stats",
    "mcp__visual-memory__memory_search", "mcp__visual-memory__memory_view",
    "mcp__visual-memory__memory_recall_recent",
    "mcp__visual-memory__memory_recall_app",
    "mcp__visual-memory__memory_recall_time",
    "mcp__bluebeam__get_status", "mcp__bluebeam__get_window_info",
    "mcp__bluebeam__take_screenshot", "mcp__bluebeam__get_pdf_info",
    "mcp__bluebeam__go_to_page",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_tabs",
    "mcp__windows-browser__browser_screenshot",
    "mcp__windows-browser__get_monitors",
    "mcp__cdp-browser__cdp_status", "mcp__cdp-browser__cdp_list_tabs",
    "mcp__cdp-browser__cdp_get_text", "mcp__cdp-browser__cdp_get_html",
    "mcp__cdp-browser__cdp_screenshot",
    "mcp__excel-mcp__get_excel_status",
    "mcp__excel-mcp__list_open_workbooks",
    "mcp__excel-mcp__get_active_workbook_info",
    "mcp__excel-mcp__get_active_sheet_info",
    "mcp__excel-mcp__get_workbook_info",
    "mcp__excel-mcp__list_worksheets",
    "mcp__excel-mcp__read_cell", "mcp__excel-mcp__read_range",
    "mcp__excel-mcp__get_used_range", "mcp__excel-mcp__get_formula",
    "mcp__excel-mcp__find_value", "mcp__excel-mcp__list_named_ranges",
    "mcp__excel-mcp__get_named_range_value",
    "mcp__excel-mcp__list_charts", "mcp__excel-mcp__list_tables",
    "mcp__excel-mcp__list_pivot_tables",
    "mcp__excel-mcp__get_selection", "mcp__excel-mcp__read_comment",
    "mcp__excel-mcp__list_comments", "mcp__excel-mcp__get_filter_info",
    "mcp__excel-mcp__get_print_settings",
    "mcp__excel-mcp__list_conditional_formats_tool",
    "mcp__excel-mcp__list_shapes", "mcp__excel-mcp__list_macros_tool",
    "mcp__excel-mcp__get_vba_code_tool",
    "mcp__excel-mcp__list_formula_cells",
    "mcp__excel-mcp__read_clipboard",
    "mcp__excel-mcp__evaluate_formula",
}

# Tier 1: Full MCP server prefixes (all tools from these servers are read-only)
TIER1_SERVERS = {
    "mcp__youtube-mcp__",
    "mcp__financial-mcp__get_",
    "mcp__financial-mcp__search_",
    "mcp__financial-mcp__find_",
    "mcp__financial-mcp__compare_",
    "mcp__financial-mcp__check_",
    "mcp__floor-plan-vision__",
}

# Tier 3: Destructive patterns
TIER3_PREFIXES = (
    "delete", "remove", "drop", "wipe", "reset",
    "destroy", "purge", "truncate",
)

# Full tool names that are always Tier 3
TIER3_TOOLS = {
    "mcp__excel-mcp__run_macro_tool",
    "mcp__github__push_files",
    "mcp__github__merge_pull_request",
    "mcp__github__delete_file",
    "mcp__sqlite-server__write_query",  # Could be DROP/DELETE
    "mcp__visual-memory__memory_wipe_last",
    "mcp__visual-memory__memory_wipe_app",
    "mcp__visual-memory__memory_wipe_range",
    "mcp__financial-mcp__reset_paper_portfolio",
}


class TierClassifier:
    """Classifies MCP tool calls into reversibility tiers."""

    def __init__(self, policy_overrides: Optional[dict] = None):
        """
        Args:
            policy_overrides: Dict of {tool_name: tier_int} from policy YAML.
        """
        self.overrides = policy_overrides or {}

    def classify(self, tool_name: str) -> TierResult:
        """Classify a tool call into a tier.

        Args:
            tool_name: Full MCP tool name (e.g. mcp__excel-mcp__read_cell)

        Returns:
            TierResult with tier, label, and reason.
        """
        # Policy override takes precedence
        if tool_name in self.overrides:
            tier = self.overrides[tool_name]
            return TierResult(
                tier=tier,
                label=_tier_label(tier),
                reason=f"Policy override",
                override=True,
            )

        # Extract the method name (last segment after __)
        parts = tool_name.split("__")
        method = parts[-1] if len(parts) >= 3 else tool_name

        # Check Tier 1: exact tool match
        if tool_name in TIER1_TOOLS:
            return TierResult(1, "FREE", f"Known read-only tool")

        # Check Tier 1: server prefix match
        for prefix in TIER1_SERVERS:
            if tool_name.startswith(prefix):
                return TierResult(1, "FREE", f"Read-only server: {prefix.rstrip('_')}")

        # Check Tier 1: method prefix match
        for prefix in TIER1_PREFIXES:
            if method.startswith(prefix) or method == prefix:
                return TierResult(1, "FREE", f"Pattern: {prefix}*")

        # Check Tier 3: exact tool match
        if tool_name in TIER3_TOOLS:
            return TierResult(3, "BLOCK", f"Known destructive tool")

        # Check Tier 3: method prefix match
        for prefix in TIER3_PREFIXES:
            if method.startswith(prefix):
                return TierResult(3, "BLOCK", f"Pattern: {prefix}*")

        # Default: Tier 2
        return TierResult(2, "CONFIRM", "Default — create/modify operation")


def _tier_label(tier: int) -> str:
    return {1: "FREE", 2: "CONFIRM", 3: "BLOCK"}.get(tier, "UNKNOWN")


def main():
    """CLI for testing classifications."""
    import sys

    classifier = TierClassifier()

    if len(sys.argv) > 1:
        for tool in sys.argv[1:]:
            result = classifier.classify(tool)
            print(f"{tool} -> Tier {result.tier} ({result.label}): {result.reason}")
    else:
        # Demo
        demos = [
            "mcp__excel-mcp__read_cell",
            "mcp__excel-mcp__write_cell",
            "mcp__github__delete_file",
            "mcp__voice__speak",
            "mcp__youtube-mcp__get_video_info",
            "mcp__bluebeam__open_document",
            "mcp__excel-mcp__run_macro_tool",
            "mcp__github__push_files",
            "mcp__financial-mcp__get_stock_quote",
            "mcp__sqlite-server__read_query",
            "mcp__visual-memory__memory_wipe_last",
            "mcp__claude-memory__memory_store",
        ]
        for tool in demos:
            result = classifier.classify(tool)
            print(f"  Tier {result.tier} ({result.label:7s}) {tool:50s} — {result.reason}")


if __name__ == "__main__":
    main()
