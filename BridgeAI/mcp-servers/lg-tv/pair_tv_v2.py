#!/usr/bin/env python3
"""Pair with LG WebOS TV - v2 with better error handling"""
import websocket
import json
import ssl
import time
import os

lg_ip = "192.168.1.46"
config_path = os.path.join(os.path.dirname(__file__), "lg_config.json")

# Try both secure and insecure connections
urls_to_try = [
    f"ws://{lg_ip}:3000/",
    f"wss://{lg_ip}:3001/",
    f"ws://{lg_ip}:3001/"
]

register_payload = {
    "type": "register",
    "payload": {
        "pairingType": "PROMPT",
        "manifest": {
            "manifestVersion": 1,
            "permissions": [
                "CONTROL_POWER",
                "CONTROL_AUDIO",
                "READ_CURRENT_CHANNEL",
                "READ_RUNNING_APPS"
            ]
        }
    }
}

print("=" * 50)
print("  LG TV PAIRING")
print("  Look at the LG TV for a pairing prompt!")
print("=" * 50)
print()

for ws_url in urls_to_try:
    print(f"Trying {ws_url}...")

    try:
        if ws_url.startswith("wss"):
            ws = websocket.create_connection(
                ws_url,
                timeout=5,
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )
        else:
            ws = websocket.create_connection(ws_url, timeout=5)

        print("Connected!")

        # Send hello/handshake first
        ws.send(json.dumps(register_payload))
        print("Sent registration request")
        print("Waiting for TV response (check TV for prompt)...")

        # Try to receive responses
        for attempt in range(20):
            try:
                ws.settimeout(2)
                raw = ws.recv()

                # Handle binary or text response
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8', errors='ignore')

                if raw.strip():
                    print(f"Received: {raw[:500]}")

                    try:
                        data = json.loads(raw)

                        if data.get('type') == 'registered':
                            client_key = data.get('payload', {}).get('client-key')
                            print()
                            print("=" * 50)
                            print("  SUCCESS! TV PAIRED!")
                            print("=" * 50)

                            if client_key:
                                with open(config_path, 'w') as f:
                                    json.dump({"ip": lg_ip, "client_key": client_key}, f)
                                print(f"Saved client key")

                            ws.close()
                            exit(0)

                        elif data.get('type') == 'response':
                            print(f"Got response: {data}")

                        elif data.get('type') == 'error':
                            print(f"Error from TV: {data.get('error')}")

                    except json.JSONDecodeError:
                        print(f"Non-JSON response: {raw[:100]}")

            except websocket.WebSocketTimeoutException:
                print(".", end="", flush=True)
            except Exception as e:
                print(f"Recv error: {e}")
                break

        ws.close()
        print()

    except Exception as e:
        print(f"  Failed: {e}")
        print()

print("\nIf no prompt appeared on TV, the TV may need to be on the home screen.")
print("Try pressing HOME on the LG remote, then run this again.")
