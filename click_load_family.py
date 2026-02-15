"""Click Load Autodesk Family button"""
import pyautogui
import subprocess
import time
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

def get_revit_rect():
    ps = '''
$revit = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
if ($revit) {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class WRect {
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    }
    public struct RECT { public int Left, Top, Right, Bottom; }
"@
    $r = New-Object RECT
    [WRect]::GetWindowRect($revit.MainWindowHandle, [ref]$r) | Out-Null
    "$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)"
}
'''
    result = _run_ps(ps)
    parts = result.stdout.strip().split(',')
    if len(parts) == 4:
        return [int(p) for p in parts]
    return None

def focus_revit():
    ps = '''
$revit = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
if ($revit) {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class WFocus {
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
"@
    [WFocus]::ShowWindow($revit.MainWindowHandle, 9)
    [WFocus]::SetForegroundWindow($revit.MainWindowHandle)
    "OK"
}
'''
    result = _run_ps(ps)
    return "OK" in result.stdout

# Main
print("Focusing Revit...")
focus_revit()
time.sleep(0.3)

print("Getting Revit window rect...")
rect = get_revit_rect()
print(f"Revit rect: {rect}")

if rect:
    left, top, right, bottom = rect

    # Load Autodesk Family button position from screenshot analysis
    # It's in the Insert tab ribbon, about 168px from left and 80px from top
    btn_x = left + 168
    btn_y = top + 80

    print(f"Clicking at: ({btn_x}, {btn_y})")
    pyautogui.click(btn_x, btn_y)
    time.sleep(1)
    print("Clicked Load Autodesk Family button")
else:
    print("Could not get Revit window position")
