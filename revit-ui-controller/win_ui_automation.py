"""
Windows UI Automation helpers for Revit UI control.
Uses PowerShell + System.Windows.Automation to enumerate and interact with UI elements.
"""

import subprocess
import json
from typing import Optional, Dict, List, Any


def run_powershell(script: str, capture_output: bool = True) -> tuple[str, str, int]:
    """Execute PowerShell script and return stdout, stderr, returncode"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=capture_output,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


def get_revit_window_info() -> Optional[Dict[str, Any]]:
    """Get information about the Revit main window."""
    script = """
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes

    $revitProc = Get-Process -Name "Revit" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revitProc -eq $null) {
        Write-Output '{"error": "Revit not running"}'
        return
    }

    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
        $revitProc.Id
    )
    $revitWindow = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)

    if ($revitWindow -eq $null) {
        Write-Output '{"error": "Could not find Revit window"}'
        return
    }

    $rect = $revitWindow.Current.BoundingRectangle
    $result = @{
        processId = $revitProc.Id
        name = $revitWindow.Current.Name
        x = $rect.X
        y = $rect.Y
        width = $rect.Width
        height = $rect.Height
    }

    Write-Output ($result | ConvertTo-Json -Compress)
    """

    stdout, stderr, code = run_powershell(script)
    if code == 0 and stdout.strip():
        try:
            return json.loads(stdout.strip())
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {stdout}"}
    return {"error": stderr or "Unknown error"}


def get_ui_elements(element_type: str = "all", max_depth: int = 3) -> List[Dict[str, Any]]:
    """
    Get UI elements from Revit window.
    element_type: "all", "Button", "MenuItem", "TabItem", "Edit", "ComboBox"
    """
    script = f"""
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes

    $revitProc = Get-Process -Name "Revit" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revitProc -eq $null) {{
        Write-Output '[]'
        return
    }}

    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
        $revitProc.Id
    )
    $revitWindow = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)

    if ($revitWindow -eq $null) {{
        Write-Output '[]'
        return
    }}

    $elements = @()

    function Get-UIElements {{
        param($parent, $depth)

        if ($depth -gt {max_depth}) {{ return }}

        $children = $parent.FindAll([System.Windows.Automation.TreeScope]::Children,
            [System.Windows.Automation.Condition]::TrueCondition)

        foreach ($child in $children) {{
            try {{
                $controlType = $child.Current.ControlType.ProgrammaticName -replace "ControlType.", ""

                if ("{element_type}" -eq "all" -or $controlType -eq "{element_type}") {{
                    $rect = $child.Current.BoundingRectangle
                    if ($rect.Width -gt 0 -and $rect.Height -gt 0) {{
                        $script:elements += @{{
                            name = $child.Current.Name
                            automationId = $child.Current.AutomationId
                            controlType = $controlType
                            x = [int]$rect.X
                            y = [int]$rect.Y
                            width = [int]$rect.Width
                            height = [int]$rect.Height
                            isEnabled = $child.Current.IsEnabled
                        }}
                    }}
                }}

                Get-UIElements -parent $child -depth ($depth + 1)
            }} catch {{
                # Skip inaccessible elements
            }}
        }}
    }}

    Get-UIElements -parent $revitWindow -depth 0

    # Limit output size
    $elements = $elements | Select-Object -First 200
    Write-Output ($elements | ConvertTo-Json -Compress)
    """

    stdout, stderr, code = run_powershell(script)
    if code == 0 and stdout.strip():
        try:
            result = json.loads(stdout.strip())
            return result if isinstance(result, list) else [result]
        except json.JSONDecodeError:
            return []
    return []


def find_element_by_name(name: str, partial_match: bool = True) -> Optional[Dict[str, Any]]:
    """Find a UI element by name."""
    elements = get_ui_elements()

    for elem in elements:
        elem_name = elem.get("name", "")
        if partial_match:
            if name.lower() in elem_name.lower():
                return elem
        else:
            if name.lower() == elem_name.lower():
                return elem

    return None


def click_at(x: int, y: int) -> bool:
    """Click at screen coordinates."""
    script = f"""
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class MouseOps {{
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
    public const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP = 0x0004;

    public static void Click(int x, int y) {{
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(50);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        System.Threading.Thread.Sleep(10);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }}
}}
'@
    [MouseOps]::Click({x}, {y})
    Write-Output "Clicked at ({x}, {y})"
    """

    stdout, stderr, code = run_powershell(script)
    return code == 0


def click_element(element_name: str) -> Dict[str, Any]:
    """Find an element by name and click its center."""
    elem = find_element_by_name(element_name)

    if elem is None:
        return {"success": False, "error": f"Element '{element_name}' not found"}

    # Calculate center of element
    center_x = elem["x"] + elem["width"] // 2
    center_y = elem["y"] + elem["height"] // 2

    success = click_at(center_x, center_y)

    return {
        "success": success,
        "element": elem,
        "clickedAt": {"x": center_x, "y": center_y}
    }


def send_keys_to_revit(keys: str) -> bool:
    """Send keystrokes to Revit window."""
    # Escape special characters for SendKeys
    escaped = keys.replace('{', '{{').replace('}', '}}').replace('+', '{+}').replace('^', '{^}').replace('%', '{%}')

    script = f"""
    Add-Type -AssemblyName System.Windows.Forms

    $revitProc = Get-Process -Name "Revit" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revitProc -eq $null) {{
        Write-Output "Revit not running"
        exit 1
    }}

    # Bring Revit to foreground
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI {{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}}
'@
    [WinAPI]::SetForegroundWindow($revitProc.MainWindowHandle)
    Start-Sleep -Milliseconds 100

    [System.Windows.Forms.SendKeys]::SendWait("{escaped}")
    Write-Output "Sent keys"
    """

    stdout, stderr, code = run_powershell(script)
    return code == 0


def get_dialog_info() -> Optional[Dict[str, Any]]:
    """Get information about any open dialog in Revit."""
    script = """
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes

    $revitProc = Get-Process -Name "Revit" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($revitProc -eq $null) {
        Write-Output '{"error": "Revit not running"}'
        return
    }

    $root = [System.Windows.Automation.AutomationElement]::RootElement

    # Find all windows belonging to Revit process
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
        $revitProc.Id
    )
    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)

    $dialogs = @()
    foreach ($win in $windows) {
        $controlType = $win.Current.ControlType.ProgrammaticName
        if ($controlType -eq "ControlType.Window") {
            $name = $win.Current.Name
            if ($name -and $name -ne "" -and -not $name.StartsWith("Autodesk Revit")) {
                # Find buttons in this dialog
                $buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                    [System.Windows.Automation.ControlType]::Button
                )
                $buttons = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)

                $buttonNames = @()
                foreach ($btn in $buttons) {
                    if ($btn.Current.Name) {
                        $buttonNames += $btn.Current.Name
                    }
                }

                $rect = $win.Current.BoundingRectangle
                $dialogs += @{
                    title = $name
                    x = [int]$rect.X
                    y = [int]$rect.Y
                    width = [int]$rect.Width
                    height = [int]$rect.Height
                    buttons = $buttonNames
                }
            }
        }
    }

    if ($dialogs.Count -eq 0) {
        Write-Output '{"hasDialog": false}'
    } else {
        $result = @{
            hasDialog = $true
            dialogs = $dialogs
        }
        Write-Output ($result | ConvertTo-Json -Compress -Depth 3)
    }
    """

    stdout, stderr, code = run_powershell(script)
    if code == 0 and stdout.strip():
        try:
            return json.loads(stdout.strip())
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {stdout}"}
    return {"error": stderr or "Unknown error"}


def click_dialog_button(button_name: str) -> Dict[str, Any]:
    """Click a button in the currently open dialog."""
    dialog_info = get_dialog_info()

    if not dialog_info.get("hasDialog"):
        return {"success": False, "error": "No dialog open"}

    # Search for button in all dialogs
    for dialog in dialog_info.get("dialogs", []):
        if button_name in dialog.get("buttons", []):
            # Find the button element
            script = f"""
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes

            $revitProc = Get-Process -Name "Revit" -ErrorAction SilentlyContinue | Select-Object -First 1
            $root = [System.Windows.Automation.AutomationElement]::RootElement

            # Find dialog by title
            $dialogCondition = New-Object System.Windows.Automation.AndCondition(
                (New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
                    $revitProc.Id
                )),
                (New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::NameProperty,
                    "{dialog['title']}"
                ))
            )

            $dialog = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $dialogCondition)
            if ($dialog -eq $null) {{
                Write-Output '{{"success": false, "error": "Dialog not found"}}'
                return
            }}

            # Find button
            $buttonCondition = New-Object System.Windows.Automation.AndCondition(
                (New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                    [System.Windows.Automation.ControlType]::Button
                )),
                (New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::NameProperty,
                    "{button_name}"
                ))
            )

            $button = $dialog.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
            if ($button -eq $null) {{
                Write-Output '{{"success": false, "error": "Button not found"}}'
                return
            }}

            # Invoke the button
            $invokePattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            $invokePattern.Invoke()

            Write-Output '{{"success": true, "clicked": "{button_name}"}}'
            """

            stdout, stderr, code = run_powershell(script)
            if code == 0 and stdout.strip():
                try:
                    return json.loads(stdout.strip())
                except json.JSONDecodeError:
                    pass

            return {"success": False, "error": stderr or "Failed to click button"}

    return {"success": False, "error": f"Button '{button_name}' not found in any dialog"}


if __name__ == "__main__":
    # Test the module
    print("Testing Revit UI Automation...")

    print("\n1. Getting Revit window info:")
    info = get_revit_window_info()
    print(json.dumps(info, indent=2))

    print("\n2. Getting UI elements (buttons):")
    elements = get_ui_elements("Button", max_depth=2)
    print(f"Found {len(elements)} buttons")
    for elem in elements[:5]:
        print(f"  - {elem.get('name', 'unnamed')} at ({elem.get('x')}, {elem.get('y')})")

    print("\n3. Checking for dialogs:")
    dialog = get_dialog_info()
    print(json.dumps(dialog, indent=2))
