# Desktop Automation Guide
# Load when doing desktop work: Excel, Bluebeam, browser, window positioning

> Created: February 23, 2026 (merged from kernel.md + WINDOW_MANAGEMENT.md)

---

## MONITOR LAYOUT

3 monitors, all 3840x2160 physical, 150% DPI scaling = 2560x1440 virtual:

```
+----------------+----------------+----------------+
|   DISPLAY3     |   DISPLAY2     |   DISPLAY1     |
|    "left"      |   "center"     |   "right"      |
|  x = -5120     |  x = -2560     |   x = 0        |
|  w = 2560      |  w = 2560      |  w = 2560      |
|                |                |  (PRIMARY)     |
+----------------+----------------+----------------+
```

| System | Left | Center | Right |
|--------|------|--------|-------|
| Windows | DISPLAY3 | DISPLAY2 | DISPLAY1 (primary) |
| Screenshot tool | `"left"` | `"center"` | `"right"` or `"primary"` |
| Virtual X range | -5120 to -2560 | -2560 to 0 | 0 to 2560 |

**Working height:** 1400 on all monitors
**Weber's preferred demo monitor:** CENTER (DISPLAY2, x=-2560)

---

## THE DPI PROBLEM

DPI scaling = 1.5x. Without `SetProcessDPIAware()`, all coordinates are silently scaled by 1.5x, landing windows on the WRONG monitor.

---

## WINDOW POSITIONING PATTERN

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

# STEP 4: POSITION ON TARGET MONITOR
# Left: x=-5120  |  Center: x=-2560  |  Right: x=0
[WinMgr]::SetWindowPos(\$hwnd, [IntPtr]::Zero, -2560, 0, 2560, 1400, 0x0004)
Start-Sleep -Milliseconds 300

# STEP 5: BRING TO FRONT
[WinMgr]::SetForegroundWindow(\$hwnd)

# STEP 6: VERIFY POSITION
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

## VERIFY LOOP (after EVERY desktop operation)

### 1. Screenshot the result
- Use `mcp__windows-browser__browser_screenshot` on the correct monitor
- Take BEFORE telling the user you're done

### 2. Inspect
- Is data visible? (scroll position matters)
- Charts positioned correctly, not overlapping?
- Formatting applied as intended?
- Any error dialogs or unexpected UI states?
- Window fits properly on target monitor?

### 3. Fix or Report
- Issues found: fix silently, re-screenshot
- Wrong view: navigate correctly first
- Only say "done" after final verification screenshot

**NEVER say "done" without a verification screenshot.**

---

## FOCUS MANAGEMENT

```powershell
$hwnd = [WinMgr]::FindWindow('Excel')
[WinMgr]::ShowWindow($hwnd, 1)          # Restore if minimized
[WinMgr]::SetForegroundWindow($hwnd)      # Bring to front
Start-Sleep -Milliseconds 500             # Wait for focus
# NOW safe to send keys
```

**Always verify focus with a screenshot before sending keystrokes.**

---

## COMMON GOTCHAS

| Symptom | Cause | Fix |
|---------|-------|-----|
| Window on wrong monitor | No SetProcessDPIAware | Add DPI awareness call first |
| Window spans two monitors | Used SW_MAXIMIZE | Use SetWindowPos with exact dims |
| Keys go to wrong window | Focus not set | SetForegroundWindow + sleep + verify |
| Excel data off-screen | View scrolled after chart | Navigate to A1 after chart creation |
| COM binding broken | Used Start-Process excel.exe | Use New-Object -ComObject Excel.Application |

---

## PROACTIVE VISUAL REASONING

When reviewing screenshots, scan for:
- Error dialogs, #REF/#VALUE errors, "Not Responding" states
- Blank cells, truncated text, overlapping elements
- Controls in wrong state, unexpected popups

When to take proactive screenshots:
- After user mentions an app is acting weird
- When switching to an idle app
- When Revit/Bluebeam operations take longer than expected
- At session start if desktop apps are open
