# Continuous Revit Model Processor
# Runs multiple batches back-to-back until all models are processed
# Designed for overnight unattended operation

param(
    [string]$ModelListCsv = "D:\revit_models_list.csv",
    [string]$OutputDir = "D:\_CLAUDE-TOOLS\revit-model-extractor\extracted",
    [string]$LogFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\continuous_log.txt",
    [string]$ProcessedFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\processed_models.txt",
    [int]$ModelsPerBatch = 50,
    [int]$TotalModelsToProcess = 200,
    [int]$WaitAfterOpenSeconds = 20
)

# Initialize log
$startTime = Get-Date
"`n======================================" | Out-File $LogFile -Append
"CONTINUOUS Processing Started: $startTime" | Out-File $LogFile -Append
"Target: $TotalModelsToProcess models" | Out-File $LogFile -Append
"======================================" | Out-File $LogFile -Append

function Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$timestamp - $Message" | Out-File $LogFile -Append
    Write-Host "$timestamp - $Message"
}

function Connect-MCP {
    try {
        $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
        $pipe.Connect(15000)
        $writer = New-Object System.IO.StreamWriter($pipe)
        $reader = New-Object System.IO.StreamReader($pipe)
        return @{
            Pipe = $pipe
            Writer = $writer
            Reader = $reader
        }
    } catch {
        return $null
    }
}

