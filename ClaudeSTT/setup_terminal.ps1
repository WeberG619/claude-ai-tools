# Setup script to add voice commands to PowerShell terminal

Write-Host "Setting up Claude voice commands for terminal..." -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $scriptPath "python"

# Add to Python path
$env:PYTHONPATH = "$pythonPath;$env:PYTHONPATH"

# Create PowerShell functions that call the Python scripts
$functionDefinitions = @'
function Claude-Voice {
    param(
        [string]$Prompt = "Say 'Claude' then your command:",
        [int]$Timeout = 30
    )
    
    $scriptPath = "D:\ClaudeSTT\python"
    $result = & python "$scriptPath\terminal_stt.py" --timeout $Timeout 2>$null
    return $result
}

function Claude-Terminal {
    $scriptPath = "D:\ClaudeSTT\python"
    & python "$scriptPath\claude_terminal.py"
}

function Voice-Input {
    param(
        [string]$Prompt = "",
        [string]$WakeWord = "claude",
        [int]$Timeout = 30
    )
    
    $scriptPath = "D:\ClaudeSTT\python"
    $pyCode = @"
import sys
sys.path.insert(0, r'$scriptPath')
from voice_input import voice_input
result = voice_input('$Prompt', '$WakeWord', $Timeout)
if result:
    print(result)
"@
    
    $result = & python -c $pyCode 2>$null
    return $result
}

function Voice-Command {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$Command
    )
    
    $voice = Voice-Input -Prompt "Say 'Claude' then speak your command:"
    if ($voice) {
        Write-Host "Executing: $voice" -ForegroundColor Yellow
        Invoke-Expression $voice
    }
}

# Alias for quick access
Set-Alias -Name vc -Value Voice-Command
Set-Alias -Name vi -Value Voice-Input
Set-Alias -Name ct -Value Claude-Terminal
'@

# Add functions to current session
Invoke-Expression $functionDefinitions

# Save to profile for persistence
$profileContent = @"

# Claude Voice Commands
$functionDefinitions

Write-Host "Claude voice commands loaded. Use 'Get-Help Voice-*' for info." -ForegroundColor Green
"@

# Ask if user wants to save to profile
Write-Host "`nDo you want to add these commands to your PowerShell profile?" -ForegroundColor Yellow
Write-Host "This will make them available in all future sessions." -ForegroundColor Gray
$response = Read-Host "Add to profile? (Y/N)"

if ($response -eq 'Y' -or $response -eq 'y') {
    if (!(Test-Path $PROFILE)) {
        New-Item -Path $PROFILE -ItemType File -Force | Out-Null
    }
    
    Add-Content -Path $PROFILE -Value $profileContent
    Write-Host "Added to profile: $PROFILE" -ForegroundColor Green
}

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "`nAvailable commands:" -ForegroundColor Cyan
Write-Host "  Voice-Input     " -NoNewline -ForegroundColor Yellow
Write-Host "- Get voice input (alias: vi)"
Write-Host "  Voice-Command   " -NoNewline -ForegroundColor Yellow
Write-Host "- Execute voice command (alias: vc)"
Write-Host "  Claude-Terminal " -NoNewline -ForegroundColor Yellow
Write-Host "- Start voice-enabled terminal (alias: ct)"
Write-Host "  Claude-Voice    " -NoNewline -ForegroundColor Yellow
Write-Host "- Get raw voice transcription"

Write-Host "`nExamples:" -ForegroundColor Cyan
Write-Host '  $name = Voice-Input "What is your name?"'
Write-Host '  Voice-Command  # Say "list files" to run ls/dir'
Write-Host '  Claude-Terminal  # Full voice terminal experience'

Write-Host "`nTry it now:" -ForegroundColor Green
Write-Host '  Voice-Command' -ForegroundColor White