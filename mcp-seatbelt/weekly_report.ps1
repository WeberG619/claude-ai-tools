# MCP Seatbelt Weekly Report
# Run every Sunday to review the week's security events

$reportPath = "D:\_CLAUDE-TOOLS\mcp-seatbelt"
$logFile = "D:\_CLAUDE-TOOLS\system-bridge\seatbelt_weekly.log"

# Generate report
$report = python "$reportPath\seatbelt_cli.py" report 2>&1
$report | Out-File -FilePath $logFile -Encoding utf8

# Get summary for voice
$blocked = ($report | Select-String "Blocked:.*?(\d+)" | ForEach-Object { $_.Matches[0].Groups[1].Value })
$total = ($report | Select-String "Total calls.*?(\d+)" | ForEach-Object { $_.Matches[0].Groups[1].Value })

if ($blocked -and $total) {
    $summary = "Weekly seatbelt report: $blocked calls blocked out of $total total. Check the full report for details."
    python "D:\_CLAUDE-TOOLS\voice-mcp\speak.py" $summary
}

Write-Host "Report saved to $logFile"
Write-Host $report
