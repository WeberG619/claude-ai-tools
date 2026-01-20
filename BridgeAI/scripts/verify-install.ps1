# BridgeAI Installation Verification
# Run this to verify all components are working

param(
    [switch]$Verbose
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BridgeAI Installation Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BridgeAIPath = "D:\_CLAUDE-TOOLS\BridgeAI"
$passed = 0
$failed = 0

function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$Test
    )

    Write-Host "  Testing: $Name..." -NoNewline
    try {
        $result = & $Test
        if ($result) {
            Write-Host " PASS" -ForegroundColor Green
            $script:passed++
            return $true
        } else {
            Write-Host " FAIL" -ForegroundColor Red
            $script:failed++
            return $false
        }
    } catch {
        Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

# Core Dependencies
Write-Host "Core Dependencies:" -ForegroundColor Yellow
Test-Component "Node.js" { node --version 2>$null }
Test-Component "Python" { python --version 2>$null }
Test-Component "Claude Code" { claude --version 2>$null }
Test-Component "pip" { pip --version 2>$null }

Write-Host ""

# MCP Servers
Write-Host "MCP Servers:" -ForegroundColor Yellow
$servers = @(
    @{Name="System"; Path="$BridgeAIPath\mcp-servers\system\server.py"},
    @{Name="Print"; Path="$BridgeAIPath\mcp-servers\print\server.py"},
    @{Name="Files"; Path="$BridgeAIPath\mcp-servers\files\server.py"},
    @{Name="Apps"; Path="$BridgeAIPath\mcp-servers\apps\server.py"},
    @{Name="Voice"; Path="$BridgeAIPath\mcp-servers\voice\server.py"},
    @{Name="Memory"; Path="$BridgeAIPath\mcp-servers\memory\src\server.py"},
    @{Name="Browser"; Path="$BridgeAIPath\mcp-servers\browser\src\server.py"}
)

foreach ($server in $servers) {
    Test-Component $server.Name {
        Test-Path $server.Path
    }
}

Write-Host ""

# Configuration Files
Write-Host "Configuration:" -ForegroundColor Yellow
Test-Component "CLAUDE.md" { Test-Path "$BridgeAIPath\CLAUDE.md" }
Test-Component "Settings" { Test-Path "$BridgeAIPath\.claude\settings.json" }
Test-Component "User Guide" { Test-Path "$BridgeAIPath\docs\USER_GUIDE.md" }

Write-Host ""

# PowerShell Scripts
Write-Host "Scripts:" -ForegroundColor Yellow
Test-Component "System Diagnostics" {
    $result = & powershell.exe -ExecutionPolicy Bypass -File "$BridgeAIPath\scripts\system-diagnostics.ps1" -Check cpu 2>$null
    $result -match "usage_percent"
}
Test-Component "Launcher" { Test-Path "$BridgeAIPath\Start-BridgeAI.ps1" }

Write-Host ""

# Python Dependencies
Write-Host "Python Packages:" -ForegroundColor Yellow
Test-Component "mcp" { python -c "import mcp" 2>$null; $LASTEXITCODE -eq 0 }
Test-Component "fastmcp" { python -c "from mcp.server.fastmcp import FastMCP" 2>$null; $LASTEXITCODE -eq 0 }
Test-Component "edge-tts" { python -c "import edge_tts" 2>$null; $LASTEXITCODE -eq 0 }

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
$total = $passed + $failed
$percentage = [math]::Round(($passed / $total) * 100, 0)

if ($failed -eq 0) {
    Write-Host "  All $passed tests passed!" -ForegroundColor Green
    Write-Host "  BridgeAI is ready to use." -ForegroundColor Green
} else {
    Write-Host "  Passed: $passed / $total ($percentage%)" -ForegroundColor $(if ($percentage -ge 80) { "Yellow" } else { "Red" })
    Write-Host "  Failed: $failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Some components need attention." -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
