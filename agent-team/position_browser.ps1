# Position Chrome window to fit in the dashboard's "Live View" area
# Run this after opening the dashboard and Chrome

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Window {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

# Find Chrome window
$chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1

if ($chrome) {
    # Dashboard layout: 280px left panel + main content + 320px right panel
    # For center monitor (starting at x=-2560 based on your setup)
    # Adjust these values based on your monitor setup

    $monitorX = -2560  # Center monitor X offset
    $leftPanelWidth = 280
    $rightPanelWidth = 320
    $headerHeight = 120  # Header + mode indicator

    # Calculate Chrome position to fit in the "Live View" area
    $chromeX = $monitorX + $leftPanelWidth
    $chromeY = $headerHeight
    $chromeWidth = 2560 - $leftPanelWidth - $rightPanelWidth  # ~1960px
    $chromeHeight = 1440 - $headerHeight - 40  # Leave some margin

    Write-Host "Positioning Chrome window..."
    Write-Host "Position: X=$chromeX, Y=$chromeY, W=$chromeWidth, H=$chromeHeight"

    [Window]::MoveWindow($chrome.MainWindowHandle, $chromeX, $chromeY, $chromeWidth, $chromeHeight, $true)
    [Window]::SetForegroundWindow($chrome.MainWindowHandle)

    Write-Host "Chrome positioned in Live View area!"
} else {
    Write-Host "Chrome not found. Please open Chrome first."
}
