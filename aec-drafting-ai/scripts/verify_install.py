#!/usr/bin/env python3
"""
AEC Drafting AI - Installation Verifier

Checks that all components are properly installed and configured.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check(name, condition, fix_hint=""):
    """Check a condition and print result."""
    if condition:
        print(f"  ✓ {name}")
        return True
    else:
        print(f"  ✗ {name}")
        if fix_hint:
            print(f"    Fix: {fix_hint}")
        return False

def main():
    print("=" * 50)
    print("  AEC Drafting AI - Installation Verification")
    print("=" * 50)
    print()

    all_passed = True

    # 1. Check Python version
    print("[Python Environment]")
    py_version = sys.version_info
    all_passed &= check(
        f"Python {py_version.major}.{py_version.minor}.{py_version.micro}",
        py_version >= (3, 10),
        "Upgrade to Python 3.10+"
    )

    # 2. Check required packages
    print("\n[Python Packages]")
    packages = ["pydantic", "mcp", "numpy"]
    for pkg in packages:
        try:
            __import__(pkg)
            all_passed &= check(f"{pkg} installed", True)
        except ImportError:
            all_passed &= check(f"{pkg} installed", False, f"pip install {pkg}")

    # 3. Check Revit add-in
    print("\n[Revit Add-in]")
    revit_versions = ["2026", "2025", "2024"]
    addin_found = False
    for version in revit_versions:
        addin_path = Path(os.environ.get("APPDATA", "")) / f"Autodesk/Revit/Addins/{version}/RevitMCPBridge2026.dll"
        if addin_path.exists():
            all_passed &= check(f"RevitMCPBridge2026.dll in Revit {version}", True)
            addin_found = True
            break

    if not addin_found:
        all_passed &= check("RevitMCPBridge2026.dll", False, "Run install.ps1 or copy DLL manually")

    # 4. Check Claude Code
    print("\n[Claude Code CLI]")
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        all_passed &= check(f"Claude CLI: {result.stdout.strip()}", result.returncode == 0)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        all_passed &= check("Claude CLI", False, "npm install -g @anthropic/claude-code")

    # 5. Check project registry
    print("\n[Configuration]")
    registry_paths = [
        Path(__file__).parent.parent / "project_registry.json",
        Path(__file__).parent.parent / "config" / "project_registry.json"
    ]
    registry_found = any(p.exists() for p in registry_paths)
    all_passed &= check("Project registry", registry_found, "Copy config/project_registry.json template")

    # 6. Check MCP pipe (only if Revit is running)
    print("\n[Revit Connection]")
    pipe_path = r"\\.\pipe\RevitMCPBridge2026"
    # Can't easily check Windows named pipe from Python, so just note it
    print(f"  ? MCP Pipe: {pipe_path}")
    print("    (Start Revit to verify connection)")

    # Summary
    print()
    print("=" * 50)
    if all_passed:
        print("  All checks passed!")
        print("  You're ready to use AEC Drafting AI")
    else:
        print("  Some checks failed")
        print("  Please fix the issues above")
    print("=" * 50)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
