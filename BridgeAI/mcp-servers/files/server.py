#!/usr/bin/env python3
"""
BridgeAI File Helper MCP Server
User-friendly file operations for everyday tasks
"""

import subprocess
import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/mnt/d/_MCP-SERVERS')

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("bridgeai-files")


def get_windows_path(path: str) -> str:
    """Convert WSL path to Windows path if needed"""
    if path.startswith('/mnt/'):
        return path[5].upper() + ':' + path[6:].replace('/', '\\')
    return path


def get_user_folders() -> dict:
    """Get common user folder paths"""
    home = os.path.expanduser('~')
    # For WSL, map to Windows user folders
    win_user = subprocess.run(
        ["powershell.exe", "-Command", "$env:USERPROFILE"],
        capture_output=True, text=True
    ).stdout.strip()

    return {
        "desktop": os.path.join(win_user, "Desktop"),
        "documents": os.path.join(win_user, "Documents"),
        "downloads": os.path.join(win_user, "Downloads"),
        "pictures": os.path.join(win_user, "Pictures"),
        "music": os.path.join(win_user, "Music"),
        "videos": os.path.join(win_user, "Videos"),
    }


@mcp.tool()
def get_common_folders() -> str:
    """
    Get paths to common user folders (Desktop, Documents, Downloads, etc.)
    Use this to help user navigate to their files.
    """
    folders = get_user_folders()
    return json.dumps(folders, indent=2)


