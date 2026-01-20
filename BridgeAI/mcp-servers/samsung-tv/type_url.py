#!/usr/bin/env python3
"""Type URL into Samsung TV browser"""
import websocket
import json
import base64
import time
import ssl

tv_ip = "192.168.1.150"
url_to_type = "192.168.1.51:5001"

name = base64.b64encode("BridgeAI".encode()).decode()
ws_url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

def send_key(ws, key):
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
    time.sleep(0.15)

print(f"Connecting to TV at {tv_ip}...")

try:
    ws = websocket.create_connection(ws_url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
    print("Connected!")

    print(f"Typing URL: {url_to_type}")

    for char in url_to_type:
        if char.isdigit():
            key = f"KEY_{char}"
        elif char == '.':
            key = "KEY_DOT"
        elif char == ':':
            key = "KEY_COLON"
        else:
            key = f"KEY_{char.upper()}"

        print(f"  Sending {key} for '{char}'")
        send_key(ws, key)

    print("\nURL typed! Pressing ENTER to navigate...")
    time.sleep(0.5)
    send_key(ws, "KEY_ENTER")

    ws.close()
    print("Done! Check your TV.")

except Exception as e:
    print(f"Error: {e}")
