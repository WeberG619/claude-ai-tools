"""Launch Chrome with CDP on port 9222."""
import subprocess
import time
import urllib.request
import json
import os

# Kill any existing Chrome
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"],
               capture_output=True, timeout=10)
time.sleep(3)

# Launch Chrome with CDP
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
args = [
    chrome,
    "--remote-debugging-port=9222",
    "--profile-directory=Profile 6",
    "--restore-last-session",
]
print(f"Launching: {' '.join(args)}")
proc = subprocess.Popen(args)
print(f"Chrome PID: {proc.pid}")

# Wait for CDP to come up
for i in range(30):
    time.sleep(1)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
        data = json.loads(r.read())
        print(f"CDP ACTIVE on port 9222!")
        print(f"  Browser: {data.get('Browser')}")
        print(f"  WS: {data.get('webSocketDebuggerUrl')}")

        # List tabs
        r2 = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2)
        tabs = json.loads(r2.read())
        print(f"  Tabs: {len(tabs)}")
        for t in tabs[:5]:
            print(f"    - {t.get('title', '?')[:50]}")
        break
    except Exception:
        if i % 5 == 4:
            print(f"  Waiting... ({i+1}s)")
            # Check DevToolsActivePort
            port_file = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\DevToolsActivePort"
            if os.path.exists(port_file):
                with open(port_file) as f:
                    print(f"  DevToolsActivePort: {f.read().strip()}")
else:
    print("CDP failed to start after 30s")
    # Check what happened
    port_file = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\DevToolsActivePort"
    if os.path.exists(port_file):
        with open(port_file) as f:
            content = f.read().strip()
            print(f"  DevToolsActivePort says: {content}")
    else:
        print("  No DevToolsActivePort file created")
