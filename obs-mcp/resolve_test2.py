#!/usr/bin/env python
"""Debug test: try to connect to DaVinci Resolve with verbose output."""
import sys
import os
import traceback

print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")
print()

# Method 1: Direct DLL load
print("=== Method 1: Direct fusionscript.dll load ===")
try:
    import importlib.machinery
    import importlib.util
    dll_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
    loader = importlib.machinery.ExtensionFileLoader("fusionscript", dll_path)
    spec = importlib.util.spec_from_loader("fusionscript", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    print(f"Module loaded: {module}")
    print(f"Dir: {dir(module)}")

    # Try scriptapp
    resolve = module.scriptapp("Resolve")
    print(f"scriptapp('Resolve') returned: {resolve}")
    if resolve:
        print(f"Product: {resolve.GetProductName()}")
        print(f"Version: {resolve.GetVersionString()}")
    else:
        print("scriptapp returned None - Resolve may need external scripting enabled")

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print()
print("=== Method 2: Via DaVinciResolveScript module ===")
try:
    script_api = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                               "Blackmagic Design", "DaVinci Resolve",
                               "Support", "Developer", "Scripting")
    sys.path.insert(0, os.path.join(script_api, "Modules"))

    import DaVinciResolveScript as dvr
    print(f"Module: {dvr}")

    resolve = dvr.scriptapp("Resolve")
    print(f"scriptapp('Resolve') returned: {resolve}")
    if resolve:
        print(f"Product: {resolve.GetProductName()}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
