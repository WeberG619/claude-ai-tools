#!/usr/bin/env python3
"""Clear TV input field and type URL correctly"""
import websocket
import json
import base64
import time
import ssl

tv_ip = "192.168.1.150"

name = base64.b64encode("BridgeAI".encode()).decode()
ws_url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

def send_key(ws, key, delay=0.2):
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
    time.sleep(delay)

def send_text(ws, text):
    """Send text using InputText command"""
    cmd = {
        "method": "ms.remote.control",
        "params": {
            "Cmd": text,
            "DataOfCmd": "base64",
            "Option": "false",
            "TypeOfRemote": "SendInputString"
        }
    }
    ws.send(json.dumps(cmd))

print(f"Connecting to TV...")

try:
    ws = websocket.create_connection(ws_url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
    print("Connected!")

    # Step 1: Clear the field - select all and delete
    print("Clearing field...")

    # Press backspace many times to clear
    for i in range(30):
        send_key(ws, "KEY_BACKSPACE", 0.05)

    print("Field cleared")
    time.sleep(0.5)

    # Step 2: Type the URL using InputString method (sends text directly)
    url = "192.168.1.51:5001"
    print(f"Typing: {url}")

    # Try sending as base64 encoded string
    url_b64 = base64.b64encode(url.encode()).decode()

    text_cmd = {
        "method": "ms.remote.control",
        "params": {
            "Cmd": url_b64,
            "DataOfCmd": url_b64,
            "Option": "false",
            "TypeOfRemote": "SendInputString"
        }
    }
    ws.send(json.dumps(text_cmd))
    print("Sent text input")

    time.sleep(1)

    # Step 3: Press Enter
    print("Pressing ENTER...")
    send_key(ws, "KEY_ENTER", 0.3)

    ws.close()
    print("Done! Check your TV.")

except Exception as e:
    print(f"Error: {e}")
