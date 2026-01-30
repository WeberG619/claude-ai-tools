# Smart Revit Startup Dialog Dismisser v2.0
# ENHANCED: Uses AppActivate to actively find and close dialogs
# Stops when no more dialogs are detected
# Author: BIM Ops Studio

param(
    [int]$MaxAttempts = 30,       # Maximum dialogs to try closing
    [int]$DelayMs = 500,          # Delay between attempts
    [int]$InitialDelayMs = 3000,  # Wait for Revit to show first dialog
    [switch]$Quiet                # Suppress output
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName Microsoft.VisualBasic

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;

public class Win32Dialog {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    public static List<IntPtr> FindWindowsByTitle(string[] patterns) {
        var results = new List<IntPtr>();
        EnumWindows((hWnd, lParam) => {
            if (IsWindowVisible(hWnd)) {
                int length = GetWindowTextLength(hWnd);
                if (length > 0) {
                    var sb = new StringBuilder(length + 1);
                    GetWindowText(hWnd, sb, sb.Capacity);
                    string title = sb.ToString();
                    foreach (string pattern in patterns) {
                        if (title.IndexOf(pattern, StringComparison.OrdinalIgnoreCase) >= 0) {
                            results.Add(hWnd);
                            break;
                        }
                    }
                }
            }
            return true;
        }, IntPtr.Zero);
        return results;
    }
}
"@

# Dialog title patterns to look for (Revit add-in dialogs)
$dialogPatterns = @(
    "RIACCA",
    "Code Compliance",
    "External Tools",
    "Add-In Manager",
    "AddIn",
    "Assistant loaded",
    "loaded successfully",
    "Configure",
    "Update Available",
    "License",
    "Warning",
    "Error Report",
    "Failed to load"
)

function Find-RevitDialogs {
    param([string[]]$Patterns)
    return [Win32Dialog]::FindWindowsByTitle($Patterns)
}

function Get-WindowTitle {
    param([IntPtr]$hwnd)
    $length = [Win32Dialog]::GetWindowTextLength($hwnd)
    $sb = New-Object System.Text.StringBuilder($length + 1)
    [Win32Dialog]::GetWindowText($hwnd, $sb, $sb.Capacity) | Out-Null
    return $sb.ToString()
}

function Close-DialogWindow {
    param([IntPtr]$hwnd, [string]$title)

    # Method 1: SetForegroundWindow + SendKeys
    [Win32Dialog]::ShowWindow($hwnd, 9)  # SW_RESTORE
    [Win32Dialog]::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 150
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    Start-Sleep -Milliseconds 100

    # Verify it closed
    $stillExists = [Win32Dialog]::IsWindowVisible($hwnd)
    if ($stillExists) {
        # Method 2: Try AppActivate
        try {
            [Microsoft.VisualBasic.Interaction]::AppActivate($title)
            Start-Sleep -Milliseconds 150
            [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
        } catch {
            # Ignore AppActivate failures
        }
    }

    return (-not [Win32Dialog]::IsWindowVisible($hwnd))
}

if (-not $Quiet) {
    Write-Host ""
    Write-Host "=== Smart Revit Dialog Dismisser v2.0 ===" -ForegroundColor Cyan
    Write-Host "Waiting $($InitialDelayMs/1000)s for Revit to start..." -ForegroundColor Gray
}

Start-Sleep -Milliseconds $InitialDelayMs

$dialogsClosed = 0
$noDialogRounds = 0
$maxNoDialogRounds = 5  # Stop after 5 rounds with no dialogs found

for ($round = 1; $round -le $MaxAttempts; $round++) {
    # Actively search for dialog windows
    $dialogs = Find-RevitDialogs -Patterns $dialogPatterns

    if ($dialogs.Count -gt 0) {
        $noDialogRounds = 0

        foreach ($hwnd in $dialogs) {
            $title = Get-WindowTitle -hwnd $hwnd

            if (-not $Quiet) {
                Write-Host "  [FOUND] $title" -ForegroundColor Yellow
            }

            $closed = Close-DialogWindow -hwnd $hwnd -title $title

            if ($closed) {
                $dialogsClosed++
                if (-not $Quiet) {
                    Write-Host "  [CLOSED] $title" -ForegroundColor Green
                }
            } else {
                if (-not $Quiet) {
                    Write-Host "  [RETRY] $title (will retry)" -ForegroundColor DarkYellow
                }
            }

            Start-Sleep -Milliseconds 200
        }
    } else {
        $noDialogRounds++
        if (-not $Quiet -and $round -gt 1) {
            Write-Host "  [SCAN] No dialogs found (round $round)" -ForegroundColor DarkGray
        }

        if ($noDialogRounds -ge $maxNoDialogRounds) {
            if (-not $Quiet) {
                Write-Host ""
                Write-Host "No more dialogs detected after $noDialogRounds scans." -ForegroundColor Yellow
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
