#!/usr/bin/env python3
"""Try multiple methods to launch Samsung TV browser"""
import websocket
import json
import base64
import time
import ssl

tv_ip = "192.168.1.150"
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
    print(f"  Sent {key}")
    time.sleep(0.5)

print("Connecting to TV...")
ws = websocket.create_connection(ws_url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
print("Connected!")

# Try KEY_HOME first to get to home screen
print("\nGoing to Home...")
send_key(ws, "KEY_HOME")
time.sleep(2)

# Then try to launch browser with various keys
print("\nTrying to open browser...")
browser_keys = ["KEY_WWW", "KEY_INTERNET", "KEY_W"]
for key in browser_keys:
    send_key(ws, key)
    time.sleep(1)

ws.close()
print("\nDone! Check your TV.")
