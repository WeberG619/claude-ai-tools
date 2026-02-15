#!/usr/bin/env python3
"""
MCP Seatbelt Dashboard - Visual audit log viewer
Run: python app.py
Open: http://localhost:5050
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Support both Windows and WSL paths
import platform
if platform.system() == 'Windows':
    AUDIT_LOG = Path(r"D:\_CLAUDE-TOOLS\system-bridge\audit.ndjson")
else:
    AUDIT_LOG = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson")

def load_audit_logs(days=7, limit=1000):
    """Load audit logs from NDJSON file."""
    logs = []
    if not AUDIT_LOG.exists():
        return logs

    cutoff = datetime.now().astimezone() - timedelta(days=days)

    with open(AUDIT_LOG, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                # Parse timestamp
                ts = entry.get('timestamp', '')
                if ts:
                    entry['_dt'] = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if entry['_dt'] >= cutoff:
                        logs.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    return logs[-limit:]  # Return most recent entries

def get_stats(logs):
    """Calculate statistics from logs."""
    stats = {
        'total': len(logs),
        'blocked': sum(1 for l in logs if l.get('action') == 'block'),
        'allowed': sum(1 for l in logs if l.get('action') in ('allow', 'log_only')),
        'warned': sum(1 for l in logs if l.get('action') == 'warn'),
        'by_tool': defaultdict(int),
        'by_day': defaultdict(int),
        'by_action': defaultdict(int),
        'high_risk': [],
        'avg_risk': 0
    }

    total_risk = 0
    for log in logs:
        tool = log.get('tool', 'unknown')
        # Shorten tool name for display
        short_tool = tool.replace('mcp__', '').split('__')[0] if tool.startswith('mcp__') else tool
        stats['by_tool'][short_tool] += 1

        action = log.get('action', 'unknown')
        stats['by_action'][action] += 1

        if '_dt' in log:
            day = log['_dt'].strftime('%Y-%m-%d')
            stats['by_day'][day] += 1

        risk = log.get('risk_score', 0)
        total_risk += risk

        if risk >= 7:
            stats['high_risk'].append(log)

    if logs:
        stats['avg_risk'] = round(total_risk / len(logs), 1)

    # Sort high risk by timestamp descending
    stats['high_risk'] = sorted(stats['high_risk'], key=lambda x: x.get('timestamp', ''), reverse=True)[:20]

    return stats

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard stats."""
    days = request.args.get('days', 7, type=int)
    logs = load_audit_logs(days=days)
    stats = get_stats(logs)

    # Convert defaultdicts to regular dicts for JSON
    return jsonify({
        'total': stats['total'],
        'blocked': stats['blocked'],
        'allowed': stats['allowed'],
        'warned': stats['warned'],
        'avg_risk': stats['avg_risk'],
        'by_tool': dict(stats['by_tool']),
        'by_day': dict(sorted(stats['by_day'].items())),
        'by_action': dict(stats['by_action']),
        'high_risk': [{
            'timestamp': l.get('timestamp', '')[:19],
            'tool': l.get('tool', '').replace('mcp__', ''),
            'action': l.get('action', ''),
            'risk_score': l.get('risk_score', 0),
            'reason': l.get('reason', '-')
        } for l in stats['high_risk']]
    })

@app.route('/api/logs')
def api_logs():
    """API endpoint for filtered logs."""
    days = request.args.get('days', 7, type=int)
    tool_filter = request.args.get('tool', '')
    action_filter = request.args.get('action', '')
    min_risk = request.args.get('min_risk', 0, type=int)

    logs = load_audit_logs(days=days)

    # Apply filters
    if tool_filter:
        logs = [l for l in logs if tool_filter.lower() in l.get('tool', '').lower()]
    if action_filter:
        logs = [l for l in logs if l.get('action') == action_filter]
    if min_risk > 0:
        logs = [l for l in logs if l.get('risk_score', 0) >= min_risk]

    # Return most recent 100
    logs = sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:100]

    return jsonify([{
        'timestamp': l.get('timestamp', '')[:19],
        'tool': l.get('tool', '').replace('mcp__', ''),
        'action': l.get('action', ''),
        'risk_score': l.get('risk_score', 0),
        'reason': l.get('reason') or '-',
        'session_id': l.get('session_id', '')[:8]
    } for l in logs])

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  MCP Seatbelt Dashboard")
    print("  http://localhost:5050")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5050, debug=False)
