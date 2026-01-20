# Force Close PowerPoint Dialog
# More aggressive approach

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Threading;

public class ForceClose {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    
    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    const int MOUSEEVENTF_LEFTDOWN = 0x02;
    const int MOUSEEVENTF_LEFTUP = 0x04;
    const int MOUSEEVENTF_RIGHTDOWN = 0x08;
    const int MOUSEEVENTF_RIGHTUP = 0x10;
    const int VK_ESCAPE = 0x1B;
    const uint WM_CLOSE = 0x0010;
    const uint WM_KEYDOWN = 0x0100;
    
    public static void MultiClick(int x, int y) {
        SetCursorPos(x, y);
        Thread.Sleep(50);
        
        // Try single click
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(30);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
        Thread.Sleep(100);
        
        // Try double click
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
        Thread.Sleep(50);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }
    
    public static void RightClick(int x, int y) {
        SetCursorPos(x, y);
        Thread.Sleep(50);
        mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0);
        Thread.Sleep(30);
        mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0);
    }
    
    public static void PressEscapeMultiple() {
        for (int i = 0; i < 3; i++) {
            keybd_event(VK_ESCAPE, 0, 0, 0);
            Thread.Sleep(50);
            keybd_event(VK_ESCAPE, 0, 2, 0);
            Thread.Sleep(100);
        }
    }
}
"@

Write-Host "`nForce Closing PowerPoint Dialog" -ForegroundColor Red
Write-Host "===============================" -ForegroundColor Red

# Get current window
$currentWindow = [ForceClose]::GetForegroundWindow()

# Multiple X button locations to try
$xButtons = @(
    @{X=1271; Y=497; Name="Copilot X"},
    @{X=1270; Y=495; Name="Copilot X Alt1"},
    @{X=1272; Y=499; Name="Copilot X Alt2"},
    @{X=1895; Y=45; Name="Top Right X"},
    @{X=1850; Y=45; Name="Window X"}
)

# Try each X button location
foreach ($button in $xButtons) {
    Write-Host "`nTrying $($button.Name) at ($($button.X), $($button.Y))..." -ForegroundColor Yellow
    [ForceClose]::MultiClick($button.X, $button.Y)
    Start-Sleep -Milliseconds 200
}

# Press ESC multiple times
Write-Host "`nPressing ESC multiple times..." -ForegroundColor Yellow
[ForceClose]::PressEscapeMultiple()

# SendKeys combinations
Write-Host "`nTrying keyboard shortcuts..." -ForegroundColor Yellow
Add-Type -AssemblyName System.Windows.Forms

# ESC
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep -Milliseconds 200

# Ctrl+W (close window/pane)
[System.Windows.Forms.SendKeys]::SendWait("^w")
Start-Sleep -Milliseconds 200

# Alt+F4
[System.Windows.Forms.SendKeys]::SendWait("%{F4}")
Start-Sleep -Milliseconds 200

# Click in multiple areas to dismiss
Write-Host "`nClicking in multiple areas..." -ForegroundColor Yellow
$dismissClicks = @(
    @{X=400; Y=300},
    @{X=600; Y=400},
    @{X=800; Y=500},
    @{X=200; Y=200}
)

foreach ($click in $dismissClicks) {
    [ForceClose]::MultiClick($click.X, $click.Y)
    Start-Sleep -Milliseconds 100
}

# Right-click and ESC (sometimes works for context menus)
Write-Host "`nTrying right-click dismiss..." -ForegroundColor Yellow
[ForceClose]::RightClick(1271, 497)
Start-Sleep -Milliseconds 200
[ForceClose]::PressEscapeMultiple()

# Final attempt - click PowerPoint main area and ESC
Write-Host "`nFinal attempt - focus main area..." -ForegroundColor Yellow
[ForceClose]::MultiClick(700, 400)
[ForceClose]::PressEscapeMultiple()

Write-Host "`n✓ All force close methods attempted!" -ForegroundColor Green
Write-Host "`nIf the dialog is still open:" -ForegroundColor Cyan
Write-Host "1. Try manually clicking somewhere in PowerPoint first" -ForegroundColor White
Write-Host "2. Then run this script again" -ForegroundColor White
Write-Host "3. Or try restarting PowerPoint" -ForegroundColor White