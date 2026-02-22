Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinHelper {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    public static readonly IntPtr HWND_TOP = IntPtr.Zero;
}
"@

# Find and maximize Revit 2026
[WinHelper]::EnumWindows({
    param([IntPtr]$hWnd, [IntPtr]$lParam)
    if ([WinHelper]::IsWindowVisible($hWnd)) {
        $sb = New-Object System.Text.StringBuilder 256
        [WinHelper]::GetWindowText($hWnd, $sb, 256)
        $title = $sb.ToString()
        if ($title -like '*Revit 2026*') {
            Write-Host "Found: $title"
            # Move to left monitor (-2560,0) and make it full screen
            [WinHelper]::SetWindowPos($hWnd, [WinHelper]::HWND_TOP, -2560, 0, 2560, 1440, 0)
            [WinHelper]::SetForegroundWindow($hWnd)
            Write-Host "Positioned and focused Revit 2026 on left monitor"
        }
    }
    return $true
}, [IntPtr]::Zero)
