# Revit Live View Capture

Automatically captures screenshots of open Revit windows so Claude can see what you see.

## Auto-Start (ENABLED)

This system starts automatically when you log into Windows. No manual action needed.

**Scheduled Tasks Installed:**
- `RevitLiveViewDaemon` - Starts capture daemon at Windows login
- `RevitLiveViewWatchdog` - Checks every 5 minutes, restarts daemon if crashed

## Files

| File | Purpose |
|------|---------|
| `capture-now.ps1` | One-time capture (use anytime) |
| `revit-capture-daemon.ps1` | Continuous capture daemon |
| `start-daemon.bat` | Start daemon with visible console |
| `start-background.vbs` | Start daemon hidden (no window) |
| `stop-daemon.ps1` | Stop the running daemon |
| `watchdog.ps1` | Auto-restart daemon if it crashes |
| `check-status.ps1` | Quick status check of entire system |

## Quick Status Check
```powershell
powershell -ExecutionPolicy Bypass -File "D:\_CLAUDE-TOOLS\revit-live-view\check-status.ps1"
```

## Manual Usage (if needed)

### Quick Capture (One Time)
```powershell
powershell -ExecutionPolicy Bypass -File "D:\_CLAUDE-TOOLS\revit-live-view\capture-now.ps1"
```

### Start Continuous Capture
```batch
# With visible console:
D:\_CLAUDE-TOOLS\revit-live-view\start-daemon.bat

# Hidden in background:
wscript "D:\_CLAUDE-TOOLS\revit-live-view\start-background.vbs"
```

### Stop Daemon
```powershell
powershell -ExecutionPolicy Bypass -File "D:\_CLAUDE-TOOLS\revit-live-view\stop-daemon.ps1"
```

## Output Files

| File | Description |
|------|-------------|
| `D:\revit_live_view.png` | Screenshot of Revit (single instance) |
| `D:\revit_live_view_1.png` | Screenshot of first Revit instance |
| `D:\revit_live_view_2.png` | Screenshot of second Revit instance |
| `D:\revit_live_status.json` | Status info (timestamp, which windows captured) |

## Configuration

Edit `revit-capture-daemon.ps1` parameters:
- `$IntervalSeconds` - Capture frequency (default: 5 seconds)
- `$OutputFolder` - Where to save screenshots (default: D:\)

## Integration with Claude Code

Claude can read the live view anytime:
```
Read /mnt/d/revit_live_view.png
```

Or check status:
```
Read /mnt/d/revit_live_status.json
```

## Troubleshooting

If daemon isn't running:
1. Run `check-status.ps1` to see what's wrong
2. Check Task Scheduler for `RevitLiveView*` tasks
3. Manually start with `start-background.vbs`
4. Check `watchdog.log` for restart history
