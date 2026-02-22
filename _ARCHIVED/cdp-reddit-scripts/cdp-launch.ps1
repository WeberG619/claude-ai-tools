# CDP Chrome Launcher - launches Chrome with remote debugging + user profile
# Usage: powershell -ExecutionPolicy Bypass -File cdp-launch.ps1 [url]
param(
    [string]$Url = "",
    [int]$Port = 9222
)

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

# Kill any existing Chrome
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Build args - profile directory with space needs special handling
$argList = "--remote-debugging-port=$Port --remote-debugging-address=0.0.0.0 `"--profile-directory=Profile 1`" --restore-last-session"
if ($Url) {
    $argList += " $Url"
}

# Launch Chrome
$proc = Start-Process $chromePath -ArgumentList $argList -PassThru
Write-Output "Chrome PID: $($proc.Id)"

# Wait for CDP
$maxWait = 15
$waited = 0
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/version" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Output "CDP ready on port $Port after ${waited}s"
        Write-Output $r.Content

        # Set up port proxy for WSL access
        $wslIp = (Get-NetIPAddress -InterfaceAlias "vEthernet (WSL*)" -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
        if ($wslIp) {
            # Remove old proxy if exists
            netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=$wslIp 2>$null
            # Add new proxy
            netsh interface portproxy add v4tov4 listenport=$Port listenaddress=$wslIp connectport=$Port connectaddress=127.0.0.1
            Write-Output "Port proxy: $wslIp`:$Port -> 127.0.0.1:$Port"
        }
        exit 0
    } catch {
        if ($waited % 3 -eq 0) { Write-Output "Waiting... ${waited}s" }
    }
}

Write-Output "CDP failed to start after ${maxWait}s"
Write-Output "Port check:"
netstat -an | Select-String ":$Port"
exit 1
