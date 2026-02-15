# Revit Startup Dialog Auto-Closer

Automatically finds and clicks "Close" buttons on Revit add-in dialogs that appear at startup.

## Quick Start

**Option 1: Double-click the batch file**
```
auto_close_dialogs.bat
```

**Option 2: Run from command line**
```powershell
# PowerShell version
powershell.exe -ExecutionPolicy Bypass -File "D:\_CLAUDE-TOOLS\revit-startup-helper\click_close_button.ps1"

# Python version (more reliable)
python "D:\_CLAUDE-TOOLS\revit-startup-helper\click_close_button.py"
```

## How It Works

1. Uses Windows UI Automation to find Revit dialog windows
2. Looks for buttons named: Close, OK, Yes, Continue, Accept
3. Clicks the first matching button using proper UI Automation (not just sending keys)
4. Falls back to Enter key if no button can be clicked

## Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max-attempts` | 20 | Maximum dialogs to try closing |
| `--delay` | 0.8s | Delay between attempts |
| `--initial-delay` | 3.0s | Wait before starting (let Revit show dialogs) |
| `--quiet` | false | Suppress output |

## Example

```powershell
# Close dialogs with 5 second initial wait
python click_close_button.py --initial-delay 5

# Quick silent mode
python click_close_button.py --quiet --initial-delay 2
```

## Scheduled Task (Auto-run with Revit)

To run automatically when Revit starts, create a Windows Scheduled Task:
1. Trigger: On program start (Revit.exe)
2. Action: Run `auto_close_dialogs.bat`
3. Delay: 5 seconds after trigger

---
*BIM Ops Studio*
