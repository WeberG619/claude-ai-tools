# Revit C# Add-in Starter Kit

A production-ready Visual Studio solution for building Autodesk Revit add-ins. Multi-targets **Revit 2024, 2025, and 2026** from a single codebase. Opens in Visual Studio 2022 and builds immediately once you point it at your Revit API DLLs.

---

## What's Included

| File | Purpose |
|------|---------|
| `App.cs` | `IExternalApplication` with full ribbon setup (custom tab, panel, push buttons, separators). Includes commented examples for stacked buttons, pull-down menus, and split buttons. |
| `Commands/SampleCommand.cs` | Read-only `IExternalCommand` that gathers document info, element counts by category, and selection details. Demonstrates `FilteredElementCollector`, `TaskDialog`, and error handling. |
| `Commands/DataExportCommand.cs` | Exports element data to CSV. Shows parameter reading, unit handling, `SaveFileDialog`, CSV generation, and post-export actions (open file / open folder). |
| `Commands/ShowDialogCommand.cs` | Launches a WPF dialog from a command, passes data in, reads results back, and executes a transaction based on user input. |
| `UI/MainWindow.xaml` + `.cs` | Clean WPF dialog with styled controls, combo box with search, checkboxes, validation, and standard OK/Cancel pattern. |
| `Utils/RevitHelper.cs` | 40+ static helper methods: parameter reading/writing, unit conversion, element selection, transaction wrappers, geometry helpers, and more. |
| `RevitStarterKit.addin` | Add-in manifest template ready to deploy. |

---

## Quick Start

### Prerequisites

- **Visual Studio 2022** (Community edition or higher)
- **.NET Framework 4.8 SDK** (for Revit 2024 builds)
- **.NET 8.0 SDK** (for Revit 2025/2026 builds)
- **Autodesk Revit** 2024, 2025, or 2026 installed (for the API DLLs)

### Step 1: Open the Solution

Open `RevitStarterKit.sln` in Visual Studio 2022.

### Step 2: Set Your Revit API Path

The project needs to find `RevitAPI.dll` and `RevitAPIUI.dll`. Choose one method:

**Option A - Environment Variable (Recommended)**

Set the `REVIT_API_PATH` environment variable to your Revit installation folder:

```
REVIT_API_PATH = C:\Program Files\Autodesk\Revit 2026
```

You can set this in Windows System Properties > Environment Variables, or in a terminal:

```powershell
[System.Environment]::SetEnvironmentVariable("REVIT_API_PATH", "C:\Program Files\Autodesk\Revit 2026", "User")
```

**Option B - Edit the .csproj**

Open `RevitStarterKit.csproj` and edit the `RevitApiPath` property directly:

```xml
<RevitApiPath>C:\Program Files\Autodesk\Revit 2026</RevitApiPath>
```

### Step 3: Select Build Configuration

In Visual Studio's toolbar, select the build configuration matching your Revit version:

| Configuration | Target | Framework |
|---------------|--------|-----------|
| `Debug R24` | Revit 2024 | .NET Framework 4.8 |
| `Debug R25` | Revit 2025 | .NET 8.0 |
| `Debug R26` | Revit 2026 | .NET 8.0 |
| `Release R24` | Revit 2024 | .NET Framework 4.8 |
| `Release R25` | Revit 2025 | .NET 8.0 |
| `Release R26` | Revit 2026 | .NET 8.0 |

### Step 4: Build

Press `Ctrl+Shift+B` to build. The output DLL will be in:

```
RevitStarterKit\bin\{Configuration}\{TargetFramework}\RevitStarterKit.dll
```

### Step 5: Deploy to Revit

1. Copy `RevitStarterKit.addin` to your Revit Addins folder:
   ```
   %AppData%\Autodesk\Revit\Addins\2026\
   ```

2. Edit the `<Assembly>` path in the copied `.addin` file to point to your built DLL:
   ```xml
   <Assembly>C:\path\to\RevitStarterKit.dll</Assembly>
   ```

3. Launch Revit. You should see a **Starter Kit** tab in the ribbon.

**Auto-deploy (Optional):** Uncomment the `CopyAddinManifest` target in the `.csproj` to automatically copy files to the Revit Addins folder on each build.

---

## Project Structure

```
RevitStarterKit/
  App.cs                          # Application entry point, ribbon UI
  Commands/
    SampleCommand.cs              # Basic command template
    DataExportCommand.cs          # CSV export command
    ShowDialogCommand.cs          # WPF dialog launcher
  UI/
    MainWindow.xaml               # WPF dialog layout
    MainWindow.xaml.cs            # WPF dialog logic
  Utils/
    RevitHelper.cs                # Reusable helper methods
  Resources/                      # Place button icons here (16x16 and 32x32 PNG)
  Properties/
    AssemblyInfo.cs               # Version and metadata
  RevitStarterKit.addin           # Revit manifest template
  RevitStarterKit.csproj          # Multi-target project file
RevitStarterKit.sln               # Visual Studio solution
```

---

## Multi-Version Development

This project uses **build configurations** to target multiple Revit versions from a single codebase. Each configuration sets:

- The correct **target framework** (`.NET Framework 4.8` or `.NET 8.0`)
- A **conditional compilation symbol** (`REVIT2024`, `REVIT2025`, or `REVIT2026`)

Use these symbols in your code when the API differs between versions:

```csharp
#if REVIT2024
    // Revit 2024-specific code (.NET Framework 4.8)
    if (param.Definition.ParameterType == ParameterType.YesNo)
        return param.AsInteger() == 1 ? "Yes" : "No";
#else
    // Revit 2025+ (.NET 8.0)
    if (param.Definition.GetDataType() == SpecTypeId.Boolean.YesNo)
        return param.AsInteger() == 1 ? "Yes" : "No";
#endif
```

