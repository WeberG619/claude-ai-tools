#!/usr/bin/env python3
"""Turn on Samsung TV"""
import websocket
import json
import base64
import ssl
import time
import socket

tv_ip = "192.168.1.150"
tv_mac = "68:72:c3:36:93:96"

def send_wol():
    """Send Wake-on-LAN packet"""
    mac_bytes = bytes.fromhex(tv_mac.replace(':', '').replace('-', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, ('255.255.255.255', 9))
    sock.sendto(magic_packet, ('192.168.1.255', 9))
    sock.sendto(magic_packet, (tv_ip, 9))
    sock.close()
    print("Sent Wake-on-LAN packet")

def send_power_key():
    """Send power key via WebSocket"""
    name = base64.b64encode("BridgeAI".encode()).decode()
    url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

    try:
        ws = websocket.create_connection(url, timeout=5, sslopt={"cert_reqs": ssl.CERT_NONE})

        # Try multiple power-related keys
        power_keys = ["KEY_POWER", "KEY_POWERON", "KEY_POWEROFF"]
        for key in power_keys:
            cmd = {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey"
                }
            }
            ws.send(json.dumps(cmd))
            print(f"Sent {key}")
            time.sleep(0.5)

        ws.close()
    except Exception as e:
        print(f"WebSocket error: {e}")

print("=" * 40)
print("  Turning ON Samsung TV")
print("=" * 40)
print()

# Step 1: Send WOL
print("Step 1: Wake-on-LAN")
for i in range(3):
    send_wol()
    time.sleep(0.5)

print()
print("Waiting 5 seconds...")
time.sleep(5)

# Step 2: Send power key
print()
print("Step 2: Sending power commands")
send_power_key()

print()
print("Done! Check the Samsung TV.")
