# BridgeAI System Repair Tools
# PowerShell scripts for fixing common system issues

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("clear_temp", "kill_process", "flush_dns", "reset_network", "empty_trash", "disable_startup", "find_large_files", "disk_cleanup")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [string]$Target,

    [Parameter(Mandatory=$false)]
    [switch]$Confirm
)

function Clear-TempFiles {
    $paths = @(
        "$env:TEMP",
        "$env:LOCALAPPDATA\Temp",
        "C:\Windows\Temp"
    )

    $totalCleared = 0
    $results = @()

    foreach ($path in $paths) {
        if (Test-Path $path) {
            $before = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum

            if ($Confirm) {
                Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                $after = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                $cleared = [math]::Round(($before - $after) / 1MB, 1)
                $totalCleared += $cleared
                $results += @{ path = $path; cleared_mb = $cleared }
            } else {
                $sizeMB = [math]::Round($before / 1MB, 1)
                $results += @{ path = $path; would_clear_mb = $sizeMB }
            }
        }
    }

    return @{
        action = "clear_temp"
        confirmed = $Confirm.IsPresent
        results = $results
        total_mb = if ($Confirm) { $totalCleared } else { ($results | Measure-Object -Property would_clear_mb -Sum).Sum }
        message = if ($Confirm) { "Cleared $totalCleared MB of temporary files" } else { "Would clear approximately $(($results | Measure-Object -Property would_clear_mb -Sum).Sum) MB - run with -Confirm to proceed" }
    }
}

function Stop-TargetProcess {
    param([string]$ProcessName)

    if (-not $ProcessName) {
        return @{ error = "No process name provided" }
    }

    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue

    if (-not $processes) {
        return @{
            action = "kill_process"
            target = $ProcessName
            found = $false
            message = "No process found with name '$ProcessName'"
        }
    }

    if ($Confirm) {
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
        return @{
            action = "kill_process"
            target = $ProcessName
            killed = $processes.Count
            message = "Stopped $($processes.Count) instance(s) of $ProcessName"
        }
    } else {
        return @{
            action = "kill_process"
            target = $ProcessName
            found = $processes.Count
            memory_mb = [math]::Round(($processes | Measure-Object -Property WorkingSet64 -Sum).Sum / 1MB, 0)
            message = "Found $($processes.Count) instance(s) of $ProcessName - run with -Confirm to stop"
        }
    }
}

function Clear-DNSCache {
    if ($Confirm) {
        Clear-DnsClientCache
        return @{
            action = "flush_dns"
            success = $true
            message = "DNS cache cleared - this can help fix website loading issues"
        }
    } else {
        return @{
            action = "flush_dns"
            message = "Will clear DNS cache - run with -Confirm to proceed"
        }
    }
}

function Reset-NetworkStack {
    if ($Confirm) {
        $results = @()

        # Release and renew IP
        ipconfig /release | Out-Null
        ipconfig /renew | Out-Null
        $results += "IP address refreshed"

        # Flush DNS
        Clear-DnsClientCache
        $results += "DNS cache cleared"

        # Reset Winsock
        netsh winsock reset | Out-Null
        $results += "Network socket reset"

        return @{
            action = "reset_network"
            success = $true
            steps = $results
            message = "Network reset complete - you may need to reconnect to WiFi"
        }
    } else {
        return @{
            action = "reset_network"
            steps = @("Release/renew IP", "Clear DNS cache", "Reset Winsock")
            message = "Will reset network stack - run with -Confirm to proceed (may disconnect you temporarily)"
        }
    }
}

function Clear-RecycleBin {
    if ($Confirm) {
        Clear-RecycleBin -Force -ErrorAction SilentlyContinue
        return @{
            action = "empty_trash"
            success = $true
            message = "Recycle bin emptied"
        }
    } else {
        $shell = New-Object -ComObject Shell.Application
        $recycleBin = $shell.Namespace(0xA)
        $itemCount = $recycleBin.Items().Count

        return @{
            action = "empty_trash"
            items = $itemCount
            message = "Recycle bin has $itemCount items - run with -Confirm to empty"
        }
    }
}

function Disable-StartupItem {
    param([string]$ItemName)

    if (-not $ItemName) {
        # List all startup items
        $startupItems = Get-CimInstance -ClassName Win32_StartupCommand
        return @{
            action = "disable_startup"
            items = $startupItems | ForEach-Object { @{ name = $_.Name; command = $_.Command } }
            message = "Provide -Target with item name to disable"
        }
    }

    # This is complex and varies by location - returning guidance
    return @{
        action = "disable_startup"
        target = $ItemName
        message = "To disable '$ItemName', open Task Manager > Startup tab and disable it there. This is safer than registry editing."
        guidance = "I can guide you through this step by step if you'd like."
    }
}

function Find-LargeFiles {
    param([string]$Path = "C:\Users")

    $largeFiles = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 100MB } |
        Sort-Object -Property Length -Descending |
        Select-Object -First 20 |
        ForEach-Object {
            @{
                path = $_.FullName
                size_mb = [math]::Round($_.Length / 1MB, 0)
                last_modified = $_.LastWriteTime.ToString("yyyy-MM-dd")
            }
        }

    $totalMB = ($largeFiles | Measure-Object -Property size_mb -Sum).Sum

    return @{
        action = "find_large_files"
        search_path = $Path
        files = $largeFiles
        total_large_files_mb = $totalMB
        message = "Found $($largeFiles.Count) files over 100MB totaling $totalMB MB"
    }
}

function Start-DiskCleanup {
    if ($Confirm) {
        # Run Windows Disk Cleanup silently
        Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/d C /sagerun:1" -Wait -NoNewWindow
        return @{
            action = "disk_cleanup"
            success = $true
            message = "Windows Disk Cleanup completed"
        }
    } else {
        return @{
            action = "disk_cleanup"
            message = "Will run Windows Disk Cleanup - run with -Confirm to proceed"
        }
    }
}

# Execute requested action
$result = switch ($Action) {
    "clear_temp" { Clear-TempFiles }
    "kill_process" { Stop-TargetProcess -ProcessName $Target }
    "flush_dns" { Clear-DNSCache }
    "reset_network" { Reset-NetworkStack }
    "empty_trash" { Clear-RecycleBin }
    "disable_startup" { Disable-StartupItem -ItemName $Target }
    "find_large_files" { Find-LargeFiles -Path $Target }
    "disk_cleanup" { Start-DiskCleanup }
}

$result | ConvertTo-Json -Depth 5
