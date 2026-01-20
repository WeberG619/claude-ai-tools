# Smart Revit Startup Dialog Dismisser
# Detects and closes add-in startup dialogs intelligently
# Stops when no more dialogs are detected

param(
    [int]$MaxAttempts = 20,       # Maximum dialogs to try closing
    [int]$DelayMs = 600,          # Delay between attempts
    [int]$InitialDelayMs = 2000,  # Wait for Revit to show first dialog
    [switch]$Quiet                # Suppress output
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@

function Get-ForegroundWindowTitle {
    $hwnd = [Win32]::GetForegroundWindow()
    $length = [Win32]::GetWindowTextLength($hwnd)
    $sb = New-Object System.Text.StringBuilder($length + 1)
    [Win32]::GetWindowText($hwnd, $sb, $sb.Capacity) | Out-Null
    return $sb.ToString()
}

function Get-ForegroundWindowProcess {
    $hwnd = [Win32]::GetForegroundWindow()
    $processId = 0
    [Win32]::GetWindowThreadProcessId($hwnd, [ref]$processId) | Out-Null
    try {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        return $proc.ProcessName
    } catch {
        return "Unknown"
    }
}

function Is-RevitDialog {
    $title = Get-ForegroundWindowTitle
    $proc = Get-ForegroundWindowProcess

    # Check if foreground window belongs to Revit and looks like a dialog
    $isRevit = $proc -like "*Revit*"
    $isDialog = $title -match "External Tools|RIACCA|Code Compliance|Error|Warning|Failed|Loaded|Assistant|AddIn|Add-In|Configure|Update|License"

    return ($isRevit -and $isDialog)
}

if (-not $Quiet) {
    Write-Host ""
    Write-Host "=== Smart Revit Dialog Dismisser ===" -ForegroundColor Cyan
    Write-Host "Waiting $($InitialDelayMs/1000)s for Revit dialogs..." -ForegroundColor Gray
}

Start-Sleep -Milliseconds $InitialDelayMs

$dialogsClosed = 0
$noDialogCount = 0
$maxNoDialog = 3  # Stop after 3 consecutive non-dialog checks

for ($i = 1; $i -le $MaxAttempts; $i++) {
    $title = Get-ForegroundWindowTitle
    $proc = Get-ForegroundWindowProcess

    if (Is-RevitDialog) {
        # It's a Revit dialog - close it
        [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
        $dialogsClosed++
        $noDialogCount = 0

        if (-not $Quiet) {
            Write-Host "  [CLOSED] $title" -ForegroundColor Green
        }
    } else {
        $noDialogCount++
        if (-not $Quiet) {
            Write-Host "  [SKIP] Not a dialog: $title" -ForegroundColor DarkGray
        }

        # If we've seen non-dialogs multiple times, we're probably done
        if ($noDialogCount -ge $maxNoDialog) {
            if (-not $Quiet) {
                Write-Host ""
                Write-Host "No more dialogs detected." -ForegroundColor Yellow
            }
            break
        }
    }

    Start-Sleep -Milliseconds $DelayMs
}

if (-not $Quiet) {
    Write-Host ""
    Write-Host "=== Complete ===" -ForegroundColor Cyan
    Write-Host "Dialogs closed: $dialogsClosed" -ForegroundColor Green
    Write-Host ""
}

# Return count for programmatic use
return $dialogsClosed