---

## Adding a New Command

1. **Create the command class** in `Commands/`:

```csharp
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitStarterKit.Commands
{
    [Transaction(TransactionMode.Manual)]
    public class MyNewCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            UIDocument uiDoc = commandData.Application.ActiveUIDocument;
            Document doc = uiDoc.Document;

            // Your code here...

            return Result.Succeeded;
        }
    }
}
```

2. **Add a ribbon button** in `App.cs` inside the `CreateRibbonTab` method:

```csharp
PushButtonData myBtnData = new PushButtonData(
    name: "cmdMyNewCommand",
    text: "My New\nCommand",
    assemblyName: AssemblyPath,
    className: "RevitStarterKit.Commands.MyNewCommand")
{
    ToolTip = "Description of what this command does."
};

toolsPanel.AddItem(myBtnData);
```

3. Build and test.

---

## Helper Methods Reference

The `RevitHelper` class provides these categories of methods (see `Utils/RevitHelper.cs` for full documentation):

### Parameter Reading
- `GetParameterValueAsString(element, builtInParam)` - Read any parameter as string
- `GetParameterValueAsString(element, "Parameter Name")` - Read by name (checks instance then type)
- `GetParameterDouble(element, bip, defaultValue)` - Read double parameter
- `GetParameterInt(element, bip, defaultValue)` - Read integer parameter

### Parameter Writing
- `SetParameterValue(element, bip, value)` - Set by built-in parameter
- `SetParameterValue(element, "Name", value)` - Set by parameter name

### Unit Conversion
- `FeetToMm(value)` / `MmToFeet(value)` - Length conversion
- `FeetToMeters(value)` - Feet to meters
- `SqFeetToSqMeters(value)` - Area conversion
- `ConvertFromInternal(value, unitTypeId)` - Generic unit conversion

### Element Selection
- `GetSelectedElements(uiDoc)` - Get current selection as list
- `GetSelectedElements<Wall>(uiDoc)` - Get selected elements filtered by type
- `PickElement(uiDoc, "prompt")` - Interactive single pick
- `PickElements(uiDoc, "prompt")` - Interactive multi pick

### Element Collection
- `GetElementsOfCategory(doc, BuiltInCategory.OST_Walls)` - All instances by category
- `GetElementsOfCategory(doc, category, viewId)` - Visible in specific view
- `GetTypesOfCategory(doc, category)` - Element types by category
- `GetElementsOfClass<Level>(doc)` - By element class
- `GetLevelsSorted(doc)` - All levels sorted by elevation
- `GetViewsOfType(doc, ViewType.FloorPlan)` - Views by type (excludes templates)

### Transactions
- `ExecuteInTransaction(doc, "Name", () => { ... })` - Auto-managed transaction
- `ExecuteInTransaction<T>(doc, "Name", () => { return value; })` - With return value
- `ExecuteInTransactionGroup(doc, "Name", () => { ... })` - Transaction group

### Geometry
- `GetElementCenter(element)` - Bounding box center point
- `GetLocationPoint(element)` - Location point (point-based elements)
- `GetLocationCurve(element)` - Location curve (line-based elements)

### Utilities
- `GetFamilyName(element)` / `GetTypeName(element)` - Name lookups
- `ShowMessage(title, message)` - Simple TaskDialog wrapper
- `Confirm(title, message)` - Yes/No confirmation dialog
- `GetStableId(element)` / `FindByUniqueId(doc, id)` - Persistent element identification

---

## Debugging

1. In Visual Studio, go to **Debug > Attach to Process** (or press `Ctrl+Alt+P`)
2. Find and select `Revit.exe` in the process list
3. Set breakpoints in your code
4. Trigger your command from the Revit ribbon

For faster iteration, set Revit as the startup application:
1. Right-click the project > Properties > Debug
2. Set **Start external program** to `C:\Program Files\Autodesk\Revit 2026\Revit.exe`
3. Press `F5` to build, deploy, and launch Revit with the debugger attached

---

## Tips for Production Add-ins

- **Always check for null** - Revit API methods frequently return null in unexpected places
- **Scope your collectors** - Use `FilteredElementCollector(doc, viewId)` instead of `(doc)` when possible for better performance
- **Keep transactions short** - Never leave a transaction open during user interaction (e.g., while a dialog is shown)
- **Handle OperationCanceledException** - Users can press Escape during pick operations; always catch this
- **Test with workshared models** - Behavior differs from local files (element ownership, sync timing)
- **Set `Private=false`** on Revit API references - Never copy Revit DLLs to your output folder
- **Log errors** - Use `System.Diagnostics.Debug.WriteLine` during development and consider a proper logging framework for production

---

## Customizing for Your Project

1. **Rename the namespace** - Find and replace `RevitStarterKit` with your project name across all files
2. **Update the GUIDs** - Generate new GUIDs for `AddInId` in the `.addin` file and `ProjectGuid` in the `.csproj`
3. **Change the ribbon tab name** - Edit `TabName` in `App.cs`
4. **Add button icons** - Place 16x16 and 32x32 PNG files in the `Resources/` folder and reference them in `App.cs`
5. **Update AssemblyInfo** - Edit `Properties/AssemblyInfo.cs` with your company name and version

---

## License

This starter kit is licensed for use in your own projects. You may modify and distribute the compiled add-ins you build with it. Do not redistribute the source code of this template or resell it as a competing product.

---

Built by **Weber Gouin** | [BIM Ops Studio](https://weberg619.github.io/bimops-studio/)
