# Quick View Capture
# Captures the current active view or a specific view to an image
# Usage: .\07-quick-capture.ps1 -Version 2026|2025 [-ViewId 123] [-OutputPath "D:\image.png"] [-Width 1920]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [int]$ViewId = 0,

    [string]$OutputPath = "",

    [int]$Width = 1920
)

$pipeName = "RevitMCPBridge$Version"

function Invoke-RevitMCP {
    param([string]$Method, [hashtable]$Params = @{})

    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.AutoFlush = $true

    $request = @{ method = $Method; params = $Params } | ConvertTo-Json -Compress
    $writer.WriteLine($request)
    $response = $reader.ReadLine() | ConvertFrom-Json
    $pipe.Close()

    return $response
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "QUICK VIEW CAPTURE - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Set default output path if not provided
if (-not $OutputPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputPath = "D:\_CLAUDE-TOOLS\revit-automations\capture_$timestamp.png"
}

Write-Host "Output: $OutputPath" -ForegroundColor Gray
Write-Host "Width:  $Width px" -ForegroundColor Gray
Write-Host ""

# Capture
$params = @{
    outputPath = $OutputPath
    width = $Width
}

if ($ViewId -gt 0) {
    $params.viewId = $ViewId
    Write-Host "Capturing view ID: $ViewId" -ForegroundColor White
} else {
    Write-Host "Capturing active view..." -ForegroundColor White
}

$result = Invoke-RevitMCP -Method "captureViewport" -Params $params

# Handle Revit's modified filename (from gotchas) - Revit appends view name
$dir = [System.IO.Path]::GetDirectoryName($OutputPath)
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($OutputPath)
$ext = [System.IO.Path]::GetExtension($OutputPath)

# Always check for file - API may report failure even when file was created
Start-Sleep -Milliseconds 500  # Brief wait for file system
$actualFiles = Get-ChildItem -Path $dir -Filter "$baseName*$ext" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-1) }

if ($actualFiles) {
    $actualPath = $actualFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Write-Host ""
    Write-Host "SUCCESS" -ForegroundColor Green
    Write-Host "  File: $($actualPath.FullName)" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($actualPath.Length / 1KB, 1)) KB" -ForegroundColor Gray
} elseif ($result.success) {
    Write-Host ""
    Write-Host "API reported success but file not found" -ForegroundColor Yellow
    Write-Host "Check: $dir" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "FAILED: $($result.error)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
