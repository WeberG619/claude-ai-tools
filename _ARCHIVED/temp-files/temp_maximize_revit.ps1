Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinMax {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    public const int SW_MAXIMIZE = 3;
}
"@

[WinMax]::EnumWindows({
    param([IntPtr]$hWnd, [IntPtr]$lParam)
    if ([WinMax]::IsWindowVisible($hWnd)) {
        $sb = New-Object System.Text.StringBuilder 256
        [WinMax]::GetWindowText($hWnd, $sb, 256)
        $title = $sb.ToString()
        if ($title -like '*Revit 2026*') {
            Write-Host "Maximizing: $title"
            [WinMax]::ShowWindow($hWnd, [WinMax]::SW_MAXIMIZE)
            [WinMax]::SetForegroundWindow($hWnd)
            Write-Host "Done"
        }
    }
    return $true
}, [IntPtr]::Zero)

Start-Sleep -Milliseconds 500
