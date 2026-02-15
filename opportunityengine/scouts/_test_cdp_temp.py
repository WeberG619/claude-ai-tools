"""Test CDP with temp profile to isolate the issue."""
import subprocess
import time
import urllib.request
import json
import tempfile
import os

# Kill Chrome
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True, timeout=10)
time.sleep(3)

# Try with temp user data dir (isolates from profile issues)
temp_dir = os.path.join(tempfile.gettempdir(), "chrome_cdp_test")
os.makedirs(temp_dir, exist_ok=True)

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
args = [
    chrome,
    "--remote-debugging-port=9222",
    f"--user-data-dir={temp_dir}",
    "--no-first-run",
    "--remote-allow-origins=*",
    "about:blank",
]
print(f"Testing CDP with temp profile...")
proc = subprocess.Popen(args)
print(f"Chrome PID: {proc.pid}")

for i in range(20):
    time.sleep(1)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
        data = json.loads(r.read())
        print(f"\nCDP WORKS! Browser: {data.get('Browser')}")
        print(f"WS: {data.get('webSocketDebuggerUrl')}")

        # Now we know CDP works - kill this and relaunch with real profile
        proc.terminate()
        time.sleep(2)
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
        time.sleep(2)

        # Relaunch with real profile + remote-allow-origins
        args2 = [
            chrome,
            "--remote-debugging-port=9222",
            "--remote-allow-origins=*",
            "--profile-directory=Profile 6",
            "--restore-last-session",
        ]
        print(f"\nRelaunching with real profile...")
        proc2 = subprocess.Popen(args2)

        for j in range(20):
            time.sleep(1)
            try:
                r2 = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
                data2 = json.loads(r2.read())
                print(f"CDP with real profile: {data2.get('Browser')}")

                r3 = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2)
                tabs = json.loads(r3.read())
                print(f"Tabs: {len(tabs)}")
                for t in tabs[:5]:
                    print(f"  - {t.get('title', '?')[:60]}")
                break
            except Exception:
                if j % 5 == 4:
                    print(f"  Real profile waiting... ({j+1}s)")
                    pf = os.path.join(r"C:\Users\rick\AppData\Local\Google\Chrome\User Data", "DevToolsActivePort")
                    if os.path.exists(pf):
                        with open(pf) as f:
                            print(f"  DevToolsActivePort: {f.read().strip()}")
        else:
            print("Real profile CDP failed after 20s")
        break
    except Exception:
        if i % 5 == 4:
            print(f"  Temp profile waiting... ({i+1}s)")
            pf = os.path.join(temp_dir, "DevToolsActivePort")
            if os.path.exists(pf):
                with open(pf) as f:
                    print(f"  DevToolsActivePort: {f.read().strip()}")
else:
    print("\nCDP does NOT work even with temp profile!")
    print("This is a Chrome/system-level issue, not a profile issue.")
    proc.terminate()
