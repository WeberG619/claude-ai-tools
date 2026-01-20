#!/usr/bin/env python3
"""
BridgeAI Wake-on-LAN Controller
================================
Wake up computers and devices remotely.
Super lightweight - just sends magic packets.

Features:
- Wake computers by name or MAC address
- Check if device woke up successfully
- Scheduled wake-ups
- Can be triggered via API
"""

import socket
import struct
import json
import time
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/BridgeAI/Logs/wol.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

CONFIG_FILE = Path('C:/BridgeAI/config/wol_config.json')

DEFAULT_CONFIG = {
    "devices": {
        "main_pc": {
            "name": "Main PC",
            "mac": "XX:XX:XX:XX:XX:XX",  # User needs to fill in
            "ip": "192.168.1.51",
            "check_port": 445
        },
        "samsung_tv": {
            "name": "Samsung TV",
            "mac": "68:72:c3:36:93:96",
            "ip": "192.168.1.150",
            "check_port": 8001
        }
    },
    "broadcast_address": "192.168.1.255",
    "wol_port": 9,
    "check_timeout": 60,
    "check_interval": 5
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


def create_magic_packet(mac_address):
    """Create a Wake-on-LAN magic packet"""
    # Remove separators from MAC address
    mac = mac_address.replace(':', '').replace('-', '').replace('.', '')

    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac_address}")

    # Convert to bytes
    mac_bytes = bytes.fromhex(mac)

    # Magic packet = 6 bytes of FF + 16 repetitions of MAC address
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    return magic_packet


def send_wol(mac_address, broadcast='192.168.1.255', port=9):
    """Send a Wake-on-LAN packet"""
    try:
        packet = create_magic_packet(mac_address)

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Send packet
        sock.sendto(packet, (broadcast, port))
        sock.close()

        log.info(f"WOL packet sent to {mac_address}")
        return True

    except Exception as e:
        log.error(f"Failed to send WOL: {e}")
        return False


def check_device_online(ip, port, timeout=2):
    """Check if a device is online"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def wake_device(device_name, wait_for_online=True):
    """Wake a device by name and optionally wait for it to come online"""
    config = load_config()

    if device_name not in config['devices']:
        log.error(f"Unknown device: {device_name}")
        return {'success': False, 'error': f'Unknown device: {device_name}'}

    device = config['devices'][device_name]
    mac = device['mac']
    ip = device['ip']
    check_port = device.get('check_port', 445)

    # Check if already online
    if check_device_online(ip, check_port):
        log.info(f"{device['name']} is already online")
        return {'success': True, 'message': 'Device already online', 'was_online': True}

    # Send WOL packet
    broadcast = config.get('broadcast_address', '192.168.1.255')
    wol_port = config.get('wol_port', 9)

    success = send_wol(mac, broadcast, wol_port)

    if not success:
        return {'success': False, 'error': 'Failed to send WOL packet'}

    if not wait_for_online:
        return {'success': True, 'message': 'WOL packet sent', 'was_online': False}

    # Wait for device to come online
    timeout = config.get('check_timeout', 60)
    interval = config.get('check_interval', 5)
    start_time = time.time()

    log.info(f"Waiting for {device['name']} to come online...")

    while time.time() - start_time < timeout:
        if check_device_online(ip, check_port):
            elapsed = round(time.time() - start_time, 1)
            log.info(f"{device['name']} is online after {elapsed} seconds")
            return {
                'success': True,
                'message': f'Device online after {elapsed}s',
                'was_online': False,
                'boot_time': elapsed
            }
        time.sleep(interval)

    log.warning(f"{device['name']} did not come online within {timeout} seconds")
    return {
        'success': False,
        'error': f'Device did not respond within {timeout} seconds',
        'was_online': False
    }


def wake_all():
    """Wake all configured devices"""
    config = load_config()
    results = {}

    for device_name in config['devices']:
        results[device_name] = wake_device(device_name, wait_for_online=False)

    return results


def get_status():
    """Get status of all devices"""
    config = load_config()
    status = {}

    for device_name, device in config['devices'].items():
        online = check_device_online(device['ip'], device.get('check_port', 445))
        status[device_name] = {
            'name': device['name'],
            'online': online,
            'ip': device['ip'],
            'mac': device['mac']
        }

    return status


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("BridgeAI Wake-on-LAN Controller")
        print()
        print("Usage:")
        print("  python wol_controller.py wake <device_name>  - Wake a device")
        print("  python wol_controller.py wake_all            - Wake all devices")
        print("  python wol_controller.py status              - Check device status")
        print("  python wol_controller.py config              - Show configuration")
        print()
        print("Configured devices:")
        config = load_config()
        for name, device in config['devices'].items():
            print(f"  - {name}: {device['name']} ({device['ip']})")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'wake' and len(sys.argv) > 2:
        device_name = sys.argv[2]
        result = wake_device(device_name)
        print(json.dumps(result, indent=2))

    elif cmd == 'wake_all':
        result = wake_all()
        print(json.dumps(result, indent=2))

    elif cmd == 'status':
        status = get_status()
        print(json.dumps(status, indent=2))

    elif cmd == 'config':
        config = load_config()
        print(json.dumps(config, indent=2))

    else:
        print(f"Unknown command: {cmd}")
