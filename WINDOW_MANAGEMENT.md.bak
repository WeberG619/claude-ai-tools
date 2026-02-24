# Window Management Guide
# Critical reference for multi-monitor DPI-aware window positioning

> **Created:** February 16, 2026
> **Problem solved:** Windows placed on wrong monitor due to DPI scaling mismatch

---

## MONITOR LAYOUT

Weber's 3-monitor setup (all 3840x2160 physical, 150% DPI scaling = 2560x1440 virtual):

```
┌──────────────┐┌──────────────┐┌──────────────┐
│   DISPLAY3   ││   DISPLAY2   ││   DISPLAY1   │
│    "left"    ││   "center"   ││   "right"    │
│  x = -5120   ││  x = -2560   ││   x = 0      │
│  w = 2560    ││  w = 2560    ││  w = 2560    │
│              ││              ││  (PRIMARY)   │
└──────────────┘└──────────────┘└──────────────┘
```

### Name Mapping

| System | Left Monitor | Center Monitor | Right Monitor |
|--------|-------------|----------------|---------------|
| Windows | DISPLAY3 | DISPLAY2 | DISPLAY1 (primary) |
| Screenshot tool | `monitor="left"` | `monitor="center"` | `monitor="right"` or `"primary"` |
| Virtual X range | -5120 to -2560 | -2560 to 0 | 0 to 2560 |
| Working height | 1400 | 1400 | 1400 |

**Weber's preferred demo monitor: CENTER** (DISPLAY2, x=-2560)

---

## THE DPI PROBLEM

**DPI scaling = 1.5x** means coordinates are interpreted differently depending on DPI awareness:

| Process DPI Awareness | Coordinate Interpretation | Result |
|-----------------------|--------------------------|--------|
| NOT DPI-aware (default) | Coordinates silently scaled by 1.5x | Window lands on WRONG monitor |
| DPI-aware | Coordinates used as-is (virtual) | Window lands CORRECTLY |

**Example:** `SetWindowPos(hwnd, 0, -2560, 0, 2560, 1400, 0)`
- Without DPI-aware: actually positions at -3840 (wrong monitor!)
- With DPI-aware: positions at -2560 (correct!)

---

## THE CORRECT PATTERN (USE THIS)

```powershell
powershell.exe -Command "& {
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinMgr {
    [DllImport(\"user32.dll\")]
    public static extern bool SetProcessDPIAware();

    [DllImport(\"user32.dll\", SetLastError=true)]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
        int X, int Y, int cx, int cy, uint uFlags);

    [DllImport(\"user32.dll\")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport(\"user32.dll\")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport(\"user32.dll\")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport(\"user32.dll\", SetLastError=true)]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport(\"user32.dll\")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport(\"user32.dll\")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static IntPtr FoundHwnd = IntPtr.Zero;
    public static string SearchTitle = \"\";

    public static bool EnumCb(IntPtr hWnd, IntPtr lParam) {
        if (!IsWindowVisible(hWnd)) return true;
        StringBuilder sb = new StringBuilder(256);
        GetWindowText(hWnd, sb, 256);
        if (sb.ToString().Contains(SearchTitle)) { FoundHwnd = hWnd; return false; }
        return true;
    }

    public static IntPtr FindWindow(string titleFragment) {
        FoundHwnd = IntPtr.Zero;
        SearchTitle = titleFragment;
        EnumWindows(EnumCb, IntPtr.Zero);
        return FoundHwnd;
    }
}
'@

# STEP 1: SET DPI AWARENESS (MUST be first!)
[WinMgr]::SetProcessDPIAware()

# STEP 2: FIND THE WINDOW
\$hwnd = [WinMgr]::FindWindow('Excel')  # Change to match target app

# STEP 3: RESTORE FROM MAXIMIZE (if maximized)
[WinMgr]::ShowWindow(\$hwnd, 1)  # SW_NORMAL
Start-Sleep -Milliseconds 300

# STEP 4: POSITION ON TARGET MONITOR (fill without maximize)
# For CENTER monitor: x=-2560, y=0, w=2560, h=1400
[WinMgr]::SetWindowPos(\$hwnd, [IntPtr]::Zero, -2560, 0, 2560, 1400, 0x0004)
Start-Sleep -Milliseconds 300

# STEP 5: BRING TO FRONT
[WinMgr]::SetForegroundWindow(\$hwnd)

# STEP 6: VERIFY
\$rect = New-Object WinMgr+RECT
[WinMgr]::GetWindowRect(\$hwnd, [ref]\$rect)
Write-Host \"Window: L=\$(\$rect.Left) R=\$(\$rect.Right) W=\$(\$rect.Right-\$rect.Left)\"
}"
```

