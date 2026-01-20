"""
Keyboard-based Autodesk Family Cloud loading.
Uses pure keyboard navigation which is more reliable than mouse clicks.
"""
import pyautogui
import time
import subprocess
import sys

def focus_revit():
    """Focus the Revit window using PowerShell"""
    ps = '''
$revit = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
if ($revit) {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class FW {
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
"@
    [FW]::ShowWindow($revit.MainWindowHandle, 9)
    [FW]::SetForegroundWindow($revit.MainWindowHandle)
    "OK"
}
'''
    result = subprocess.run(['powershell.exe', '-Command', ps], capture_output=True, text=True)
    return "OK" in result.stdout

def keyboard_to_load_autodesk_family():
    """Navigate using keyboard to Load Autodesk Family"""

    # Press Escape to clear any active state
    print("Pressing Escape to clear state...")
    pyautogui.press('escape')
    time.sleep(0.3)

    # Press Alt to activate ribbon key tips
    print("Pressing Alt to show key tips...")
    pyautogui.press('alt')
    time.sleep(1)

    # In Revit 2026, Insert tab key is typically 'N'
    print("Pressing 'N' for Insert tab...")
    pyautogui.press('n')
    time.sleep(0.8)

    # After Insert tab opens, we need the key for Load Autodesk Family
    # This might be 'LA' or we might need to press 'L' then 'A'
    print("Pressing 'L' for Load options...")
    pyautogui.press('l')
    time.sleep(0.5)

    # Check if we need 'A' for Autodesk
    print("Pressing 'A' for Autodesk...")
    pyautogui.press('a')
    time.sleep(2)

    print("Keyboard navigation complete")

def main():
    print("=" * 50)
    print("Keyboard-based Autodesk Family Loading")
    print("=" * 50)

    # Step 1: Focus Revit
    print("\n1. Focusing Revit...")
    if focus_revit():
        print("   Revit focused")
    else:
        print("   Warning: Could not confirm Revit focus")
    time.sleep(0.5)

    # Step 2: Keyboard navigation
    print("\n2. Using keyboard navigation...")
    keyboard_to_load_autodesk_family()

    print("\n" + "=" * 50)
    print("Done! Check Revit for the dialog.")
    print("=" * 50)

if __name__ == "__main__":
    main()
