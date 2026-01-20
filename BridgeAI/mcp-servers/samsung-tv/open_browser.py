#!/usr/bin/env python3
"""Open browser on Samsung TV"""
import websocket
import json
import base64
import time
import ssl
import sys

tv_ip = "192.168.1.150"
name = base64.b64encode("BridgeAI".encode()).decode()
url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

print(f"Connecting to TV at {tv_ip}...")

try:
    ws = websocket.create_connection(url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
    print("Connected!")

    # Send KEY_INTERNET to open browser
    cmd = {
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click",
            "DataOfCmd": "KEY_INTERNET",
            "Option": "false",
            "TypeOfRemote": "SendRemoteKey"
        }
    }
    ws.send(json.dumps(cmd))
    print("Sent KEY_INTERNET - browser should open")

    time.sleep(2)
    ws.close()
    print("Done!")

except websocket.WebSocketException as e:
    print(f"WebSocket error: {e}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