@mcp.tool()
def list_folder(folder_path: str = None, folder_name: str = None) -> str:
    """
    List contents of a folder.
    Can use folder_path for specific path, or folder_name for common folders
    (desktop, documents, downloads, pictures, music, videos).

    Returns files and folders with sizes and dates.
    """
    if folder_name:
        folders = get_user_folders()
        if folder_name.lower() in folders:
            folder_path = folders[folder_name.lower()]
        else:
            return json.dumps({"error": f"Unknown folder name: {folder_name}. Use: desktop, documents, downloads, pictures, music, videos"})

    if not folder_path:
        return json.dumps({"error": "Provide either folder_path or folder_name"})

    win_path = get_windows_path(folder_path)

    try:
        cmd = f"""
        Get-ChildItem -Path '{win_path}' | Select-Object Name,
            @{{N='Type';E={{if($_.PSIsContainer){{'Folder'}}else{{'File'}}}}}},
            @{{N='Size_MB';E={{[math]::Round($_.Length/1MB, 2)}}}},
            @{{N='Modified';E={{$_.LastWriteTime.ToString('yyyy-MM-dd HH:mm')}}}} |
        ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if not output:
            return json.dumps({"folder": win_path, "contents": [], "message": "Folder is empty"})
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            output = '[' + output[output.index('{'):] + ']'
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_files(search_term: str, folder_name: str = None, folder_path: str = None, file_type: str = None) -> str:
    """
    Search for files by name.

    Args:
        search_term: What to search for in file names
        folder_name: Common folder to search (desktop, documents, downloads, etc.)
        folder_path: Specific path to search (optional)
        file_type: Filter by extension like 'pdf', 'doc', 'jpg' (optional)

    Example: search_files("tax", folder_name="documents", file_type="pdf")
    """
    if folder_name:
        folders = get_user_folders()
        if folder_name.lower() in folders:
            folder_path = folders[folder_name.lower()]

    if not folder_path:
        # Default to user profile
        folder_path = subprocess.run(
            ["powershell.exe", "-Command", "$env:USERPROFILE"],
            capture_output=True, text=True
        ).stdout.strip()

    win_path = get_windows_path(folder_path)

    # Build filter
    filter_pattern = f"*{search_term}*"
    if file_type:
        filter_pattern = f"*{search_term}*.{file_type.lstrip('.')}"

    try:
        cmd = f"""
        Get-ChildItem -Path '{win_path}' -Recurse -Filter '{filter_pattern}' -ErrorAction SilentlyContinue |
        Select-Object FullName,
            @{{N='Size_MB';E={{[math]::Round($_.Length/1MB, 2)}}}},
            @{{N='Modified';E={{$_.LastWriteTime.ToString('yyyy-MM-dd')}}}} |
        Select-Object -First 50 |
        ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout.strip()
        if not output:
            return json.dumps({"search_term": search_term, "results": [], "message": "No files found"})
        if '[' in output:
            output = output[output.index('['):]
        elif '{' in output:
            output = '[' + output[output.index('{'):] + ']'
        return output
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def create_folder(folder_path: str = None, folder_name: str = None, parent_folder: str = None) -> str:
    """
    Create a new folder.

    Args:
        folder_path: Full path for new folder, OR
        folder_name: Name for new folder
        parent_folder: Where to create it (desktop, documents, etc.) - used with folder_name
    """
    if folder_name and parent_folder:
        folders = get_user_folders()
        if parent_folder.lower() in folders:
            folder_path = os.path.join(folders[parent_folder.lower()], folder_name)
        else:
            return json.dumps({"error": f"Unknown parent folder: {parent_folder}"})

    if not folder_path:
        return json.dumps({"error": "Provide folder_path or both folder_name and parent_folder"})

    win_path = get_windows_path(folder_path)

    try:
        cmd = f"New-Item -Path '{win_path}' -ItemType Directory -Force | Select-Object FullName | ConvertTo-Json"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        return json.dumps({
            "success": True,
            "created": win_path,
            "message": f"Created folder: {os.path.basename(win_path)}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def move_file(source_path: str, destination_folder: str = None, destination_path: str = None) -> str:
    """
    Move a file to a new location.

    Args:
        source_path: File to move
        destination_folder: Common folder name (desktop, documents, etc.), OR
        destination_path: Full destination path
    """
    if destination_folder:
        folders = get_user_folders()
        if destination_folder.lower() in folders:
            destination_path = folders[destination_folder.lower()]
        else:
            return json.dumps({"error": f"Unknown destination folder: {destination_folder}"})

    if not destination_path:
        return json.dumps({"error": "Provide destination_folder or destination_path"})

    win_source = get_windows_path(source_path)
    win_dest = get_windows_path(destination_path)

    try:
        cmd = f"Move-Item -Path '{win_source}' -Destination '{win_dest}' -PassThru | Select-Object FullName | ConvertTo-Json"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        return json.dumps({
            "success": True,
            "from": win_source,
            "to": win_dest,
            "message": f"Moved {os.path.basename(win_source)} to {destination_folder or destination_path}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def copy_file(source_path: str, destination_folder: str = None, destination_path: str = None) -> str:
    """
    Copy a file to a new location.

    Args:
        source_path: File to copy
        destination_folder: Common folder name (desktop, documents, etc.), OR
        destination_path: Full destination path
    """
    if destination_folder:
        folders = get_user_folders()
        if destination_folder.lower() in folders:
            destination_path = folders[destination_folder.lower()]

    if not destination_path:
        return json.dumps({"error": "Provide destination_folder or destination_path"})

    win_source = get_windows_path(source_path)
    win_dest = get_windows_path(destination_path)

    try:
        cmd = f"Copy-Item -Path '{win_source}' -Destination '{win_dest}' -PassThru | Select-Object FullName | ConvertTo-Json"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        return json.dumps({
            "success": True,
            "from": win_source,
            "to": win_dest,
            "message": f"Copied {os.path.basename(win_source)}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def delete_file(file_path: str, confirm: bool = False) -> str:
    """
    Delete a file. ALWAYS preview first (confirm=False), then ask user before confirming.

    Args:
        file_path: File to delete
        confirm: Must be True to actually delete
    """
    win_path = get_windows_path(file_path)

    # Check if file exists
    try:
        cmd = f"Test-Path '{win_path}'"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        if 'False' in result.stdout:
            return json.dumps({"error": f"File not found: {win_path}"})

        # Get file info
        cmd = f"Get-Item '{win_path}' | Select-Object Name, @{{N='Size_MB';E={{[math]::Round($_.Length/1MB, 2)}}}} | ConvertTo-Json"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )

        if not confirm:
            return json.dumps({
                "action": "delete",
                "file": win_path,
                "confirm_required": True,
                "message": f"Ready to delete {os.path.basename(win_path)}. Call again with confirm=True to proceed."
            })

        # Actually delete
        cmd = f"Remove-Item -Path '{win_path}' -Force"
        subprocess.run(["powershell.exe", "-Command", cmd], timeout=30)
        return json.dumps({
            "success": True,
            "deleted": win_path,
            "message": f"Deleted {os.path.basename(win_path)}"
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def rename_file(file_path: str, new_name: str) -> str:
    """
    Rename a file.

    Args:
        file_path: File to rename
        new_name: New name for the file (just the name, not full path)
    """
    win_path = get_windows_path(file_path)

    try:
        cmd = f"Rename-Item -Path '{win_path}' -NewName '{new_name}' -PassThru | Select-Object FullName | ConvertTo-Json"
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        return json.dumps({
            "success": True,
            "old_name": os.path.basename(win_path),
            "new_name": new_name,
            "message": f"Renamed to {new_name}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def open_file(file_path: str) -> str:
    """
    Open a file with its default application.
    Works for documents, images, videos, etc.
    """
    win_path = get_windows_path(file_path)

    try:
        cmd = f"Start-Process '{win_path}'"
        subprocess.run(["powershell.exe", "-Command", cmd], timeout=10)
        return json.dumps({
            "success": True,
            "opened": win_path,
            "message": f"Opened {os.path.basename(win_path)}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def open_folder(folder_path: str = None, folder_name: str = None) -> str:
    """
    Open a folder in File Explorer.

    Args:
        folder_path: Full path to folder, OR
        folder_name: Common folder (desktop, documents, downloads, etc.)
    """
    if folder_name:
        folders = get_user_folders()
        if folder_name.lower() in folders:
            folder_path = folders[folder_name.lower()]
        else:
            return json.dumps({"error": f"Unknown folder: {folder_name}"})

    if not folder_path:
        return json.dumps({"error": "Provide folder_path or folder_name"})

    win_path = get_windows_path(folder_path)

    try:
        cmd = f"explorer.exe '{win_path}'"
        subprocess.run(["powershell.exe", "-Command", cmd], timeout=10)
        return json.dumps({
            "success": True,
            "opened": win_path,
            "message": f"Opened folder in File Explorer"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def create_text_file(file_name: str, content: str, folder_name: str = None, folder_path: str = None) -> str:
    """
    Create a new text file with content.

    Args:
        file_name: Name for the file (will add .txt if no extension)
        content: Text to put in the file
        folder_name: Common folder (desktop, documents, etc.), OR
        folder_path: Full path where to save
    """
    if folder_name:
        folders = get_user_folders()
        if folder_name.lower() in folders:
            folder_path = folders[folder_name.lower()]

    if not folder_path:
        folder_path = get_user_folders()["documents"]

    # Add .txt extension if none provided
    if '.' not in file_name:
        file_name += '.txt'

    full_path = os.path.join(folder_path, file_name)
    win_path = get_windows_path(full_path)

    try:
        # Escape content for PowerShell
        escaped_content = content.replace("'", "''")
        cmd = f"Set-Content -Path '{win_path}' -Value '{escaped_content}'"
        subprocess.run(["powershell.exe", "-Command", cmd], timeout=30)
        return json.dumps({
            "success": True,
            "created": win_path,
            "message": f"Created {file_name}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
