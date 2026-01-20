#!/usr/bin/env python3
"""Lower LG TV volume"""
import json
import os
from pywebostv.connection import WebOSClient
from pywebostv.controls import MediaControl

config_path = os.path.join(os.path.dirname(__file__), "lg_config.json")

with open(config_path) as f:
    store = json.load(f).get("store", {})

client = WebOSClient("192.168.1.46")
client.connect()
for status in client.register(store):
    if status == WebOSClient.REGISTERED:
        break

media = MediaControl(client)

# Get current volume
current = media.get_volume()
print(f"Current volume: {current.get('volume', '?')}")

# Lower volume by 10
print("Lowering volume...")
for i in range(10):
    media.volume_down()

# Get new volume
new = media.get_volume()
print(f"New volume: {new.get('volume', '?')}")
