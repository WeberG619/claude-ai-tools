# Revit Dialog Close Button Clicker
# Uses Windows UI Automation to find and click Close/OK buttons properly
# Author: BIM Ops Studio

param(
    [int]$MaxAttempts = 20,
    [int]$DelayMs = 800,
    [int]$InitialDelayMs = 3000,
    [string[]]$ButtonNames = @("Close", "OK", "Yes", "Continue", "Accept"),
    [switch]$Quiet
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

# Win32 API for window detection
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class Win32Dialogs {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@

function Get-WindowTitle($hwnd) {
    $length = [Win32Dialogs]::GetWindowTextLength($hwnd)
    if ($length -eq 0) { return "" }
    $sb = New-Object System.Text.StringBuilder($length + 1)
    [Win32Dialogs]::GetWindowText($hwnd, $sb, $sb.Capacity) | Out-Null
    return $sb.ToString()
}

function Get-WindowProcessName($hwnd) {
    $processId = 0
    [Win32Dialogs]::GetWindowThreadProcessId($hwnd, [ref]$processId) | Out-Null
    try {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        return $proc.ProcessName
    } catch {
        return $null
    }
}

function Find-RevitDialogs {
    # Find all Revit process IDs
    $revitProcs = Get-Process -Name "*Revit*" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id
    if (-not $revitProcs) { return @() }

    $dialogs = @()

    # Use UI Automation to find all windows
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Window
    )

    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)

    foreach ($window in $windows) {
        try {
            $processId = $window.Current.ProcessId
            if ($processId -in $revitProcs) {
                $name = $window.Current.Name
                # Check if it looks like a dialog (not the main Revit window)
                $isMainWindow = $name -match "Autodesk Revit \d{4}" -and $name -notmatch "Error|Warning|Dialog"
                if (-not $isMainWindow -and $name) {
                    $dialogs += @{
                        Element = $window
                        Name = $name
                        ProcessId = $processId
                    }
                }
            }
        } catch {
            # Skip inaccessible windows
        }
    }

    return $dialogs
}

function Click-ButtonInWindow($windowElement, $buttonNames) {
    # Find buttons in the window
    $buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button
    )

    $buttons = $windowElement.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)

    # Try to find buttons in order of preference
    foreach ($targetName in $buttonNames) {
        foreach ($button in $buttons) {
            try {
                $btnName = $button.Current.Name
                if ($btnName -like "*$targetName*") {
                    # Found the button - click it
                    $invokePattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                    if ($invokePattern) {
                        $invokePattern.Invoke()
                        return @{ Success = $true; ButtonName = $btnName }
                    }
                }
            } catch {
                # Button might not support invoke pattern
            }
        }
    }

    # Fallback: try to find ANY clickable button
    foreach ($button in $buttons) {
        try {
            $btnName = $button.Current.Name
            $invokePattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            if ($invokePattern) {
                $invokePattern.Invoke()
                return @{ Success = $true; ButtonName = $btnName; Fallback = $true }
            }
        } catch {
            # Continue to next button
        }
    }

    return @{ Success = $false }
}

# Main execution
if (-not $Quiet) {
    Write-Host ""
    Write-Host "=== Revit Dialog Close Button Clicker ===" -ForegroundColor Cyan
    Write-Host "Looking for buttons: $($ButtonNames -join ', ')" -ForegroundColor Gray
    Write-Host "Waiting $($InitialDelayMs/1000)s for Revit dialogs..." -ForegroundColor Gray
    Write-Host ""
}

Start-Sleep -Milliseconds $InitialDelayMs

$dialogsClosed = 0
$consecutiveEmpty = 0
$maxEmpty = 3

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $dialogs = Find-RevitDialogs

    if ($dialogs.Count -eq 0) {
        $consecutiveEmpty++
        if (-not $Quiet) {
            Write-Host "  [CHECK $attempt] No Revit dialogs found" -ForegroundColor DarkGray
        }

        if ($consecutiveEmpty -ge $maxEmpty) {
            if (-not $Quiet) {
                Write-Host ""
                Write-Host "No more dialogs detected after $maxEmpty checks." -ForegroundColor Yellow
            }
            break
        }
    } else {
        $consecutiveEmpty = 0

        foreach ($dialog in $dialogs) {
            if (-not $Quiet) {
                Write-Host "  [FOUND] Dialog: $($dialog.Name)" -ForegroundColor Yellow
            }

            $result = Click-ButtonInWindow $dialog.Element $ButtonNames

            if ($result.Success) {
                $dialogsClosed++
                $msg = if ($result.Fallback) { "(fallback)" } else { "" }
                if (-not $Quiet) {
                    Write-Host "    [CLICKED] Button: $($result.ButtonName) $msg" -ForegroundColor Green
                }
            } else {
                if (-not $Quiet) {
                    Write-Host "    [FAILED] Could not click any button - trying Enter key" -ForegroundColor Red
                }
                # Fallback to Enter key
                [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
                $dialogsClosed++
            }
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

return $dialogsClosed