function Send-MCPRequest {
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

function Open-RevitModel {
    param($Connection, [string]$FilePath)
    Log "  Opening: $(Split-Path $FilePath -Leaf)"
    $result = Send-MCPRequest -Connection $Connection -Method "openProject" -Params @{filePath = $FilePath}
    if ($result.success) {
        Log "  Opened: $($result.result.documentTitle)"
        Start-Sleep -Seconds $WaitAfterOpenSeconds
        return $true
    } else {
        Log "  ERROR: $($result.error)"
        return $false
    }
}

function Extract-ModelData {
    param($Connection, [string]$FilePath)

    $modelData = @{
        extractedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        filePath = $FilePath
        fileName = [System.IO.Path]::GetFileName($FilePath)
        projectInfo = @{}
        levels = @()
        wallTypes = @()
        walls = @()
        rooms = @()
        doors = @()
        windows = @()
        floorTypes = @()
        ceilingTypes = @()
        doorTypes = @()
        windowTypes = @()
    }

    # Get Project Info
    $result = Send-MCPRequest -Connection $Connection -Method "getProjectInfo"
    if ($result.success -or $result.projectName) { $modelData.projectInfo = $result }

    # Get Levels
    $result = Send-MCPRequest -Connection $Connection -Method "getLevels"
    if ($result.levels) {
        $modelData.levels = $result.levels
        Log "    Levels: $($result.levels.Count)"
    }

    # Get Wall Types
    $result = Send-MCPRequest -Connection $Connection -Method "getWallTypes"
    if ($result.wallTypes) {
        $modelData.wallTypes = $result.wallTypes
        Log "    Wall types: $($result.wallTypes.Count)"
    }

    # Get Walls
    $result = Send-MCPRequest -Connection $Connection -Method "getWalls"
    if ($result.walls) {
        $modelData.walls = $result.walls
        Log "    Walls: $($result.wallCount)"
    }

    # Get Rooms
    $result = Send-MCPRequest -Connection $Connection -Method "getRooms"
    if ($result.rooms) {
        $modelData.rooms = $result.rooms
        Log "    Rooms: $($result.rooms.Count)"
    }

    # Get Doors
    $result = Send-MCPRequest -Connection $Connection -Method "getDoors"
    if ($result.doors) {
        $modelData.doors = $result.doors
        Log "    Doors: $($result.doors.Count)"
    }

    # Get Windows
    $result = Send-MCPRequest -Connection $Connection -Method "getWindows"
    if ($result.windows) {
        $modelData.windows = $result.windows
        Log "    Windows: $($result.windows.Count)"
    }

    return $modelData
}

function Get-FileHashQuick {
    param([string]$Path, [long]$Size)
    return "$Size-$(Split-Path $Path -Leaf)"
}

# =====================
# MAIN EXECUTION
# =====================

Log "Loading model list from: $ModelListCsv"

if (-not (Test-Path $ModelListCsv)) {
    Log "ERROR: Model list not found"
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Load already processed models
$processedModels = @{}
if (Test-Path $ProcessedFile) {
    Get-Content $ProcessedFile | ForEach-Object { $processedModels[$_] = $true }
    Log "Already processed: $($processedModels.Count) models"
}

# Load and dedupe model list
$allModels = Import-Csv $ModelListCsv
Log "Total files in CSV: $($allModels.Count)"

# Filter out already processed and dedupe
$uniqueModels = @{}
foreach ($model in $allModels) {
    $hash = Get-FileHashQuick -Path $model.FullName -Size $model.Length
    if (-not $uniqueModels.ContainsKey($hash) -and -not $processedModels.ContainsKey($model.FullName)) {
        $uniqueModels[$hash] = $model
    }
}

$modelList = $uniqueModels.Values | Select-Object -First $TotalModelsToProcess
Log "Models to process this run: $($modelList.Count)"

if ($modelList.Count -eq 0) {
    Log "No new models to process!"
    exit 0
}

# Verify MCP connection
Log "Connecting to Revit MCP Bridge..."
$conn = Connect-MCP
if (-not $conn) {
    Log "ERROR: Could not connect to Revit MCP Bridge"
    exit 1
}
Log "MCP Bridge connected!"

# Track progress
$processed = 0
$successful = 0
$failed = 0
$previousDocTitle = ""

foreach ($model in $modelList) {
    $processed++
    Log ""
    Log "===== Model $processed of $($modelList.Count) ====="
    Log "File: $(Split-Path $model.FullName -Leaf)"
    Log "Size: $($model.SizeMB) MB"

    try {
        # Reconnect if needed
        try {
            $testResult = Send-MCPRequest -Connection $conn -Method "ping"
        } catch {
            Log "  Reconnecting..."
            $conn.Pipe.Close()
            Start-Sleep -Seconds 2
            $conn = Connect-MCP
            if (-not $conn) {
                Log "  ERROR: Reconnect failed"
                $failed++
                continue
            }
        }

        # Open the model
        if (Open-RevitModel -Connection $conn -FilePath $model.FullName) {
            # Get current doc title
            $currentDocResult = Send-MCPRequest -Connection $conn -Method "getOpenDocuments"
            $currentDocTitle = $currentDocResult.result.activeDocument

            # Close previous document if exists
            if ($previousDocTitle -ne "" -and $previousDocTitle -ne $currentDocTitle) {
                Send-MCPRequest -Connection $conn -Method "closeProject" -Params @{documentTitle = $previousDocTitle; save = $false} | Out-Null
            }

            # Extract data
            Log "  Extracting data..."
            $data = Extract-ModelData -Connection $conn -FilePath $model.FullName

            # Save to JSON
            $safeName = [System.IO.Path]::GetFileNameWithoutExtension($model.FullName) -replace '[^\w\-]', '_'
            $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
            $outputFile = Join-Path $OutputDir "${safeName}_${timestamp}.json"
            $data | ConvertTo-Json -Depth 20 | Out-File -FilePath $outputFile -Encoding UTF8

            Log "  SUCCESS: Saved to $outputFile"
            $successful++

            # Mark as processed
            $model.FullName | Out-File $ProcessedFile -Append
            $previousDocTitle = $currentDocTitle

        } else {
            Log "  FAILED: Could not open"
            $failed++
            # Still mark as processed to skip next time
            $model.FullName | Out-File $ProcessedFile -Append
        }

    } catch {
        Log "  ERROR: $_"
        $failed++
    }

    Start-Sleep -Seconds 3
}

# Close connection
$conn.Pipe.Close()

# Summary
$endTime = Get-Date
$duration = $endTime - $startTime

Log ""
Log "======================================"
Log "CONTINUOUS Processing Complete"
Log "======================================"
Log "Duration: $duration"
Log "Processed: $processed models"
Log "Successful: $successful"
Log "Failed: $failed"
Log ""

# Voice summary
try {
    $summaryText = "Continuous processing complete. $successful models extracted successfully. $failed failures."
    & python "D:\_CLAUDE-TOOLS\voice-mcp\speak.py" $summaryText
} catch {}
