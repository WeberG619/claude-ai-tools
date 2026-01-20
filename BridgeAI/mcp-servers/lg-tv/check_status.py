#!/usr/bin/env python3
"""Check what's currently on the LG TV screen"""
import websocket
import json
import ssl
import time

lg_ip = "192.168.1.46"
ws_url = f"wss://{lg_ip}:3001/"

# LG WebOS requires a handshake/registration
register_payload = {
    "type": "register",
    "id": "register_0",
    "payload": {
        "forcePairing": False,
        "pairingType": "PROMPT",
        "manifest": {
            "manifestVersion": 1,
            "appVersion": "1.0",
            "signed": {
                "created": "20230101",
                "appId": "com.bridgeai.tv",
                "vendorId": "com.bridgeai",
                "localizedAppNames": {"": "BridgeAI"},
                "localizedVendorNames": {"": "BridgeAI"},
                "permissions": ["READ_CURRENT_CHANNEL", "READ_RUNNING_APPS", "CONTROL_POWER"],
                "serial": "1234567890"
            }
        }
    }
}

# Request to get foreground app
get_foreground_app = {
    "type": "request",
    "id": "getForegroundApp",
    "uri": "ssap://com.webos.applicationManager/getForegroundAppInfo"
}

# Request to get current channel (if watching TV)
get_current_channel = {
    "type": "request",
    "id": "getCurrentChannel",
    "uri": "ssap://tv/getCurrentChannel"
}

# Get system info
get_system_info = {
    "type": "request",
    "id": "getSystemInfo",
    "uri": "ssap://system/getSystemInfo"
}

print(f"Connecting to LG TV at {lg_ip}...")

try:
    ws = websocket.create_connection(
        ws_url,
        timeout=10,
        sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    print("Connected!")

    # Register with TV
    print("Registering with TV...")
    ws.send(json.dumps(register_payload))

    # Wait for registration response
    time.sleep(2)
    response = ws.recv()
    reg_data = json.loads(response)
    print(f"Registration: {reg_data.get('type', 'unknown')}")

    # If we need to accept pairing on TV, wait
    if reg_data.get('type') == 'registered' or 'client-key' in str(reg_data):
        print("Registered successfully!")
    elif reg_data.get('type') == 'response' and reg_data.get('payload', {}).get('pairingType') == 'PROMPT':
        print("*** CHECK TV - You may need to accept the pairing prompt ***")
        time.sleep(5)
        response = ws.recv()
        print(f"After prompt: {response[:200]}")

    # Get foreground app
    print("\nGetting current screen info...")
    ws.send(json.dumps(get_foreground_app))
    time.sleep(1)
    response = ws.recv()
    app_data = json.loads(response)

    if app_data.get('payload'):
        payload = app_data['payload']
        app_id = payload.get('appId', 'Unknown')
        print(f"\nCurrent App: {app_id}")

        # Translate common app IDs to names
        app_names = {
            'com.webos.app.livetv': 'Live TV',
            'netflix': 'Netflix',
            'youtube.leanback.v4': 'YouTube',
            'amazon': 'Amazon Prime Video',
            'hulu': 'Hulu',
            'disney': 'Disney+',
            'com.webos.app.hdmi1': 'HDMI 1',
            'com.webos.app.hdmi2': 'HDMI 2',
            'com.webos.app.hdmi3': 'HDMI 3',
            'com.webos.app.browser': 'Web Browser',
            'com.webos.app.home': 'Home Screen'
        }

        friendly_name = app_names.get(app_id, app_id)
        print(f"Watching: {friendly_name}")

    # If it's live TV, get channel info
    ws.send(json.dumps(get_current_channel))
    time.sleep(1)
    try:
        response = ws.recv()
        channel_data = json.loads(response)
        if channel_data.get('payload') and channel_data['payload'].get('channelName'):
            ch = channel_data['payload']
            print(f"Channel: {ch.get('channelNumber', '?')} - {ch.get('channelName', 'Unknown')}")
    except:
        pass

    ws.close()

except websocket.WebSocketException as e:
    print(f"WebSocket error: {e}")
except Exception as e:
    print(f"Error: {e}")
