import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class ClaudeCodeRevitSetup:
    """
    Complete setup for Claude Code + Drop Zones for Revit development
    """
    
    def __init__(self, base_path="D:\\claude-code-revit"):
        self.base_path = Path(base_path)
        self.revit_zones_path = self.base_path / "revit_zones"
        self.dev_zones_path = self.base_path / "dev_zones"
        self.project_zones = self.base_path / "project_zones"
        self.config_path = self.base_path / "config"
        
    def create_complete_setup(self):
        """Create the entire Claude Code + Drop Zones setup"""
        print("🚀 Setting up Claude Code + Drop Zones for Revit Development")
        print("=" * 70)
        
        # Create directory structure
        self.create_directory_structure()
        
        # Create configuration files
        self.create_claude_code_config()
        
        # Create development zones
        self.create_code_generator_zone()
        self.create_error_debugger_zone()
        self.create_test_generator_zone()
        self.create_doc_builder_zone()
        self.create_api_helper_zone()
        self.create_plugin_builder_zone()
        
        # Create integration scripts
        self.create_integration_scripts()
        
        # Create workflow examples
        self.create_workflow_examples()
        
        print("\n✅ Setup Complete!")
        print(f"📁 Location: {self.base_path}")
        
    def create_directory_structure(self):
        """Create all necessary directories"""
        zones = [
            # Revit-specific zones
            "revit_zones/code_generator",
            "revit_zones/error_debugger", 
            "revit_zones/api_explorer",
            "revit_zones/family_coder",
            "revit_zones/dynamo_converter",
            
            # Development zones
            "dev_zones/test_generator",
            "dev_zones/doc_builder",
            "dev_zones/refactor_helper",
            "dev_zones/performance_analyzer",
            
            # Project zones
            "project_zones/plugin_builder",
            "project_zones/ribbon_designer",
            "project_zones/form_creator",
            
            # Config and templates
            "config",
            "templates",
            "snippets"
        ]
        
        for zone in zones:
            zone_path = self.base_path / zone
            zone_path.mkdir(parents=True, exist_ok=True)
            (zone_path / "processed").mkdir(exist_ok=True)
            
        print(f"✓ Created {len(zones)} development zones")
    
    def create_claude_code_config(self):
        """Create Claude Code configuration files"""
        print("\n📝 Creating Claude Code Configuration...")
        
        # Main configuration
        config = {
            "claude_code_settings": {
                "model": "claude-3-opus",
                "temperature": 0.2,
                "max_tokens": 4000,
                "context_window": "full"
            },
            "revit_settings": {
                "default_revit_version": "2024",
                "api_version": "2024.1",
                "target_framework": "net48",
                "default_references": [
                    "RevitAPI.dll",
                    "RevitAPIUI.dll",
                    "AdWindows.dll"
                ]
            },
            "drop_zone_settings": {
                "watch_interval": 3,
                "auto_process": True,
                "keep_processed": True,
                "notification_sound": True
            },
            "development_preferences": {
                "code_style": "microsoft",
                "use_regions": True,
                "generate_comments": True,
                "include_error_handling": True,
                "unit_test_framework": "NUnit"
            }
        }
        
        config_file = self.config_path / "claude_code_config.json"
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
            
        # Create .clauderc file for project integration
        clauderc = """# Claude Code Configuration for Revit Development

# Default prompts for Revit development
defaults:
  language: csharp
  framework: revit-api
  version: 2024
  
# Custom commands
commands:
  revit-addin: "Create a Revit add-in with ribbon integration"
  revit-debug: "Debug this Revit API error"
  revit-test: "Generate unit tests for this Revit code"
  revit-docs: "Generate API documentation"
  
# Templates
templates:
  - revit-command
  - revit-application
  - revit-dockable-pane
  - revit-updater
  
# Code style
style:
  indent: 4
  braces: next-line
  regions: true
"""
        
        with open(self.base_path / ".clauderc", "w") as f:
            f.write(clauderc)
            
        print("  ✓ Created Claude Code configuration files")
    
    def create_code_generator_zone(self):
        """Create code generator zone with templates"""
        print("\n💻 Setting up Code Generator Zone...")
        
        zone_path = self.revit_zones_path / "code_generator"
        
        # Create instruction template
        instruction_template = """# Code Generator Drop Zone

## How to Use:
1. Create a text file describing what you want to build
2. Drop it here
3. Get complete Revit add-in code

## Example Requests:

### Simple Command:
"Create a command that counts all doors in the model and displays the result"

### Complex Tool:
"Build a tool that:
- Finds all walls
- Groups them by type
- Creates a schedule
- Exports to Excel"

### With Specific Requirements:
"Door renumbering tool with:
- UI for prefix/suffix
- Preview before applying
- Undo capability
- Progress bar for large models"

## File Format:
Save your request as a .txt file and drop it here!
"""
        
        with open(zone_path / "README.md", "w") as f:
            f.write(instruction_template)
            
        # Create templates directory
        templates_dir = zone_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Create example request
        example_request = """Revit Add-in Request: Smart Sheet Creator

Purpose: Automate sheet creation from Excel template

Requirements:
1. Read Excel file with sheet list
2. Create sheets with proper numbering
3. Place views on sheets automatically
4. Apply view templates
5. Set sheet parameters from Excel data

Features:
- Ribbon button in "Sheet Tools" panel
- Progress dialog for large sets
- Error handling for missing views
- Dry run mode to preview
- Logging of all actions

Technical specs:
- Target Revit 2024
- Use EPPlus for Excel reading
- Implement IExternalCommand
- Add configuration dialog

Please generate complete, production-ready code with proper error handling.
"""
        
        with open(templates_dir / "example_sheet_creator_request.txt", "w") as f:
            f.write(example_request)
            
        print("  ✓ Code Generator zone ready")
    
    def create_error_debugger_zone(self):
        """Create error debugger zone"""
        print("\n🐛 Setting up Error Debugger Zone...")
        
        zone_path = self.revit_zones_path / "error_debugger"
        
        # Error template
        error_template = """# Error Debugger Drop Zone

## How to Use:
1. Copy error message from Revit or journal file
2. Save as .txt file with relevant code snippet
3. Drop here for analysis and fix

## Format:

```
ERROR MESSAGE:
[Paste error here]

CODE THAT CAUSED ERROR:
[Paste relevant code]

REVIT VERSION: 2024
API VERSION: 2024.1

WHAT I WAS TRYING TO DO:
[Brief description]
```

## Common Errors We Fix:
- Transaction errors
- Element access violations
- Null reference exceptions
- Invalid element ID errors
- Parameter access issues
- View-specific errors
- Family/Type errors
"""
        
        with open(zone_path / "README.md", "w") as f:
            f.write(error_template)
            
        # Create templates directory
        templates_dir = zone_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Create example error
        example_error = """ERROR MESSAGE:
Autodesk.Revit.Exceptions.InvalidOperationException: Cannot access this method without an active transaction.
   at Autodesk.Revit.DB.Element.SetParameterValue(Parameter param, Object value)
   at MyAddin.SetDoorMark(Document doc, ElementId doorId, String mark)

CODE THAT CAUSED ERROR:
public void SetDoorMark(Document doc, ElementId doorId, string mark)
{
    Element door = doc.GetElement(doorId);
    Parameter markParam = door.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    markParam.Set(mark);  // Error occurs here
}

REVIT VERSION: 2024
API VERSION: 2024.1

WHAT I WAS TRYING TO DO:
Set door mark parameter without starting a transaction
"""
        
        with open(templates_dir / "example_transaction_error.txt", "w") as f:
            f.write(example_error)
            
        print("  ✓ Error Debugger zone ready")
    
    def create_test_generator_zone(self):
        """Create test generator zone"""
        print("\n🧪 Setting up Test Generator Zone...")
        
        zone_path = self.dev_zones_path / "test_generator"
        
        # Test generator instructions
        instructions = """# Test Generator Drop Zone

## How to Use:
1. Drop your Revit add-in .cs files here
2. Get comprehensive unit tests back

## What We Generate:
- NUnit test fixtures
- Mock Revit API objects
- Test cases for all public methods
- Edge case testing
- Performance tests

## Supported Frameworks:
- NUnit 3.x
- xUnit
- MSTest

## Example Output:
- Tests for commands
- Tests for utilities
- Integration test suggestions
- Mock object setup
"""
        
        with open(zone_path / "README.md", "w") as f:
            f.write(instructions)
            
        print("  ✓ Test Generator zone ready")
    
    def create_doc_builder_zone(self):
        """Create documentation builder zone"""
        print("\n📚 Setting up Documentation Builder Zone...")
        
        zone_path = self.dev_zones_path / "doc_builder"
        
        # Documentation template
        doc_template = """# Documentation Builder Drop Zone

## How to Use:
1. Drop your completed add-in code here
2. Get professional documentation

## What We Generate:
- README.md with installation/usage
- API documentation
- Code comments
- User guide with screenshots
- Developer documentation

## Formats:
- Markdown
- HTML
- XML documentation comments
- Wiki format

## Special Features:
- Automatic screenshot placeholders
- Version history template
- Troubleshooting section
- FAQ generation
"""
        
        with open(zone_path / "README.md", "w") as f:
            f.write(doc_template)
            
        print("  ✓ Documentation Builder zone ready")
    
    def create_api_helper_zone(self):
        """Create API helper zone"""
        print("\n🔧 Setting up API Helper Zone...")
        
        zone_path = self.revit_zones_path / "api_explorer"
        
        # Create templates directory
        templates_dir = zone_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # API helper request template
        api_template = """API Method Request: Find Elements

I need to:
1. Find all elements of a specific category
2. Filter by parameter value
3. Get elements only from active view
4. Sort by element ID

Show me:
- Different approaches
- Performance considerations
- Best practices
- Example code

Revit Version: 2024
"""
        
        with open(templates_dir / "api_method_request.txt", "w") as f:
            f.write(api_template)
            
        print("  ✓ API Helper zone ready")
    
    def create_plugin_builder_zone(self):
        """Create plugin builder zone"""
        print("\n🏗️ Setting up Plugin Builder Zone...")
        
        zone_path = self.project_zones / "plugin_builder"
        
        # Create templates directory
        templates_dir = zone_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Plugin specification template
        plugin_spec = {
            "plugin_info": {
                "name": "RevitToolsPro",
                "version": "1.0.0",
                "author": "Your Name",
                "description": "Professional tools for Revit",
                "min_revit_version": "2021",
                "max_revit_version": "2025"
            },
            "ribbon_tabs": [{
                "name": "Tools Pro",
                "panels": [{
                    "name": "Modeling Tools",
                    "buttons": [
                        {
                            "name": "Smart Walls",
                            "description": "Intelligent wall creation",
                            "command": "SmartWallCommand",
                            "icon": "wall_icon.png",
                            "tooltip": "Create walls with automatic joins"
                        }
                    ]
                }]
            }],
            "commands": [
                {
                    "class_name": "SmartWallCommand",
                    "transaction_mode": "Manual",
                    "regeneration_option": "Manual",
                    "journaling": True
                }
            ],
            "dependencies": [
                "Newtonsoft.Json",
                "EPPlus"
            ]
        }
        
        with open(templates_dir / "plugin_specification.json", "w") as f:
            json.dump(plugin_spec, f, indent=2)
            
        print("  ✓ Plugin Builder zone ready")
    
    def create_integration_scripts(self):
        """Create PowerShell integration scripts"""
        print("\n⚡ Creating Integration Scripts...")
        
        # Main integration script
        ps_script = """# Claude Code + Drop Zones Integration for Revit Development
# This script provides quick commands for your development workflow

# Global variables
$global:ClaudeCodeBase = "D:\\claude-code-revit"
$global:RevitZones = "$ClaudeCodeBase\\revit_zones"
$global:DevZones = "$ClaudeCodeBase\\dev_zones"

# Function to drop files into zones
function Drop-Revit {
    param(
        [Parameter(Mandatory=$true)]
        [string]$File,
        
        [Parameter(Mandatory=$true)]
        [string]$Zone
    )
    
    $zones = @{
        "code" = "$RevitZones\\code_generator"
        "error" = "$RevitZones\\error_debugger"
        "test" = "$DevZones\\test_generator"
        "doc" = "$DevZones\\doc_builder"
        "api" = "$RevitZones\\api_explorer"
    }
    
    if ($zones.ContainsKey($Zone)) {
        $destination = $zones[$Zone]
        Copy-Item $File -Destination $destination
        Write-Host "✓ Dropped $File into $Zone zone" -ForegroundColor Green
    } else {
        Write-Host "❌ Unknown zone: $Zone" -ForegroundColor Red
        Write-Host "Available zones: $($zones.Keys -join ', ')" -ForegroundColor Yellow
    }
}

# Quick command to create a new Revit tool request
function New-RevitTool {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Description
    )
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "tool_request_$timestamp.txt"
    $content = @"
Revit Tool Request
Created: $(Get-Date)

Description:
$Description

Requirements:
- Target Revit 2024
- Include error handling
- Add progress reporting
- Create ribbon button
- Include documentation

Please generate complete, working code.
"@
    
    $content | Out-File -FilePath $filename -Encoding UTF8
    Drop-Revit $filename "code"
    
    Write-Host "✓ Created and dropped tool request" -ForegroundColor Green
}

# Debug a Revit error quickly
function Debug-RevitError {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Error,
        
        [string]$Code = ""
    )
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "error_debug_$timestamp.txt"
    $content = @"
ERROR TO DEBUG
Time: $(Get-Date)

ERROR MESSAGE:
$Error

RELEVANT CODE:
$Code

REVIT VERSION: 2024
Need: Fixed code with explanation
"@
    
    $content | Out-File -FilePath $filename -Encoding UTF8
    Drop-Revit $filename "error"
    
    Write-Host "✓ Submitted error for debugging" -ForegroundColor Green
}

# Generate tests for existing code
function Generate-RevitTests {
    param(
        [Parameter(Mandatory=$true)]
        [string]$CodeFile
    )
    
    if (Test-Path $CodeFile) {
        Drop-Revit $CodeFile "test"
        Write-Host "✓ Submitted code for test generation" -ForegroundColor Green
    } else {
        Write-Host "❌ File not found: $CodeFile" -ForegroundColor Red
    }
}

# Create documentation for your add-in
function Build-RevitDocs {
    param(
        [Parameter(Mandatory=$true)]
        [string]$CodeFile
    )
    
    if (Test-Path $CodeFile) {
        Drop-Revit $CodeFile "doc"
        Write-Host "✓ Submitted code for documentation" -ForegroundColor Green
    } else {
        Write-Host "❌ File not found: $CodeFile" -ForegroundColor Red
    }
}

# Show available commands
function Show-RevitCommands {
    Write-Host ""
    Write-Host "🚀 Claude Code + Revit Commands:" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "New-RevitTool 'description'" -ForegroundColor Yellow
    Write-Host "  Create a new tool request" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Debug-RevitError 'error message' -Code 'code snippet'" -ForegroundColor Yellow
    Write-Host "  Debug a Revit API error" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Generate-RevitTests 'MyCommand.cs'" -ForegroundColor Yellow
    Write-Host "  Generate unit tests for your code" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Build-RevitDocs 'MyAddin.cs'" -ForegroundColor Yellow
    Write-Host "  Create documentation for your add-in" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Drop-Revit 'file.txt' 'zone'" -ForegroundColor Yellow
    Write-Host "  Drop any file into a specific zone" -ForegroundColor Gray
    Write-Host ""
}

# Initialize
Write-Host "✨ Claude Code + Revit Drop Zones Loaded!" -ForegroundColor Green
Write-Host "Type 'Show-RevitCommands' to see available commands" -ForegroundColor Cyan

# Set alias for quick access
Set-Alias -Name revit -Value Show-RevitCommands
"""
        
        script_path = self.base_path / "claude_code_integration.ps1"
        with open(script_path, "w") as f:
            f.write(ps_script)
            
        # Create profile loader
        profile_loader = """# Add this to your PowerShell profile to auto-load Claude Code commands
# Run: notepad $PROFILE

# Load Claude Code + Revit integration
$claudeCodeScript = "D:\\claude-code-revit\\claude_code_integration.ps1"
if (Test-Path $claudeCodeScript) {
    . $claudeCodeScript
}
"""
        
        with open(self.base_path / "add_to_profile.ps1", "w") as f:
            f.write(profile_loader)
            
        print("  ✓ Created integration scripts")
    
    def create_workflow_examples(self):
        """Create example workflows"""
        print("\n📖 Creating Workflow Examples...")
        
        # Complete workflow example
        workflow_md = """# Claude Code + Drop Zones Workflow Examples

## 🚀 Complete Development Workflow

### 1. Start New Project
```powershell
# Create a new tool request
New-RevitTool "Create a tool that renumbers all doors based on room location"

# This drops a request into code_generator
# Claude generates complete add-in code
```

### 2. Open in Claude Code
```bash
# Navigate to generated code
cd D:\\claude-code-revit\\revit_zones\\code_generator\\processed
claude-code DoorRenumberTool.cs

# Now you can refine with Claude Code's full capabilities
```

### 3. Debug Issues
```powershell
# When you hit an error
Debug-RevitError "Cannot access element without transaction" -Code "door.get_Parameter()"

# Get fixed code with explanation
```

### 4. Generate Tests
```powershell
# Create comprehensive tests
Generate-RevitTests "DoorRenumberTool.cs"

# Tests appear in dev_zones/test_generator/processed
```

### 5. Create Documentation
```powershell
# Generate user and developer docs
Build-RevitDocs "DoorRenumberTool.cs"

# Professional documentation ready
```

## 🎯 Quick Recipes

### Recipe: Fix a Broken Add-in
1. Copy error from Revit journal
2. `Debug-RevitError "error message"`
3. Apply fix from processed folder

### Recipe: Create Ribbon UI
1. Create UI specification
2. Drop in `plugin_builder` zone
3. Get complete ribbon setup code

### Recipe: Convert Dynamo to C#
1. Export Dynamo graph
2. Drop in `dynamo_converter` zone
3. Get equivalent C# code

## 💡 Pro Tips

1. **Chain Operations**: 
   - Generate code → Test → Document

2. **Use Templates**:
   - Each zone has template files
   - Customize for your needs

3. **Batch Processing**:
   - Drop multiple files
   - Process entire projects

4. **Integration**:
   - Works alongside Claude Code
   - Enhances not replaces
"""
        
        with open(self.base_path / "WORKFLOW_EXAMPLES.md", "w") as f:
            f.write(workflow_md)
            
        # Create quick start guide
        quickstart = """# 🚀 QUICK START - Claude Code + Revit Drop Zones

## 1️⃣ One-Time Setup (2 minutes)
```powershell
# Add to PowerShell profile
notepad $PROFILE
# Paste the line from add_to_profile.ps1
# Restart PowerShell
```

## 2️⃣ Your First Tool (30 seconds)
```powershell
New-RevitTool "Count all doors and show summary"
# Check revit_zones/code_generator/processed/
# Complete add-in code ready!
```

## 3️⃣ Debug an Error (20 seconds)
```powershell
Debug-RevitError "Object reference not set to an instance"
# Get fixed code instantly
```

## 4️⃣ Available Zones
- **code**: Generate new tools
- **error**: Debug problems  
- **test**: Create unit tests
- **doc**: Build documentation
- **api**: Explore Revit API

## 5️⃣ Remember
- Files process in ~5 seconds
- Check processed/ folders for results
- Chain operations for full workflow

Ready to build amazing Revit tools! 🚀
"""
        
        with open(self.base_path / "QUICKSTART.md", "w") as f:
            f.write(quickstart)
            
        print("  ✓ Created workflow examples")


