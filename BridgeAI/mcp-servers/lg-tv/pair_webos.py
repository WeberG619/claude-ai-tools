#!/usr/bin/env python3
"""Pair with LG WebOS TV using pywebostv library"""
import json
import os

try:
    from pywebostv.connection import WebOSClient
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pywebostv", "-q"])
    from pywebostv.connection import WebOSClient

config_path = os.path.join(os.path.dirname(__file__), "lg_config.json")
lg_ip = "192.168.1.46"

print("=" * 50)
print("  LG TV PAIRING")
print("=" * 50)
print()
print("Connecting to LG TV at", lg_ip)
print()

# Storage for client key
store = {}

# Load existing key if available
if os.path.exists(config_path):
    try:
        with open(config_path) as f:
            data = json.load(f)
            if "store" in data:
                store = data["store"]
                print("Found existing client key")
    except:
        pass

try:
    client = WebOSClient(lg_ip)
    client.connect()
    print("Connected!")
    print()
    print("=" * 50)
    print("  CHECK YOUR LG TV NOW!")
    print("  A prompt should appear - press ACCEPT")
    print("=" * 50)
    print()

    for status in client.register(store):
        if status == WebOSClient.PROMPTED:
            print(">>> Pairing prompt displayed on TV!")
            print(">>> Press ACCEPT on your LG remote...")
        elif status == WebOSClient.REGISTERED:
            print()
            print("=" * 50)
            print("  SUCCESS! TV PAIRED!")
            print("=" * 50)
            print()

            # Save the client key
            with open(config_path, "w") as f:
                json.dump({"ip": lg_ip, "store": store}, f, indent=2)
            print("Client key saved for future use.")
            break

except Exception as e:
    print(f"Error: {e}")
    print()
    print("Tips:")
    print("- Make sure LG TV is ON (not in standby)")
    print("- Try pressing HOME on the remote first")
    print("- The TV must be on the same network")
