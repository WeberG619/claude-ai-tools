# Robust Windows UI Automation System
# Addresses clicking failures, verification issues, and task completion

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

public class RobustUIAutomation {
    // Mouse event constants
    const int MOUSEEVENTF_LEFTDOWN = 0x02;
    const int MOUSEEVENTF_LEFTUP = 0x04;
    const int MOUSEEVENTF_RIGHTDOWN = 0x08;
    const int MOUSEEVENTF_RIGHTUP = 0x10;
    const int MOUSEEVENTF_MIDDLEDOWN = 0x20;
    const int MOUSEEVENTF_MIDDLEUP = 0x40;
    const int MOUSEEVENTF_ABSOLUTE = 0x8000;
    const int MOUSEEVENTF_MOVE = 0x0001;
    
    // Input type constants
    const int INPUT_MOUSE = 0;
    const int INPUT_KEYBOARD = 1;
    
    // Virtual key codes
    const int VK_ESCAPE = 0x1B;
    const int VK_RETURN = 0x0D;
    const int VK_TAB = 0x09;
    const int VK_SPACE = 0x20;
    
    // Window message constants
    const int WM_CLOSE = 0x0010;
    const int WM_LBUTTONDOWN = 0x0201;
    const int WM_LBUTTONUP = 0x0202;
    const int BM_CLICK = 0x00F5;

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
    static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    
    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    
    [DllImport("user32.dll")]
    static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
    
    [DllImport("user32.dll")]
    static extern short GetAsyncKeyState(int vKey);
    
    [DllImport("user32.dll")]
    static extern IntPtr GetDesktopWindow();
    
    [DllImport("user32.dll")]
    static extern IntPtr ChildWindowFromPoint(IntPtr hWndParent, POINT pt);
    
    [DllImport("user32.dll")]
    static extern bool ScreenToClient(IntPtr hWnd, ref POINT lpPoint);
    
    [DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern bool IsWindowEnabled(IntPtr hWnd);
    
    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr FindWindowEx(IntPtr hWndParent, IntPtr hWndChildAfter, string lpszClass, string lpszWindow);
    
    [DllImport("user32.dll")]
    static extern bool UpdateWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    static extern bool InvalidateRect(IntPtr hWnd, IntPtr lpRect, bool bErase);
    
    [DllImport("user32.dll")]
    static extern bool RedrawWindow(IntPtr hWnd, IntPtr lprcUpdate, IntPtr hrgnUpdate, uint flags);
    
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    
    [DllImport("user32.dll")]
    static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    
    [DllImport("kernel32.dll")]
    static extern uint GetCurrentThreadId();
    
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }
    
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
    
    [StructLayout(LayoutKind.Sequential)]
    struct INPUT {
        public int type;
        public INPUTUNION u;
    }
    
    [StructLayout(LayoutKind.Explicit)]
    struct INPUTUNION {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
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
    
    [StructLayout(LayoutKind.Sequential)]
    struct KEYBDINPUT {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }
    
    // Verify cursor position after movement
    public static bool VerifyCursorPosition(int x, int y, int tolerance = 5) {
        POINT currentPos;
        GetCursorPos(out currentPos);
        return Math.Abs(currentPos.X - x) <= tolerance && Math.Abs(currentPos.Y - y) <= tolerance;
    }
    
    // Enhanced click with multiple methods and verification
    public static bool RobustClick(int x, int y, int retries = 3) {
        for (int attempt = 0; attempt < retries; attempt++) {
            Console.WriteLine($"Click attempt {attempt + 1} at ({x}, {y})");
            
            // Method 1: SetCursorPos + mouse_event
            if (ClickMethod1(x, y)) {
                Console.WriteLine("Method 1 succeeded");
                return true;
            }
            
            Thread.Sleep(100);
            
            // Method 2: SendInput
            if (ClickMethod2(x, y)) {
                Console.WriteLine("Method 2 succeeded");
                return true;
            }
            
            Thread.Sleep(100);
            
            // Method 3: Window messages
            if (ClickMethod3(x, y)) {
                Console.WriteLine("Method 3 succeeded");
                return true;
            }
            
            Thread.Sleep(200);
        }
        
        return false;
    }
    
