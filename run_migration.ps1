param(
    [string]$SqlFile,
    [string]$ProjectRef,
    [string]$Token
)

$sql = Get-Content -Path $SqlFile -Raw

$body = @{ query = $sql } | ConvertTo-Json -Depth 3 -Compress

$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "https://api.supabase.com/v1/projects/$ProjectRef/database/query" -Method POST -Headers $headers -Body $body -TimeoutSec 60
    Write-Output "SUCCESS"
    Write-Output ($response | ConvertTo-Json -Depth 5)
}
catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Output "Response: $responseBody"
    }
}