### Monitor Coordinates Quick Reference

| Target Monitor | X | Y | Width | Height |
|---------------|---|---|-------|--------|
| Left (DISPLAY3) | -5120 | 0 | 2560 | 1400 |
| Center (DISPLAY2) | -2560 | 0 | 2560 | 1400 |
| Right/Primary (DISPLAY1) | 0 | 0 | 2560 | 1400 |

---

## CRITICAL RULES

### 1. ALWAYS call SetProcessDPIAware() FIRST
Before any SetWindowPos, GetWindowRect, or coordinate math. Without this, all coordinates are wrong by 1.5x.

### 2. NEVER use ShowWindow(SW_MAXIMIZE)
`ShowWindow(hwnd, 3)` (SW_MAXIMIZE) causes windows to span across multiple monitors. Instead, use `SetWindowPos` to fill the exact monitor dimensions. This gives the same visual result without spanning.

### 3. NEVER use mcp__windows-browser__window_move for precise positioning
The `window_move` MCP tool is NOT DPI-aware and does NOT reliably position windows on specific monitors. Always use the DPI-aware PowerShell pattern above.

### 4. ALWAYS verify with screenshot after positioning
```
mcp__windows-browser__browser_screenshot(monitor="center")
```
Check that:
- The full window is visible (title bar, all columns, status bar)
- No content is cut off on any edge
- The window is on the CORRECT monitor

### 5. FOCUS before sending keys
Before using `browser_send_keys`, always focus the target window first using `SetForegroundWindow`. Verify focus landed correctly by checking the screenshot — keys will go to whatever window has focus, which may NOT be the one you positioned.

---

## FOCUS MANAGEMENT PATTERN

```powershell
# Find and focus a window reliably
$hwnd = [WinMgr]::FindWindow('Excel')
[WinMgr]::ShowWindow($hwnd, 1)          # Restore if minimized
[WinMgr]::SetForegroundWindow($hwnd)      # Bring to front
Start-Sleep -Milliseconds 500             # Wait for focus
# NOW safe to send keys
```

**Always verify focus with a screenshot before sending keystrokes.**

---

## COMMON FAILURES AND FIXES

| Symptom | Cause | Fix |
|---------|-------|-----|
| Window on wrong monitor | No SetProcessDPIAware | Add DPI awareness call first |
| Window spans two monitors | Used SW_MAXIMIZE | Use SetWindowPos with exact dimensions instead |
| Only right half visible on center | Coordinates scaled by 1.5x | Ensure DPI-aware before SetWindowPos |
| Keys go to wrong window | Focus not set | SetForegroundWindow + sleep + verify |
| GetWindowRect returns wrong values | Not DPI-aware | Call SetProcessDPIAware before reading rect |
| window_move puts window in wrong place | MCP tool not DPI-aware | Use PowerShell pattern instead |

---

*Last Updated: 2026-02-16*
*Root cause: PowerShell processes are NOT DPI-aware by default. With 1.5x scaling, all Win32 coordinate APIs return/accept wrong values unless SetProcessDPIAware() is called first.*
