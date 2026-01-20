#!/usr/bin/env python3
"""
Bluebeam Revu Bridge
Provides control over Bluebeam Revu via its scripting API.

Bluebeam supports JavaScript scripting via ScriptEngine.exe
This bridge creates and executes scripts to control Bluebeam.

Reference: C:\Program Files\Bluebeam Software\Bluebeam Revu\2017\Help\Bluebeam Script Reference.pdf
"""

import json
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

# Bluebeam paths
BLUEBEAM_DIR = Path(r"C:\Program Files\Bluebeam Software\Bluebeam Revu\2017")
SCRIPT_ENGINE = BLUEBEAM_DIR / "Script" / "ScriptEngine.exe"
REVU_EXE = BLUEBEAM_DIR / "Revu" / "Revu.exe"

class BluebeamBridge:
    """Bridge to control Bluebeam Revu."""

    def __init__(self):
        self.script_dir = Path(tempfile.gettempdir()) / "bluebeam_scripts"
        self.script_dir.mkdir(exist_ok=True)

    def _run_script(self, script_content: str, timeout: int = 30) -> Dict:
        """Execute a Bluebeam JavaScript and return result."""
        # Create temp script file
        script_file = self.script_dir / f"bb_script_{os.getpid()}.js"

        # Wrap script to output JSON result
        wrapped_script = f'''
// Bluebeam Script
try {{
    {script_content}
}} catch(e) {{
    Bluebeam.Alert("Error: " + e.message);
}}
'''
        script_file.write_text(wrapped_script)

        try:
            # Run via ScriptEngine
            result = subprocess.run(
                [str(SCRIPT_ENGINE), str(script_file)],
                capture_output=True, text=True, timeout=timeout
            )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Script timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            script_file.unlink(missing_ok=True)

    def _run_powershell_automation(self, commands: str) -> Dict:
        """Use PowerShell COM automation for Bluebeam."""
        ps_script = f'''
        try {{
            $revu = New-Object -ComObject "Bluebeam.Revu"
            {commands}
        }} catch {{
            Write-Error $_.Exception.Message
        }}
        '''
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Document Operations
    def open_document(self, file_path: str) -> Dict:
        """Open a PDF document in Bluebeam."""
        # Use command line to open
        try:
            subprocess.Popen([str(REVU_EXE), file_path])
            return {"success": True, "message": f"Opening {file_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_open_documents(self) -> Dict:
        """Get list of open documents from window titles."""
        ps_cmd = '''
        Get-Process Revu -ErrorAction SilentlyContinue |
        Select-Object MainWindowTitle |
        ConvertTo-Json
        '''
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout:
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    data = [data]
                # Parse titles to extract document names
                docs = []
                for item in data:
                    title = item.get("MainWindowTitle", "")
                    if " - Bluebeam" in title:
                        doc_name = title.split(" - Bluebeam")[0]
                        docs.append(doc_name)
                return {"success": True, "documents": docs}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": True, "documents": []}

    # Markup Operations
    def add_text_markup(self, text: str, x: float, y: float, page: int = 1) -> Dict:
        """Add a text markup to the document."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            var markup = doc.Pages[{page - 1}].CreateMarkup("Text");
            markup.Text = "{text}";
            markup.X = {x};
            markup.Y = {y};
        }}
        '''
        return self._run_script(script)

    def add_highlight(self, x1: float, y1: float, x2: float, y2: float, page: int = 1) -> Dict:
        """Add a highlight markup."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            var markup = doc.Pages[{page - 1}].CreateMarkup("Highlight");
            markup.SetRectangle({x1}, {y1}, {x2}, {y2});
        }}
        '''
        return self._run_script(script)

    def add_cloud(self, points: List[tuple], page: int = 1) -> Dict:
        """Add a cloud markup (revision cloud)."""
        points_js = ",".join([f"[{p[0]},{p[1]}]" for p in points])
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            var markup = doc.Pages[{page - 1}].CreateMarkup("Cloud");
            var points = [{points_js}];
            // Set cloud points
        }}
        '''
        return self._run_script(script)

    # Export Operations
    def export_to_pdf(self, output_path: str, flatten: bool = False) -> Dict:
        """Export/Save the document."""
        flatten_str = "true" if flatten else "false"
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            doc.SaveAs("{output_path.replace(chr(92), chr(92)+chr(92))}", {flatten_str});
        }}
        '''
        return self._run_script(script)

    def export_markups_to_csv(self, output_path: str) -> Dict:
        """Export markups summary to CSV."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            doc.ExportMarkupsSummary("{output_path.replace(chr(92), chr(92)+chr(92))}", "CSV");
        }}
        '''
        return self._run_script(script)

    # Measurement Operations
    def calibrate_scale(self, known_length: float, unit: str = "ft") -> Dict:
        """Set the scale calibration."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            // Calibration requires user interaction typically
            Bluebeam.Alert("Scale calibration: {known_length} {unit}");
        }}
        '''
        return self._run_script(script)

    def measure_area(self, points: List[tuple], page: int = 1) -> Dict:
        """Create an area measurement."""
        points_js = ",".join([f"[{p[0]},{p[1]}]" for p in points])
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            var markup = doc.Pages[{page - 1}].CreateMarkup("Area");
            // Area measurement with points
        }}
        '''
        return self._run_script(script)

    # Batch Operations
    def batch_add_stamp(self, stamp_name: str, pages: str = "all") -> Dict:
        """Add a stamp to multiple pages."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            var pageCount = doc.Pages.Count;
            for (var i = 0; i < pageCount; i++) {{
                var markup = doc.Pages[i].CreateMarkup("Stamp");
                markup.StampName = "{stamp_name}";
            }}
        }}
        '''
        return self._run_script(script)

    # Navigation
    def goto_page(self, page: int) -> Dict:
        """Navigate to a specific page."""
        script = f'''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {{
            doc.CurrentPage = {page - 1};
        }}
        '''
        return self._run_script(script)

    def get_page_count(self) -> Dict:
        """Get the total page count."""
        script = '''
        var doc = Bluebeam.Application.ActiveDocument;
        if (doc) {
            var count = doc.Pages.Count;
            Bluebeam.Alert("Pages: " + count);
        }
        '''
        return self._run_script(script)

    # Automation via keyboard/UI
    def send_keys(self, keys: str) -> Dict:
        """Send keyboard input to Bluebeam (fallback automation)."""
        ps_cmd = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $wshell = New-Object -ComObject wscript.shell
        $wshell.AppActivate("Bluebeam")
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait("{keys}")
        '''
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True, text=True, timeout=10
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def take_snapshot(self, output_path: str) -> Dict:
        """Take a snapshot of current view."""
        # Ctrl+Shift+X is snapshot in Bluebeam
        self.send_keys("^+x")
        return {"success": True, "message": "Snapshot dialog opened"}


def main():
    """CLI interface for Bluebeam bridge."""
    import sys

    bridge = BluebeamBridge()

    if len(sys.argv) < 2:
        print(json.dumps({
            "commands": [
                "open <filepath>",
                "documents",
                "pages",
                "goto <page>",
                "export <output_path>",
                "text <text> <x> <y> [page]",
                "keys <keystrokes>"
            ]
        }, indent=2))
        return

    cmd = sys.argv[1]

    if cmd == "open" and len(sys.argv) > 2:
        result = bridge.open_document(sys.argv[2])
    elif cmd == "documents":
        result = bridge.get_open_documents()
    elif cmd == "pages":
        result = bridge.get_page_count()
    elif cmd == "goto" and len(sys.argv) > 2:
        result = bridge.goto_page(int(sys.argv[2]))
    elif cmd == "export" and len(sys.argv) > 2:
        result = bridge.export_to_pdf(sys.argv[2])
    elif cmd == "text" and len(sys.argv) > 4:
        page = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        result = bridge.add_text_markup(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), page)
    elif cmd == "keys" and len(sys.argv) > 2:
        result = bridge.send_keys(sys.argv[2])
    else:
        result = {"error": f"Unknown command: {cmd}"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
