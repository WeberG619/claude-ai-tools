#!/usr/bin/env python3
"""
BridgeAI Application Control MCP Server
Launch, manage, and control applications
"""

import subprocess
import json
import os
import sys

sys.path.insert(0, '/mnt/d/_MCP-SERVERS')

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("bridgeai-apps")

# Common applications and their launch commands
COMMON_APPS = {
    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",

    # Microsoft Office
    "word": "WINWORD.EXE",
    "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "microsoft excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",

    # System
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "task manager": "taskmgr.exe",

    # Media
    "photos": "ms-photos:",
    "music": "mswindowsmusic:",
    "movies": "mswindowsvideo:",

    # Communication
    "teams": "msteams.exe",
    "microsoft teams": "msteams.exe",
    "zoom": "zoom.exe",
    "slack": "slack.exe",

    # Development
    "vscode": "code",
    "visual studio code": "code",
    "cursor": "cursor.exe",

    # Other common
    "snipping tool": "snippingtool.exe",
    "paint": "mspaint.exe",
}


@mcp.tool()
def launch_app(app_name: str, file_to_open: str = None) -> str:
    """
    Launch an application by name.
    Can optionally open a specific file with the app.

    Common apps: chrome, edge, word, excel, powerpoint, outlook, notepad,
                 calculator, file explorer, settings, paint, photos

    Args:
        app_name: Name of the application (common names work)
        file_to_open: Optional file to open with the app
    """
    app_lower = app_name.lower()

    # Check if it's a common app
    if app_lower in COMMON_APPS:
        launch_cmd = COMMON_APPS[app_lower]
    else:
        # Try to find it
        launch_cmd = app_name

    try:
        if file_to_open:
            # Open file with app
            cmd = f"Start-Process '{launch_cmd}' -ArgumentList '{file_to_open}'"
        elif launch_cmd.startswith("ms-"):
            # Windows URI scheme
            cmd = f"Start-Process '{launch_cmd}'"
        else:
            cmd = f"Start-Process '{launch_cmd}'"

        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode == 0 or not result.stderr:
            return json.dumps({
                "success": True,
                "launched": app_name,
                "message": f"Launched {app_name}"
            })
        else:
            return json.dumps({
                "success": False,
                "error": result.stderr,
                "suggestion": "Try the full application name or check if it's installed"
            })

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def close_app(app_name: str, force: bool = False) -> str:
    """
    Close an application.

    Args:
        app_name: Name of the application to close
        force: If True, force close (may lose unsaved work)
    """
    app_lower = app_name.lower()

    # Map common names to process names
    process_names = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "msedge",
        "word": "WINWORD",
        "excel": "EXCEL",
        "notepad": "notepad",
        "firefox": "firefox",
        "teams": "Teams",
    }

    process_name = process_names.get(app_lower, app_name)

    try:
        # Check if running
        check_cmd = f"Get-Process -Name '{process_name}' -ErrorAction SilentlyContinue"
        result = subprocess.run(
            ["powershell.exe", "-Command", check_cmd],
            capture_output=True, text=True, timeout=10
        )

        if not result.stdout.strip():
            return json.dumps({
                "success": False,
                "message": f"{app_name} doesn't appear to be running"
            })

        # Close it
        if force:
            cmd = f"Stop-Process -Name '{process_name}' -Force"
        else:
            cmd = f"Get-Process -Name '{process_name}' | ForEach-Object {{ $_.CloseMainWindow() }}"

        subprocess.run(["powershell.exe", "-Command", cmd], timeout=15)

        return json.dumps({
            "success": True,
            "closed": app_name,
            "forced": force,
            "message": f"Closed {app_name}" + (" (forced)" if force else "")
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_running_apps() -> str:
    """
    Get list of applications currently running.
    Shows name and memory usage for each.
    """
    try:
        cmd = """
        Get-Process | Where-Object {$_.MainWindowTitle -ne ''} |
        Select-Object ProcessName, @{N='Window';E={$_.MainWindowTitle}},
            @{N='Memory_MB';E={[math]::Round($_.WorkingSet64/1MB, 0)}} |
        Sort-Object Memory_MB -Descending |
        ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            output = '[' + output[output.index('{'):] + ']'
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def switch_to_app(app_name: str) -> str:
    """
    Bring an application window to the front.

    Args:
        app_name: Name of the application to switch to
    """
    app_lower = app_name.lower()
    process_names = {
        "chrome": "chrome",
        "edge": "msedge",
        "word": "WINWORD",
        "excel": "EXCEL",
    }
    process_name = process_names.get(app_lower, app_name)

    try:
        cmd = f"""
        $app = Get-Process -Name '{process_name}' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($app) {{
            $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
            Add-Type -MemberDefinition $sig -Name Win32 -Namespace Native
            [Native.Win32]::SetForegroundWindow($app.MainWindowHandle)
            'success'
        }} else {{
            'not_found'
        }}
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )

        if 'success' in result.stdout:
            return json.dumps({
                "success": True,
                "message": f"Switched to {app_name}"
            })
        else:
            return json.dumps({
                "success": False,
                "message": f"{app_name} not found or not running"
            })

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_web(query: str, browser: str = "default") -> str:
    """
    Search the web for something.
    Opens browser with search results.

    Args:
        query: What to search for
        browser: Which browser to use (chrome, edge, firefox, or default)
    """
    import urllib.parse
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

    browser_map = {
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "firefox": "firefox.exe",
        "default": "start"
    }

    browser_cmd = browser_map.get(browser.lower(), "start")

    try:
        if browser_cmd == "start":
            cmd = f"Start-Process '{search_url}'"
        else:
            cmd = f"Start-Process '{browser_cmd}' -ArgumentList '{search_url}'"

        subprocess.run(["powershell.exe", "-Command", cmd], timeout=10)

        return json.dumps({
            "success": True,
            "searched": query,
            "message": f"Searching for: {query}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def open_website(url: str, browser: str = "default") -> str:
    """
    Open a website in the browser.

    Args:
        url: Website address (can be just the name like "amazon" or full URL)
        browser: Which browser (chrome, edge, firefox, or default)
    """
    # Handle simple site names
    if not url.startswith(('http://', 'https://', 'www.')):
        common_sites = {
            "amazon": "https://www.amazon.com",
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "facebook": "https://www.facebook.com",
            "twitter": "https://www.twitter.com",
            "gmail": "https://mail.google.com",
            "netflix": "https://www.netflix.com",
            "reddit": "https://www.reddit.com",
        }
        url = common_sites.get(url.lower(), f"https://www.{url}.com")

    if not url.startswith('http'):
        url = 'https://' + url

    browser_map = {
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "firefox": "firefox.exe",
        "default": "start"
    }
    browser_cmd = browser_map.get(browser.lower(), "start")

    try:
        if browser_cmd == "start":
            cmd = f"Start-Process '{url}'"
        else:
            cmd = f"Start-Process '{browser_cmd}' -ArgumentList '{url}'"

        subprocess.run(["powershell.exe", "-Command", cmd], timeout=10)

        return json.dumps({
            "success": True,
            "opened": url,
            "message": f"Opened {url}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def take_screenshot(save_path: str = None) -> str:
    """
    Take a screenshot of the entire screen.
    Saves to Pictures folder by default.

    Args:
        save_path: Where to save (optional, defaults to Pictures folder)
    """
    from datetime import datetime

    if not save_path:
        # Default to Pictures folder
        pictures = subprocess.run(
            ["powershell.exe", "-Command", "[Environment]::GetFolderPath('MyPictures')"],
            capture_output=True, text=True
        ).stdout.strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(pictures, f"screenshot_{timestamp}.png")

    try:
        cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save('{save_path}')
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        subprocess.run(["powershell.exe", "-Command", cmd], timeout=15)

        return json.dumps({
            "success": True,
            "saved": save_path,
            "message": f"Screenshot saved to {os.path.basename(save_path)}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
