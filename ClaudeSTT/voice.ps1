# Simple voice command for PowerShell
param(
    [string]$Prompt = "Say 'Claude' then your command:",
    [switch]$Execute,
    [switch]$Continuous
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptPath "python\terminal_stt.py"

if ($Continuous) {
    # Continuous listening mode
    & python $pythonScript --continuous
}
else {
    # Single command mode
    $result = & python $pythonScript 2>$null
    
    if ($result) {
        Write-Host "You said: $result" -ForegroundColor Cyan
        
        if ($Execute) {
            Write-Host "Executing command..." -ForegroundColor Yellow
            try {
                Invoke-Expression $result
            }
            catch {
                Write-Host "Error executing command: $_" -ForegroundColor Red
            }
        }
        
        # Return the transcription
        return $result
    }
    else {
        Write-Host "No command received" -ForegroundColor Yellow
    }
}