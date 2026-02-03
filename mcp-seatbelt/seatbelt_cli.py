#!/usr/bin/env python3
"""
MCP Seatbelt CLI - View audit logs and statistics.

Usage:
    python seatbelt_cli.py stats         # Show statistics
    python seatbelt_cli.py recent [N]    # Show N most recent entries
    python seatbelt_cli.py blocked       # Show blocked calls
    python seatbelt_cli.py tools         # Show calls by tool
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from audit_logger import AuditLogger


def cmd_stats(args):
    """Show audit statistics."""
    logger = AuditLogger()
    stats = logger.get_stats()

    print("\n=== MCP Seatbelt Statistics ===\n")
    print(f"Total MCP Calls:  {stats['total_calls']}")
    print(f"Blocked:          {stats['blocked_count']}")
    print(f"Errors:           {stats['error_count']}")

    print("\n--- By Action ---")
    for action, count in sorted(stats['by_action'].items()):
        print(f"  {action}: {count}")

    print("\n--- By Risk Level ---")
    for level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
        count = stats['by_risk_level'].get(level, 0)
        bar = '█' * (count // 5) if count > 0 else ''
        print(f"  {level:8}: {count:4} {bar}")

    print("\n--- Top Tools ---")
    sorted_tools = sorted(stats['by_tool'].items(), key=lambda x: x[1], reverse=True)[:10]
    for tool, count in sorted_tools:
        print(f"  {tool}: {count}")


def cmd_recent(args):
    """Show recent audit entries."""
    logger = AuditLogger()
    limit = args.count or 10

    entries = logger.query(limit=limit)

    print(f"\n=== Last {len(entries)} MCP Calls ===\n")

    for entry in reversed(entries):  # Oldest first
        action_emoji = {
            'block': '🛑',
            'warn': '⚠️',
            'allow': '✅',
            'log_only': '📝',
            'error': '❌'
        }.get(entry.get('action', ''), '❓')

        tool = entry.get('tool', 'unknown')
        # Shorten tool name
        if tool.startswith('mcp__'):
            parts = tool.split('__')
            tool = f"{parts[1]}:{parts[2]}" if len(parts) > 2 else parts[1]

        risk = entry.get('risk_score', '?')
        timestamp = entry.get('timestamp', '')[:19]  # Trim microseconds

        print(f"{action_emoji} [{timestamp}] {tool} (risk:{risk})")
        if entry.get('reason'):
            print(f"   └─ {entry['reason']}")


def cmd_blocked(args):
    """Show blocked calls."""
    logger = AuditLogger()

    entries = logger.query(filters={'action': 'block'}, limit=50)

    print(f"\n=== Blocked Calls ({len(entries)} found) ===\n")

    for entry in reversed(entries):
        tool = entry.get('tool', 'unknown')
        reason = entry.get('reason', 'No reason')
        timestamp = entry.get('timestamp', '')[:19]
        policy = entry.get('policy_matched', 'unknown')

        print(f"🛑 {tool}")
        print(f"   Time:   {timestamp}")
        print(f"   Reason: {reason}")
        print(f"   Policy: {policy}")
        print()


def cmd_tools(args):
    """Show calls grouped by tool."""
    logger = AuditLogger()
    stats = logger.get_stats()

    print("\n=== MCP Tool Usage ===\n")

    sorted_tools = sorted(stats['by_tool'].items(), key=lambda x: x[1], reverse=True)

    for tool, count in sorted_tools:
        # Get blocked count for this tool
        blocked = len(logger.query(
            filters={'action': 'block'},
            limit=1000
        ))

        bar = '█' * (count // 2)
        print(f"{tool:40} {count:4} calls {bar}")


def main():
    parser = argparse.ArgumentParser(description='MCP Seatbelt CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Stats command
    subparsers.add_parser('stats', help='Show statistics')

    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recent entries')
    recent_parser.add_argument('count', type=int, nargs='?', default=10,
                               help='Number of entries to show')

    # Blocked command
    subparsers.add_parser('blocked', help='Show blocked calls')

    # Tools command
    subparsers.add_parser('tools', help='Show calls by tool')

    args = parser.parse_args()

    if args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'recent':
        cmd_recent(args)
    elif args.command == 'blocked':
        cmd_blocked(args)
    elif args.command == 'tools':
        cmd_tools(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
