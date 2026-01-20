# PowerPoint Copilot Dialog Fix Script
# Comprehensive solution for persistent dialog issues

# Load the robust automation system
. .\robust_ui_automation.ps1

function Fix-CopilotDialog {
    Write-Host "`nPowerPoint Copilot Dialog Fix" -ForegroundColor Magenta
    Write-Host "==============================" -ForegroundColor Magenta
    
    $success = $false
    
    # Strategy 1: Direct X button click with all methods
    Write-Host "`nStrategy 1: Clicking X button at (1271, 497)" -ForegroundColor Yellow
    for ($i = 1; $i -le 3; $i++) {
        Write-Host "  Attempt $i..." -ForegroundColor Gray
        $result = Invoke-RobustClick -X 1271 -Y 497 -Retries 2
        Start-Sleep -Milliseconds 500
        
        if ($result) {
            Write-Host "  Click registered!" -ForegroundColor Green
            $success = $true
            break
        }
    }
    
    # Strategy 2: Escape key variations
    if (-not $success) {
        Write-Host "`nStrategy 2: Escape key methods" -ForegroundColor Yellow
        
        # Method A: SendKeys
        Write-Host "  Method A: SendKeys ESC" -ForegroundColor Gray
        [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
        Start-Sleep -Milliseconds 300
        
        # Method B: Multiple ESC presses
        Write-Host "  Method B: Multiple ESC presses" -ForegroundColor Gray
        for ($i = 1; $i -le 3; $i++) {
            [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
            Start-Sleep -Milliseconds 100
        }
        
        # Method C: Alt+F4 for dialog
        Write-Host "  Method C: Alt+F4" -ForegroundColor Gray
        [System.Windows.Forms.SendKeys]::SendWait("%{F4}")
        Start-Sleep -Milliseconds 300
    }
    
    # Strategy 3: Click outside dialog
    if (-not $success) {
        Write-Host "`nStrategy 3: Click outside dialog area" -ForegroundColor Yellow
        
        # Click in multiple safe areas
        $safeAreas = @(
            @{X=400; Y=300},
            @{X=600; Y=200},
            @{X=200; Y=400}
        )
        
        foreach ($area in $safeAreas) {
            Write-Host "  Clicking at ($($area.X), $($area.Y))" -ForegroundColor Gray
            Invoke-RobustClick @area
            Start-Sleep -Milliseconds 200
            [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
            Start-Sleep -Milliseconds 200
        }
    }
    
    # Strategy 4: Window message approach
    if (-not $success) {
        Write-Host "`nStrategy 4: Direct window messages" -ForegroundColor Yellow
        Close-WindowAtPosition -X 1271 -Y 497
        Start-Sleep -Milliseconds 500
    }
    
    # Strategy 5: Focus main window and keyboard shortcuts
    if (-not $success) {
        Write-Host "`nStrategy 5: Focus main window" -ForegroundColor Yellow
        
        # Click on PowerPoint main area
        Write-Host "  Clicking main PowerPoint area" -ForegroundColor Gray
        Invoke-RobustClick -X 700 -Y 400
        Start-Sleep -Milliseconds 200
        
        # Try Ctrl+W (close current pane)
        Write-Host "  Sending Ctrl+W" -ForegroundColor Gray
        [System.Windows.Forms.SendKeys]::SendWait("^w")
        Start-Sleep -Milliseconds 300
    }
    
    # Strategy 6: UI Automation approach
    if (-not $success) {
        Write-Host "`nStrategy 6: UI Automation" -ForegroundColor Yellow
        try {
            Add-Type -AssemblyName UIAutomationClient
            $automation = [System.Windows.Automation.AutomationElement]::RootElement
            
            # Find PowerPoint window
            $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, "PowerPoint")
            $powerpoint = $automation.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
            
            if ($powerpoint) {
                # Look for close buttons
                $buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
                $buttons = $powerpoint.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
                
                foreach ($button in $buttons) {
                    if ($button.Current.Name -like "*Close*" -or $button.Current.Name -eq "X") {
                        Write-Host "  Found close button: $($button.Current.Name)" -ForegroundColor Gray
                        $invokePattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                        if ($invokePattern) {
                            $invokePattern.Invoke()
                            $success = $true
                            break
                        }
                    }
                }
            }
        } catch {
            Write-Host "  UI Automation failed: $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`nFix attempt completed. Verify if dialog is closed." -ForegroundColor Cyan
    return $success
}

function Test-AllCloseButtons {
    Write-Host "`nSearching for all close buttons in PowerPoint" -ForegroundColor Yellow
    
    # Common close button locations
    $closeButtonLocations = @(
        @{X=1271; Y=497; Name="Copilot X"},
        @{X=1895; Y=45; Name="PowerPoint X"},
        @{X=1850; Y=100; Name="Ribbon X"},
        @{X=1200; Y=100; Name="Dialog X"}
    )
    
    foreach ($location in $closeButtonLocations) {
        Write-Host "`nTesting: $($location.Name)" -ForegroundColor Cyan
        $window = Test-WindowAtPosition -X $location.X -Y $location.Y
        
        if ($window.IsVisible -and $window.IsEnabled) {
            Write-Host "  Found active window - attempting click" -ForegroundColor Green
            Invoke-RobustClick -X $location.X -Y $location.Y -Verify
            Start-Sleep -Milliseconds 500
        }
    }
}

# Main execution
Write-Host @"

PowerPoint Copilot Dialog Fix Tool
==================================

This tool will attempt multiple strategies to close the persistent Copilot dialog.

Commands:
- Fix-CopilotDialog : Run all fix strategies
- Test-AllCloseButtons : Test all common close button locations
- Test-CopilotDialog : Run diagnostic tests

"@ -ForegroundColor Cyan

# Auto-run the fix
$response = Read-Host "Run the fix now? (Y/N)"
if ($response -eq 'Y' -or $response -eq 'y') {
    Fix-CopilotDialog
}