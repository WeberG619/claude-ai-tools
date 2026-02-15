"""Launch Chrome CDP with cookies copied from real profile."""
import subprocess
import time
import urllib.request
import json
import shutil
import os

# Kill Chrome
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, timeout=10)
time.sleep(3)

# Setup paths
real_profile = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\Profile 6"
cdp_dir = r"C:\Users\rick\AppData\Local\Google\Chrome\CDP_Profile"

# Clean and recreate CDP profile directory
if os.path.exists(cdp_dir):
    shutil.rmtree(cdp_dir, ignore_errors=True)
    time.sleep(1)
os.makedirs(cdp_dir, exist_ok=True)
os.makedirs(os.path.join(cdp_dir, "Default"), exist_ok=True)

# Copy critical files that contain login sessions
files_to_copy = [
    "Cookies",
    "Login Data",
    "Web Data",
    "Preferences",
    "Secure Preferences",
    "Local State",
]

for f in files_to_copy:
    src = os.path.join(real_profile, f)
    dst = os.path.join(cdp_dir, "Default", f)
    if os.path.exists(src):
        try:
            shutil.copy2(src, dst)
            print(f"  Copied {f}")
        except Exception as e:
            print(f"  Failed to copy {f}: {e}")

# Also copy Local State from user data root (needed for encryption)
local_state_src = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data\Local State"
local_state_dst = os.path.join(cdp_dir, "Local State")
if os.path.exists(local_state_src):
    shutil.copy2(local_state_src, local_state_dst)
    print("  Copied Local State (encryption keys)")

# Launch Chrome with CDP using the cookie-cloned profile
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
args = [
    chrome,
    "--remote-debugging-port=9222",
    f"--user-data-dir={cdp_dir}",
    "--no-first-run",
    "--remote-allow-origins=*",
    "--restore-last-session",
]
print(f"\nLaunching Chrome with CDP profile...")
proc = subprocess.Popen(args)

for i in range(20):
    time.sleep(1)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
        data = json.loads(r.read())
        print(f"\nCDP ACTIVE! Browser: {data.get('Browser')}")
        print(f"WS: {data.get('webSocketDebuggerUrl')}")

        r2 = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2)
        tabs = json.loads(r2.read())
        print(f"Tabs: {len(tabs)}")
        for t in tabs[:5]:
            print(f"  - {t.get('title', '?')[:60]} | {t.get('url', '?')[:60]}")
        break
    except Exception:
        if i % 5 == 4:
            print(f"  Waiting... ({i+1}s)")
else:
    print("CDP failed after 20s")
