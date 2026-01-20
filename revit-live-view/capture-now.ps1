# Quick one-time capture of Revit window(s)
# Usage: powershell -File capture-now.ps1

param(
    [string]$OutputFolder = "D:\"
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

# Find Revit processes
$revitProcesses = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
$captured = @()

if ($revitProcesses.Count -eq 0) {
    Write-Output '{"success":false,"error":"No Revit windows found"}'
    exit 1
}

$index = 0
foreach ($proc in $revitProcesses) {
    if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
        $index++

        if ($revitProcesses.Count -eq 1) {
            $outputPath = Join-Path $OutputFolder "revit_live_view.png"
        } else {
            $outputPath = Join-Path $OutputFolder "revit_live_view_$index.png"
        }

        try {
            $isMinimized = [Win32.WinAPI]::IsIconic($proc.MainWindowHandle)
            $isVisible = [Win32.WinAPI]::IsWindowVisible($proc.MainWindowHandle)

            if (-not $isMinimized -and $isVisible) {
                $success = Capture-Window -Handle $proc.MainWindowHandle -OutputPath $outputPath

                if ($success) {
                    $captured += @{
                        title = $proc.MainWindowTitle
                        file = $outputPath
                        process_id = $proc.Id
                    }
                }
            }
        } catch {
            Write-Host "Error: $_"
        }
    }
}

$result = @{
    success = $true
    captured_count = $captured.Count
    files = $captured
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
}

$result | ConvertTo-Json -Depth 3
