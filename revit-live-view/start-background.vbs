' Start Revit Live View Capture Daemon in background (hidden window)
' This script launches the PowerShell daemon without showing a window

Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""D:\_CLAUDE-TOOLS\revit-live-view\revit-capture-daemon.ps1"" -Silent", 0, False
