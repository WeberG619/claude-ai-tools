#!/usr/bin/env python3
"""
Adaptive Retry CLI — View retry history and statistics.

Usage:
    retry_cli.py stats              Show retry statistics
    retry_cli.py history [--op X]   Show retry history
    retry_cli.py strategies         Show available strategies
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retry_engine import AdaptiveRetryLoop, _load_strategies


def main():
    parser = argparse.ArgumentParser(description="Adaptive Retry CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # stats
    sub.add_parser("stats", help="Show retry statistics")

    # history
    p_hist = sub.add_parser("history", help="Show retry history")
    p_hist.add_argument("--op", "--operation", default=None, help="Filter by operation")
    p_hist.add_argument("--limit", type=int, default=20)

    # strategies
    sub.add_parser("strategies", help="Show available strategies")

    args = parser.parse_args()

    if args.command == "stats":
        stats = AdaptiveRetryLoop.get_stats()
        if not stats:
            print("No retry data yet.")
            return
        print(f"Total attempts:  {stats['total_attempts']}")
        print(f"Successes:       {stats['total_successes']}")
        print(f"Success rate:    {stats['success_rate']}%")
        print("\nBy strategy:")
        for strategy, count in stats.get("by_strategy", {}).items():
            successes = stats.get("success_by_strategy", {}).get(strategy, 0)
            print(f"  {strategy:15s}  {count} attempts, {successes} successes")

    elif args.command == "history":
        history = AdaptiveRetryLoop.get_history(operation=args.op, limit=args.limit)
        if not history:
            print("No retry history.")
            return
        for h in history:
            status = "OK" if h['success'] else "FAIL"
            print(f"  [{status}] {h['timestamp'][:19]}  {h['strategy']:12s}  {h['operation'][:40]}  {h.get('error', '')[:60]}")

    elif args.command == "strategies":
        config = _load_strategies()
        print("Strategy Ladder:")
        cumulative = 0
        for i, s in enumerate(config["strategies"], 1):
            max_att = s.get("max_attempts", 1)
            cumulative += max_att
            print(f"  {i}. {s['name']:15s} ({max_att} attempt{'s' if max_att > 1 else ''})  — {s['description']}")
        print(f"\nMax total attempts: {config.get('max_total_attempts', 5)}")
        print(f"Hard timeout: {config.get('hard_timeout_minutes', 15)} minutes")


if __name__ == "__main__":
    main()
