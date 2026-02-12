#!/usr/bin/env python3
"""
System Status Dashboard

Shows status of all Claude personal assistant services.
"""

import json
import subprocess
import socket
from pathlib import Path
from datetime import datetime

def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is listening"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except:
        return False

def check_http(url: str) -> bool:
    """Check if HTTP endpoint responds"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', url],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == '200'
    except:
        return False

def get_process_status(pattern: str) -> dict:
    """Check if a process is running"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', pattern],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return {
            'running': len(pids) > 0,
            'pids': pids
        }
    except:
        return {'running': False, 'pids': []}

def get_live_state() -> dict:
    """Read live system state"""
    try:
        state_file = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
        if state_file.exists():
            return json.loads(state_file.read_text())
    except:
        pass
    return {}

def check_daemon_pid(name: str) -> dict:
    """Check daemon PID file and verify process is alive"""
    pid_dir = Path("/mnt/d/_CLAUDE-TOOLS/gateway/pids")
    pidfile = pid_dir / f"{name}.pid"
    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
            # Check if process is alive
            result = subprocess.run(['kill', '-0', str(pid)], capture_output=True)
            if result.returncode == 0:
                # Get uptime
                uptime_result = subprocess.run(
                    ['ps', '-o', 'etime=', '-p', str(pid)],
                    capture_output=True, text=True
                )
                uptime = uptime_result.stdout.strip() if uptime_result.stdout else "?"
                return {'running': True, 'pid': pid, 'uptime': uptime}
        except:
            pass
    return {'running': False, 'pid': None, 'uptime': None}


def fmt_status(running: bool, extra: str = "") -> str:
    """Format a colored status string"""
    if running:
        s = "\033[92mRUNNING\033[0m"
        if extra:
            s += f" ({extra})"
        return s
    else:
        return "\033[91mSTOPPED\033[0m"


def main():
    """Print status dashboard"""
    print("=" * 70)
    print("      CLAUDE PERSONAL ASSISTANT - SERVICE STATUS")
    print("=" * 70)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Daemon-managed services
    print("\n[DAEMON SERVICES]")
    print("-" * 70)

    daemon_services = [
        ("gateway-hub",  "Gateway Hub (ws://127.0.0.1:18789)"),
        ("telegram-bot", "Telegram Bot"),
        ("whatsapp-gw",  "WhatsApp Gateway"),
        ("web-chat",     "Web Chat (http://localhost:5555)"),
        ("proactive",    "Proactive Scheduler (7AM briefing)"),
    ]

    for svc_name, label in daemon_services:
        info = check_daemon_pid(svc_name)
        extra = f"PID {info['pid']}, up {info['uptime']}" if info['running'] else ""
        print(f"  {label:42s}: {fmt_status(info['running'], extra)}")

    # Fallback: also check by process pattern if daemon not used
    print("\n[NETWORK CHECKS]")
    print("-" * 70)

    hub_up = check_port("localhost", 18789)
    print(f"  {'Gateway Hub port 18789':42s}: {fmt_status(hub_up)}")

    webchat_up = check_port("localhost", 5555)
    print(f"  {'Web Chat port 5555':42s}: {fmt_status(webchat_up)}")

    # Messaging Channels process check
    print("\n[MESSAGING CHANNELS - PROCESS CHECK]")
    print("-" * 70)

    telegram = get_process_status("bot.py")
    print(f"  {'Telegram Bot (bot.py)':42s}: {fmt_status(telegram['running'])}")

    whatsapp = get_process_status("whatsapp-gateway/server.js")
    print(f"  {'WhatsApp Gateway (server.js)':42s}: {fmt_status(whatsapp['running'])}")

    # System Resources
    print("\n[SYSTEM RESOURCES]")
    print("-" * 70)

    state = get_live_state()
    system = state.get('system', {})

    memory = system.get('memory_percent', 'N/A')
    cpu = system.get('cpu_percent', 'N/A')
    total_mem = system.get('memory_total_gb', 'N/A')
    used_mem = system.get('memory_used_gb', 'N/A')

    print(f"  Memory Usage: {memory}% ({used_mem}/{total_mem} GB)")
    print(f"  CPU Usage: {cpu}%")

    monitors = state.get('monitors', {})
    print(f"  Monitors: {monitors.get('count', 'N/A')}")

    # Email Status
    print("\n[EMAIL STATUS]")
    print("-" * 70)

    email = state.get('email', {})
    unread = email.get('unread_count', 0)
    urgent = email.get('urgent_count', 0)
    needs_response = email.get('needs_response_count', 0)
    last_check = email.get('last_check', 'Never')

    print(f"  Unread: {unread} | Urgent: {urgent} | Needs Response: {needs_response}")
    print(f"  Last Check: {last_check}")

    # Active Apps
    print("\n[ACTIVE APPLICATIONS]")
    print("-" * 70)

    apps = state.get('applications', [])
    for app in apps[:5]:  # Show top 5
        name = app.get('ProcessName', 'Unknown')
        title = app.get('MainWindowTitle', '')[:40]
        monitor = app.get('Monitor', '?')
        print(f"  [{monitor}] {name}: {title}")

    print("\n" + "=" * 70)
    print("  DAEMON:  claude-daemon start|stop|restart|status|logs")
    print("  WINDOWS: D:\\_CLAUDE-TOOLS\\gateway\\START_ALL.bat")
    print("  BRIEFING: python3 /mnt/d/_CLAUDE-TOOLS/proactive/scheduler.py --briefing-now")
    print("  TEST NOTIFY: python3 /mnt/d/_CLAUDE-TOOLS/proactive/notify_channels.py \"test\"")
    print("=" * 70)

if __name__ == "__main__":
    main()
