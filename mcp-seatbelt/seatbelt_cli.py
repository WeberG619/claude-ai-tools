#!/usr/bin/env python3
"""
MCP Seatbelt CLI - Complete management interface.

Usage:
    seatbelt stats                    # Show statistics
    seatbelt recent [N]               # Show N most recent entries
    seatbelt blocked                  # Show blocked calls
    seatbelt report                   # Generate weekly review report

    seatbelt whitelist                # Show current whitelist
    seatbelt whitelist add <contact>  # Add contact to whitelist
    seatbelt whitelist remove <contact>  # Remove from whitelist

    seatbelt policy <tool>            # Show policy for a tool
    seatbelt upgrade <tool>           # Increase restriction (log→warn→block)
    seatbelt downgrade <tool>         # Decrease restriction (block→warn→log)
"""

import argparse
import io
import json
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from audit_logger import AuditLogger
from policy_engine import PolicyEngine

POLICIES_DIR = Path(__file__).parent / "policies"
WEBER_YAML = POLICIES_DIR / "weber.yaml"


def load_weber_config():
    """Load weber.yaml configuration."""
    if WEBER_YAML.exists():
        with open(WEBER_YAML) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_weber_config(config):
    """Save weber.yaml configuration."""
    with open(WEBER_YAML, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def cmd_stats(args):
    """Show audit statistics."""
    logger = AuditLogger()
    stats = logger.get_stats()

    print("\n╔══════════════════════════════════════════╗")
    print("║       MCP SEATBELT STATISTICS            ║")
    print("╚══════════════════════════════════════════╝\n")

    print(f"  Total MCP Calls:  {stats['total_calls']}")
    print(f"  Blocked:          {stats['blocked_count']} ({_pct(stats['blocked_count'], stats['total_calls'])})")
    print(f"  Warnings:         {stats['by_action'].get('warn', 0)}")
    print(f"  Errors:           {stats['error_count']}")

    print("\n  ─── Actions ───")
    action_order = ['block', 'warn', 'log_only', 'allow', 'error']
    for action in action_order:
        count = stats['by_action'].get(action, 0)
        if count > 0:
            emoji = {'block': '🛑', 'warn': '⚠️', 'log_only': '📝', 'allow': '✅', 'error': '❌'}.get(action, '')
            bar = '█' * min(count, 30)
            print(f"  {emoji} {action:10}: {count:4} {bar}")

    print("\n  ─── Risk Distribution ───")
    for level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
        count = stats['by_risk_level'].get(level, 0)
        if count > 0:
            color = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🟠', 'CRITICAL': '🔴'}.get(level, '')
            bar = '█' * min(count, 20)
            print(f"  {color} {level:8}: {count:4} {bar}")

    print("\n  ─── Top 10 Tools ───")
    sorted_tools = sorted(stats['by_tool'].items(), key=lambda x: x[1], reverse=True)[:10]
    for tool, count in sorted_tools:
        short = _short_tool(tool)
        print(f"  {short:35} {count:4}")

    print()


def cmd_recent(args):
    """Show recent audit entries."""
    logger = AuditLogger()
    limit = args.count or 15

    entries = logger.query(limit=limit)

    print(f"\n═══ Last {len(entries)} MCP Calls ═══\n")

    for entry in reversed(entries):
        action = entry.get('action', '')
        emoji = {'block': '🛑', 'warn': '⚠️', 'allow': '✅', 'log_only': '📝', 'error': '❌'}.get(action, '❓')

        tool = _short_tool(entry.get('tool', 'unknown'))
        risk = entry.get('risk_score', '?')
        timestamp = entry.get('timestamp', '')[:19].replace('T', ' ')

        print(f"{emoji} {timestamp} │ {tool:30} │ risk:{risk}")
        if entry.get('reason'):
            print(f"   └─ {entry['reason']}")


def cmd_blocked(args):
    """Show blocked calls."""
    logger = AuditLogger()
    entries = logger.query(filters={'action': 'block'}, limit=50)

    print(f"\n═══ Blocked Calls ({len(entries)}) ═══\n")

    for entry in reversed(entries):
        tool = entry.get('tool', 'unknown')
        reason = entry.get('reason', 'No reason')
        timestamp = entry.get('timestamp', '')[:19].replace('T', ' ')
        risk = entry.get('risk_score', '?')

        print(f"🛑 {_short_tool(tool)}")
        print(f"   Time:   {timestamp}")
        print(f"   Risk:   {risk}/10")
        print(f"   Reason: {reason}")
        print()


def cmd_report(args):
    """Generate a review report."""
    logger = AuditLogger()
    stats = logger.get_stats()

    # Get recent entries
    all_entries = logger.query(limit=1000)

    # Filter to last 7 days
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    recent = [e for e in all_entries if _parse_ts(e.get('timestamp', '')) > week_ago]

    blocked = [e for e in recent if e.get('action') == 'block']
    warnings = [e for e in recent if e.get('action') == 'warn']

    print("\n" + "═" * 60)
    print("       MCP SEATBELT - WEEKLY REVIEW REPORT")
    print("═" * 60)
    print(f"\nReport Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Period: Last 7 days")
    print(f"\n{'─' * 60}")

    print(f"\n📊 SUMMARY")
    print(f"   Total calls this week:  {len(recent)}")
    print(f"   Blocked:                {len(blocked)}")
    print(f"   Warnings:               {len(warnings)}")
    print(f"   Block rate:             {_pct(len(blocked), len(recent))}")

    print(f"\n🛑 BLOCKED OPERATIONS ({len(blocked)})")
    if blocked:
        # Group by tool
        by_tool = {}
        for e in blocked:
            tool = e.get('tool', 'unknown')
            by_tool[tool] = by_tool.get(tool, 0) + 1

        for tool, count in sorted(by_tool.items(), key=lambda x: -x[1]):
            print(f"   {count:3}x  {_short_tool(tool)}")
            # Show sample reason
            sample = next((e for e in blocked if e.get('tool') == tool), None)
            if sample and sample.get('reason'):
                print(f"         └─ {sample['reason'][:60]}")
    else:
        print("   None! ✅")

    print(f"\n📈 RECOMMENDATIONS")

    # Find tools with high log_only counts that might need upgrading
    log_only = [e for e in recent if e.get('action') == 'log_only']
    log_by_tool = {}
    for e in log_only:
        tool = e.get('tool', 'unknown')
        log_by_tool[tool] = log_by_tool.get(tool, 0) + 1

    high_volume = [(t, c) for t, c in log_by_tool.items() if c >= 10]
    if high_volume:
        print("   Tools with high activity (consider reviewing):")
        for tool, count in sorted(high_volume, key=lambda x: -x[1])[:5]:
            print(f"   → {_short_tool(tool)} ({count} calls)")
    else:
        print("   No high-volume tools requiring review.")

    print(f"\n{'─' * 60}")
    print("Run 'seatbelt upgrade <tool>' to increase restrictions")
    print("Run 'seatbelt whitelist add <contact>' to add trusted contacts")
    print("═" * 60 + "\n")


def cmd_whitelist(args):
    """Manage whitelist."""
    config = load_weber_config()
    whitelist = config.get('contacts_whitelist', [])

    if args.action == 'list' or args.action is None:
        print("\n═══ Contacts Whitelist ═══\n")
        if whitelist:
            for i, contact in enumerate(whitelist, 1):
                print(f"  {i:2}. {contact}")
        else:
            print("  (empty)")
        print(f"\n  Total: {len(whitelist)} contacts")
        print("  Add: seatbelt whitelist add <contact>")
        print()

    elif args.action == 'add':
        if not args.contact:
            print("Error: Specify contact to add")
            return
        contact = args.contact
        if contact not in whitelist:
            whitelist.append(contact)
            config['contacts_whitelist'] = whitelist
            save_weber_config(config)
            print(f"✅ Added '{contact}' to whitelist")
        else:
            print(f"ℹ️  '{contact}' already in whitelist")

    elif args.action == 'remove':
        if not args.contact:
            print("Error: Specify contact to remove")
            return
        contact = args.contact
        if contact in whitelist:
            whitelist.remove(contact)
            config['contacts_whitelist'] = whitelist
            save_weber_config(config)
            print(f"✅ Removed '{contact}' from whitelist")
        else:
            print(f"ℹ️  '{contact}' not in whitelist")


def cmd_policy(args):
    """Show policy for a tool."""
    engine = PolicyEngine()
    tool = args.tool

    # If partial name, try to match
    if not tool.startswith('mcp__'):
        tool = f"mcp__{tool}"

    policy = engine.get_policy(tool)

    print(f"\n═══ Policy: {tool} ═══\n")
    print(f"  Pattern:     {policy.pattern}")
    print(f"  Action:      {policy.action}")
    print(f"  Risk:        {policy.risk}/10")
    print(f"  Description: {policy.description or 'N/A'}")

    if policy.rules:
        print(f"\n  Rules:")
        for rule in policy.rules:
            print(f"    • {rule.type}: {rule.config}")
    print()


def cmd_upgrade(args):
    """Upgrade tool restriction level."""
    tool = args.tool
    if not tool.startswith('mcp__'):
        tool = f"mcp__{tool}"

    config = load_weber_config()
    tools = config.setdefault('tools', {})

    # Get current policy
    engine = PolicyEngine()
    current = engine.get_policy(tool)

    # Determine new action
    upgrade_path = {'allow': 'log_only', 'log_only': 'warn', 'warn': 'block'}
    new_action = upgrade_path.get(current.action, 'block')

    if current.action == 'block':
        print(f"ℹ️  {tool} is already at maximum restriction (block)")
        return

    # Update weber.yaml
    if tool not in tools:
        tools[tool] = {'risk': current.risk, 'action': new_action}
    else:
        tools[tool]['action'] = new_action

    save_weber_config(config)
    print(f"✅ Upgraded {_short_tool(tool)}: {current.action} → {new_action}")


def cmd_downgrade(args):
    """Downgrade tool restriction level."""
    tool = args.tool
    if not tool.startswith('mcp__'):
        tool = f"mcp__{tool}"

    config = load_weber_config()
    tools = config.setdefault('tools', {})

    # Get current policy
    engine = PolicyEngine()
    current = engine.get_policy(tool)

    # Determine new action
    downgrade_path = {'block': 'warn', 'warn': 'log_only', 'log_only': 'allow'}
    new_action = downgrade_path.get(current.action, 'allow')

    if current.action in ['allow', 'log_only']:
        print(f"ℹ️  {tool} is already at minimum restriction ({current.action})")
        return

    # Update weber.yaml
    if tool not in tools:
        tools[tool] = {'risk': current.risk, 'action': new_action}
    else:
        tools[tool]['action'] = new_action

    save_weber_config(config)
    print(f"✅ Downgraded {_short_tool(tool)}: {current.action} → {new_action}")


# === Helpers ===

def _short_tool(tool):
    """Shorten tool name for display."""
    if tool and tool.startswith('mcp__'):
        parts = tool.split('__')
        if len(parts) >= 3:
            return f"{parts[1]}:{parts[2]}"
        return parts[1] if len(parts) > 1 else tool
    return tool or 'unknown'


def _pct(num, total):
    """Calculate percentage string."""
    if total == 0:
        return "0%"
    return f"{(num / total) * 100:.1f}%"


def _parse_ts(ts_str):
    """Parse timestamp string to datetime."""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00').split('+')[0])
    except:
        return datetime.min


def main():
    parser = argparse.ArgumentParser(
        description='MCP Seatbelt Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  seatbelt stats                    Show statistics
  seatbelt recent 20                Show last 20 calls
  seatbelt blocked                  Show blocked calls
  seatbelt report                   Weekly review report

  seatbelt whitelist                Show whitelist
  seatbelt whitelist add bruce@x.com   Add contact
  seatbelt whitelist remove test@x.com Remove contact

  seatbelt policy excel-mcp         Show policy for Excel tools
  seatbelt upgrade sqlite-server    Increase restrictions
  seatbelt downgrade whatsapp       Decrease restrictions
"""
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Stats
    subparsers.add_parser('stats', help='Show statistics')

    # Recent
    recent_p = subparsers.add_parser('recent', help='Show recent entries')
    recent_p.add_argument('count', type=int, nargs='?', default=15)

    # Blocked
    subparsers.add_parser('blocked', help='Show blocked calls')

    # Report
    subparsers.add_parser('report', help='Generate weekly review report')

    # Whitelist
    wl_p = subparsers.add_parser('whitelist', help='Manage contacts whitelist')
    wl_p.add_argument('action', nargs='?', choices=['list', 'add', 'remove'])
    wl_p.add_argument('contact', nargs='?', help='Contact to add/remove')

    # Policy
    pol_p = subparsers.add_parser('policy', help='Show policy for a tool')
    pol_p.add_argument('tool', help='Tool name (e.g., excel-mcp or mcp__excel-mcp__*)')

    # Upgrade
    up_p = subparsers.add_parser('upgrade', help='Increase tool restriction')
    up_p.add_argument('tool', help='Tool to upgrade')

    # Downgrade
    down_p = subparsers.add_parser('downgrade', help='Decrease tool restriction')
    down_p.add_argument('tool', help='Tool to downgrade')

    args = parser.parse_args()

    commands = {
        'stats': cmd_stats,
        'recent': cmd_recent,
        'blocked': cmd_blocked,
        'report': cmd_report,
        'whitelist': cmd_whitelist,
        'policy': cmd_policy,
        'upgrade': cmd_upgrade,
        'downgrade': cmd_downgrade,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
