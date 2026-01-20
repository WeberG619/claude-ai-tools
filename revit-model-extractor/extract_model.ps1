# Revit Model Data Extractor
# This script extracts all data from the currently open Revit model
# and sends it to Claude for database storage

param(
    [string]$ModelPath = "",
    [string]$OutputDir = "D:\_CLAUDE-TOOLS\revit-model-extractor\extracted"
)

# Create output directory if needed
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

function Connect-RevitMCP {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
    try {
        $pipe.Connect(10000)
        $writer = New-Object System.IO.StreamWriter($pipe)
        $reader = New-Object System.IO.StreamReader($pipe)
        return @{
            Pipe = $pipe
            Writer = $writer
            Reader = $reader
        }
    } catch {
        Write-Host "ERROR: Could not connect to Revit MCP Bridge. Is Revit open with the add-in loaded?"
        return $null
    }
}

function Send-Request {
    param($Connection, $Method, $Params = @{})

    $request = @{
        method = $Method
        params = $Params
    } | ConvertTo-Json -Compress -Depth 10

    $Connection.Writer.WriteLine($request)
    $Connection.Writer.Flush()
    $response = $Connection.Reader.ReadLine()
    return $response | ConvertFrom-Json
}

function Extract-ModelData {
    param($Connection)

    $modelData = @{
        extractedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        levels = @()
        walls = @()
        rooms = @()
        doors = @()
        windows = @()
        wallTypes = @()
        projectInfo = @{}
    }

    # Get Project Info
    Write-Host "  Extracting project info..."
    $result = Send-Request -Connection $Connection -Method "getProjectInfo"
    if ($result.success) {
        $modelData.projectInfo = $result
    }

    # Get Levels
    Write-Host "  Extracting levels..."
    $result = Send-Request -Connection $Connection -Method "getLevels"
    if ($result.success -or $result.levels) {
        $modelData.levels = $result.levels
        Write-Host "    Found $($result.levels.Count) levels"
    }

    # Get Wall Types
    Write-Host "  Extracting wall types..."
    $result = Send-Request -Connection $Connection -Method "getWallTypes"
    if ($result.success -or $result.wallTypes) {
        $modelData.wallTypes = $result.wallTypes
        Write-Host "    Found $($result.wallTypes.Count) wall types"
    }

    # Get Walls
    Write-Host "  Extracting walls..."
    $result = Send-Request -Connection $Connection -Method "getWalls"
    if ($result.success -or $result.walls) {
        $modelData.walls = $result.walls
        Write-Host "    Found $($result.wallCount) walls"
    }

    # Get Rooms
    Write-Host "  Extracting rooms..."
    $result = Send-Request -Connection $Connection -Method "getRooms"
    if ($result.success -or $result.rooms) {
        $modelData.rooms = $result.rooms
        Write-Host "    Found $($result.rooms.Count) rooms"
    }

    # Get Doors
    Write-Host "  Extracting doors..."
    $result = Send-Request -Connection $Connection -Method "getDoors"
    if ($result.success -or $result.doors) {
        $modelData.doors = $result.doors
        Write-Host "    Found $($result.doors.Count) doors"
    }

    # Get Windows
    Write-Host "  Extracting windows..."
    $result = Send-Request -Connection $Connection -Method "getWindows"
    if ($result.success -or $result.windows) {
        $modelData.windows = $result.windows
        Write-Host "    Found $($result.windows.Count) windows"
    }

    return $modelData
}

# Main execution
Write-Host "========================================"
Write-Host "Revit Model Data Extractor"
Write-Host "========================================"
Write-Host ""

# Connect to Revit
Write-Host "Connecting to Revit MCP Bridge..."
$conn = Connect-RevitMCP
if (-not $conn) {
    exit 1
}

Write-Host "Connected successfully!"
Write-Host ""

# Extract data
Write-Host "Extracting model data..."
$data = Extract-ModelData -Connection $conn

# Generate output filename based on timestamp
$timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outputFile = Join-Path $OutputDir "model_extract_$timestamp.json"

# Save to JSON
Write-Host ""
Write-Host "Saving to $outputFile..."
$data | ConvertTo-Json -Depth 20 | Out-File -FilePath $outputFile -Encoding UTF8

Write-Host ""
Write-Host "Extraction complete!"
Write-Host "  Levels: $($data.levels.Count)"
Write-Host "  Walls: $($data.walls.Count)"
Write-Host "  Rooms: $($data.rooms.Count)"
Write-Host "  Doors: $($data.doors.Count)"
Write-Host "  Windows: $($data.windows.Count)"
Write-Host ""
Write-Host "Data saved to: $outputFile"

# Close connection
$conn.Pipe.Close()

# Return output file path for further processing
return $outputFile
