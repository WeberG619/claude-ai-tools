# NAS Auto-Reconnect Script
# Reconnects to BridgeAI NAS when it comes online after sleep

$nasIP = "192.168.1.31"
$shares = @(
    @{Drive="B:"; Share="\\$nasIP\BridgeAI"},
    @{Drive="U:"; Share="\\$nasIP\Users"}
)

function Test-NASOnline {
    $ping = Test-Connection -ComputerName $nasIP -Count 1 -Quiet -TimeoutSeconds 2
    return $ping
}

function Reconnect-Shares {
    foreach ($share in $shares) {
        $connected = Test-Path $share.Drive
        if (-not $connected) {
            Write-Host "Reconnecting $($share.Drive) to $($share.Share)..."
            net use $share.Drive $share.Share /persistent:yes 2>$null
            if ($?) {
                Write-Host "  Connected successfully" -ForegroundColor Green
            } else {
                Write-Host "  Failed to connect" -ForegroundColor Red
            }
        } else {
            Write-Host "$($share.Drive) already connected" -ForegroundColor Cyan
        }
    }
}

# Main
if (Test-NASOnline) {
    Write-Host "NAS is online at $nasIP" -ForegroundColor Green
    Reconnect-Shares
} else {
    Write-Host "NAS at $nasIP is offline" -ForegroundColor Yellow
}
