#!/usr/bin/env python
"""Try all scriptapp variants and check if Resolve is fully loaded."""
import sys
import importlib.machinery
import importlib.util
import time

dll_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
loader = importlib.machinery.ExtensionFileLoader("fusionscript", dll_path)
spec = importlib.util.spec_from_loader("fusionscript", loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

# Try different app names
for name in ["Resolve", "resolve", "DaVinci Resolve", "Fusion", "fusion"]:
    result = module.scriptapp(name)
    print(f"scriptapp('{name}') = {result}")

# Also try with empty string and None
try:
    result = module.scriptapp("")
    print(f"scriptapp('') = {result}")
except:
    pass
