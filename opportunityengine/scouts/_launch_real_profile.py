"""Try launching CDP with the real Chrome user data directory."""
import subprocess
import time
import urllib.request
import json
import os

# Kill Chrome completely
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, timeout=10)
time.sleep(5)

# Remove lock files
user_data = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data"
for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
    p = os.path.join(user_data, lock)
    if os.path.exists(p):
        os.remove(p)
        print(f"Removed {lock}")

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Try with the real user-data-dir (original path so cookies work)
# Use --no-sandbox and --disable-features to prevent profile picker from blocking CDP
args = [
    chrome,
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    f"--user-data-dir={user_data}",
    "--profile-directory=Profile 6",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=ChromeProfilePicker",
]

print(f"Launching Chrome with real profile...")
print(f"  Args: {args[1:5]}")
proc = subprocess.Popen(args)
print(f"  PID: {proc.pid}")

for i in range(30):
    time.sleep(1)
    # Check DevToolsActivePort
    port_file = os.path.join(user_data, "DevToolsActivePort")
    if os.path.exists(port_file):
        with open(port_file) as f:
            content = f.read().strip()
        lines = content.split("\n")
        port = lines[0] if lines else "?"
        print(f"\n  DevToolsActivePort found! Port: {port}")
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3)
            data = json.loads(r.read())
            print(f"  CDP ACTIVE on port {port}!")
            print(f"  Browser: {data.get('Browser')}")

            r2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3)
            tabs = json.loads(r2.read())
            print(f"  Tabs: {len(tabs)}")
            for t in tabs[:5]:
                print(f"    - {t.get('title', '?')[:50]} | {t.get('url', '?')[:50]}")
            break
        except Exception as e:
            print(f"  Port {port} found but HTTP failed: {e}")

    # Also try 9222 directly
    try:
        r = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1)
        data = json.loads(r.read())
        print(f"\nCDP on 9222: {data.get('Browser')}")
        break
    except:
        pass

    if i % 5 == 4:
        print(f"  Waiting... ({i+1}s)")
else:
    print("\nCDP failed after 30s")
    port_file = os.path.join(user_data, "DevToolsActivePort")
    print(f"  DevToolsActivePort exists: {os.path.exists(port_file)}")