    // Method 1: Traditional approach with verification
    static bool ClickMethod1(int x, int y) {
        // Move cursor
        SetCursorPos(x, y);
        Thread.Sleep(50);
        
        // Verify position
        if (!VerifyCursorPosition(x, y)) {
            Console.WriteLine("Failed to position cursor accurately");
            return false;
        }
        
        // Perform click
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(30);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
        
        return true;
    }
    
    // Method 2: SendInput with absolute positioning
    static bool ClickMethod2(int x, int y) {
        // Get screen dimensions
        int screenWidth = Screen.PrimaryScreen.Bounds.Width;
        int screenHeight = Screen.PrimaryScreen.Bounds.Height;
        
        // Convert to absolute coordinates
        int absoluteX = (65535 * x) / screenWidth;
        int absoluteY = (65535 * y) / screenHeight;
        
        INPUT[] inputs = new INPUT[3];
        
        // Move mouse
        inputs[0].type = INPUT_MOUSE;
        inputs[0].u.mi.dx = absoluteX;
        inputs[0].u.mi.dy = absoluteY;
        inputs[0].u.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
        
        // Mouse down
        inputs[1].type = INPUT_MOUSE;
        inputs[1].u.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
        
        // Mouse up
        inputs[2].type = INPUT_MOUSE;
        inputs[2].u.mi.dwFlags = MOUSEEVENTF_LEFTUP;
        
        uint result = SendInput(3, inputs, Marshal.SizeOf(typeof(INPUT)));
        return result == 3;
    }
    
    // Method 3: Direct window message
    static bool ClickMethod3(int x, int y) {
        POINT pt = new POINT { X = x, Y = y };
        IntPtr hwnd = WindowFromPoint(pt);
        
        if (hwnd == IntPtr.Zero) {
            Console.WriteLine("No window found at position");
            return false;
        }
        
        // Convert to client coordinates
        ScreenToClient(hwnd, ref pt);
        
        // Create lParam
        IntPtr lParam = (IntPtr)((pt.Y << 16) | (pt.X & 0xFFFF));
        
        // Send click messages
        PostMessage(hwnd, WM_LBUTTONDOWN, IntPtr.Zero, lParam);
        Thread.Sleep(30);
        PostMessage(hwnd, WM_LBUTTONUP, IntPtr.Zero, lParam);
        
        return true;
    }
    
    // Force close a window at specific coordinates
    public static bool ForceCloseWindow(int x, int y) {
        POINT pt = new POINT { X = x, Y = y };
        IntPtr hwnd = WindowFromPoint(pt);
        
        if (hwnd != IntPtr.Zero) {
            // Try multiple close methods
            PostMessage(hwnd, WM_CLOSE, IntPtr.Zero, IntPtr.Zero);
            Thread.Sleep(100);
            
            // Press Escape key
            keybd_event(VK_ESCAPE, 0, 0, 0);
            Thread.Sleep(50);
            keybd_event(VK_ESCAPE, 0, 2, 0);
            
            return true;
        }
        
        return false;
    }
    
    // Enhanced window focus
    public static bool EnsureWindowFocus(IntPtr hwnd) {
        if (hwnd == IntPtr.Zero) return false;
        
        // Get current thread and target thread
        uint targetThread = GetWindowThreadProcessId(hwnd, out uint targetProcess);
        uint currentThread = GetCurrentThreadId();
        
        // Attach input queues
        AttachThreadInput(currentThread, targetThread, true);
        
        // Bring to front
        SetForegroundWindow(hwnd);
        ShowWindow(hwnd, 3); // SW_MAXIMIZE
        
        // Detach input queues
        AttachThreadInput(currentThread, targetThread, false);
        
        // Force redraw
        InvalidateRect(hwnd, IntPtr.Zero, true);
        UpdateWindow(hwnd);
        
        return GetForegroundWindow() == hwnd;
    }
    
    // Get window at position with details
    public static WindowInfo GetWindowAtPosition(int x, int y) {
        POINT pt = new POINT { X = x, Y = y };
        IntPtr hwnd = WindowFromPoint(pt);
        
        WindowInfo info = new WindowInfo();
        info.Handle = hwnd;
        
        if (hwnd != IntPtr.Zero) {
            RECT rect;
            GetWindowRect(hwnd, out rect);
            info.Left = rect.Left;
            info.Top = rect.Top;
            info.Width = rect.Right - rect.Left;
            info.Height = rect.Bottom - rect.Top;
            info.IsVisible = IsWindowVisible(hwnd);
            info.IsEnabled = IsWindowEnabled(hwnd);
        }
        
        return info;
    }
    
