#!/usr/bin/env python3
"""
Self-Healing Workflow System

Detects recurring failures and automatically adjusts approaches.
Learns from past corrections to prevent future errors.

Key Features:
1. Pattern detection in failures
2. Automatic retry with adjusted parameters
3. Fallback strategy selection
4. Learning from successful recoveries
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")
HEALING_LOG = Path("/mnt/d/_CLAUDE-TOOLS/self-healing/healing_log.json")


class WorkflowHealer:
    """Detects patterns and heals recurring issues."""

    def __init__(self):
        self.conn = None
        if MEMORY_DB.exists():
            self.conn = sqlite3.connect(str(MEMORY_DB))
            self.conn.row_factory = sqlite3.Row

        self.healing_strategies = self._load_strategies()

    def _load_strategies(self) -> Dict:
        """Load known healing strategies."""
        return {
            "wall_coordinate_error": {
                "pattern": ["coordinate", "DXF", "wall", "wrong location"],
                "strategies": [
                    {"action": "use_raw_coordinates", "description": "Use raw DXF coordinates without conversion"},
                    {"action": "expand_slowly", "description": "Start from known good area and expand"},
                    {"action": "verify_each", "description": "Verify each wall placement before continuing"},
                ],
                "success_rate": {}
            },
            "viewport_placement_error": {
                "pattern": ["viewport", "sheet", "bounds", "placement"],
                "strategies": [
                    {"action": "check_bounds_first", "description": "Verify drawable area before placement"},
                    {"action": "use_offset_origin", "description": "Calculate from sheet origin with offset"},
                    {"action": "single_placement", "description": "Place one viewport at a time"},
                ],
                "success_rate": {}
            },
            "element_copy_error": {
                "pattern": ["copy", "between documents", "transfer", "view"],
                "strategies": [
                    {"action": "manual_placement", "description": "Copy element, place manually"},
                    {"action": "recreate_instead", "description": "Recreate element instead of copying"},
                ],
                "success_rate": {}
            }
        }

    def detect_issue_pattern(self, error_message: str) -> Optional[str]:
        """Detect which known issue pattern matches the error."""
        error_lower = error_message.lower()

        for issue_type, config in self.healing_strategies.items():
            matches = sum(1 for kw in config["pattern"] if kw.lower() in error_lower)
            if matches >= 2:  # At least 2 keywords match
                return issue_type

        return None

    def get_healing_strategy(self, issue_type: str, attempt: int = 1) -> Optional[Dict]:
        """Get the best healing strategy for an issue type."""
        if issue_type not in self.healing_strategies:
            return None

        strategies = self.healing_strategies[issue_type]["strategies"]
        success_rates = self.healing_strategies[issue_type].get("success_rate", {})

        # Sort by success rate, then by order
        sorted_strategies = sorted(
            enumerate(strategies),
            key=lambda x: (success_rates.get(x[1]["action"], 0.5), -x[0]),
            reverse=True
        )

        # Return strategy for current attempt
        if attempt <= len(sorted_strategies):
            return sorted_strategies[attempt - 1][1]

        return None

    def record_outcome(self, issue_type: str, strategy: str, success: bool):
        """Record the outcome of a healing attempt."""
        if issue_type not in self.healing_strategies:
            return

        success_rates = self.healing_strategies[issue_type].setdefault("success_rate", {})

        # Update success rate with exponential moving average
        current_rate = success_rates.get(strategy, 0.5)
        new_rate = current_rate * 0.7 + (1.0 if success else 0.0) * 0.3
        success_rates[strategy] = new_rate

        # Log the outcome
        self._log_healing({
            "timestamp": datetime.now().isoformat(),
            "issue_type": issue_type,
            "strategy": strategy,
            "success": success,
            "new_rate": new_rate
        })

    def _log_healing(self, entry: Dict):
        """Append to healing log."""
        try:
            HEALING_LOG.parent.mkdir(parents=True, exist_ok=True)

            log = []
            if HEALING_LOG.exists():
                with open(HEALING_LOG) as f:
                    log = json.load(f)

            log.append(entry)

            # Keep last 1000 entries
            log = log[-1000:]

            with open(HEALING_LOG, 'w') as f:
                json.dump(log, f, indent=2)
        except:
            pass

    def analyze_failure_patterns(self, days: int = 30) -> Dict:
        """Analyze failure patterns from memory."""
        if not self.conn:
            return {}

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT content, project, created_at
            FROM memories
            WHERE memory_type = 'error'
            AND created_at > ?
            ORDER BY created_at DESC
        """, (cutoff,))

        results = [dict(row) for row in cursor.fetchall()]

        # Categorize by issue type
        categories = {}
        for result in results:
            issue_type = self.detect_issue_pattern(result.get("content", ""))
            if issue_type:
                if issue_type not in categories:
                    categories[issue_type] = []
                categories[issue_type].append(result)

        return {
            "total_errors": len(results),
            "categorized": {k: len(v) for k, v in categories.items()},
            "uncategorized": len(results) - sum(len(v) for v in categories.values())
        }

    def suggest_preventive_action(self, context: str) -> Optional[Dict]:
        """Suggest preventive action based on context."""
        issue_type = self.detect_issue_pattern(context)

        if issue_type:
            strategy = self.get_healing_strategy(issue_type, 1)
            if strategy:
                return {
                    "issue_type": issue_type,
                    "recommendation": strategy["description"],
                    "action": strategy["action"]
                }

        return None


def main():
    """CLI entry point."""
    import sys

    healer = WorkflowHealer()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--analyze":
            analysis = healer.analyze_failure_patterns()
            print(json.dumps(analysis, indent=2))

        elif sys.argv[1] == "--suggest":
            context = " ".join(sys.argv[2:])
            suggestion = healer.suggest_preventive_action(context)
            if suggestion:
                print(f"Issue: {suggestion['issue_type']}")
                print(f"Recommendation: {suggestion['recommendation']}")
            else:
                print("No specific recommendations for this context.")

        elif sys.argv[1] == "--heal":
            error = " ".join(sys.argv[2:])
            issue_type = healer.detect_issue_pattern(error)
            if issue_type:
                for attempt in range(1, 4):
                    strategy = healer.get_healing_strategy(issue_type, attempt)
                    if strategy:
                        print(f"Attempt {attempt}: {strategy['description']}")
            else:
                print("Unknown error pattern - no healing strategies available.")
    else:
        print("Usage:")
        print("  workflow_healer.py --analyze              # Analyze failure patterns")
        print("  workflow_healer.py --suggest <context>    # Get preventive suggestions")
        print("  workflow_healer.py --heal <error>         # Get healing strategies")


if __name__ == "__main__":
    main()
