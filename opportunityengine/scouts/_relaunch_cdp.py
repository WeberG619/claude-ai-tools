"""Relaunch Chrome CDP with proper cookie copy."""
import subprocess
import time
import urllib.request
import json
import shutil
import os

# Kill Chrome
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, timeout=10)
time.sleep(3)

real_profile = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\Profile 6"
cdp_dir = r"C:\Users\rick\AppData\Local\Google\Chrome\CDP_Profile"

# Clean CDP directory
if os.path.exists(cdp_dir):
    shutil.rmtree(cdp_dir, ignore_errors=True)
    time.sleep(1)

# Copy the ENTIRE profile directory to preserve all session data
print("Copying full profile (this may take a moment)...")
shutil.copytree(real_profile, os.path.join(cdp_dir, "Default"), dirs_exist_ok=True)
print("  Profile copied!")

# Also copy Local State from user data root
local_state_src = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\Local State"
local_state_dst = os.path.join(cdp_dir, "Local State")
shutil.copy2(local_state_src, local_state_dst)
print("  Local State copied!")

# Remove any lock files
for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
    p = os.path.join(cdp_dir, lock)
    if os.path.exists(p):
        os.remove(p)
    p2 = os.path.join(cdp_dir, "Default", lock)
    if os.path.exists(p2):
        os.remove(p2)

# Launch Chrome
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
args = [
    chrome,
    "--remote-debugging-port=9222",
    f"--user-data-dir={cdp_dir}",
    "--no-first-run",
    "--remote-allow-origins=*",
]
print(f"\nLaunching Chrome with CDP...")
proc = subprocess.Popen(args)

for i in range(25):
    time.sleep(1)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
        data = json.loads(r.read())
        print(f"\nCDP ACTIVE! Browser: {data.get('Browser')}")

        r2 = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2)
        tabs = json.loads(r2.read())
        print(f"Tabs: {len(tabs)}")
        for t in tabs[:5]:
            print(f"  - {t.get('title', '?')[:50]} | {t.get('url', '?')[:50]}")
        break
    except Exception:
        if i % 5 == 4:
            print(f"  Waiting... ({i+1}s)")
else:
    print("CDP failed after 25s")
