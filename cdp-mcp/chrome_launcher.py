"""
Chrome/Edge Launcher — Detect and launch browsers with CDP on Windows.
Runs natively on Windows Python (invoked via powershell.exe from Claude Code).
No WSL networking hacks needed — everything is localhost on Windows.
"""

import os
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
from typing import Optional

CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
CDP_USER_DATA_DIR = os.environ.get("CDP_USER_DATA_DIR", r"C:\Temp\chrome-cdp")
EDGE_USER_DATA_DIR = os.environ.get("CDP_EDGE_USER_DATA_DIR", r"C:\Temp\edge-cdp")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# Edge port = Chrome port + 1
EDGE_CDP_PORT = int(os.environ.get("EDGE_CDP_PORT", "9226"))


def check_cdp_available(host: str = "127.0.0.1", port: int = None) -> dict:
    """
    Check if a browser CDP is available on the given host:port.
    Returns: {available: bool, browser: str|None, error: str|None}
    """
    port = port or CDP_PORT
    try:
        url = f"http://{host}:{port}/json/version"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = resp.read().decode()
            info = json.loads(data)
            return {
                "available": True,
                "browser": info.get("Browser", "Unknown"),
                "protocol_version": info.get("Protocol-Version", ""),
                "error": None,
            }
    except urllib.error.URLError as e:
        return {"available": False, "browser": None, "error": str(e)}
    except Exception as e:
        return {"available": False, "browser": None, "error": str(e)}


def _check_process_running(process_name: str) -> bool:
    """Check if a Windows process is running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        return process_name.lower() in result.stdout.lower()
    except Exception:
        return False


def _launch_browser(exe_path: str, port: int, user_data_dir: str, url: str = None) -> dict:
    """
    Launch a browser with CDP enabled using a dedicated user-data-dir.
    Using a separate user-data-dir avoids the 'already running' issue.
    Returns: {success: bool, message: str}
    """
    if not os.path.exists(exe_path):
        return {"success": False, "message": f"Browser not found at: {exe_path}"}

    # Ensure user data dir exists
    os.makedirs(user_data_dir, exist_ok=True)

    args = [
        exe_path,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={user_data_dir}",
    ]
    if url:
        args.append(url)

    try:
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except Exception as e:
        return {"success": False, "message": f"Failed to launch browser: {e}"}

    # Wait for CDP to become available
    browser_name = "Edge" if "edge" in exe_path.lower() else "Chrome"
    for i in range(10):
        time.sleep(1)
        cdp = check_cdp_available(port=port)
        if cdp["available"]:
            return {
                "success": True,
                "message": f"{browser_name} launched with CDP on port {port}. Browser: {cdp['browser']}",
            }

    return {
        "success": False,
        "message": f"{browser_name} launched but CDP not available on port {port} after 10s",
    }


def ensure_chrome_cdp(url: str = None) -> dict:
    """
    Ensure Chrome is running with CDP.
    - If CDP already available, returns ready
    - If Chrome not running at all, launches with dedicated profile
    - If Chrome running but no CDP, launches a SECOND instance with dedicated profile

    Returns: {ready: bool, message: str}
    """
    # Check if CDP is already available
    cdp = check_cdp_available(port=CDP_PORT)
    if cdp["available"]:
        return {"ready": True, "message": f"Chrome CDP ready on port {CDP_PORT}. Browser: {cdp['browser']}"}

    # Launch Chrome with dedicated profile (works even if another Chrome is running)
    return _launch_browser(CHROME_PATH, CDP_PORT, CDP_USER_DATA_DIR, url=url)


def ensure_edge_cdp(url: str = None) -> dict:
    """
    Ensure Edge is running with CDP.
    Returns: {ready: bool, message: str}
    """
    cdp = check_cdp_available(port=EDGE_CDP_PORT)
    if cdp["available"]:
        return {"ready": True, "message": f"Edge CDP ready on port {EDGE_CDP_PORT}. Browser: {cdp['browser']}"}

    return _launch_browser(EDGE_PATH, EDGE_CDP_PORT, EDGE_USER_DATA_DIR, url=url)


def get_status() -> dict:
    """Get status of all CDP-enabled browsers."""
    chrome_cdp = check_cdp_available(port=CDP_PORT)
    edge_cdp = check_cdp_available(port=EDGE_CDP_PORT)

    return {
        "chrome": {
            "port": CDP_PORT,
            "available": chrome_cdp["available"],
            "browser": chrome_cdp.get("browser"),
        },
        "edge": {
            "port": EDGE_CDP_PORT,
            "available": edge_cdp["available"],
            "browser": edge_cdp.get("browser"),
        },
    }
