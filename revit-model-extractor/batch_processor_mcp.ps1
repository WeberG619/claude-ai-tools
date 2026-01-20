# Revit Model Batch Processor (MCP Version)
# Opens Revit models via MCP bridge, extracts data, and stores in database
# Designed to run overnight unattended - REQUIRES Revit to already be open

param(
    [string]$ModelListCsv = "D:\revit_models_list.csv",
    [string]$OutputDir = "D:\_CLAUDE-TOOLS\revit-model-extractor\extracted",
    [string]$LogFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\processing_log.txt",
    [int]$MaxModelsPerRun = 100,
    [int]$WaitAfterOpenSeconds = 30
)

# Initialize log
$startTime = Get-Date
"`n======================================" | Out-File $LogFile -Append
"Batch Processing Started: $startTime" | Out-File $LogFile -Append
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

    Log "  Opening via MCP: $FilePath"
    $result = Send-MCPRequest -Connection $Connection -Method "openProject" -Params @{filePath = $FilePath}

    if ($result.success) {
        Log "  Model opened: $($result.result.documentTitle)"
        Start-Sleep -Seconds $WaitAfterOpenSeconds
        return $true
    } else {
        Log "  ERROR opening model: $($result.error)"
        return $false
    }
}

function Close-RevitModel {
    param($Connection, [string]$DocumentTitle = "", [bool]$Save = $false)

    Log "  Closing model: $DocumentTitle..."
    # Note: Revit API cannot close the ACTIVE document directly
    # The workaround is to open the next document first, which makes it active
    # Then we can close the previous (now non-active) document
    $result = Send-MCPRequest -Connection $Connection -Method "closeProject" -Params @{documentTitle = $DocumentTitle; save = $Save}

    if ($result.success) {
        Log "  Model closed"
        return $true
    } else {
        # This is expected if trying to close active doc - just log and continue
        Log "  Note: $($result.error)"
        return $false
    }
}

function Close-NonActiveDocuments {
    param($Connection, [string]$KeepDocTitle)

    # Get all open documents
    $docs = Send-MCPRequest -Connection $Connection -Method "getOpenDocuments"
    if ($docs.result.documents) {
        foreach ($doc in $docs.result.documents) {
            if ($doc.title -ne $KeepDocTitle -and -not $doc.isActive) {
                Log "  Closing non-active: $($doc.title)"
                Send-MCPRequest -Connection $Connection -Method "closeProject" -Params @{documentTitle = $doc.title; save = $false}
            }
        }
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
    }

    # Get Project Info
    Log "    Getting project info..."
    $result = Send-MCPRequest -Connection $Connection -Method "getProjectInfo"
    if ($result.success -or $result.projectName) {
        $modelData.projectInfo = $result
    }

    # Get Levels
    Log "    Getting levels..."
    $result = Send-MCPRequest -Connection $Connection -Method "getLevels"
    if ($result.levels) {
        $modelData.levels = $result.levels
        Log "      Found $($result.levels.Count) levels"
    }

    # Get Wall Types
    Log "    Getting wall types..."
    $result = Send-MCPRequest -Connection $Connection -Method "getWallTypes"
    if ($result.wallTypes) {
        $modelData.wallTypes = $result.wallTypes
        Log "      Found $($result.wallTypes.Count) wall types"
    }

    # Get Walls
    Log "    Getting walls..."
    $result = Send-MCPRequest -Connection $Connection -Method "getWalls"
    if ($result.walls) {
        $modelData.walls = $result.walls
        Log "      Found $($result.wallCount) walls"
    }

    # Get Rooms
    Log "    Getting rooms..."
    $result = Send-MCPRequest -Connection $Connection -Method "getRooms"
    if ($result.rooms) {
        $modelData.rooms = $result.rooms
        Log "      Found $($result.rooms.Count) rooms"
    }

    # Get Doors
    Log "    Getting doors..."
    $result = Send-MCPRequest -Connection $Connection -Method "getDoors"
    if ($result.doors) {
        $modelData.doors = $result.doors
        Log "      Found $($result.doors.Count) doors"
    }

    # Get Windows
    Log "    Getting windows..."
    $result = Send-MCPRequest -Connection $Connection -Method "getWindows"
    if ($result.windows) {
        $modelData.windows = $result.windows
        Log "      Found $($result.windows.Count) windows"
    }

    return $modelData
}

