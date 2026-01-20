# Revit Live View Capture Daemon
# Captures screenshots of all open Revit windows periodically
# Saves to D:\revit_live_view.png (numbered for multiple instances)

param(
    [int]$IntervalSeconds = 5,
    [string]$OutputFolder = "D:\",
    [switch]$Silent
)

# Load required assemblies
Add-Type -AssemblyName System.Windows.Forms
[void][System.Reflection.Assembly]::LoadWithPartialName("System.Drawing")

# Define the Windows API functions
$signature = @"
[DllImport("user32.dll")]
public static extern IntPtr GetWindowRect(IntPtr hWnd, ref RECT rect);

[DllImport("user32.dll")]
public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

[DllImport("user32.dll")]
public static extern bool IsIconic(IntPtr hWnd);

[DllImport("user32.dll")]
public static extern bool IsWindowVisible(IntPtr hWnd);

[StructLayout(LayoutKind.Sequential)]
public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}
"@

Add-Type -MemberDefinition $signature -Name WinAPI -Namespace Win32 -ReferencedAssemblies System.Drawing

function Capture-Window {
    param([IntPtr]$Handle, [string]$OutputPath)

    try {
        $rect = New-Object Win32.WinAPI+RECT
        [Win32.WinAPI]::GetWindowRect($Handle, [ref]$rect) | Out-Null

        $width = $rect.Right - $rect.Left
        $height = $rect.Bottom - $rect.Top

        if ($width -le 0 -or $height -le 0) { return $false }

        $bitmap = New-Object System.Drawing.Bitmap($width, $height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $hdc = $graphics.GetHdc()

        # PrintWindow with PW_RENDERFULLCONTENT flag (2)
        [Win32.WinAPI]::PrintWindow($Handle, $hdc, 2) | Out-Null

        $graphics.ReleaseHdc($hdc)
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)

        $graphics.Dispose()
        $bitmap.Dispose()

        return $true
    }
    catch {
        return $false
    }
}

function Write-StatusFile {
    param(
        [array]$CapturedWindows,
        [string]$OutputFolder
    )

    $status = @{
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        captured_count = $CapturedWindows.Count
        windows = $CapturedWindows
        interval_seconds = $IntervalSeconds
        daemon_running = $true
    }

    $status | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $OutputFolder "revit_live_status.json")
}

# Banner
if (-not $Silent) {
    Write-Host "=========================================="
    Write-Host "  Revit Live View Capture Daemon"
    Write-Host "=========================================="
    Write-Host "Output folder: $OutputFolder"
    Write-Host "Capture interval: $IntervalSeconds seconds"
    Write-Host "Press Ctrl+C to stop"
    Write-Host ""
}

# Main loop
while ($true) {
    $revitProcesses = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
    $captured = @()

    if ($revitProcesses.Count -gt 0) {
        $index = 0

        foreach ($proc in $revitProcesses) {
            if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
                $index++

                # Determine output filename
                if ($revitProcesses.Count -eq 1) {
                    $outputPath = Join-Path $OutputFolder "revit_live_view.png"
                } else {
                    $outputPath = Join-Path $OutputFolder "revit_live_view_$index.png"
                }

                $isMinimized = [Win32.WinAPI]::IsIconic($proc.MainWindowHandle)
                $isVisible = [Win32.WinAPI]::IsWindowVisible($proc.MainWindowHandle)

                if (-not $isMinimized -and $isVisible) {
                    $success = Capture-Window -Handle $proc.MainWindowHandle -OutputPath $outputPath

                    if ($success) {
                        # Extract version from title
                        $version = "Unknown"
                        if ($proc.MainWindowTitle -match "Revit (\d{4})") {
                            $version = $matches[1]
                        }

                        $captured += @{
                            index = $index
                            version = $version
                            title = $proc.MainWindowTitle
                            file = $outputPath
                            process_id = $proc.Id
                            captured_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
                        }

                        if (-not $Silent) {
                            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Captured Revit $version -> $outputPath"
                        }
                    }
                }
            }
        }

        # Write status file
        Write-StatusFile -CapturedWindows $captured -OutputFolder $OutputFolder
    }
    else {
        if (-not $Silent) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] No Revit windows found..."
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
