# Quick PowerPoint Dialog Closer
# Simple script to close the Copilot dialog

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Threading;

public class QuickUIHelper {
    [DllImport("user32.dll")]
    static extern bool SetCursorPos(int X, int Y);
    
    [DllImport("user32.dll")]
    static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    
    const int MOUSEEVENTF_LEFTDOWN = 0x02;
    const int MOUSEEVENTF_LEFTUP = 0x04;
    const int VK_ESCAPE = 0x1B;
    
    public static void ClickAt(int x, int y) {
        SetCursorPos(x, y);
        Thread.Sleep(100);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(50);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }
    
    public static void PressEscape() {
        keybd_event(VK_ESCAPE, 0, 0, 0);
        Thread.Sleep(50);
        keybd_event(VK_ESCAPE, 0, 2, 0);
    }
}
"@

Write-Host "`nClosing PowerPoint Copilot Dialog" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Method 1: Click the X button
Write-Host "`n1. Clicking X button at (1271, 497)..." -ForegroundColor Yellow
[QuickUIHelper]::ClickAt(1271, 497)
Start-Sleep -Milliseconds 500

# Method 2: Press ESC
Write-Host "2. Pressing ESC key..." -ForegroundColor Yellow
[QuickUIHelper]::PressEscape()
Start-Sleep -Milliseconds 300

# Method 3: SendKeys ESC
Write-Host "3. Sending ESC via SendKeys..." -ForegroundColor Yellow
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep -Milliseconds 300

# Method 4: Click outside
Write-Host "4. Clicking outside dialog..." -ForegroundColor Yellow
[QuickUIHelper]::ClickAt(500, 300)
Start-Sleep -Milliseconds 300
[QuickUIHelper]::PressEscape()

# Method 5: Alt+F4
Write-Host "5. Trying Alt+F4..." -ForegroundColor Yellow
[System.Windows.Forms.SendKeys]::SendWait("%{F4}")

Write-Host "`n✓ All methods attempted!" -ForegroundColor Green
Write-Host "Check if the dialog is closed." -ForegroundColor Cyan