"""
Automated Family Loading from Autodesk Family Cloud
This script automates the process of loading families via Revit's UI.
"""
import pyautogui
import time
import subprocess
import sys

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def focus_revit():
    """Focus the Revit window"""
    ps_script = '''
    $revit = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revit) {
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32 {
            [DllImport("user32.dll")]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")]
            public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        }
"@
        [Win32]::ShowWindow($revit.MainWindowHandle, 9)  # SW_RESTORE
        [Win32]::SetForegroundWindow($revit.MainWindowHandle)
        Write-Output "Focused Revit"
    } else {
        Write-Output "Revit not found"
    }
    '''
    result = _run_ps(ps_script)
    print(result.stdout.strip())
    time.sleep(0.5)
    return "Focused Revit" in result.stdout

def get_revit_window_info():
    """Get Revit window position and size"""
    ps_script = '''
    $revit = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revit) {
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32Rect {
            [DllImport("user32.dll")]
            public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
        }
        public struct RECT {
            public int Left, Top, Right, Bottom;
        }
"@
        $rect = New-Object RECT
        [Win32Rect]::GetWindowRect($revit.MainWindowHandle, [ref]$rect) | Out-Null
        Write-Output "$($rect.Left),$($rect.Top),$($rect.Right),$($rect.Bottom)"
    }
    '''
    result = _run_ps(ps_script)
    coords = result.stdout.strip().split(',')
    if len(coords) == 4:
        return [int(c) for c in coords]
    return None

def navigate_to_insert_tab():
    """Navigate to Insert tab using keyboard"""
    print("Pressing Escape to clear any active state...")
    pyautogui.press('escape')
    time.sleep(0.3)

    print("Pressing Alt to activate ribbon key tips...")
    pyautogui.press('alt')
    time.sleep(0.8)

    # In Revit 2026, Insert tab is typically 'I' or 'N' depending on configuration
    # Let's try 'I' for Insert
    print("Pressing 'I' for Insert tab...")
    pyautogui.press('i')
    time.sleep(0.5)

def click_load_autodesk_family():
    """Click on Load Autodesk Family button"""
    # After Insert tab is active, we need to find and click Load Autodesk Family
    # The keyboard shortcut for this within Insert tab varies
    # Let's try pressing 'L' for Load, then look for Autodesk Family option
    print("Pressing 'L' for Load Family options...")
    pyautogui.press('l')
    time.sleep(0.5)

    # If a dropdown appears, we need to select Autodesk Family
    # Try pressing 'A' for Autodesk
    print("Looking for Autodesk Family option...")
    pyautogui.press('a')
    time.sleep(1)

def search_and_load_family(family_name):
    """Search for and load a family from Autodesk Family Cloud"""
    print(f"Searching for family: {family_name}")

    # Wait for search dialog to appear
    time.sleep(2)

    # Type the search term
    pyautogui.typewrite(family_name, interval=0.05)
    time.sleep(1)

    # Press Enter to search
    pyautogui.press('enter')
    time.sleep(2)

    print(f"Search initiated for: {family_name}")

def main():
    if len(sys.argv) < 2:
        family_name = "plaster"  # Default search term
    else:
        family_name = sys.argv[1]

    print("=" * 50)
    print("Automated Family Loading from Autodesk Family Cloud")
    print("=" * 50)

    # Step 1: Focus Revit
    print("\nStep 1: Focusing Revit...")
    if not focus_revit():
        print("ERROR: Could not focus Revit")
        return

    # Step 2: Get window info
    print("\nStep 2: Getting window info...")
    rect = get_revit_window_info()
    if rect:
        print(f"Revit window: {rect}")

    # Step 3: Navigate to Insert tab
    print("\nStep 3: Navigating to Insert tab...")
    navigate_to_insert_tab()

    # Step 4: Click Load Autodesk Family
    print("\nStep 4: Opening Load Autodesk Family...")
    click_load_autodesk_family()

    # Step 5: Search for family
    print(f"\nStep 5: Searching for '{family_name}'...")
    search_and_load_family(family_name)

    print("\n" + "=" * 50)
    print("Automation sequence complete!")
    print("Check Revit for the family search dialog.")
    print("=" * 50)

if __name__ == "__main__":
    main()
