#!/usr/bin/env python3
"""Pair with LG WebOS TV"""
import websocket
import json
import ssl
import time
import os

lg_ip = "192.168.1.46"
ws_url = f"wss://{lg_ip}:3001/"
config_path = os.path.join(os.path.dirname(__file__), "lg_config.json")

# Registration payload for LG WebOS
register_payload = {
    "type": "register",
    "id": "register_0",
    "payload": {
        "forcePairing": False,
        "pairingType": "PROMPT",
        "client-key": "",  # Will be filled if we have one
        "manifest": {
            "manifestVersion": 1,
            "appVersion": "1.1",
            "signed": {
                "created": "20240101",
                "appId": "com.bridgeai.remote",
                "vendorId": "com.bridgeai",
                "localizedAppNames": {"": "BridgeAI", "en-US": "BridgeAI"},
                "localizedVendorNames": {"": "BridgeAI"},
                "permissions": [
                    "LAUNCH",
                    "LAUNCH_WEBAPP",
                    "APP_TO_APP",
                    "CLOSE",
                    "TEST_OPEN",
                    "TEST_PROTECTED",
                    "CONTROL_AUDIO",
                    "CONTROL_DISPLAY",
                    "CONTROL_INPUT_JOYSTICK",
                    "CONTROL_INPUT_MEDIA_RECORDING",
                    "CONTROL_INPUT_MEDIA_PLAYBACK",
                    "CONTROL_INPUT_TV",
                    "CONTROL_POWER",
                    "READ_APP_STATUS",
                    "READ_CURRENT_CHANNEL",
                    "READ_INPUT_DEVICE_LIST",
                    "READ_NETWORK_STATE",
                    "READ_RUNNING_APPS",
                    "READ_TV_CHANNEL_LIST",
                    "WRITE_NOTIFICATION_TOAST",
                    "READ_POWER_STATE",
                    "READ_COUNTRY_INFO"
                ],
                "serial": "BridgeAI2024"
            },
            "permissions": [
                "LAUNCH",
                "LAUNCH_WEBAPP",
                "CONTROL_AUDIO",
                "CONTROL_POWER",
                "READ_CURRENT_CHANNEL",
                "READ_RUNNING_APPS",
                "WRITE_NOTIFICATION_TOAST"
            ],
            "signatures": [{"signatureVersion": 1, "signature": "mock"}]
        }
    }
}

# Check if we already have a client key
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
        if config.get("client_key"):
            register_payload["payload"]["client-key"] = config["client_key"]
            print(f"Found saved client key")

print(f"Connecting to LG TV at {lg_ip}...")
print("=" * 50)
print("  CHECK YOUR LG TV!")
print("  A pairing prompt should appear.")
print("  Press ACCEPT on the TV remote.")
print("=" * 50)
print()

try:
    ws = websocket.create_connection(
        ws_url,
        timeout=30,
        sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    print("Connected to TV!")

    # Send registration
    print("Sending pairing request...")
    ws.send(json.dumps(register_payload))

    # Wait for response (user needs to accept on TV)
    print("Waiting for you to accept on TV...")

    client_key = None
    for i in range(30):  # Wait up to 30 seconds
        try:
            ws.settimeout(2)
            response = ws.recv()
            data = json.loads(response)

            print(f"Response type: {data.get('type', 'unknown')}")

            if data.get('type') == 'registered':
                client_key = data.get('payload', {}).get('client-key')
                if client_key:
                    print()
                    print("=" * 50)
                    print("  PAIRING SUCCESSFUL!")
                    print("=" * 50)

                    # Save client key for future use
                    with open(config_path, 'w') as f:
                        json.dump({
                            "ip": lg_ip,
                            "client_key": client_key
                        }, f, indent=2)
                    print(f"Client key saved to {config_path}")
                    break

            elif data.get('type') == 'error':
                print(f"Error: {data.get('error')}")
                break

        except websocket.WebSocketTimeoutException:
            print(".", end="", flush=True)
            continue
        except Exception as e:
            print(f"Error receiving: {e}")
            break

    if not client_key:
        print("\nPairing timed out. Make sure to press ACCEPT on the TV.")

    ws.close()

except Exception as e:
    print(f"Connection error: {e}")
