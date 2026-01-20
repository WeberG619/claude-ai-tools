# BridgeAI System Diagnostics
# PowerShell scripts for checking system health

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("cpu", "memory", "disk", "network", "processes", "startup", "all", "health")]
    [string]$Check
)

function Get-CPUUsage {
    $cpu = Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty LoadPercentage
    return @{
        usage_percent = $cpu
        status = if ($cpu -lt 50) { "good" } elseif ($cpu -lt 80) { "moderate" } else { "high" }
        message = if ($cpu -lt 50) { "CPU is running smoothly" } elseif ($cpu -lt 80) { "CPU is moderately busy" } else { "CPU is very busy - something might be using too much" }
    }
}

function Get-MemoryUsage {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    $usedGB = $totalGB - $freeGB
    $usedPercent = [math]::Round(($usedGB / $totalGB) * 100, 0)

    return @{
        total_gb = $totalGB
        used_gb = $usedGB
        free_gb = $freeGB
        used_percent = $usedPercent
        status = if ($usedPercent -lt 60) { "good" } elseif ($usedPercent -lt 85) { "moderate" } else { "high" }
        message = if ($usedPercent -lt 60) { "Plenty of memory available" } elseif ($usedPercent -lt 85) { "Memory usage is moderate" } else { "Memory is getting full - might slow things down" }
    }
}

function Get-DiskSpace {
    $drives = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
        $totalGB = [math]::Round($_.Size / 1GB, 1)
        $freeGB = [math]::Round($_.FreeSpace / 1GB, 1)
        $usedGB = $totalGB - $freeGB
        $usedPercent = if ($totalGB -gt 0) { [math]::Round(($usedGB / $totalGB) * 100, 0) } else { 0 }

        @{
            drive = $_.DeviceID
            total_gb = $totalGB
            free_gb = $freeGB
            used_percent = $usedPercent
            status = if ($usedPercent -lt 70) { "good" } elseif ($usedPercent -lt 90) { "moderate" } else { "critical" }
            message = if ($usedPercent -lt 70) { "Plenty of space" } elseif ($usedPercent -lt 90) { "Getting full, consider cleanup" } else { "Very low space - needs attention" }
        }
    }
    return $drives
}

function Get-NetworkStatus {
    $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
    $connectivity = Test-NetConnection -ComputerName "8.8.8.8" -WarningAction SilentlyContinue

    return @{
        connected = $connectivity.PingSucceeded
        adapters = $adapters | ForEach-Object { $_.Name }
        latency_ms = $connectivity.PingReplyDetails.RoundtripTime
        status = if ($connectivity.PingSucceeded) { "connected" } else { "disconnected" }
        message = if ($connectivity.PingSucceeded) { "Internet is working" } else { "No internet connection detected" }
    }
}

function Get-TopProcesses {
    $processes = Get-Process | Sort-Object -Property WorkingSet64 -Descending | Select-Object -First 10 | ForEach-Object {
        @{
            name = $_.ProcessName
            memory_mb = [math]::Round($_.WorkingSet64 / 1MB, 0)
            cpu_seconds = [math]::Round($_.CPU, 1)
        }
    }
    return $processes
}

function Get-StartupPrograms {
    $startup = Get-CimInstance -ClassName Win32_StartupCommand | ForEach-Object {
        @{
            name = $_.Name
            command = $_.Command
            location = $_.Location
        }
    }
    return $startup
}

function Get-SystemHealth {
    return @{
        cpu = Get-CPUUsage
        memory = Get-MemoryUsage
        disk = Get-DiskSpace
        network = Get-NetworkStatus
        timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }
}

# Execute requested check
$result = switch ($Check) {
    "cpu" { Get-CPUUsage }
    "memory" { Get-MemoryUsage }
    "disk" { Get-DiskSpace }
    "network" { Get-NetworkStatus }
    "processes" { Get-TopProcesses }
    "startup" { Get-StartupPrograms }
    "health" { Get-SystemHealth }
    "all" { Get-SystemHealth }
}

$result | ConvertTo-Json -Depth 5
