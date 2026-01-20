# Check installed Windows voices
Add-Type -AssemblyName System.Speech

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $synth.GetInstalledVoices()

Write-Host "=== Installed Windows SAPI Voices ==="
foreach ($voice in $voices) {
    $info = $voice.VoiceInfo
    Write-Host "  - $($info.Name)"
    Write-Host "    Culture: $($info.Culture)"
    Write-Host "    Gender: $($info.Gender)"
    Write-Host ""
}
$synth.Dispose()

Write-Host ""
Write-Host "=== Checking for OneCore/Neural Voices ==="
Write-Host "(These are the natural-sounding voices)"
Write-Host ""

# Check registry for OneCore voices
$onecorePath = "HKLM:\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
if (Test-Path $onecorePath) {
    $onecore = Get-ChildItem $onecorePath
    Write-Host "OneCore voices found: $($onecore.Count)"
    foreach ($v in $onecore) {
        Write-Host "  - $(Split-Path $v.Name -Leaf)"
    }
} else {
    Write-Host "No OneCore voices found in registry"
}
