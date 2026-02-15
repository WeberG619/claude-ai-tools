#!/usr/bin/env python3
"""
BridgeAI Print MCP Server
Provides printing capabilities for documents
"""

import subprocess
import json
import os
import sys

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

sys.path.insert(0, '/mnt/d/_MCP-SERVERS')

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("bridgeai-print")


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


@mcp.tool()
def list_printers() -> str:
    """
    Get a list of all available printers on this computer.
    Shows printer name, status, and whether it's the default.
    Use this first when user wants to print something.
    """
    try:
        result = _run_ps(
            "Get-Printer | Select-Object Name, PrinterStatus, Default, PortName | ConvertTo-Json",
            timeout=30
        )
        output = result.stdout.strip()
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            # Single printer returns object not array
            output = output[output.index('{'):]
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_default_printer() -> str:
    """
    Get the name of the default printer.
    """
    try:
        result = _run_ps(
            "(Get-Printer | Where-Object {$_.Default -eq $true}).Name",
            timeout=30
        )
        printer_name = result.stdout.strip()
        return json.dumps({"default_printer": printer_name if printer_name else "No default printer set"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def print_file(file_path: str, printer_name: str = None, copies: int = 1) -> str:
    """
    Print a file to the specified printer (or default printer if not specified).
    Supports common file types: PDF, TXT, DOC, DOCX, images.

    Args:
        file_path: Full path to the file to print
        printer_name: Name of printer (optional, uses default if not provided)
        copies: Number of copies to print (default 1)
    """
    # Convert WSL path to Windows path if needed
    if file_path.startswith('/mnt/'):
        # /mnt/d/... -> D:/...
        file_path = file_path[5].upper() + ':' + file_path[6:]

    # Check if file exists
    check_cmd = f"Test-Path '{file_path}'"
    result = _run_ps(check_cmd)
    if 'False' in result.stdout:
        return json.dumps({"error": f"File not found: {file_path}"})

    # Get file extension
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in ['.txt', '.log']:
            # Text files - use Out-Printer
            printer_arg = f"-Name '{printer_name}'" if printer_name else ""
            cmd = f"Get-Content '{file_path}' | Out-Printer {printer_arg}"
            for _ in range(copies):
                _run_ps(cmd, timeout=60)

        elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            # Use Start-Process with -Verb Print
            printer_arg = f"(Get-Printer -Name '{printer_name}').Name" if printer_name else "(Get-Printer | Where-Object {$_.Default}).Name"

            for _ in range(copies):
                # Use shell verb 'print' which works for most document types
                cmd = f"Start-Process -FilePath '{file_path}' -Verb Print -PassThru | Wait-Process -Timeout 30"
                _run_ps(cmd, timeout=60)

        else:
            return json.dumps({
                "error": f"Unsupported file type: {ext}",
                "supported_types": [".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"]
            })

        return json.dumps({
            "success": True,
            "file": file_path,
            "printer": printer_name or "default",
            "copies": copies,
            "message": f"Sent {os.path.basename(file_path)} to printer"
        })

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Print operation timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_print_queue(printer_name: str = None) -> str:
    """
    Get the current print queue (jobs waiting to print).
    Shows all printers if no name specified.
    """
    try:
        if printer_name:
            cmd = f"Get-PrintJob -PrinterName '{printer_name}' | Select-Object Id, DocumentName, JobStatus, Size | ConvertTo-Json"
        else:
            cmd = "Get-Printer | ForEach-Object { $p = $_; Get-PrintJob -PrinterName $_.Name -ErrorAction SilentlyContinue | Select-Object @{N='Printer';E={$p.Name}}, Id, DocumentName, JobStatus } | ConvertTo-Json"

        result = _run_ps(cmd, timeout=30)
        output = result.stdout.strip()
        if not output:
            return json.dumps({"message": "No print jobs in queue", "jobs": []})
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            output = output[output.index('{'):]
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def cancel_print_job(printer_name: str, job_id: int) -> str:
    """
    Cancel a print job that's waiting in the queue.
    Use get_print_queue first to find the job ID.
    """
    try:
        cmd = f"Remove-PrintJob -PrinterName '{printer_name}' -ID {job_id}"
        _run_ps(cmd, timeout=30)
        return json.dumps({
            "success": True,
            "message": f"Cancelled print job {job_id} on {printer_name}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_default_printer(printer_name: str) -> str:
    """
    Set a printer as the default printer.
    """
    try:
        cmd = f"Set-Printer -Name '{printer_name}' -Default"
        result = _run_ps(cmd, timeout=30)
        if result.returncode == 0:
            return json.dumps({
                "success": True,
                "message": f"Set {printer_name} as default printer"
            })
        else:
            return json.dumps({"error": result.stderr or "Failed to set default printer"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
