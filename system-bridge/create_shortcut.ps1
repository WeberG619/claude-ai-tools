$WshShell = New-Object -ComObject WScript.Shell
$StartupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupPath\ClaudeServices.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = "D:\_CLAUDE-TOOLS\system-bridge\watchdog.py"
$Shortcut.WorkingDirectory = "D:\_CLAUDE-TOOLS\system-bridge"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Claude System Bridge Watchdog"
$Shortcut.Save()

Write-Host "Created startup shortcut at: $ShortcutPath"
