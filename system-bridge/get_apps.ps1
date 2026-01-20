# Get all applications with window titles
$apps = Get-Process | Where-Object {$_.MainWindowTitle -ne ""} |
    Select-Object ProcessName, Id, MainWindowTitle

$result = @()
foreach ($app in $apps) {
    $result += @{
        ProcessName = $app.ProcessName
        Id = $app.Id
        MainWindowTitle = $app.MainWindowTitle
    }
}

$result | ConvertTo-Json -Compress
