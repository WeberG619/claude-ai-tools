# File Scanner for Claude System
# Scans directories and outputs JSON

param(
    [string]$BasePath = "D:\001 - PROJECTS",
    [string]$OutputFile = "D:\_CLAUDE-TOOLS\system-bridge\scanned_files.json"
)

$extensions = @('.rvt', '.rfa', '.pdf', '.dwg', '.dxf', '.ifc', '.nwc')

$files = @()

try {
    Get-ChildItem -Path $BasePath -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $extensions -contains $_.Extension.ToLower() } |
    ForEach-Object {
        $files += @{
            FullName = $_.FullName
            Name = $_.Name
            Extension = $_.Extension.ToLower()
            Length = $_.Length
            LastWriteTime = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            Directory = $_.DirectoryName
        }
    }
} catch {
    Write-Host "Error scanning: $_"
}

$files | ConvertTo-Json -Depth 3 | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host "Scanned $($files.Count) files from $BasePath"
