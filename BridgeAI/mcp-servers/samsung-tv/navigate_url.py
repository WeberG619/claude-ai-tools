#!/usr/bin/env python3
"""Navigate Samsung TV browser to a URL"""
import websocket
import json
import base64
import time
import ssl
import sys

tv_ip = "192.168.1.150"
target_url = "http://192.168.1.51:5001"

name = base64.b64encode("BridgeAI".encode()).decode()
ws_url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

print(f"Connecting to TV...")

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
    time.sleep(0.3)

def type_text(ws, text):
    """Type text character by character using virtual keyboard"""
    for char in text:
        # Send each character as a key
        if char.isdigit():
            send_key(ws, f"KEY_{char}")
        elif char == '.':
            send_key(ws, "KEY_DOT")
        elif char == ':':
            send_key(ws, "KEY_COLON")
        elif char == '/':
            send_key(ws, "KEY_SLASH")
        elif char.isalpha():
            send_key(ws, f"KEY_{char.upper()}")

try:
    ws = websocket.create_connection(ws_url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
    print("Connected!")

    # Wait for browser to be ready
    time.sleep(2)

    # Try method 1: Send URL via browser app launch
    print("Trying to open URL directly...")

    # Method using ms.channel.emit to open URL
    url_cmd = {
        "method": "ms.channel.emit",
        "params": {
            "event": "ed.apps.launch",
            "to": "host",
            "data": {
                "appId": "org.tizen.browser",
                "action_type": "NATIVE_LAUNCH",
                "metaTag": target_url
            }
        }
    }
    ws.send(json.dumps(url_cmd))
    print(f"Sent URL command: {target_url}")

    time.sleep(2)
    ws.close()
    print("Done! Check your TV.")

except websocket.WebSocketException as e:
    print(f"WebSocket error: {e}")
except Exception as e:
    print(f"Error: {e}")