    public class WindowInfo {
        public IntPtr Handle { get; set; }
        public int Left { get; set; }
        public int Top { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
        public bool IsVisible { get; set; }
        public bool IsEnabled { get; set; }
    }
}
"@ -ReferencedAssemblies System.Drawing, System.Windows.Forms

# PowerShell functions for easy use

function Test-WindowAtPosition {
    param(
        [int]$X,
        [int]$Y
    )
    
    $info = [RobustUIAutomation]::GetWindowAtPosition($X, $Y)
    
    Write-Host "Window at ($X, $Y):" -ForegroundColor Cyan
    Write-Host "  Handle: $($info.Handle)"
    Write-Host "  Position: ($($info.Left), $($info.Top))"
    Write-Host "  Size: $($info.Width) x $($info.Height)"
    Write-Host "  Visible: $($info.IsVisible)"
    Write-Host "  Enabled: $($info.IsEnabled)"
    
    return $info
}

function Invoke-RobustClick {
    param(
        [int]$X,
        [int]$Y,
        [int]$Retries = 3,
        [switch]$Verify
    )
    
    Write-Host "Performing robust click at ($X, $Y)" -ForegroundColor Yellow
    
    # Test window first if verify flag is set
    if ($Verify) {
        $window = Test-WindowAtPosition -X $X -Y $Y
        if (-not $window.IsEnabled) {
            Write-Host "Warning: Window is not enabled" -ForegroundColor Red
        }
    }
    
    $result = [RobustUIAutomation]::RobustClick($X, $Y, $Retries)
    
    if ($result) {
        Write-Host "Click successful!" -ForegroundColor Green
    } else {
        Write-Host "Click failed after all attempts" -ForegroundColor Red
    }
    
    return $result
}

function Close-WindowAtPosition {
    param(
        [int]$X,
        [int]$Y
    )
    
    Write-Host "Attempting to close window at ($X, $Y)" -ForegroundColor Yellow
    
    # First try clicking the X button
    $clicked = Invoke-RobustClick -X $X -Y $Y
    Start-Sleep -Milliseconds 500
    
    # Then try force close
    $closed = [RobustUIAutomation]::ForceCloseWindow($X, $Y)
    
    if ($closed) {
        Write-Host "Window close signal sent" -ForegroundColor Green
    }
    
    return $closed
}

function Test-CopilotDialog {
    Write-Host "`nTesting PowerPoint Copilot Dialog Closure" -ForegroundColor Magenta
    Write-Host "=========================================" -ForegroundColor Magenta
    
    # Coordinates for the X button
    $xButton = @{X = 1271; Y = 497}
    
    # Test 1: Verify window exists
    Write-Host "`nTest 1: Checking window at X button position" -ForegroundColor Yellow
    $window = Test-WindowAtPosition @xButton
    
    # Test 2: Try robust click
    Write-Host "`nTest 2: Attempting robust click on X button" -ForegroundColor Yellow
    $clicked = Invoke-RobustClick @xButton -Verify
    
    # Test 3: Try alternative close methods
    if (-not $clicked) {
        Write-Host "`nTest 3: Trying alternative close methods" -ForegroundColor Yellow
        Close-WindowAtPosition @xButton
    }
    
    # Test 4: Try clicking elsewhere and ESC
    Write-Host "`nTest 4: Clicking outside dialog and pressing ESC" -ForegroundColor Yellow
    Invoke-RobustClick -X 500 -Y 400  # Click somewhere else
    Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
    
    Write-Host "`nAll tests completed. Check if Copilot dialog is closed." -ForegroundColor Cyan
}

# Export functions
Export-ModuleMember -Function Test-WindowAtPosition, Invoke-RobustClick, Close-WindowAtPosition, Test-CopilotDialog

Write-Host @"

Robust UI Automation System Loaded!
==================================

Available Functions:
- Test-WindowAtPosition -X <x> -Y <y>
- Invoke-RobustClick -X <x> -Y <y> [-Retries <n>] [-Verify]
- Close-WindowAtPosition -X <x> -Y <y>
- Test-CopilotDialog

To close the Copilot dialog, run:
  Test-CopilotDialog

To perform a verified click:
  Invoke-RobustClick -X 1271 -Y 497 -Verify

"@ -ForegroundColor Green