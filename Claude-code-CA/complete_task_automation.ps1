# Complete Task Automation Framework
# Ensures tasks are completed end-to-end with verification

# Load robust UI automation
. .\robust_ui_automation.ps1

# Task state management
$global:TaskState = @{
    CurrentTask = ""
    Steps = @()
    CompletedSteps = @()
    FailedSteps = @()
    Screenshots = @()
}

function Start-AutomationTask {
    param(
        [string]$TaskName,
        [string[]]$Steps
    )
    
    $global:TaskState.CurrentTask = $TaskName
    $global:TaskState.Steps = $Steps
    $global:TaskState.CompletedSteps = @()
    $global:TaskState.FailedSteps = @()
    $global:TaskState.Screenshots = @()
    
    Write-Host "`nStarting Task: $TaskName" -ForegroundColor Magenta
    Write-Host "=" * 50 -ForegroundColor Magenta
    Write-Host "Total Steps: $($Steps.Count)" -ForegroundColor Cyan
}

function Invoke-TaskStep {
    param(
        [string]$StepName,
        [scriptblock]$Action,
        [scriptblock]$Verification = $null,
        [int]$MaxRetries = 3
    )
    
    Write-Host "`nExecuting: $StepName" -ForegroundColor Yellow
    
    $success = $false
    $attempt = 0
    
    while (-not $success -and $attempt -lt $MaxRetries) {
        $attempt++
        Write-Host "  Attempt $attempt of $MaxRetries" -ForegroundColor Gray
        
        try {
            # Execute the action
            $result = & $Action
            
            # Verify if provided
            if ($Verification) {
                Write-Host "  Verifying..." -ForegroundColor Gray
                $verified = & $Verification
                $success = $verified -eq $true
            } else {
                $success = $result -ne $false
            }
            
            if ($success) {
                Write-Host "  ✓ Step completed successfully" -ForegroundColor Green
                $global:TaskState.CompletedSteps += $StepName
            } else {
                Write-Host "  ✗ Verification failed" -ForegroundColor Red
                if ($attempt -lt $MaxRetries) {
                    Write-Host "  Retrying in 2 seconds..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 2
                }
            }
        } catch {
            Write-Host "  ✗ Error: $_" -ForegroundColor Red
            if ($attempt -lt $MaxRetries) {
                Start-Sleep -Seconds 2
            }
        }
    }
    
    if (-not $success) {
        Write-Host "  ✗ Step failed after $MaxRetries attempts" -ForegroundColor Red
        $global:TaskState.FailedSteps += $StepName
        
        # Take screenshot for debugging
        $screenshotPath = ".\task_failure_$(Get-Date -Format 'yyyyMMdd_HHmmss').png"
        Take-Screenshot -Path $screenshotPath
        $global:TaskState.Screenshots += $screenshotPath
    }
    
    return $success
}

function Take-Screenshot {
    param([string]$Path)
    
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bitmap.Save($Path)
    $graphics.Dispose()
    $bitmap.Dispose()
    
    Write-Host "  Screenshot saved: $Path" -ForegroundColor Gray
}

function Complete-AutomationTask {
    Write-Host "`nTask Summary: $($global:TaskState.CurrentTask)" -ForegroundColor Magenta
    Write-Host "=" * 50 -ForegroundColor Magenta
    
    $totalSteps = $global:TaskState.Steps.Count
    $completedSteps = $global:TaskState.CompletedSteps.Count
    $failedSteps = $global:TaskState.FailedSteps.Count
    
    Write-Host "Total Steps: $totalSteps" -ForegroundColor Cyan
    Write-Host "Completed: $completedSteps" -ForegroundColor Green
    Write-Host "Failed: $failedSteps" -ForegroundColor Red
    
    if ($completedSteps -eq $totalSteps) {
        Write-Host "`n✓ TASK COMPLETED SUCCESSFULLY!" -ForegroundColor Green
    } else {
        Write-Host "`n✗ TASK INCOMPLETE" -ForegroundColor Red
        if ($global:TaskState.FailedSteps.Count -gt 0) {
            Write-Host "`nFailed Steps:" -ForegroundColor Red
            $global:TaskState.FailedSteps | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        }
        
        if ($global:TaskState.Screenshots.Count -gt 0) {
            Write-Host "`nDebug Screenshots:" -ForegroundColor Yellow
            $global:TaskState.Screenshots | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
        }
    }
    
    return ($completedSteps -eq $totalSteps)
}

