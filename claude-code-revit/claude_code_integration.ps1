# Claude Code + Drop Zones Integration for Revit Development
# This script provides quick commands for your development workflow

# Global variables
$global:ClaudeCodeBase = "D:\claude-code-revit"
$global:RevitZones = "$ClaudeCodeBase\revit_zones"
$global:DevZones = "$ClaudeCodeBase\dev_zones"

# Function to drop files into zones
function Drop-Revit {
    param(
        [Parameter(Mandatory=$true)]
        [string]$File,
        
        [Parameter(Mandatory=$true)]
        [string]$Zone
    )
    
    $zones = @{
        "code" = "$RevitZones\code_generator"
        "error" = "$RevitZones\error_debugger"
        "test" = "$DevZones\test_generator"
        "doc" = "$DevZones\doc_builder"
        "api" = "$RevitZones\api_explorer"
    }
    
    if ($zones.ContainsKey($Zone)) {
        $destination = $zones[$Zone]
        Copy-Item $File -Destination $destination
        Write-Host "✓ Dropped $File into $Zone zone" -ForegroundColor Green
    } else {
        Write-Host "❌ Unknown zone: $Zone" -ForegroundColor Red
        Write-Host "Available zones: $($zones.Keys -join ', ')" -ForegroundColor Yellow
    }
}

# Quick command to create a new Revit tool request
function New-RevitTool {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Description
    )
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "tool_request_$timestamp.txt"
    $content = @"
Revit Tool Request
Created: $(Get-Date)

Description:
$Description

Requirements:
- Target Revit 2024
- Include error handling
- Add progress reporting
- Create ribbon button
- Include documentation

Please generate complete, working code.
"@
    
    $content | Out-File -FilePath $filename -Encoding UTF8
    Drop-Revit $filename "code"
    
    Write-Host "✓ Created and dropped tool request" -ForegroundColor Green
}

# Debug a Revit error quickly
function Debug-RevitError {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Error,
        
        [string]$Code = ""
    )
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "error_debug_$timestamp.txt"
    $content = @"
ERROR TO DEBUG
Time: $(Get-Date)

ERROR MESSAGE:
$Error

RELEVANT CODE:
$Code

REVIT VERSION: 2024
Need: Fixed code with explanation
"@
    
    $content | Out-File -FilePath $filename -Encoding UTF8
    Drop-Revit $filename "error"
    
    Write-Host "✓ Submitted error for debugging" -ForegroundColor Green
}

# Generate tests for existing code
function Generate-RevitTests {
    param(
        [Parameter(Mandatory=$true)]
        [string]$CodeFile
    )
    
    if (Test-Path $CodeFile) {
        Drop-Revit $CodeFile "test"
        Write-Host "✓ Submitted code for test generation" -ForegroundColor Green
    } else {
        Write-Host "❌ File not found: $CodeFile" -ForegroundColor Red
    }
}

# Create documentation for your add-in
function Build-RevitDocs {
    param(
        [Parameter(Mandatory=$true)]
        [string]$CodeFile
    )
    
    if (Test-Path $CodeFile) {
        Drop-Revit $CodeFile "doc"
        Write-Host "✓ Submitted code for documentation" -ForegroundColor Green
    } else {
        Write-Host "❌ File not found: $CodeFile" -ForegroundColor Red
    }
}

# Show available commands
function Show-RevitCommands {
    Write-Host ""
    Write-Host "🚀 Claude Code + Revit Commands:" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "New-RevitTool 'description'" -ForegroundColor Yellow
    Write-Host "  Create a new tool request" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Debug-RevitError 'error message' -Code 'code snippet'" -ForegroundColor Yellow
    Write-Host "  Debug a Revit API error" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Generate-RevitTests 'MyCommand.cs'" -ForegroundColor Yellow
    Write-Host "  Generate unit tests for your code" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Build-RevitDocs 'MyAddin.cs'" -ForegroundColor Yellow
    Write-Host "  Create documentation for your add-in" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Drop-Revit 'file.txt' 'zone'" -ForegroundColor Yellow
    Write-Host "  Drop any file into a specific zone" -ForegroundColor Gray
    Write-Host ""
}

# Initialize
Write-Host "✨ Claude Code + Revit Drop Zones Loaded!" -ForegroundColor Green
Write-Host "Type 'Show-RevitCommands' to see available commands" -ForegroundColor Cyan

# Set alias for quick access
Set-Alias -Name revit -Value Show-RevitCommands
