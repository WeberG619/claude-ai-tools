# Claude Code + Drop Zones Workflow Examples

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
cd D:\claude-code-revit\revit_zones\code_generator\processed
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
