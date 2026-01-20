#!/usr/bin/env python3
"""
BridgeAI System Monitor
========================
Lightweight system monitoring with alerts.
Uses minimal resources - perfect for 8GB RAM systems.

Features:
- Monitor CPU, RAM, disk usage
- Check if devices are online
- Alert on problems
- Log system stats over time
"""

import os
import json
import time
import socket
import psutil
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/BridgeAI/Logs/monitor.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

CONFIG_FILE = Path('C:/BridgeAI/config/monitor_config.json')
STATS_FILE = Path('C:/BridgeAI/data/system_stats.json')
ALERTS_FILE = Path('C:/BridgeAI/data/alerts.json')

DEFAULT_CONFIG = {
    "check_interval_seconds": 60,
    "thresholds": {
        "cpu_percent": 90,
        "memory_percent": 85,
        "disk_percent": 90
    },
    "devices_to_monitor": [
        {"name": "Main PC", "ip": "192.168.1.51", "port": 445},
        {"name": "Samsung TV", "ip": "192.168.1.150", "port": 8001},
        {"name": "LG TV", "ip": "192.168.1.46", "port": 3001}
    ],
    "services_to_monitor": [
        {"name": "Hub Server", "url": "http://localhost:5000/api/health"},
        {"name": "Brain API", "url": "http://localhost:5001/status"}
    ],
    "alert_methods": {
        "log": True,
        "file": True,
        "sound": False
    },
    "max_stats_entries": 1440  # 24 hours at 1-minute intervals
}


def load_config():
    """Load or create configuration"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG


def check_port(ip, port, timeout=2):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def check_url(url, timeout=5):
    """Check if a URL is responding"""
    try:
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except:
        return False


def get_system_stats():
    """Get current system statistics"""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'percent': psutil.virtual_memory().percent,
            'used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
            'total_gb': round(psutil.virtual_memory().total / (1024**3), 2)
        },
        'disk': {}
    }

    # Get disk usage for each drive
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            stats['disk'][partition.mountpoint] = {
                'percent': usage.percent,
                'free_gb': round(usage.free / (1024**3), 2),
                'total_gb': round(usage.total / (1024**3), 2)
            }
        except:
            pass

    return stats


def check_devices(devices):
    """Check status of network devices"""
    results = {}
    for device in devices:
        online = check_port(device['ip'], device['port'])
        results[device['name']] = {
            'online': online,
            'ip': device['ip'],
            'checked_at': datetime.now().isoformat()
        }
    return results


def check_services(services):
    """Check status of local services"""
    results = {}
    for service in services:
        healthy = check_url(service['url'])
        results[service['name']] = {
            'healthy': healthy,
            'url': service['url'],
            'checked_at': datetime.now().isoformat()
        }
    return results


def save_alert(alert_type, message, severity='warning'):
    """Save an alert to file"""
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    alerts = []
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE) as f:
                alerts = json.load(f)
        except:
            pass

    alert = {
        'timestamp': datetime.now().isoformat(),
        'type': alert_type,
        'message': message,
        'severity': severity,
        'acknowledged': False
    }
    alerts.append(alert)

    # Keep only last 100 alerts
    alerts = alerts[-100:]

    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)

    log.warning(f"ALERT [{severity}]: {message}")


def check_thresholds(stats, thresholds, previous_alerts):
    """Check if any thresholds are exceeded"""
    alerts = []

    # CPU
    if stats['cpu_percent'] > thresholds.get('cpu_percent', 90):
        key = 'cpu_high'
        if key not in previous_alerts:
            save_alert('cpu', f"CPU usage high: {stats['cpu_percent']}%")
            alerts.append(key)

    # Memory
    if stats['memory']['percent'] > thresholds.get('memory_percent', 85):
        key = 'memory_high'
        if key not in previous_alerts:
            save_alert('memory', f"Memory usage high: {stats['memory']['percent']}%")
            alerts.append(key)

    # Disk
    for mount, disk_stats in stats['disk'].items():
        if disk_stats['percent'] > thresholds.get('disk_percent', 90):
            key = f'disk_high_{mount}'
            if key not in previous_alerts:
                save_alert('disk', f"Disk {mount} usage high: {disk_stats['percent']}%")
                alerts.append(key)

    return alerts


def save_stats(stats, max_entries):
    """Save stats to history file"""
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE) as f:
                history = json.load(f)
        except:
            pass

    history.append(stats)
    history = history[-max_entries:]

    with open(STATS_FILE, 'w') as f:
        json.dump(history, f)


def run_monitor(single_pass=False):
    """Run the system monitor"""
    config = load_config()
    previous_alerts = set()

    log.info("=" * 50)
    log.info("BridgeAI System Monitor Started")
    log.info("=" * 50)

    while True:
        try:
            # Get system stats
            stats = get_system_stats()

            # Check devices
            stats['devices'] = check_devices(config.get('devices_to_monitor', []))

            # Check services
            stats['services'] = check_services(config.get('services_to_monitor', []))

            # Check thresholds and alert
            new_alerts = check_thresholds(stats, config.get('thresholds', {}), previous_alerts)
            previous_alerts.update(new_alerts)

            # Check for offline devices
            for device_name, device_status in stats['devices'].items():
                if not device_status['online']:
                    key = f'device_offline_{device_name}'
                    if key not in previous_alerts:
                        save_alert('device', f"{device_name} is offline")
                        previous_alerts.add(key)
                else:
                    # Clear alert if device comes back online
                    key = f'device_offline_{device_name}'
                    if key in previous_alerts:
                        previous_alerts.remove(key)
                        log.info(f"{device_name} is back online")

            # Save stats
            save_stats(stats, config.get('max_stats_entries', 1440))

            # Log summary
            log.debug(f"CPU: {stats['cpu_percent']}% | RAM: {stats['memory']['percent']}%")

            if single_pass:
                return stats

            time.sleep(config.get('check_interval_seconds', 60))

        except KeyboardInterrupt:
            log.info("Monitor stopped")
            break
        except Exception as e:
            log.error(f"Monitor error: {e}")
            time.sleep(60)


def get_status():
    """Get current status"""
    config = load_config()
    stats = get_system_stats()
    stats['devices'] = check_devices(config.get('devices_to_monitor', []))
    stats['services'] = check_services(config.get('services_to_monitor', []))
    return stats


def get_alerts():
    """Get recent alerts"""
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE) as f:
            return json.load(f)
    return []


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'status':
            print(json.dumps(get_status(), indent=2))
        elif cmd == 'alerts':
            print(json.dumps(get_alerts(), indent=2))
        elif cmd == 'once':
            stats = run_monitor(single_pass=True)
            print(json.dumps(stats, indent=2))
        elif cmd == 'config':
            config = load_config()
            print(json.dumps(config, indent=2))
        else:
            print("Usage: python system_monitor.py [status|alerts|once|config]")
    else:
        run_monitor()
