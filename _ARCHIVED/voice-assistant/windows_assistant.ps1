# Claude Voice Assistant - Windows Native
# Uses Windows Speech Recognition and Edge TTS

Add-Type -AssemblyName System.Speech

# Configuration
$WakeWords = @("hey claude", "hey cloud", "claude", "okay claude")
$VoiceName = "en-US-AndrewNeural"
$AudioDir = "D:\.playwright-mcp\audio"

# Ensure audio directory exists
if (-not (Test-Path $AudioDir)) {
    New-Item -ItemType Directory -Path $AudioDir -Force | Out-Null
}

# Speech Recognition Engine
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$recognizer.SetInputToDefaultAudioDevice()

# Grammar for wake word
$grammarBuilder = New-Object System.Speech.Recognition.GrammarBuilder
$grammarBuilder.Append((New-Object System.Speech.Recognition.Choices($WakeWords)))
$grammar = New-Object System.Speech.Recognition.Grammar($grammarBuilder)
$recognizer.LoadGrammar($grammar)

# Also add dictation grammar for commands
$dictationGrammar = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($dictationGrammar)

function Speak-Text {
    param([string]$Text, [string]$Rate = "+5%")

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $audioFile = "$AudioDir\assistant_$timestamp.mp3"
    $wslPath = "/mnt/d/.playwright-mcp/audio/assistant_$timestamp.mp3"

    # Generate audio with edge-tts via WSL
    $null = wsl edge-tts --voice $VoiceName --rate $Rate --text $Text --write-media $wslPath 2>&1

    Start-Sleep -Milliseconds 500

    # Play audio
    Add-Type -AssemblyName PresentationCore
    $player = New-Object System.Windows.Media.MediaPlayer
    $player.Open($audioFile)
    Start-Sleep -Milliseconds 300
    $player.Play()

    while ($player.NaturalDuration.HasTimeSpan -eq $false) {
        Start-Sleep -Milliseconds 100
    }
    $duration = $player.NaturalDuration.TimeSpan.TotalSeconds
    Start-Sleep -Seconds ($duration + 0.5)
    $player.Close()
}

function Send-ToClaudeCode {
    param([string]$Command)

    # Run Claude Code in print mode and capture output
    $result = wsl bash -c "cd /mnt/d && claude -p '$Command' 2>&1"
    return $result -join " "
}

function Check-WakeWord {
    param([string]$Text)

    $textLower = $Text.ToLower()
    foreach ($word in $WakeWords) {
        if ($textLower.Contains($word)) {
            return $true
        }
    }
    return $false
}

function Extract-Command {
    param([string]$Text)

    $textLower = $Text.ToLower()
    foreach ($word in $WakeWords) {
        if ($textLower.Contains($word)) {
            $idx = $textLower.IndexOf($word)
            return $Text.Substring($idx + $word.Length).Trim()
        }
    }
    return $Text
}

# Main Loop
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "   Claude Voice Assistant"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "Say 'Hey Claude' followed by your command"  -ForegroundColor Yellow
Write-Host "Say 'Goodbye' to exit"  -ForegroundColor Yellow
Write-Host ""

Speak-Text "Voice assistant ready. Say Hey Claude when you need me."

$running = $true
while ($running) {
    Write-Host ""
    Write-Host "Listening..."  -ForegroundColor Green

    try {
        $result = $recognizer.Recognize([TimeSpan]::FromSeconds(10))

        if ($result -ne $null -and $result.Text -ne "") {
            $text = $result.Text
            Write-Host "Heard: $text"  -ForegroundColor Gray

            if (Check-WakeWord $text) {
                $command = Extract-Command $text

                if ($command -eq "" -or $command.Length -lt 3) {
                    Speak-Text "Yes?"

                    # Listen for actual command
                    Write-Host "Listening for command..."  -ForegroundColor Yellow
                    $cmdResult = $recognizer.Recognize([TimeSpan]::FromSeconds(15))

                    if ($cmdResult -ne $null -and $cmdResult.Text -ne "") {
                        $command = $cmdResult.Text
                        Write-Host "Command: $command"  -ForegroundColor Cyan
                    }
                }

                if ($command -ne "" -and $command.Length -ge 3) {
                    # Check for exit
                    $cmdLower = $command.ToLower()
                    if ($cmdLower -match "goodbye|exit|quit|stop listening") {
                        Speak-Text "Goodbye Weber. I will be here when you need me."
                        $running = $false
                        break
                    }

                    Write-Host "Processing: $command"  -ForegroundColor Cyan
                    Speak-Text "Let me work on that."

                    # Send to Claude
                    $response = Send-ToClaudeCode $command

                    # Truncate long responses for speech
                    if ($response.Length -gt 500) {
                        $shortResponse = $response.Substring(0, 500)
                        $summaryPrompt = "Summarize this in 2-3 short sentences: $shortResponse"
                        $response = Send-ToClaudeCode $summaryPrompt
                    }

                    Speak-Text $response
                    Write-Host "Done"  -ForegroundColor Green
                }
            }
        }
    }
    catch {
        # Timeout or error, continue listening
        Write-Host "."  -NoNewline -ForegroundColor DarkGray
    }
}

$recognizer.Dispose()
Write-Host ""
Write-Host "Voice assistant stopped."  -ForegroundColor Yellow
