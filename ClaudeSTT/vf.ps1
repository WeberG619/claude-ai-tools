# Flexible voice command script
param(
    [switch]$Execute,
    [switch]$Help,
    [switch]$Debug
)

if ($Help) {
    Write-Host @"
Flexible Voice Command Tool
===========================

This version uses improved wake word detection that recognizes:
- "Claude" (exact)
- Common mishearings: "cloud", "clod", "glad", etc.
- Phonetic variations

Usage:
  .\vf.ps1          - Get voice input as text
  .\vf.ps1 -Execute - Get voice input and execute as command
  .\vf.ps1 -Debug   - Debug wake word detection

Examples:
  `$name = .\vf.ps1
  .\vf.ps1 -Execute  # Say "Claude get-childitem"

Tips:
  - Speak clearly and close to microphone
  - Say "Claude" then pause briefly before your command
  - Try "Hey Claude" if "Claude" alone doesn't work

"@ -ForegroundColor Cyan
    return
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Debug) {
    # Run debug tool
    $debugScript = Join-Path $scriptPath "python\debug_wake_word.py"
    python $debugScript
    return
}

$pythonScript = Join-Path $scriptPath "python\voice_cli_flexible.py"

# Show prompt
Write-Host "🎤 " -NoNewline -ForegroundColor Cyan
Write-Host "Say 'Claude' then your command (flexible detection)..." -ForegroundColor Gray

# Get voice input
$result = & python $pythonScript 2>$null

if ($result -and $result.Trim()) {
    Write-Host "📝 " -NoNewline -ForegroundColor Green
    Write-Host $result -ForegroundColor White
    
    if ($Execute) {
        Write-Host "⚡ " -NoNewline -ForegroundColor Yellow
        Write-Host "Executing..." -ForegroundColor Gray
        
        try {
            # Try to execute as PowerShell command
            Invoke-Expression $result
        }
        catch {
            # Try as external command
            try {
                $parts = $result -split ' ', 2
                if ($parts.Length -eq 1) {
                    & $parts[0]
                } else {
                    & $parts[0] $parts[1]
                }
            }
            catch {
                Write-Host "❌ Error: $_" -ForegroundColor Red
                Write-Host "💡 Try saying the exact command name" -ForegroundColor Yellow
            }
        }
    }
    
    return $result
}
else {
    Write-Host "⏱️  No command received" -ForegroundColor Yellow
    Write-Host "💡 Try: .\vf.ps1 -Debug to test wake word detection" -ForegroundColor Gray
    return $null
}