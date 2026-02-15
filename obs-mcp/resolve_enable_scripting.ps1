# Enable external scripting in DaVinci Resolve via UI automation
# Opens Preferences and navigates to enable Local scripting

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
"@

# Focus Resolve
$resolve = Get-Process Resolve -ErrorAction SilentlyContinue
if (-not $resolve) {
    Write-Host "ERROR: DaVinci Resolve is not running"
    exit 1
}

Write-Host "Focusing DaVinci Resolve..."
[Win32]::SetForegroundWindow($resolve.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 1000

# Open Preferences with Ctrl+, (comma)
Write-Host "Opening Preferences (Ctrl+,)..."
[System.Windows.Forms.SendKeys]::SendWait("^{,}")
Start-Sleep -Milliseconds 3000

Write-Host "Preferences dialog should be open now."
Write-Host "Please check if the Preferences window appeared in DaVinci Resolve."
Write-Host "If it did, I'll need you to manually enable:"
Write-Host "  General > External scripting using > Local"
Write-Host ""
Write-Host "Then click Save."
