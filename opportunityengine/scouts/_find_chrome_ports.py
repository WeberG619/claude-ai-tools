"""Find all Chrome listening ports via netstat."""
import subprocess
import re

# Get netstat output
result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)

# Get all Chrome PIDs
tasklist = subprocess.run(["tasklist", "/fi", "imagename eq chrome.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True)

chrome_pids = set()
for line in tasklist.stdout.strip().split("\n"):
    parts = line.strip('"').split('","')
    if len(parts) >= 2:
        try:
            chrome_pids.add(int(parts[1]))
        except ValueError:
            pass

print(f"Chrome PIDs: {len(chrome_pids)}")

# Find listening ports for Chrome
for line in result.stdout.split("\n"):
    if "LISTENING" in line:
        parts = line.split()
        if len(parts) >= 5:
            try:
                pid = int(parts[-1])
                if pid in chrome_pids:
                    addr = parts[1]
                    print(f"  Chrome PID {pid} LISTENING on {addr}")
            except ValueError:
                pass

# Also scan common debugging ports with HTTP
import urllib.request
import json

print("\nScanning all ports 9000-9999 for CDP...")
for port in range(9000, 10000):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.5)
        data = json.loads(r.read())
        print(f"  CDP found on port {port}: {data.get('Browser', '?')}")
        break
    except Exception:
        pass
else:
    print("  No CDP found on 9000-9999")
