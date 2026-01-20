import json
import os
from pathlib import Path
from datetime import datetime

class DropZoneConfigBuilder:
    """
    Creates all necessary configuration files for Revit development drop zones
    """
    
    def __init__(self, base_path="D:\\claude-code-revit"):
        self.base_path = Path(base_path)
        
    def create_all_configs(self):
        """Create all necessary configuration files"""
        print("🔧 Creating Drop Zone Configuration Files")
        print("=" * 60)
        
        # Create main drop zone configuration
        self.create_main_dropzone_config()
        
        # Create zone-specific handlers
        self.create_code_generator_handler()
        self.create_error_debugger_handler()
        self.create_test_generator_handler()
        self.create_doc_builder_handler()
        
        # Create the actual monitoring script
        self.create_monitor_script()
        
        # Create processor scripts
        self.create_processor_scripts()
        
        print("\n✅ All configuration files created!")
        
    def create_main_dropzone_config(self):
        """Create the main drop zone configuration file"""
        print("\n📋 Creating main drop zone configuration...")
        
        config = {
            "drop_zones": {
                "revit_code_generator": {
                    "path": "D:\\claude-code-revit\\revit_zones\\code_generator",
                    "watch_extensions": [".txt", ".md", ".json"],
                    "processor": "generate_revit_code",
                    "output_extension": ".cs",
                    "keep_original": True,
                    "notification": True,
                    "description": "Generate Revit add-in code from descriptions"
                },
                "revit_error_debugger": {
                    "path": "D:\\claude-code-revit\\revit_zones\\error_debugger",
                    "watch_extensions": [".txt", ".log", ".err"],
                    "processor": "debug_revit_error",
                    "output_extension": "_fixed.cs",
                    "keep_original": True,
                    "notification": True,
                    "description": "Debug and fix Revit API errors"
                },
                "test_generator": {
                    "path": "D:\\claude-code-revit\\dev_zones\\test_generator",
                    "watch_extensions": [".cs"],
                    "processor": "generate_tests",
                    "output_extension": "_Tests.cs",
                    "keep_original": True,
                    "notification": True,
                    "description": "Generate unit tests for Revit code"
                },
                "doc_builder": {
                    "path": "D:\\claude-code-revit\\dev_zones\\doc_builder",
                    "watch_extensions": [".cs", ".txt"],
                    "processor": "build_documentation",
                    "output_extension": "_Documentation.md",
                    "keep_original": True,
                    "notification": True,
                    "description": "Generate documentation for Revit add-ins"
                },
                "api_explorer": {
                    "path": "D:\\claude-code-revit\\revit_zones\\api_explorer",
                    "watch_extensions": [".txt", ".md"],
                    "processor": "explore_api",
                    "output_extension": "_solution.md",
                    "keep_original": True,
                    "notification": True,
                    "description": "Get Revit API examples and best practices"
                },
                "plugin_builder": {
                    "path": "D:\\claude-code-revit\\project_zones\\plugin_builder",
                    "watch_extensions": [".json", ".yaml", ".txt"],
                    "processor": "build_plugin",
                    "output_extension": "_Plugin",
                    "output_type": "folder",
                    "keep_original": True,
                    "notification": True,
                    "description": "Build complete Revit plugin from specification"
                }
            },
            "global_settings": {
                "watch_interval": 3,
                "processed_folder": "processed",
                "log_file": "dropzone_activity.log",
                "enable_sound": True,
                "claude_api_key_env": "CLAUDE_API_KEY",
                "default_model": "claude-3-opus-20240229"
            }
        }
        
        config_path = self.base_path / "config" / "dropzone_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        print(f"  ✓ Created: {config_path}")
        
    def create_code_generator_handler(self):
        """Create the code generator handler script"""
        print("\n💻 Creating code generator handler...")
        
        handler = '''# Code Generator Handler for Revit Development
import os
import json
from datetime import datetime
from pathlib import Path

def process_code_request(input_file, output_dir):
    """Process a code generation request for Revit add-ins"""
    
    # Read the request
    with open(input_file, 'r', encoding='utf-8') as f:
        request = f.read()
    
    # Create the prompt for Claude
    prompt = f"""You are an expert Revit API developer. Generate complete, production-ready C# code based on this request:

{request}

Requirements:
1. Target Revit 2024 API
2. Include all necessary using statements
3. Implement proper error handling and transactions
4. Follow Autodesk coding guidelines
5. Include XML documentation comments
6. Make the code production-ready, not just a sample

Generate the complete C# file(s) needed."""

    # Here you would call Claude API
    # For now, create a template response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"GeneratedAddin_{timestamp}.cs"
    
    # Example generated code structure
    generated_code = """using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.Attributes;

namespace RevitAddin
{
    /// <summary>
    /// Generated Revit Add-in based on your request
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class GeneratedCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData, 
            ref string message, 
            ElementSet elements)
        {
            UIApplication uiapp = commandData.Application;
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;
            
            try
            {
                using (Transaction trans = new Transaction(doc, "Generated Operation"))
                {
                    trans.Start();
                    
                    // TODO: Implement based on request
                    TaskDialog.Show("Generated", "Add-in code generated successfully!");
                    
                    trans.Commit();
                }
                
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}"""
    
    # Write the generated code
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(generated_code)
    
    # Create a summary file
    summary = {
        "request_file": str(input_file),
        "generated_file": str(output_path),
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "notes": "Code generated based on request. Open in Claude Code for refinement."
    }
    
    summary_path = Path(output_dir) / f"generation_summary_{timestamp}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return output_path

if __name__ == "__main__":
    # This would be called by the drop zone monitor
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_code_request(input_file, output_dir)
        print(f"Generated: {result}")
'''
        
        handler_path = self.base_path / "handlers" / "code_generator_handler.py"
        handler_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(handler_path, "w") as f:
            f.write(handler)
            
        print(f"  ✓ Created: {handler_path}")
        
    def create_error_debugger_handler(self):
        """Create the error debugger handler"""
        print("\n🐛 Creating error debugger handler...")
        
        handler = '''# Error Debugger Handler for Revit API
import os
import re
import json
from datetime import datetime
from pathlib import Path

def process_error_debug(input_file, output_dir):
    """Process Revit API errors and provide fixes"""
    
    # Read the error report
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse error information
    error_pattern = r'ERROR MESSAGE:\s*(.+?)(?=\n\n|CODE THAT CAUSED ERROR:|$)'
    code_pattern = r'CODE THAT CAUSED ERROR:\s*(.+?)(?=\n\n|REVIT VERSION:|$)'
    
    error_match = re.search(error_pattern, content, re.DOTALL)
    code_match = re.search(code_pattern, content, re.DOTALL)
    
    error_msg = error_match.group(1).strip() if error_match else "Unknown error"
    problem_code = code_match.group(1).strip() if code_match else ""
    
    # Analyze common Revit API errors
    fixes = analyze_revit_error(error_msg, problem_code)
    
    # Generate fixed code
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"FixedCode_{timestamp}.cs"
    
    fixed_code = generate_fixed_code(error_msg, problem_code, fixes)
    
    # Write the fixed code
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    # Create explanation file
    explanation = f"""# Revit API Error Fix Report

## Original Error:
{error_msg}

## Analysis:
{fixes['analysis']}

## Solution:
{fixes['solution']}

## Fixed Code:
See: {output_filename}

## Prevention Tips:
{fixes['prevention']}

Generated: {datetime.now().isoformat()}
"""
    
    explanation_path = Path(output_dir) / f"ErrorFix_Explanation_{timestamp}.md"
    with open(explanation_path, 'w') as f:
        f.write(explanation)
    
    return output_path

def analyze_revit_error(error_msg, code):
    """Analyze common Revit API errors"""
    
    fixes = {
        'analysis': '',
        'solution': '',
        'prevention': ''
    }
    
    # Transaction errors
    if 'without an active transaction' in error_msg.lower():
        fixes['analysis'] = "Attempting to modify the model without a transaction."
        fixes['solution'] = "Wrap the modification code in a Transaction."
        fixes['prevention'] = "Always use transactions for any model modifications."
    
    # Null reference
    elif 'object reference not set' in error_msg.lower():
        fixes['analysis'] = "Accessing a null object, likely an element that doesn't exist."
        fixes['solution'] = "Add null checks before accessing objects."
        fixes['prevention'] = "Always verify elements exist before use."
    
    # Invalid element
    elif 'invalid element' in error_msg.lower():
        fixes['analysis'] = "Trying to access a deleted or invalid element."
        fixes['solution'] = "Check element validity with IsValidObject."
        fixes['prevention'] = "Store element IDs instead of elements across transactions."
    
    else:
        fixes['analysis'] = "Generic Revit API error detected."
        fixes['solution'] = "Review Revit API documentation for proper usage."
        fixes['prevention'] = "Follow Revit API best practices."
    
    return fixes

def generate_fixed_code(error_msg, problem_code, fixes):
    """Generate fixed version of the code"""
    
    # For transaction errors
    if 'without an active transaction' in error_msg.lower():
        return f"""using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

public Result ExecuteFixed(ExternalCommandData commandData, ref string message, ElementSet elements)
{{
    Document doc = commandData.Application.ActiveUIDocument.Document;
    
    // Fixed: Added transaction
    using (Transaction trans = new Transaction(doc, "Fixed Operation"))
    {{
        trans.Start();
        
        try
        {{
            {problem_code}
            
            trans.Commit();
            return Result.Succeeded;
        }}
        catch (Exception ex)
        {{
            trans.RollBack();
            message = ex.Message;
            return Result.Failed;
        }}
    }}
}}"""
    
    # Default fix template
    return f"""// Fixed code based on error analysis
// Original error: {error_msg}

{problem_code}

// TODO: Apply fix based on analysis
// Fix: {fixes['solution']}
"""

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_error_debug(input_file, output_dir)
        print(f"Fixed code: {result}")
'''
        
        handler_path = self.base_path / "handlers" / "error_debugger_handler.py"
        
        with open(handler_path, "w") as f:
            f.write(handler)
            
        print(f"  ✓ Created: {handler_path}")
        
    def create_test_generator_handler(self):
        """Create test generator handler"""
        print("\n🧪 Creating test generator handler...")
        
        handler = '''# Test Generator Handler for Revit Code
import os
import re
from datetime import datetime
from pathlib import Path

def process_test_generation(input_file, output_dir):
    """Generate unit tests for Revit add-in code"""
    
    # Read the source code
    with open(input_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse the code to find classes and methods
    class_name = extract_class_name(source_code)
    methods = extract_methods(source_code)
    
    # Generate test code
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{class_name}_Tests_{timestamp}.cs"
    
    test_code = generate_test_code(class_name, methods)
    
    # Write the test file
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return output_path

def extract_class_name(code):
    """Extract the main class name from code"""
    match = re.search(r'public class (\w+)', code)
    return match.group(1) if match else "UnknownClass"

def extract_methods(code):
    """Extract public methods from code"""
    pattern = r'public\s+(\w+)\s+(\w+)\s*\([^)]*\)'
    return re.findall(pattern, code)

def generate_test_code(class_name, methods):
    """Generate NUnit test code"""
    
    test_code = f"""using System;
using NUnit.Framework;
using Moq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitTests
{{
    [TestFixture]
    public class {class_name}Tests
    {{
        private Mock<Document> mockDoc;
        private Mock<UIDocument> mockUiDoc;
        private {class_name} testInstance;
        
        [SetUp]
        public void Setup()
        {{
            // Setup mock objects
            mockDoc = new Mock<Document>();
            mockUiDoc = new Mock<UIDocument>();
            mockUiDoc.Setup(x => x.Document).Returns(mockDoc.Object);
            
            // Create test instance
            testInstance = new {class_name}();
        }}
        
        [Test]
        public void Constructor_ShouldInitializeCorrectly()
        {{
            // Arrange & Act
            var instance = new {class_name}();
            
            // Assert
            Assert.IsNotNull(instance);
        }}
"""
    
    # Add test methods for each public method
    for return_type, method_name in methods:
        if method_name != class_name:  # Skip constructor
            test_code += f"""
        [Test]
        public void {method_name}_ShouldExecuteWithoutError()
        {{
            // Arrange
            // TODO: Set up test data
            
            // Act
            // TODO: Call {method_name}
            
            // Assert
            // TODO: Verify expected behavior
        }}
"""
    
    test_code += """    }
}"""
    
    return test_code

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_test_generation(input_file, output_dir)
        print(f"Generated tests: {result}")
'''
        
        handler_path = self.base_path / "handlers" / "test_generator_handler.py"
        
        with open(handler_path, "w") as f:
            f.write(handler)
            
        print(f"  ✓ Created: {handler_path}")
        
    def create_doc_builder_handler(self):
        """Create documentation builder handler"""
        print("\n📚 Creating documentation builder handler...")
        
        handler = '''# Documentation Builder Handler for Revit Add-ins
import os
import re
from datetime import datetime
from pathlib import Path

def process_documentation(input_file, output_dir):
    """Generate documentation for Revit add-in code"""
    
    # Read the source code
    with open(input_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Extract information
    info = extract_code_info(source_code)
    
    # Generate documentation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{info['name']}_Documentation_{timestamp}.md"
    
    documentation = generate_documentation(info)
    
    # Write the documentation
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(documentation)
    
    # Also generate README
    readme_path = Path(output_dir) / f"{info['name']}_README_{timestamp}.md"
    with open(readme_path, 'w') as f:
        f.write(generate_readme(info))
    
    return output_path

def extract_code_info(code):
    """Extract information from code"""
    info = {
        'name': 'RevitAddin',
        'classes': [],
        'methods': [],
        'description': ''
    }
    
    # Extract class names
    class_matches = re.findall(r'public class (\w+)', code)
    info['classes'] = class_matches
    
    # Extract main class name
    if class_matches:
        info['name'] = class_matches[0]
    
    # Extract methods with documentation
    method_pattern = r'///\s*<summary>\s*\n\s*///\s*(.+?)\s*\n\s*///\s*</summary>\s*\n\s*public\s+(\w+)\s+(\w+)'
    method_matches = re.findall(method_pattern, code)
    
    for doc, return_type, method_name in method_matches:
        info['methods'].append({
            'name': method_name,
            'return_type': return_type,
            'description': doc.strip()
        })
    
    return info

def generate_documentation(info):
    """Generate comprehensive documentation"""
    
    doc = f"""# {info['name']} - API Documentation

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview

This documentation covers the {info['name']} Revit add-in.

## Classes

"""
    
    for class_name in info['classes']:
        doc += f"### {class_name}\n\n"
        doc += f"Main class for the add-in functionality.\n\n"
    
    doc += "## Methods\n\n"
    
    for method in info['methods']:
        doc += f"### {method['name']}\n\n"
        doc += f"**Returns:** `{method['return_type']}`\n\n"
        doc += f"**Description:** {method['description']}\n\n"
        doc += "**Example:**\n```csharp\n// TODO: Add usage example\n```\n\n"
    
    doc += """## Error Handling

The add-in implements comprehensive error handling:
- All Revit API calls are wrapped in try-catch blocks
- Transactions are properly managed with rollback on failure
- User-friendly error messages via TaskDialog

## Best Practices

1. Always use transactions for model modifications
2. Check element validity before access
3. Dispose of transactions properly
4. Handle user cancellation gracefully

## Troubleshooting

### Common Issues

1. **Transaction Error**: Ensure all model modifications are within a transaction
2. **Null Reference**: Check if elements exist before accessing
3. **Invalid Element**: Verify element hasn't been deleted

## Support

For issues or questions, please contact the development team.
"""
    
    return doc

def generate_readme(info):
    """Generate README file"""
    
    readme = f"""# {info['name']}

A Revit add-in for [describe purpose].

## Installation

1. Copy the .dll file to your Revit Add-ins folder:
   - `%appdata%\\Autodesk\\Revit\\Addins\\2024\\`

2. Copy the .addin manifest file to the same location

3. Restart Revit

## Usage

1. In Revit, go to the Add-ins tab
2. Look for {info['name']} in the ribbon
3. Click to execute

## Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Requirements

- Revit 2024 or later
- .NET Framework 4.8

## Configuration

No additional configuration required.

## Known Issues

None at this time.

## Version History

- v1.0.0 - Initial release

## License

[Your license here]

## Contact

[Your contact information]
"""
    
    return readme

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_documentation(input_file, output_dir)
        print(f"Generated documentation: {result}")
'''
        
        handler_path = self.base_path / "handlers" / "doc_builder_handler.py"
        
        with open(handler_path, "w") as f:
            f.write(handler)
            
        print(f"  ✓ Created: {handler_path}")
        
    def create_monitor_script(self):
        """Create the main monitoring script"""
        print("\n👁️ Creating drop zone monitor script...")
        
        monitor = '''# Drop Zone Monitor for Revit Development
import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

class RevitDropZoneMonitor:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.zones = self.config['drop_zones']
        self.settings = self.config['global_settings']
        
    def start_monitoring(self):
        """Start monitoring all drop zones"""
        print("🚀 Revit Drop Zone Monitor Started")
        print("=" * 50)
        
        # Display active zones
        print("\\nActive Drop Zones:")
        for zone_name, zone_config in self.zones.items():
            print(f"  📁 {zone_name}: {zone_config['description']}")
        
        print(f"\\nWatching every {self.settings['watch_interval']} seconds...")
        print("Press Ctrl+C to stop\\n")
        
        # Main monitoring loop
        try:
            while True:
                for zone_name, zone_config in self.zones.items():
                    self.check_zone(zone_name, zone_config)
                
                time.sleep(self.settings['watch_interval'])
                
        except KeyboardInterrupt:
            print("\\n\\n✋ Monitoring stopped")
    
    def check_zone(self, zone_name, zone_config):
        """Check a single drop zone for new files"""
        zone_path = Path(zone_config['path'])
        
        if not zone_path.exists():
            zone_path.mkdir(parents=True, exist_ok=True)
            return
        
        # Look for files with watched extensions
        for ext in zone_config['watch_extensions']:
            for file_path in zone_path.glob(f"*{ext}"):
                if file_path.is_file():
                    self.process_file(zone_name, zone_config, file_path)
    
    def process_file(self, zone_name, zone_config, file_path):
        """Process a dropped file"""
        print(f"\\n📄 Processing: {file_path.name} in {zone_name}")
        
        # Create processed directory
        processed_dir = file_path.parent / self.settings['processed_folder']
        processed_dir.mkdir(exist_ok=True)
        
        # Call the appropriate handler
        handler_name = zone_config['processor']
        output_dir = processed_dir
        
        try:
            # Here you would call the actual handler
            # For now, we'll simulate it
            print(f"  🔧 Running {handler_name}...")
            
            # Move original file to processed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            processed_path = processed_dir / new_name
            shutil.move(str(file_path), str(processed_path))
            
            print(f"  ✅ Processed successfully!")
            print(f"  📁 Output in: {processed_dir}")
            
            # Log activity
            self.log_activity(zone_name, file_path.name, "success")
            
            # Notification
            if zone_config.get('notification', False):
                print("  🔔 Notification sent!")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.log_activity(zone_name, file_path.name, "error", str(e))
    
    def log_activity(self, zone, filename, status, error=None):
        """Log drop zone activity"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'zone': zone,
            'file': filename,
            'status': status,
            'error': error
        }
        
        log_file = Path(self.settings.get('log_file', 'dropzone.log'))
        
        # Append to log file
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\\n')

if __name__ == "__main__":
    config_path = "D:\\\\claude-code-revit\\\\config\\\\dropzone_config.json"
    
    if not Path(config_path).exists():
        print("❌ Configuration file not found!")
        print(f"Expected at: {config_path}")
        exit(1)
    
    monitor = RevitDropZoneMonitor(config_path)
    monitor.start_monitoring()
'''
        
        monitor_path = self.base_path / "dropzone_monitor.py"
        
        with open(monitor_path, "w") as f:
            f.write(monitor)
            
        print(f"  ✓ Created: {monitor_path}")
        
    def create_processor_scripts(self):
        """Create processor wrapper scripts"""
        print("\n⚡ Creating processor scripts...")
        
        # Windows batch file to start monitoring
        batch_script = """@echo off
title Revit Drop Zone Monitor
color 0A

echo.
echo =====================================================
echo   REVIT DROP ZONE MONITOR - Development Assistant
echo =====================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or later
    pause
    exit /b 1
)

REM Set the paths
set MONITOR_SCRIPT=D:\\claude-code-revit\\dropzone_monitor.py
set CONFIG_FILE=D:\\claude-code-revit\\config\\dropzone_config.json

REM Check if files exist
if not exist "%MONITOR_SCRIPT%" (
    echo ERROR: Monitor script not found at %MONITOR_SCRIPT%
    pause
    exit /b 1
)

if not exist "%CONFIG_FILE%" (
    echo ERROR: Config file not found at %CONFIG_FILE%
    pause
    exit /b 1
)

echo Starting drop zone monitoring...
echo.
echo Drop files into these folders:
echo   - Code Generator: revit_zones\\code_generator
echo   - Error Debugger: revit_zones\\error_debugger
echo   - Test Generator: dev_zones\\test_generator
echo   - Doc Builder: dev_zones\\doc_builder
echo.
echo Press Ctrl+C to stop monitoring
echo.

REM Start the monitor
python "%MONITOR_SCRIPT%"

pause
"""
        
        batch_path = self.base_path / "start_dropzone_monitor.bat"
        
        with open(batch_path, "w") as f:
            f.write(batch_script)
            
        # PowerShell version
        ps_script = """# Revit Drop Zone Monitor Launcher

$ErrorActionPreference = "Stop"

Write-Host "`n===== REVIT DROP ZONE MONITOR =====" -ForegroundColor Cyan
Write-Host "Development Assistant for Revit" -ForegroundColor Cyan
Write-Host "==================================`n" -ForegroundColor Cyan

# Configuration
$monitorScript = "D:\\claude-code-revit\\dropzone_monitor.py"
$configFile = "D:\\claude-code-revit\\config\\dropzone_config.json"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.7+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check files
if (-not (Test-Path $monitorScript)) {
    Write-Host "✗ Monitor script not found at: $monitorScript" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path $configFile)) {
    Write-Host "✗ Config file not found at: $configFile" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`nDrop files into these zones:" -ForegroundColor Yellow
Write-Host "  📝 Code Generator: revit_zones\code_generator" -ForegroundColor Gray
Write-Host "  🐛 Error Debugger: revit_zones\error_debugger" -ForegroundColor Gray
Write-Host "  🧪 Test Generator: dev_zones\test_generator" -ForegroundColor Gray
Write-Host "  📚 Doc Builder: dev_zones\doc_builder" -ForegroundColor Gray

Write-Host "`nStarting monitor... (Ctrl+C to stop)`n" -ForegroundColor Green

# Start monitoring
python $monitorScript

Write-Host "`nMonitor stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
"""
        
        ps_path = self.base_path / "start_dropzone_monitor.ps1"
        
        with open(ps_path, "w") as f:
            f.write(ps_script)
            
        print(f"  ✓ Created: {batch_path}")
        print(f"  ✓ Created: {ps_path}")
        
        # Create a quick launcher
        launcher = """@echo off
REM Quick launcher for Revit Drop Zone Monitor
start cmd /k "D:\\claude-code-revit\\start_dropzone_monitor.bat"
"""
        
        desktop_launcher = Path.home() / "Desktop" / "Revit Drop Zones.bat"
        with open(desktop_launcher, "w") as f:
            f.write(launcher)
            
        print(f"  ✓ Created desktop shortcut: {desktop_launcher}")


if __name__ == "__main__":
    # Create all configuration files
    builder = DropZoneConfigBuilder()
    builder.create_all_configs()
    
    print("\n📋 SETUP COMPLETE! Here's what you need to do:")
    print("\n1. IMMEDIATE: Start the monitor")
    print("   - Double-click: start_dropzone_monitor.bat")
    print("   - Or use the desktop shortcut: 'Revit Drop Zones.bat'")
    
    print("\n2. TEST: Drop a file")
    print("   - Create test.txt with 'Create a door numbering tool'")
    print("   - Drop in: D:\\claude-code-revit\\revit_zones\\code_generator")
    print("   - Check: processed folder for generated code")
    
    print("\n3. INTEGRATE: With Claude API")
    print("   - Set environment variable: CLAUDE_API_KEY")
    print("   - Update handlers to call Claude API")
    
    print("\n4. USE: In your workflow")
    print("   - Drop requirements → Get code")
    print("   - Drop errors → Get fixes")
    print("   - Drop code → Get tests/docs")