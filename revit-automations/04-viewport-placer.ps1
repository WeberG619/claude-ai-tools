# Viewport Placement Helper
# Place views on sheets with standard positioning patterns
# Usage: .\04-viewport-placer.ps1 -Version 2026|2025 -SheetNumber "A1.0" -ViewIds @(123,456) [-Layout Grid|Stack|Single] [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [Parameter(Mandatory=$true)]
    [string]$SheetNumber,

    [Parameter(Mandatory=$true)]
    [int[]]$ViewIds,

    [ValidateSet("Grid", "Stack", "Single", "Row")]
    [string]$Layout = "Grid",

    [switch]$DryRun
)

$pipeName = "RevitMCPBridge$Version"

function Invoke-RevitMCP {
    param([string]$Method, [hashtable]$Params = @{})

    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.AutoFlush = $true

    $request = @{ method = $Method; params = $Params } | ConvertTo-Json -Compress -Depth 10
    $writer.WriteLine($request)
    $response = $reader.ReadLine() | ConvertFrom-Json
    $pipe.Close()

    return $response
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "VIEWPORT PLACEMENT HELPER - Revit $Version" -ForegroundColor Cyan
if ($DryRun) { Write-Host "[DRY RUN MODE - No changes will be made]" -ForegroundColor Yellow }
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Sheet bounds (ARCH D typical - from gotchas)
$sheetBounds = @{
    minX = 0.15   # Left margin
    maxX = 2.70   # Right edge
    minY = 0.12   # Bottom margin (above titleblock)
    maxY = 1.75   # Top edge
}

$usableWidth = $sheetBounds.maxX - $sheetBounds.minX
$usableHeight = $sheetBounds.maxY - $sheetBounds.minY

Write-Host "Target Sheet: $SheetNumber" -ForegroundColor White
Write-Host "Layout Mode:  $Layout" -ForegroundColor White
Write-Host "Views to Place: $($ViewIds.Count)" -ForegroundColor White
Write-Host ""

# Find sheet by number
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if (-not $sheetsResponse.success) {
    Write-Host "ERROR: Failed to get sheets" -ForegroundColor Red
    exit 1
}

$targetSheet = $sheetsResponse.result.sheets | Where-Object { $_.sheetNumber -eq $SheetNumber }
if (-not $targetSheet) {
    Write-Host "ERROR: Sheet $SheetNumber not found" -ForegroundColor Red
    exit 1
}

Write-Host "Found Sheet: $($targetSheet.sheetName) (ID: $($targetSheet.id))" -ForegroundColor Green
Write-Host "Current Views: $($targetSheet.viewCount)" -ForegroundColor Gray
Write-Host ""

# Calculate positions based on layout
$positions = @()
$count = $ViewIds.Count

switch ($Layout) {
    "Single" {
        # Center single view
        $positions += @{
            x = $sheetBounds.minX + ($usableWidth / 2)
            y = $sheetBounds.minY + ($usableHeight / 2)
        }
    }

    "Row" {
        # Horizontal row
        $spacing = $usableWidth / ($count + 1)
        for ($i = 0; $i -lt $count; $i++) {
            $positions += @{
                x = $sheetBounds.minX + ($spacing * ($i + 1))
                y = $sheetBounds.minY + ($usableHeight / 2)
            }
        }
    }

    "Stack" {
        # Vertical stack
        $spacing = $usableHeight / ($count + 1)
        for ($i = 0; $i -lt $count; $i++) {
            $positions += @{
                x = $sheetBounds.minX + ($usableWidth / 2)
                y = $sheetBounds.maxY - ($spacing * ($i + 1))
            }
        }
    }

    "Grid" {
        # Smart grid based on count
        $cols = [math]::Ceiling([math]::Sqrt($count))
        $rows = [math]::Ceiling($count / $cols)

        $colSpacing = $usableWidth / ($cols + 1)
        $rowSpacing = $usableHeight / ($rows + 1)

        $idx = 0
        for ($r = 0; $r -lt $rows; $r++) {
            for ($c = 0; $c -lt $cols; $c++) {
                if ($idx -ge $count) { break }
                $positions += @{
                    x = $sheetBounds.minX + ($colSpacing * ($c + 1))
                    y = $sheetBounds.maxY - ($rowSpacing * ($r + 1))
                }
                $idx++
            }
        }
    }
}

# Preview positions
Write-Host "PLANNED POSITIONS" -ForegroundColor Yellow
Write-Host "-" * 40
for ($i = 0; $i -lt $ViewIds.Count; $i++) {
    $viewId = $ViewIds[$i]
    $pos = $positions[$i]
    Write-Host "  View $viewId -> X: $([math]::Round($pos.x, 3)) ft, Y: $([math]::Round($pos.y, 3)) ft" -ForegroundColor White
}
Write-Host ""

# Place viewports
if (-not $DryRun) {
    Write-Host "PLACING VIEWPORTS" -ForegroundColor Yellow
    Write-Host "-" * 40

    $successCount = 0
    $errorCount = 0

    for ($i = 0; $i -lt $ViewIds.Count; $i++) {
        $viewId = $ViewIds[$i]
        $pos = $positions[$i]

        Write-Host "  Placing view $viewId..." -NoNewline

        $result = Invoke-RevitMCP -Method "placeViewOnSheet" -Params @{
            sheetId = $targetSheet.id
            viewId = $viewId
            location = @($pos.x, $pos.y)
        }

        if ($result.success) {
            Write-Host " OK (Viewport: $($result.result.viewportId))" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host " FAILED: $($result.error)" -ForegroundColor Red
            $errorCount++
        }

        # Delay between placements (from gotchas)
        Start-Sleep -Milliseconds 500
    }

    Write-Host ""
    Write-Host "SUMMARY" -ForegroundColor Yellow
    Write-Host "  Placed:  $successCount" -ForegroundColor Green
    Write-Host "  Failed:  $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
} else {
    Write-Host "This was a dry run. Run without -DryRun to place viewports." -ForegroundColor Cyan
}
