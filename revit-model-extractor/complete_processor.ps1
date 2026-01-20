# Complete Revit Model Processor
# Extracts ALL model data for ML training - walls, roofs, floors, ceilings,
# stairs, furniture, fixtures, casework, MEP, structural, and more
# Designed for overnight unattended operation

param(
    [string]$ModelListCsv = "D:\revit_models_list.csv",
    [string]$OutputDir = "D:\_CLAUDE-TOOLS\revit-model-extractor\extracted_complete",
    [string]$LogFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\complete_processor_log.txt",
    [string]$ProcessedFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\processed_complete.txt",
    [int]$ModelsPerBatch = 100,
    [int]$TotalModelsToProcess = 500,
    [int]$WaitAfterOpenSeconds = 25
)

# Initialize log
$startTime = Get-Date
"`n======================================" | Out-File $LogFile -Append
"COMPLETE Model Extraction Started: $startTime" | Out-File $LogFile -Append
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
    try {
        $request = @{
            method = $Method
            params = $Params
        } | ConvertTo-Json -Compress -Depth 10
        $Connection.Writer.WriteLine($request)
        $Connection.Writer.Flush()
        $response = $Connection.Reader.ReadLine()
        if ($response) {
            return $response | ConvertFrom-Json
        }
        return $null
    } catch {
        Log "    ERROR in $Method : $_"
        return $null
    }
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

function Safe-Extract {
    param($Connection, [string]$Method, [string]$DisplayName, [hashtable]$Params = @{})
    try {
        $result = Send-MCPRequest -Connection $Connection -Method $Method -Params $Params
        if ($result) {
            return $result
        }
    } catch {
        Log "    WARN: $DisplayName extraction failed"
    }
    return $null
}

