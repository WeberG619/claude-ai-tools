# Close PowerPoint Dialog - Working Version

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Threading;

public class DialogCloser {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    
    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    
    const int MOUSEEVENTF_LEFTDOWN = 0x02;
    const int MOUSEEVENTF_LEFTUP = 0x04;
    
    public static void ClickAt(int x, int y) {
        SetCursorPos(x, y);
        Thread.Sleep(100);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(50);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }
}
"@

Write-Host "Closing PowerPoint Dialog..." -ForegroundColor Cyan

# Click X button
[DialogCloser]::ClickAt(1271, 497)
Start-Sleep -Milliseconds 500

# Press ESC
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")

Write-Host "Done!" -ForegroundColor Green