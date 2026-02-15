#!/usr/bin/env python
"""Quick test: connect to DaVinci Resolve scripting API."""
import sys
import os

# Set up environment for Resolve scripting
resolve_script_api = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                                   "Blackmagic Design", "DaVinci Resolve",
                                   "Support", "Developer", "Scripting")
resolve_script_lib = os.path.join("C:\\Program Files", "Blackmagic Design",
                                   "DaVinci Resolve", "fusionscript.dll")
os.environ["RESOLVE_SCRIPT_API"] = resolve_script_api
os.environ["RESOLVE_SCRIPT_LIB"] = resolve_script_lib
sys.path.insert(0, os.path.join(resolve_script_api, "Modules"))

import DaVinciResolveScript as dvr_script

resolve = dvr_script.scriptapp("Resolve")
if resolve is None:
    print("ERROR: Could not connect to DaVinci Resolve.")
    print("Make sure Resolve is running and scripting is enabled.")
    print("(Preferences > General > External scripting using = Local)")
    sys.exit(1)

print(f"Connected to: {resolve.GetProductName()}")
print(f"Version: {resolve.GetVersionString()}")
print(f"Current page: {resolve.GetCurrentPage()}")

pm = resolve.GetProjectManager()
proj = pm.GetCurrentProject()
if proj:
    print(f"Current project: {proj.GetName()}")
else:
    print("No project currently open")
print("API connection OK!")
