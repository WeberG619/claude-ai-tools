# Safe UI Automation System - No Keyboard Blocking
# Fixed version that won't interfere with keyboard input

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

public class SafeUIAutomation {
    // Mouse event constants
    const int MOUSEEVENTF_LEFTDOWN = 0x02;
    const int MOUSEEVENTF_LEFTUP = 0x04;
    const int MOUSEEVENTF_ABSOLUTE = 0x8000;
    const int MOUSEEVENTF_MOVE = 0x0001;
    
    // Input type constants
    const int INPUT_MOUSE = 0;
    
    // Virtual key codes
    const int VK_ESCAPE = 0x1B;
    
    [DllImport("user32.dll")]
    static extern bool SetCursorPos(int X, int Y);
    
    [DllImport("user32.dll")]
    static extern bool GetCursorPos(out POINT lpPoint);
    
    [DllImport("user32.dll")]
    static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    
    [DllImport("user32.dll")]
    static extern IntPtr WindowFromPoint(POINT pt);
    
    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern bool IsWindowEnabled(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern bool ScreenToClient(IntPtr hWnd, ref POINT lpPoint);
    
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }
    
    [StructLayout(LayoutKind.Sequential)]
    struct INPUT {
        public int type;
        public INPUTUNION u;
    }
    
    [StructLayout(LayoutKind.Explicit)]
    struct INPUTUNION {
        [FieldOffset(0)] public MOUSEINPUT mi;
    }
    
    [StructLayout(LayoutKind.Sequential)]
    struct MOUSEINPUT {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }
    
    // Window message constants
    const int WM_CLOSE = 0x0010;
    const int WM_LBUTTONDOWN = 0x0201;
    const int WM_LBUTTONUP = 0x0202;
    
    // Safe click method - no thread attachment
    public static bool SafeClick(int x, int y) {
        try {
            // Move cursor
            SetCursorPos(x, y);
            Thread.Sleep(50);
            
            // Verify position
            POINT currentPos;
            GetCursorPos(out currentPos);
            if (Math.Abs(currentPos.X - x) > 5 || Math.Abs(currentPos.Y - y) > 5) {
                Console.WriteLine("Failed to position cursor accurately");
                return false;
            }
            
            // Click using mouse_event (safest method)
            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
            Thread.Sleep(30);
            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
            
            return true;
        }
        catch (Exception ex) {
            Console.WriteLine($"Click failed: {ex.Message}");
            return false;
        }
    }
    
    // Safe window message click
    public static bool SafeWindowClick(int x, int y) {
        try {
            POINT pt = new POINT { X = x, Y = y };
            IntPtr hwnd = WindowFromPoint(pt);
            
            if (hwnd == IntPtr.Zero) {
                return false;
            }
            
            // Convert to client coordinates
            ScreenToClient(hwnd, ref pt);
            
            // Create lParam
            IntPtr lParam = (IntPtr)((pt.Y << 16) | (pt.X & 0xFFFF));
            
            // Send click messages (PostMessage is safer than SendMessage)
            PostMessage(hwnd, WM_LBUTTONDOWN, IntPtr.Zero, lParam);
            Thread.Sleep(30);
            PostMessage(hwnd, WM_LBUTTONUP, IntPtr.Zero, lParam);
            
            return true;
        }
        catch {
            return false;
        }
    }
    
    // Safe ESC key press
    public static void SafeEscapeKey() {
        keybd_event(VK_ESCAPE, 0, 0, 0);
        Thread.Sleep(50);
        keybd_event(VK_ESCAPE, 0, 2, 0); // Key up
    }
    
    // Check window at position
    public static bool IsClickable(int x, int y) {
        POINT pt = new POINT { X = x, Y = y };
        IntPtr hwnd = WindowFromPoint(pt);
        
        if (hwnd != IntPtr.Zero) {
            return IsWindowVisible(hwnd) && IsWindowEnabled(hwnd);
        }
        
        return false;
    }
}
"@ -ReferencedAssemblies System.Drawing, System.Windows.Forms

# Safe PowerShell wrapper functions

function Invoke-SafeClick {
    param(
        [int]$X,
        [int]$Y,
        [switch]$Verify
    )
    
    Write-Host "Safe clicking at ($X, $Y)" -ForegroundColor Yellow
    
    if ($Verify) {
        $clickable = [SafeUIAutomation]::IsClickable($X, $Y)
        if (-not $clickable) {
            Write-Host "Warning: Position may not be clickable" -ForegroundColor Red
        }
    }
    
    $result = [SafeUIAutomation]::SafeClick($X, $Y)
    
    if ($result) {
        Write-Host "Click successful" -ForegroundColor Green
    } else {
        Write-Host "Click failed - trying window message method" -ForegroundColor Yellow
        $result = [SafeUIAutomation]::SafeWindowClick($X, $Y)
        if ($result) {
            Write-Host "Window click successful" -ForegroundColor Green
        }
    }
    
    return $result
}

function Close-CopilotSafely {
    Write-Host "`nSafe Copilot Dialog Closure" -ForegroundColor Magenta
    Write-Host "===========================" -ForegroundColor Magenta
    
    # Try clicking X button
    Write-Host "`nAttempting to click X button at (1271, 497)" -ForegroundColor Yellow
    $clicked = Invoke-SafeClick -X 1271 -Y 497 -Verify
    
    if ($clicked) {
        Write-Host "Click successful - waiting for dialog to close" -ForegroundColor Green
        Start-Sleep -Seconds 1
    }
    
    # Try ESC key as backup
    Write-Host "`nSending ESC key as backup" -ForegroundColor Yellow
    [SafeUIAutomation]::SafeEscapeKey()
    Start-Sleep -Milliseconds 500
    
    # Try SendKeys ESC (different method)
    Write-Host "Sending ESC via SendKeys" -ForegroundColor Yellow
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
    
    # Click outside dialog area
    Write-Host "`nClicking outside dialog area" -ForegroundColor Yellow
    Invoke-SafeClick -X 500 -Y 300
    
    Write-Host "`nSafe closure attempt completed" -ForegroundColor Cyan
    Write-Host "Your keyboard should remain fully functional" -ForegroundColor Green
}

function Test-SafeAutomation {
    Write-Host "`nTesting Safe UI Automation" -ForegroundColor Cyan
    Write-Host "==========================" -ForegroundColor Cyan
    
    Write-Host "`nThis test will NOT affect your keyboard" -ForegroundColor Green
    Write-Host "Type something now to verify keyboard is working..." -ForegroundColor Yellow
    
    Start-Sleep -Seconds 2
    
    Write-Host "`nPerforming safe click test at (800, 400)" -ForegroundColor Yellow
    $result = Invoke-SafeClick -X 800 -Y 400
    
    Write-Host "`nTest complete. Keyboard should still be working normally." -ForegroundColor Green
}

# Main execution
Write-Host @"

Safe UI Automation System Loaded
================================

This version will NOT block your keyboard!

Commands:
- Close-CopilotSafely : Safely close the Copilot dialog
- Invoke-SafeClick -X <x> -Y <y> : Perform a safe click
- Test-SafeAutomation : Test the system safely

Your keyboard will remain fully functional at all times.

"@ -ForegroundColor Green

# Export functions
Export-ModuleMember -Function Invoke-SafeClick, Close-CopilotSafely, Test-SafeAutomation