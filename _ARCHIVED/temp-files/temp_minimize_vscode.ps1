Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinMin {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    public const int SW_MINIMIZE = 6;
    public const int SW_MAXIMIZE = 3;
}
"@

# Minimize all VS Code windows, maximize Revit
[WinMin]::EnumWindows({
    param([IntPtr]$hWnd, [IntPtr]$lParam)
    if ([WinMin]::IsWindowVisible($hWnd)) {
        $sb = New-Object System.Text.StringBuilder 256
        [WinMin]::GetWindowText($hWnd, $sb, 256)
        $title = $sb.ToString()
        if ($title -like '*Visual Studio Code*') {
            Write-Host "Minimizing VS Code: $title"
            [WinMin]::ShowWindow($hWnd, [WinMin]::SW_MINIMIZE)
        }
        if ($title -like '*Revit 2026*') {
            Write-Host "Maximizing Revit: $title"
            [WinMin]::ShowWindow($hWnd, [WinMin]::SW_MAXIMIZE)
            [WinMin]::SetForegroundWindow($hWnd)
        }
    }
    return $true
}, [IntPtr]::Zero)

Start-Sleep -Milliseconds 1000
