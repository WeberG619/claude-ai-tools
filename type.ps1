# Simple type helper - usage: type.ps1 "text to type" [-Enter]
param(
    [Parameter(Mandatory=$true)][string]$Text,
    [switch]$Enter
)

Add-Type -AssemblyName System.Windows.Forms

# Escape special SendKeys characters
$escaped = $Text -replace '([+^%~(){}[\]])', '{$1}'
[System.Windows.Forms.SendKeys]::SendWait($escaped)

if ($Enter) {
    Start-Sleep -Milliseconds 50
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
}

Write-Output "Typed: $Text"
