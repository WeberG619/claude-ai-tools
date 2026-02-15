# Agent Team Session Recorder
# Records screen + system audio using ffmpeg

param(
    [string]$OutputPath = "D:\Users\Weber\Videos",
    [string]$FileName = "Agent_Team_Session",
    [int]$DurationMinutes = 30
)

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$outputFile = "$OutputPath\${FileName}_$timestamp.mp4"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agent Team Session Recorder" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output: $outputFile" -ForegroundColor Yellow
Write-Host "Duration: $DurationMinutes minutes (press Q to stop early)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Recording will start in 3 seconds..." -ForegroundColor Green
Start-Sleep -Seconds 3

# Record using ffmpeg
# -f gdigrab captures the screen
# -f dshow captures audio from speakers (via loopback)
ffmpeg -f gdigrab -framerate 30 -i desktop `
    -f dshow -i audio="Stereo Mix (High Definition Audio Device)" `
    -c:v libx264 -preset ultrafast -crf 23 `
    -c:a aac -b:a 128k `
    -t ($DurationMinutes * 60) `
    -y "$outputFile"

Write-Host ""
Write-Host "Recording saved to: $outputFile" -ForegroundColor Green
