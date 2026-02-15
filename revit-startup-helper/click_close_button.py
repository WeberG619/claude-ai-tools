#!/usr/bin/env python3
"""
Revit Dialog Close Button Clicker
Uses Windows UI Automation to find and click Close/OK buttons properly
Author: BIM Ops Studio
"""

import time
import sys
import ctypes
from ctypes import wintypes
import subprocess

try:
    import pyautogui
except ImportError:
    print("Installing pyautogui...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "-q"])
    import pyautogui

try:
    import comtypes.client
    from comtypes import COMError
except ImportError:
    print("Installing comtypes...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "comtypes", "-q"])
    import comtypes.client
    from comtypes import COMError

# Initialize UI Automation
UIAutomationCore = comtypes.client.GetModule("UIAutomationCore.dll")
uia = comtypes.client.CreateObject(
    "{ff48dba4-60ef-4201-aa87-54103eef594e}",
    interface=UIAutomationCore.IUIAutomation
)

# Control type IDs
UIA_WindowControlTypeId = 50032
UIA_ButtonControlTypeId = 50000

# Button names to look for (in priority order)
BUTTON_NAMES = ["Close", "OK", "Yes", "Continue", "Accept", "Dismiss", "Got it"]

def get_revit_pids():
    """Get all Revit process IDs"""
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command",
         "(Get-Process -Name '*Revit*' -ErrorAction SilentlyContinue).Id -join ','"],
        capture_output=True, text=True
    )
    pids = result.stdout.strip()
    if pids:
        return [int(p) for p in pids.split(',') if p]
    return []

def find_revit_dialogs():
    """Find all dialog windows belonging to Revit"""
    dialogs = []
    revit_pids = get_revit_pids()

    if not revit_pids:
        return dialogs

    root = uia.GetRootElement()

    # Find all windows
    condition = uia.CreatePropertyCondition(
        UIAutomationCore.UIA_ControlTypePropertyId,
        UIA_WindowControlTypeId
    )

    windows = root.FindAll(UIAutomationCore.TreeScope_Children, condition)

    for i in range(windows.Length):
        try:
            window = windows.GetElement(i)
            pid = window.CurrentProcessId
            name = window.CurrentName or ""

            if pid in revit_pids:
                # Check if it's a dialog (not the main Revit window)
                is_main = "Autodesk Revit" in name and not any(x in name for x in ["Error", "Warning", "Dialog", "External"])
                if not is_main and name:
                    dialogs.append({
                        'element': window,
                        'name': name,
                        'pid': pid
                    })
        except Exception:
            pass

    return dialogs

def find_and_click_button(window_element, button_names=BUTTON_NAMES):
    """Find and click a button in the window"""
    # Find all buttons
    condition = uia.CreatePropertyCondition(
        UIAutomationCore.UIA_ControlTypePropertyId,
        UIA_ButtonControlTypeId
    )

    buttons = window_element.FindAll(UIAutomationCore.TreeScope_Descendants, condition)

    # Try to find buttons in order of preference
    for target_name in button_names:
        for i in range(buttons.Length):
            try:
                button = buttons.GetElement(i)
                btn_name = button.CurrentName or ""

                if target_name.lower() in btn_name.lower():
                    # Try to invoke the button
                    try:
                        invoke_pattern = button.GetCurrentPattern(UIAutomationCore.UIA_InvokePatternId)
                        invoke_pattern.QueryInterface(UIAutomationCore.IUIAutomationInvokePattern).Invoke()
                        return {'success': True, 'button': btn_name}
                    except Exception:
                        # Try clicking by coordinates
                        try:
                            rect = button.CurrentBoundingRectangle
                            x = (rect.left + rect.right) // 2
                            y = (rect.top + rect.bottom) // 2
                            pyautogui.click(x, y)
                            return {'success': True, 'button': btn_name, 'method': 'click'}
                        except Exception:
                            pass
            except Exception:
                pass

    # Fallback: click first available button
    for i in range(buttons.Length):
        try:
            button = buttons.GetElement(i)
            btn_name = button.CurrentName or ""
            rect = button.CurrentBoundingRectangle
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2
            pyautogui.click(x, y)
            return {'success': True, 'button': btn_name, 'fallback': True}
        except Exception:
            pass

    return {'success': False}

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Revit Dialog Close Button Clicker')
    parser.add_argument('--max-attempts', type=int, default=20, help='Maximum attempts')
    parser.add_argument('--delay', type=float, default=0.8, help='Delay between attempts (seconds)')
    parser.add_argument('--initial-delay', type=float, default=3.0, help='Initial delay (seconds)')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')
    args = parser.parse_args()

    if not args.quiet:
        print("\n=== Revit Dialog Close Button Clicker ===")
        print(f"Looking for buttons: {', '.join(BUTTON_NAMES)}")
        print(f"Waiting {args.initial_delay}s for Revit dialogs...\n")

    time.sleep(args.initial_delay)

    dialogs_closed = 0
    consecutive_empty = 0
    max_empty = 3

    for attempt in range(1, args.max_attempts + 1):
        dialogs = find_revit_dialogs()

        if not dialogs:
            consecutive_empty += 1
            if not args.quiet:
                print(f"  [CHECK {attempt}] No Revit dialogs found")

            if consecutive_empty >= max_empty:
                if not args.quiet:
                    print(f"\nNo more dialogs detected after {max_empty} checks.")
                break
        else:
            consecutive_empty = 0

            for dialog in dialogs:
                if not args.quiet:
                    print(f"  [FOUND] Dialog: {dialog['name']}")

                result = find_and_click_button(dialog['element'])

                if result['success']:
                    dialogs_closed += 1
                    msg = "(fallback)" if result.get('fallback') else ""
                    method = f"via {result.get('method', 'invoke')}" if result.get('method') else ""
                    if not args.quiet:
                        print(f"    [CLICKED] Button: {result['button']} {msg} {method}")
                else:
                    if not args.quiet:
                        print(f"    [FAILED] Could not click any button - trying Enter key")
                    pyautogui.press('enter')
                    dialogs_closed += 1

        time.sleep(args.delay)

    if not args.quiet:
        print(f"\n=== Complete ===")
        print(f"Dialogs closed: {dialogs_closed}\n")

    return dialogs_closed

if __name__ == "__main__":
    sys.exit(main())