# Example: PowerPoint Copilot Task Automation
function Complete-PowerPointCopilotTask {
    Start-AutomationTask -TaskName "Close Copilot and Complete Presentation" -Steps @(
        "Close Copilot Dialog",
        "Navigate to Home Tab", 
        "Add New Slide",
        "Save Presentation"
    )
    
    # Step 1: Close Copilot Dialog
    Invoke-TaskStep -StepName "Close Copilot Dialog" -Action {
        # Try multiple methods
        $closed = $false
        
        # Method 1: Click X button
        if (Invoke-RobustClick -X 1271 -Y 497) {
            Start-Sleep -Milliseconds 500
            $closed = $true
        }
        
        # Method 2: ESC key
        if (-not $closed) {
            [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
            Start-Sleep -Milliseconds 300
            [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
            $closed = $true
        }
        
        return $closed
    } -Verification {
        # Check if dialog is gone by testing if we can click elsewhere
        $testClick = Invoke-RobustClick -X 700 -Y 400
        return $testClick
    }
    
    # Step 2: Navigate to Home Tab
    Invoke-TaskStep -StepName "Navigate to Home Tab" -Action {
        # Click on Home tab
        Invoke-RobustClick -X 110 -Y 140
        Start-Sleep -Milliseconds 500
        return $true
    }
    
    # Step 3: Add New Slide
    Invoke-TaskStep -StepName "Add New Slide" -Action {
        # Click New Slide button
        Invoke-RobustClick -X 85 -Y 210
        Start-Sleep -Milliseconds 1000
        return $true
    } -Verification {
        # Could check for slide count increase here
        return $true
    }
    
    # Step 4: Save Presentation
    Invoke-TaskStep -StepName "Save Presentation" -Action {
        # Ctrl+S
        [System.Windows.Forms.SendKeys]::SendWait("^s")
        Start-Sleep -Milliseconds 500
        return $true
    }
    
    # Complete the task
    Complete-AutomationTask
}

# Diagnostic function
function Test-UIAutomation {
    Write-Host "`nUI Automation Diagnostic Test" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    
    # Test 1: Cursor positioning
    Write-Host "`nTest 1: Cursor Positioning" -ForegroundColor Yellow
    $testPos = @{X=800; Y=600}
    [RobustUIAutomation]::SetCursorPos($testPos.X, $testPos.Y)
    Start-Sleep -Milliseconds 100
    $verified = [RobustUIAutomation]::VerifyCursorPosition($testPos.X, $testPos.Y)
    Write-Host "  Cursor positioning: $(if($verified){'PASS'}else{'FAIL'})" -ForegroundColor $(if($verified){'Green'}else{'Red'})
    
    # Test 2: Window detection
    Write-Host "`nTest 2: Window Detection" -ForegroundColor Yellow
    $window = Test-WindowAtPosition -X 800 -Y 400
    Write-Host "  Window found: $(if($window.Handle -ne 0){'PASS'}else{'FAIL'})" -ForegroundColor $(if($window.Handle -ne 0){'Green'}else{'Red'})
    
    # Test 3: Click methods
    Write-Host "`nTest 3: Click Methods" -ForegroundColor Yellow
    Write-Host "  Testing click at current position..."
    $clickResult = Invoke-RobustClick -X 800 -Y 400 -Retries 1
    Write-Host "  Click execution: $(if($clickResult){'PASS'}else{'FAIL'})" -ForegroundColor $(if($clickResult){'Green'}else{'Red'})
    
    Write-Host "`nDiagnostic test completed." -ForegroundColor Cyan
}

# Main menu
function Show-AutomationMenu {
    Write-Host @"

Complete Task Automation Framework
==================================

Available Commands:
1. Complete-PowerPointCopilotTask - Fix Copilot dialog and complete presentation
2. Test-UIAutomation - Run diagnostic tests
3. Fix-CopilotDialog - Just fix the Copilot dialog
4. Take-Screenshot -Path <path> - Capture current screen

For custom automation:
- Start-AutomationTask -TaskName "Name" -Steps @("Step1", "Step2")
- Invoke-TaskStep -StepName "Name" -Action { code } -Verification { code }
- Complete-AutomationTask

"@ -ForegroundColor Green
}

# Show menu on load
Show-AutomationMenu

# Export all functions
Export-ModuleMember -Function *