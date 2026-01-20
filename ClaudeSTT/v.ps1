# Simplified voice command script
param(
    [switch]$Execute,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Voice Command Tool
==================

Usage:
  .\v.ps1          - Get voice input as text
  .\v.ps1 -Execute - Get voice input and execute as command

Examples:
  `$name = .\v.ps1
  .\v.ps1 -Execute  # Say "get-childitem" to list files

Instructions:
  1. Run the command
  2. Say "Claude" to activate
  3. Speak your command
  4. Wait for processing

"@ -ForegroundColor Cyan
    return
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptPath "python\voice_cli.py"

# Show prompt
Write-Host "🎤 " -NoNewline -ForegroundColor Cyan
Write-Host "Say 'Claude' then your command..." -ForegroundColor Gray

# Get voice input (suppress Python output)
$result = & python $pythonScript 2>$null

if ($result -and $result.Trim()) {
    Write-Host "📝 " -NoNewline -ForegroundColor Green
    Write-Host $result -ForegroundColor White
    
    if ($Execute) {
        Write-Host "⚡ " -NoNewline -ForegroundColor Yellow
        Write-Host "Executing..." -ForegroundColor Gray
        
        try {
            # Try to execute the command
            Invoke-Expression $result
        }
        catch {
            # If that fails, try running it as a program
            try {
                $parts = $result -split ' '
                $cmd = $parts[0]
                $args = $parts[1..($parts.Length-1)]
                & $cmd $args
            }
            catch {
                Write-Host "❌ Error: $_" -ForegroundColor Red
            }
        }
    }
    
    return $result
}
else {
    Write-Host "⏱️  No command received (timeout or no speech detected)" -ForegroundColor Yellow
    return $null
}