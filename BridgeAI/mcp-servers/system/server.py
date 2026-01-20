#!/usr/bin/env python3
"""
BridgeAI System MCP Server
Provides system diagnostics, repair, and maintenance tools
"""

import subprocess
import json
import os
import sys
from datetime import datetime

# Add MCP SDK path
sys.path.insert(0, '/mnt/d/_MCP-SERVERS')

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback for different MCP installations
    from fastmcp import FastMCP

mcp = FastMCP("bridgeai-system")

SCRIPTS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')

def run_powershell(script_name: str, params: dict) -> dict:
    """Run a PowerShell script and return JSON result"""
    script_path = f"D:/_CLAUDE-TOOLS/BridgeAI/scripts/{script_name}"

    # Build argument string
    args = []
    for key, value in params.items():
        if isinstance(value, bool) and value:
            args.append(f"-{key}")
        elif value is not None:
            args.append(f"-{key}")
            args.append(str(value))

    cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # Parse JSON output
        output = result.stdout.strip()
        # Remove any non-JSON prefix (like profile messages)
        if '{' in output:
            json_start = output.index('{')
            output = output[json_start:]
        if '[' in output and ('{' not in output or output.index('[') < output.index('{')):
            json_start = output.index('[')
            output = output[json_start:]
        return json.loads(output)
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse output: {str(e)}", "raw": result.stdout[:500]}
    except Exception as e:
        return {"error": str(e)}


# ============== DIAGNOSTIC TOOLS ==============

@mcp.tool()
def check_system_health() -> str:
    """
    Get a complete health check of the computer.
    Returns CPU, memory, disk, and network status with plain English explanations.
    Use this when user says things like "how is my computer doing" or "is something wrong"
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "health"})
    return json.dumps(result, indent=2)


@mcp.tool()
def check_cpu() -> str:
    """
    Check CPU usage.
    Use when user mentions computer is slow or unresponsive.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "cpu"})
    return json.dumps(result, indent=2)


@mcp.tool()
def check_memory() -> str:
    """
    Check RAM/memory usage.
    Use when user says computer is slow or programs are crashing.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "memory"})
    return json.dumps(result, indent=2)


@mcp.tool()
def check_disk_space() -> str:
    """
    Check available disk space on all drives.
    Use when user mentions running out of space or slow performance.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "disk"})
    return json.dumps(result, indent=2)


@mcp.tool()
def check_network() -> str:
    """
    Check internet connectivity and network status.
    Use when user has internet problems or websites won't load.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "network"})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_running_processes() -> str:
    """
    Get list of programs currently running, sorted by memory usage.
    Use to find what's using resources or identify frozen programs.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "processes"})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_startup_programs() -> str:
    """
    Get list of programs that run when computer starts.
    Use when computer takes long to boot or user wants to speed up startup.
    """
    result = run_powershell("system-diagnostics.ps1", {"Check": "startup"})
    return json.dumps(result, indent=2)


# ============== REPAIR TOOLS ==============

@mcp.tool()
def clear_temp_files(confirm: bool = False) -> str:
    """
    Clear temporary files to free up space.
    Set confirm=True to actually delete, otherwise shows what would be deleted.
    Always preview first (confirm=False), then ask user before confirming.
    """
    params = {"Action": "clear_temp"}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def kill_process(process_name: str, confirm: bool = False) -> str:
    """
    Stop a running program by name.
    Use when a program is frozen or using too many resources.
    Set confirm=True to actually stop it, otherwise shows what would be stopped.
    """
    params = {"Action": "kill_process", "Target": process_name}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def flush_dns(confirm: bool = False) -> str:
    """
    Clear DNS cache to fix website loading issues.
    Use when specific websites won't load but internet works otherwise.
    """
    params = {"Action": "flush_dns"}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def reset_network(confirm: bool = False) -> str:
    """
    Reset network settings to fix connection issues.
    Use when internet isn't working and basic troubleshooting hasn't helped.
    Warning: May temporarily disconnect from WiFi.
    """
    params = {"Action": "reset_network"}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def empty_recycle_bin(confirm: bool = False) -> str:
    """
    Empty the recycle bin to free up space.
    Shows how many items are in the bin first.
    """
    params = {"Action": "empty_trash"}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def find_large_files(search_path: str = None) -> str:
    """
    Find large files (over 100MB) that might be taking up space.
    Defaults to searching user folders. Can specify a path to search.
    """
    params = {"Action": "find_large_files"}
    if search_path:
        params["Target"] = search_path
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def run_disk_cleanup(confirm: bool = False) -> str:
    """
    Run Windows Disk Cleanup to free space.
    This is the official Windows cleanup tool.
    """
    params = {"Action": "disk_cleanup"}
    if confirm:
        params["Confirm"] = True
    result = run_powershell("system-repair.ps1", params)
    return json.dumps(result, indent=2)


# ============== INFO TOOLS ==============

@mcp.tool()
def get_system_info() -> str:
    """
    Get basic information about this computer.
    Returns OS version, computer name, user name.
    """
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command",
             "$os = Get-CimInstance Win32_OperatingSystem; " +
             "$cs = Get-CimInstance Win32_ComputerSystem; " +
             "@{computer_name=$env:COMPUTERNAME; user_name=$env:USERNAME; " +
             "os_name=$os.Caption; os_version=$os.Version; " +
             "manufacturer=$cs.Manufacturer; model=$cs.Model} | ConvertTo-Json"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if '{' in output:
            output = output[output.index('{'):]
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_installed_programs() -> str:
    """
    Get list of installed programs on this computer.
    Useful for checking what software is available.
    """
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command",
             "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | " +
             "Where-Object {$_.DisplayName} | " +
             "Select-Object DisplayName, DisplayVersion, Publisher | " +
             "Sort-Object DisplayName | " +
             "ConvertTo-Json"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            output = output[output.index('{'):]
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
