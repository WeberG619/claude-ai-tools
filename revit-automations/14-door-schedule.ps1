# Door Schedule Export
# Exports door data with mark, type, dimensions, and location
# Usage: .\14-door-schedule.ps1 -Version 2026|2025 [-ExportCsv]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [switch]$ExportCsv
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
Write-Host "DOOR SCHEDULE EXPORT - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get doors
$doorsResponse = Invoke-RevitMCP -Method "getElements" -Params @{ category = "Doors" }
if (-not $doorsResponse.success) {
    Write-Host "ERROR: Failed to get doors" -ForegroundColor Red
    exit 1
}

$doors = $doorsResponse.result.elements
Write-Host "Found $($doors.Count) doors" -ForegroundColor Gray
Write-Host ""

# Group by level
$byLevel = @{}
foreach ($door in $doors) {
    $level = if ($door.level) { $door.level } else { "Unknown" }
    if (-not $byLevel.ContainsKey($level)) {
        $byLevel[$level] = @()
    }
    $byLevel[$level] += $door
}

Write-Host "DOOR SCHEDULE" -ForegroundColor Yellow
Write-Host "-" * 60

# Table header
Write-Host ""
Write-Host "  MARK     TYPE                           LEVEL" -ForegroundColor Gray
Write-Host "  ----     ----                           -----" -ForegroundColor Gray

$csvData = @()

foreach ($level in $byLevel.Keys | Sort-Object) {
    $levelDoors = $byLevel[$level] | Sort-Object { if ($_.mark) { $_.mark } else { $_.name } }

    foreach ($door in $levelDoors) {
        $mark = if ($door.mark) { $door.mark } elseif ($door.number) { $door.number } else { "---" }
        $typeName = if ($door.typeName) { $door.typeName } elseif ($door.type) { $door.type } elseif ($door.name) { $door.name } else { "Unknown" }

        # Truncate type name if too long
        if ($typeName.Length -gt 30) {
            $typeName = $typeName.Substring(0, 27) + "..."
        }

        Write-Host "  $($mark.PadRight(8)) $($typeName.PadRight(30)) $level" -ForegroundColor White

        $csvData += [PSCustomObject]@{
            Mark = $mark
            Type = $typeName
            Level = $level
            ID = $door.id
        }
    }
}

Write-Host ""
Write-Host "-" * 60

# Summary by type
$byType = @{}
foreach ($door in $doors) {
    $typeName = if ($door.typeName) { $door.typeName } elseif ($door.type) { $door.type } else { "Unknown" }
    if (-not $byType.ContainsKey($typeName)) {
        $byType[$typeName] = 0
    }
    $byType[$typeName]++
}

Write-Host ""
Write-Host "SUMMARY BY TYPE" -ForegroundColor Yellow
foreach ($entry in $byType.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10) {
    $count = $entry.Value.ToString().PadLeft(4)
    $name = if ($entry.Key.Length -gt 45) { $entry.Key.Substring(0, 42) + "..." } else { $entry.Key }
    Write-Host "  $count x  $name" -ForegroundColor White
}

if ($byType.Count -gt 10) {
    Write-Host "  ... and $($byType.Count - 10) more types" -ForegroundColor Gray
}

Write-Host ""
Write-Host "TOTAL: $($doors.Count) doors" -ForegroundColor Green

# Export to CSV if requested
if ($ExportCsv) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $csvPath = "D:\_CLAUDE-TOOLS\revit-automations\doors_$timestamp.csv"
    $csvData | Export-Csv -Path $csvPath -NoTypeInformation
    Write-Host ""
    Write-Host "Exported to: $csvPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
