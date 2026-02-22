# Simple scroll helper - usage: scroll.ps1 X Y Amount (negative=down, positive=up)
param(
    [Parameter(Mandatory=$true)][int]$X,
    [Parameter(Mandatory=$true)][int]$Y,
    [Parameter(Mandatory=$true)][int]$Amount
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class ScrollHelper {
    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);

    public const int MOUSEEVENTF_WHEEL = 0x0800;

    public static void Scroll(int amount) {
        mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0);
    }
}
"@

[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($X, $Y)
Start-Sleep -Milliseconds 50
[ScrollHelper]::Scroll($Amount)

Write-Output "Scrolled at ($X, $Y) by $Amount"
