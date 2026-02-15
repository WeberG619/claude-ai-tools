"""Launch CDP with correctly structured profile copy."""
import subprocess
import time
import urllib.request
import json
import shutil
import os

subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, timeout=10)
time.sleep(4)

src_data = r"C:\Users\rick\AppData\Local\Google\Chrome\User Data"
cdp_data = r"C:\Users\rick\AppData\Local\Google\Chrome\CDP_Data"

# Clean
if os.path.exists(cdp_data):
    shutil.rmtree(cdp_data, ignore_errors=True)
    time.sleep(1)
os.makedirs(cdp_data, exist_ok=True)

# Copy Local State (encryption keys)
shutil.copy2(os.path.join(src_data, "Local State"), os.path.join(cdp_data, "Local State"))
print("Copied Local State")

# Copy Profile 6 directory preserving its name
src_profile = os.path.join(src_data, "Profile 6")
dst_profile = os.path.join(cdp_data, "Profile 6")
print("Copying Profile 6...")
shutil.copytree(src_profile, dst_profile)
print("Copied Profile 6")

# Remove lock files
for f in os.listdir(cdp_data):
    if "Singleton" in f or "lockfile" in f.lower():
        os.remove(os.path.join(cdp_data, f))

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
args = [
    chrome,
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    f"--user-data-dir={cdp_data}",
    "--profile-directory=Profile 6",
    "--no-first-run",
    "--no-default-browser-check",
]

print(f"\nLaunching Chrome...")
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
        print("\nReady for submissions!")
        break
    except:
        if i % 5 == 4:
            print(f"  Waiting... ({i+1}s)")
else:
    print("CDP failed after 25s")