function Extract-CompleteModelData {
    param($Connection, [string]$FilePath)

    $modelData = @{
        extractedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        filePath = $FilePath
        fileName = [System.IO.Path]::GetFileName($FilePath)

        # Project info
        projectInfo = @{}

        # Levels and grids
        levels = @()
        grids = @()

        # ARCHITECTURAL ELEMENTS
        walls = @()
        wallTypes = @()
        doors = @()
        doorTypes = @()
        windows = @()
        windowTypes = @()
        floors = @()
        floorTypes = @()
        ceilings = @()
        ceilingTypes = @()
        roofs = @()
        roofTypes = @()
        stairs = @()
        railings = @()
        curtainWalls = @()
        rooms = @()

        # FURNITURE & FIXTURES
        furniture = @()
        plumbingFixtures = @()
        lightingFixtures = @()
        electricalFixtures = @()

        # STRUCTURAL
        columns = @()
        structuralBeams = @()
        structuralColumns = @()
        foundations = @()

        # MEP (if present)
        ducts = @()
        pipes = @()
        electricalCircuits = @()
        mepSystems = @()

        # FAMILIES & TYPES
        loadedFamilies = @()
        familyTypes = @()

        # MATERIALS
        materials = @()

        # VIEWS & SHEETS
        views = @()
        sheets = @()
        schedules = @()

        # METADATA
        phases = @()
        worksets = @()
        warnings = @()
    }

    $elementCount = 0

    # ===== PROJECT INFO =====
    Log "    Extracting project info..."
    $result = Safe-Extract -Connection $Connection -Method "getProjectInfo" -DisplayName "Project Info"
    if ($result) { $modelData.projectInfo = $result }

    # ===== LEVELS & GRIDS =====
    Log "    Extracting levels & grids..."
    $result = Safe-Extract -Connection $Connection -Method "getLevels" -DisplayName "Levels"
    if ($result.levels) {
        $modelData.levels = $result.levels
        Log "      Levels: $($result.levels.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getGrids" -DisplayName "Grids"
    if ($result.grids) {
        $modelData.grids = $result.grids
        Log "      Grids: $($result.grids.Count)"
    }

    # ===== WALLS =====
    Log "    Extracting walls..."
    $result = Safe-Extract -Connection $Connection -Method "getWallTypes" -DisplayName "Wall Types"
    if ($result.wallTypes) {
        $modelData.wallTypes = $result.wallTypes
        Log "      Wall types: $($result.wallTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getWalls" -DisplayName "Walls"
    if ($result.walls) {
        $modelData.walls = $result.walls
        $elementCount += $result.walls.Count
        Log "      Walls: $($result.wallCount)"
    }

    # ===== DOORS =====
    Log "    Extracting doors..."
    $result = Safe-Extract -Connection $Connection -Method "getDoorTypes" -DisplayName "Door Types"
    if ($result.doorTypes) {
        $modelData.doorTypes = $result.doorTypes
        Log "      Door types: $($result.doorTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getDoors" -DisplayName "Doors"
    if ($result.doors) {
        $modelData.doors = $result.doors
        $elementCount += $result.doors.Count
        Log "      Doors: $($result.doors.Count)"
    }

    # ===== WINDOWS =====
    Log "    Extracting windows..."
    $result = Safe-Extract -Connection $Connection -Method "getWindowTypes" -DisplayName "Window Types"
    if ($result.windowTypes) {
        $modelData.windowTypes = $result.windowTypes
        Log "      Window types: $($result.windowTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getWindows" -DisplayName "Windows"
    if ($result.windows) {
        $modelData.windows = $result.windows
        $elementCount += $result.windows.Count
        Log "      Windows: $($result.windows.Count)"
    }

    # ===== FLOORS =====
    Log "    Extracting floors..."
    $result = Safe-Extract -Connection $Connection -Method "getFloorTypes" -DisplayName "Floor Types"
    if ($result.floorTypes) {
        $modelData.floorTypes = $result.floorTypes
        Log "      Floor types: $($result.floorTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getFloors" -DisplayName "Floors"
    if ($result.floors) {
        $modelData.floors = $result.floors
        $elementCount += $result.floors.Count
        Log "      Floors: $($result.floors.Count)"
    }

    # ===== CEILINGS =====
    Log "    Extracting ceilings..."
    $result = Safe-Extract -Connection $Connection -Method "getCeilingTypes" -DisplayName "Ceiling Types"
    if ($result.ceilingTypes) {
        $modelData.ceilingTypes = $result.ceilingTypes
        Log "      Ceiling types: $($result.ceilingTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getCeilings" -DisplayName "Ceilings"
    if ($result.ceilings) {
        $modelData.ceilings = $result.ceilings
        $elementCount += $result.ceilings.Count
        Log "      Ceilings: $($result.ceilings.Count)"
    }

    # ===== ROOFS =====
    Log "    Extracting roofs..."
    $result = Safe-Extract -Connection $Connection -Method "getRoofTypes" -DisplayName "Roof Types"
    if ($result.roofTypes) {
        $modelData.roofTypes = $result.roofTypes
        Log "      Roof types: $($result.roofTypes.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getRoofs" -DisplayName "Roofs"
    if ($result.roofs) {
        $modelData.roofs = $result.roofs
        $elementCount += $result.roofs.Count
        Log "      Roofs: $($result.roofs.Count)"
    }

    # ===== STAIRS & RAILINGS =====
    Log "    Extracting stairs & railings..."
    $result = Safe-Extract -Connection $Connection -Method "getStairs" -DisplayName "Stairs"
    if ($result.stairs) {
        $modelData.stairs = $result.stairs
        $elementCount += $result.stairs.Count
        Log "      Stairs: $($result.stairs.Count)"
    }

    $result = Safe-Extract -Connection $Connection -Method "getRailings" -DisplayName "Railings"
    if ($result.railings) {
        $modelData.railings = $result.railings
        $elementCount += $result.railings.Count
        Log "      Railings: $($result.railings.Count)"
    }

    # ===== CURTAIN WALLS =====
    Log "    Extracting curtain walls..."
    $result = Safe-Extract -Connection $Connection -Method "getCurtainWalls" -DisplayName "Curtain Walls"
    if ($result.curtainWalls) {
        $modelData.curtainWalls = $result.curtainWalls
        $elementCount += $result.curtainWalls.Count
        Log "      Curtain walls: $($result.curtainWalls.Count)"
    }

    # ===== ROOMS =====
    Log "    Extracting rooms..."
    $result = Safe-Extract -Connection $Connection -Method "getRooms" -DisplayName "Rooms"
    if ($result.rooms) {
        $modelData.rooms = $result.rooms
        Log "      Rooms: $($result.rooms.Count)"
    }

    # ===== FURNITURE =====
    Log "    Extracting furniture..."
    $result = Safe-Extract -Connection $Connection -Method "getFurniture" -DisplayName "Furniture"
    if ($result.furniture) {
        $modelData.furniture = $result.furniture
        $elementCount += $result.furniture.Count
        Log "      Furniture: $($result.furniture.Count)"
    }

    # ===== PLUMBING FIXTURES =====
    Log "    Extracting plumbing fixtures..."
    $result = Safe-Extract -Connection $Connection -Method "getPlumbingFixtures" -DisplayName "Plumbing"
    if ($result.fixtures) {
        $modelData.plumbingFixtures = $result.fixtures
        $elementCount += $result.fixtures.Count
        Log "      Plumbing fixtures: $($result.fixtures.Count)"
    }

    # ===== LIGHTING FIXTURES =====
    Log "    Extracting lighting fixtures..."
    $result = Safe-Extract -Connection $Connection -Method "getLightingFixtures" -DisplayName "Lighting"
    if ($result.fixtures) {
        $modelData.lightingFixtures = $result.fixtures
        $elementCount += $result.fixtures.Count
        Log "      Lighting fixtures: $($result.fixtures.Count)"
    }

    # ===== ELECTRICAL FIXTURES =====
    Log "    Extracting electrical fixtures..."
    $result = Safe-Extract -Connection $Connection -Method "getElectricalFixtures" -DisplayName "Electrical"
    if ($result.fixtures) {
        $modelData.electricalFixtures = $result.fixtures
        $elementCount += $result.fixtures.Count
        Log "      Electrical fixtures: $($result.fixtures.Count)"
    }

    # ===== COLUMNS =====
    Log "    Extracting columns..."
    $result = Safe-Extract -Connection $Connection -Method "getColumns" -DisplayName "Columns"
    if ($result.columns) {
        $modelData.columns = $result.columns
        $elementCount += $result.columns.Count
        Log "      Columns: $($result.columns.Count)"
    }

    # ===== LOADED FAMILIES =====
    Log "    Extracting loaded families..."
    $result = Safe-Extract -Connection $Connection -Method "getLoadedFamilies" -DisplayName "Families"
    if ($result.families) {
        $modelData.loadedFamilies = $result.families
        Log "      Loaded families: $($result.families.Count)"
    }

    # ===== MATERIALS =====
    Log "    Extracting materials..."
    $result = Safe-Extract -Connection $Connection -Method "getAllMaterials" -DisplayName "Materials"
    if ($result.materials) {
        $modelData.materials = $result.materials
        Log "      Materials: $($result.materials.Count)"
    }

    # ===== VIEWS =====
    Log "    Extracting views..."
    $result = Safe-Extract -Connection $Connection -Method "getAllViews" -DisplayName "Views"
    if ($result.views) {
        $modelData.views = $result.views
        Log "      Views: $($result.views.Count)"
    }

    # ===== SHEETS =====
    Log "    Extracting sheets..."
    $result = Safe-Extract -Connection $Connection -Method "getAllSheets" -DisplayName "Sheets"
    if ($result.sheets) {
        $modelData.sheets = $result.sheets
        Log "      Sheets: $($result.sheets.Count)"
    }

    # ===== SCHEDULES =====
    Log "    Extracting schedules..."
    $result = Safe-Extract -Connection $Connection -Method "getAllSchedules" -DisplayName "Schedules"
    if ($result.schedules) {
        $modelData.schedules = $result.schedules
        Log "      Schedules: $($result.schedules.Count)"
    }

    # ===== PHASES =====
    Log "    Extracting phases..."
    $result = Safe-Extract -Connection $Connection -Method "getAllPhases" -DisplayName "Phases"
    if ($result.phases) {
        $modelData.phases = $result.phases
        Log "      Phases: $($result.phases.Count)"
    }

    # ===== WORKSETS =====
    Log "    Extracting worksets..."
    $result = Safe-Extract -Connection $Connection -Method "getAllWorksets" -DisplayName "Worksets"
    if ($result.worksets) {
        $modelData.worksets = $result.worksets
        Log "      Worksets: $($result.worksets.Count)"
    }

    # ===== WARNINGS =====
    Log "    Extracting warnings..."
    $result = Safe-Extract -Connection $Connection -Method "getProjectWarnings" -DisplayName "Warnings"
    if ($result.warnings) {
        $modelData.warnings = $result.warnings
        Log "      Warnings: $($result.warnings.Count)"
    }

    Log "    Total elements extracted: $elementCount"
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

            # Extract COMPLETE data
            Log "  Extracting COMPLETE model data..."
            $data = Extract-CompleteModelData -Connection $conn -FilePath $model.FullName

            # Save to JSON
            $safeName = [System.IO.Path]::GetFileNameWithoutExtension($model.FullName) -replace '[^\w\-]', '_'
            $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
            $outputFile = Join-Path $OutputDir "${safeName}_${timestamp}.json"
            $data | ConvertTo-Json -Depth 30 | Out-File -FilePath $outputFile -Encoding UTF8

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
Log "COMPLETE Extraction Finished"
Log "======================================"
Log "Duration: $duration"
Log "Processed: $processed models"
Log "Successful: $successful"
Log "Failed: $failed"
Log ""

# Voice summary
try {
    $summaryText = "Complete model extraction finished. $successful models extracted successfully with full element data. $failed failures."
    & python "D:\_CLAUDE-TOOLS\voice-mcp\speak.py" $summaryText
} catch {}
