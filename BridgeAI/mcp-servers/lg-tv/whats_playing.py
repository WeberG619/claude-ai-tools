#!/usr/bin/env python3
"""Check what's currently playing on LG TV"""
import json
import os

from pywebostv.connection import WebOSClient
from pywebostv.controls import ApplicationControl, MediaControl, SystemControl, SourceControl, TvControl

config_path = os.path.join(os.path.dirname(__file__), "lg_config.json")
lg_ip = "192.168.1.46"

# Load saved client key
store = {}
if os.path.exists(config_path):
    with open(config_path) as f:
        data = json.load(f)
        store = data.get("store", {})

print("Connecting to LG TV...")

client = WebOSClient(lg_ip)
client.connect()

for status in client.register(store):
    if status == WebOSClient.REGISTERED:
        break

print("Connected!")
print()

# Get system info
system = SystemControl(client)
try:
    info = system.info()
    print("=== LG TV INFO ===")
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()
except Exception as e:
    print(f"Could not get system info: {e}")

# Get current app
app_control = ApplicationControl(client)
try:
    current = app_control.get_current()
    print("=== CURRENTLY SHOWING ===")
    print(f"  App ID: {current}")

    # Translate app ID to friendly name
    app_names = {
        'com.webos.app.livetv': 'Live TV',
        'com.webos.app.hdmi1': 'HDMI 1',
        'com.webos.app.hdmi2': 'HDMI 2',
        'com.webos.app.hdmi3': 'HDMI 3',
        'com.webos.app.hdmi4': 'HDMI 4',
        'netflix': 'Netflix',
        'youtube.leanback.v4': 'YouTube',
        'amazon': 'Amazon Prime Video',
        'hulu': 'Hulu',
        'com.webos.app.browser': 'Web Browser',
        'com.webos.app.home': 'Home Screen',
        'com.webos.app.screensaver': 'Screen Saver',
        'airplay': 'AirPlay'
    }

    friendly = app_names.get(current, current)
    print(f"  Watching: {friendly}")
    print()
except Exception as e:
    print(f"Could not get current app: {e}")

# If watching live TV, get channel info
try:
    tv = TvControl(client)
    channel = tv.get_current_channel()
    if channel:
        print("=== CHANNEL INFO ===")
        print(f"  Channel: {channel}")
except:
    pass

# Get volume
try:
    media = MediaControl(client)
    vol = media.get_volume()
    print(f"=== VOLUME ===")
    print(f"  Level: {vol}")
except:
    pass

# List running apps
try:
    apps = app_control.list_apps()
    print()
    print(f"=== INSTALLED APPS ({len(apps)}) ===")
    for app in apps[:10]:
        print(f"  - {app.get('title', app.get('id', 'Unknown'))}")
    if len(apps) > 10:
        print(f"  ... and {len(apps) - 10} more")
except:
    pass
