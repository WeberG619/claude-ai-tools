# Revit Model Batch Processor
# Opens Revit models one by one, extracts data, and stores in database
# Designed to run overnight unattended

param(
    [string]$ModelListCsv = "D:\revit_models_list.csv",
    [string]$DatabasePath = "D:\_CLAUDE-TOOLS\revit-model-extractor\revit_models.db",
    [string]$LogFile = "D:\_CLAUDE-TOOLS\revit-model-extractor\processing_log.txt",
    [string]$RevitPath = "C:\Program Files\Autodesk\Revit 2026\Revit.exe",
    [int]$MaxModelsPerRun = 50,
    [int]$WaitAfterOpenSeconds = 60
)

# Initialize log
$startTime = Get-Date
"======================================" | Out-File $LogFile -Append
"Batch Processing Started: $startTime" | Out-File $LogFile -Append
"======================================" | Out-File $LogFile -Append

function Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$timestamp - $Message" | Out-File $LogFile -Append
    Write-Host "$timestamp - $Message"
}

function Get-FileHash-Quick {
    param([string]$Path, [long]$Size)
    # Quick hash based on size + first/last bytes for duplicate detection
    return "$Size-$(Split-Path $Path -Leaf)"
}

function Test-RevitRunning {
    $revit = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
    return $null -ne $revit
}

function Wait-ForRevitMCP {
    param([int]$TimeoutSeconds = 120)

    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
            $pipe.Connect(5000)
            $pipe.Close()
            return $true
        } catch {
            Start-Sleep -Seconds 5
            $elapsed += 5
        }
    }
    return $false
}

function Open-RevitModel {
    param([string]$ModelPath)

    Log "Opening model: $ModelPath"

    # Start Revit with the model
    Start-Process -FilePath $RevitPath -ArgumentList "`"$ModelPath`""

    # Wait for Revit to start and model to load
    Log "Waiting for Revit to start..."
    Start-Sleep -Seconds 30

    # Wait for MCP bridge to be available
    Log "Waiting for MCP Bridge..."
    if (Wait-ForRevitMCP -TimeoutSeconds 180) {
        Log "MCP Bridge connected!"
        Start-Sleep -Seconds $WaitAfterOpenSeconds  # Extra time for model to fully load
        return $true
    } else {
        Log "ERROR: MCP Bridge timeout"
        return $false
    }
}

function Close-Revit {
    Log "Closing Revit..."
    $revit = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
    if ($revit) {
        $revit | ForEach-Object { $_.CloseMainWindow() | Out-Null }
        Start-Sleep -Seconds 10

        # Force kill if still running
        $revit = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
        if ($revit) {
            $revit | Stop-Process -Force
            Start-Sleep -Seconds 5
        }
    }
    Log "Revit closed"
}

function Extract-CurrentModel {
    $extractScript = "D:\_CLAUDE-TOOLS\revit-model-extractor\extract_model.ps1"
    $result = & $extractScript
    return $result
}

# Main processing loop
Log "Loading model list from: $ModelListCsv"

if (-not (Test-Path $ModelListCsv)) {
    Log "ERROR: Model list not found at $ModelListCsv"
    exit 1
}

$models = Import-Csv $ModelListCsv

# Filter out duplicates by size+name hash
$uniqueModels = @{}
foreach ($model in $models) {
    $hash = Get-FileHash-Quick -Path $model.FullName -Size $model.Length
    if (-not $uniqueModels.ContainsKey($hash)) {
        $uniqueModels[$hash] = $model
    }
}

$modelList = $uniqueModels.Values | Select-Object -First $MaxModelsPerRun
Log "Processing $($modelList.Count) unique models (from $($models.Count) total files)"

# Track progress
$processed = 0
$successful = 0
$failed = 0

foreach ($model in $modelList) {
    $processed++
    Log ""
    Log "========== Model $processed of $($modelList.Count) =========="
    Log "File: $($model.FullName)"
    Log "Size: $($model.SizeMB) MB"

    try {
        # Close any existing Revit instance
        if (Test-RevitRunning) {
            Close-Revit
            Start-Sleep -Seconds 10
        }

        # Open the model
        if (Open-RevitModel -ModelPath $model.FullName) {
            # Extract data
            Log "Extracting model data..."
            $outputFile = Extract-CurrentModel

            if ($outputFile -and (Test-Path $outputFile)) {
                Log "SUCCESS: Data extracted to $outputFile"
                $successful++
            } else {
                Log "WARNING: Extraction may have failed"
                $failed++
            }
        } else {
            Log "ERROR: Failed to open model"
            $failed++
        }

    } catch {
        Log "ERROR: Exception - $_"
        $failed++
    }

    # Close Revit before next model
    Close-Revit
    Start-Sleep -Seconds 5
}

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