def create_batch_setup():
    """Create a batch file for easy setup"""
    batch_content = """@echo off
echo.
echo =====================================================
echo   Claude Code + Revit Drop Zones Setup
echo =====================================================
echo.

REM Create the setup
python -c "from claude_code_revit_setup import ClaudeCodeRevitSetup; setup = ClaudeCodeRevitSetup(); setup.create_complete_setup()"

echo.
echo Setup Complete!
echo.
echo Next Steps:
echo 1. Add integration to PowerShell profile (see add_to_profile.ps1)
echo 2. Start drop zone monitor
echo 3. Try: New-RevitTool "Your first tool idea"
echo.
pause
"""
    
    with open("D:\\claude-code-revit\\setup_claude_code_revit.bat", "w") as f:
        f.write(batch_content)


if __name__ == "__main__":
    # Create the setup
    setup = ClaudeCodeRevitSetup()
    setup.create_complete_setup()
    
    # Create batch file
    create_batch_setup()
    
    print("\n🎉 Claude Code + Drop Zones Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Run PowerShell as Administrator")
    print("2. Execute: Set-ExecutionPolicy RemoteSigned")
    print("3. Add integration to profile: notepad $PROFILE")
    print("4. Paste content from add_to_profile.ps1")
    print("5. Restart PowerShell")
    print("\n🚀 Then try: New-RevitTool 'Create a door renumbering tool'")