function Get-FileHashQuick {
    param([string]$Path, [long]$Size)
    # Quick hash based on size + name for duplicate detection
    return "$Size-$(Split-Path $Path -Leaf)"
}

# =====================
# MAIN EXECUTION
# =====================

Log "Loading model list from: $ModelListCsv"

if (-not (Test-Path $ModelListCsv)) {
    Log "ERROR: Model list not found at $ModelListCsv"
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Load and dedupe model list
$allModels = Import-Csv $ModelListCsv
Log "Total files in list: $($allModels.Count)"

$uniqueModels = @{}
foreach ($model in $allModels) {
    $hash = Get-FileHashQuick -Path $model.FullName -Size $model.Length
    if (-not $uniqueModels.ContainsKey($hash)) {
        $uniqueModels[$hash] = $model
    }
}

$modelList = $uniqueModels.Values | Select-Object -First $MaxModelsPerRun
Log "Processing $($modelList.Count) unique models"

# Verify MCP connection
Log "Connecting to Revit MCP Bridge..."
$conn = Connect-MCP
if (-not $conn) {
    Log "ERROR: Could not connect to Revit MCP Bridge. Is Revit open?"
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
    Log "========== Model $processed of $($modelList.Count) =========="
    Log "File: $($model.FullName)"
    Log "Size: $($model.SizeMB) MB"

    try {
        # Reconnect if needed
        try {
            $testResult = Send-MCPRequest -Connection $conn -Method "ping"
        } catch {
            Log "  Reconnecting to MCP..."
            $conn.Pipe.Close()
            Start-Sleep -Seconds 2
            $conn = Connect-MCP
            if (-not $conn) {
                Log "  ERROR: Could not reconnect"
                $failed++
                continue
            }
        }

        # Open the model (this makes it the active document)
        if (Open-RevitModel -Connection $conn -FilePath $model.FullName) {
            # Get the current document title
            $currentDocResult = Send-MCPRequest -Connection $conn -Method "getOpenDocuments"
            $currentDocTitle = $currentDocResult.result.activeDocument

            # Close the PREVIOUS document (now non-active) if there was one
            if ($previousDocTitle -ne "" -and $previousDocTitle -ne $currentDocTitle) {
                Close-RevitModel -Connection $conn -DocumentTitle $previousDocTitle -Save $false
            }

            # Extract data from current model
            Log "  Extracting model data..."
            $data = Extract-ModelData -Connection $conn -FilePath $model.FullName

            # Generate output filename
            $safeName = [System.IO.Path]::GetFileNameWithoutExtension($model.FullName) -replace '[^\w\-]', '_'
            $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
            $outputFile = Join-Path $OutputDir "${safeName}_${timestamp}.json"

            # Save to JSON
            $data | ConvertTo-Json -Depth 20 | Out-File -FilePath $outputFile -Encoding UTF8

            Log "  SUCCESS: Data saved to $outputFile"
            $successful++

            # Remember this document for closing when we open the next one
            $previousDocTitle = $currentDocTitle

        } else {
            Log "  FAILED: Could not open model"
            $failed++
        }

    } catch {
        Log "  ERROR: Exception - $_"
        $failed++
    }

    # Small delay between models
    Start-Sleep -Seconds 5

    # Clean up any extra open documents to prevent memory issues
    if ($processed % 10 -eq 0) {
        Log "  Periodic cleanup: checking for extra open documents..."
        $docsResult = Send-MCPRequest -Connection $conn -Method "getOpenDocuments"
        $openCount = $docsResult.result.count
        if ($openCount -gt 2) {
            Log "  Found $openCount open documents, cleaning up..."
            Close-NonActiveDocuments -Connection $conn -KeepDocTitle $previousDocTitle
        }
    }
}

# Close connection
$conn.Pipe.Close()

# Summary
$endTime = Get-Date
$duration = $endTime - $startTime

Log ""
Log "======================================"
Log "Batch Processing Complete"
Log "======================================"
Log "Started: $startTime"
Log "Ended: $endTime"
Log "Duration: $duration"
Log "Processed: $processed models"
Log "Successful: $successful"
Log "Failed: $failed"
Log ""

# Speak summary
try {
    $summaryText = "Batch processing complete. Processed $processed models. $successful successful, $failed failed."
    & python "D:\_CLAUDE-TOOLS\voice-mcp\speak.py" $summaryText
} catch {
    # Voice summary optional
}
