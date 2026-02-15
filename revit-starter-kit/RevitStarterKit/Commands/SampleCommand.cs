// ============================================================================
// SampleCommand.cs - Basic IExternalCommand Example
//
// This command demonstrates the fundamental structure of a Revit external
// command. Use it as a template when creating new commands.
//
// Every Revit command must:
//   1. Implement IExternalCommand
//   2. Have a [Transaction] attribute specifying the transaction mode
//   3. Implement the Execute method
//
// Transaction Modes:
//   - Manual:    You manage transactions yourself (most common, most control)
//   - Automatic: Revit wraps Execute in a transaction (simple modifications)
//   - ReadOnly:  No modifications allowed (queries and data display only)
// ============================================================================

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;

namespace RevitStarterKit.Commands
{
    /// <summary>
    /// A sample command that gathers information about the active document
    /// and selected elements, then displays it in a TaskDialog.
    ///
    /// This demonstrates:
    ///   - Accessing the active document and view
    ///   - Getting the current selection
    ///   - Using FilteredElementCollector
    ///   - Displaying results with TaskDialog
    ///   - Proper error handling and result codes
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    [Regeneration(RegenerationOption.Manual)]
    public class SampleCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            // --- Step 1: Get references to the application and document ---
            UIApplication uiApp = commandData.Application;
            UIDocument uiDoc = uiApp.ActiveUIDocument;

            // Guard: ensure a document is open
            if (uiDoc == null)
            {
                TaskDialog.Show("Starter Kit", "Please open a document first.");
                return Result.Cancelled;
            }

            Document doc = uiDoc.Document;

            try
            {
                // --- Step 2: Gather document information ---
                StringBuilder info = new StringBuilder();

                info.AppendLine($"Document: {doc.Title}");
                info.AppendLine($"File Path: {doc.PathName}");
                info.AppendLine($"Active View: {doc.ActiveView.Name} ({doc.ActiveView.ViewType})");
                info.AppendLine();

                // --- Step 3: Count elements by category ---
                // FilteredElementCollector is the primary way to query elements.
                // Always scope to the narrowest filter possible for performance.
                FilteredElementCollector collector = new FilteredElementCollector(doc)
                    .WhereElementIsNotElementType();

                // Group by category and count
                var categoryCounts = collector
                    .Where(e => e.Category != null)
                    .GroupBy(e => e.Category.Name)
                    .OrderByDescending(g => g.Count())
                    .Take(10);

                info.AppendLine("Top 10 Element Categories:");
                info.AppendLine(new string('-', 40));

                foreach (var group in categoryCounts)
                {
                    info.AppendLine($"  {group.Key}: {group.Count():N0}");
                }

                info.AppendLine();

                // --- Step 4: Show selection info ---
                ICollection<ElementId> selectedIds = uiDoc.Selection.GetElementIds();

                if (selectedIds.Count > 0)
                {
                    info.AppendLine($"Selected Elements: {selectedIds.Count}");
                    info.AppendLine(new string('-', 40));

                    foreach (ElementId id in selectedIds.Take(5))
                    {
                        Element elem = doc.GetElement(id);
                        string typeName = doc.GetElement(elem.GetTypeId())?.Name ?? "(no type)";
                        info.AppendLine($"  [{id.Value}] {elem.Category?.Name} - {elem.Name} ({typeName})");
                    }

                    if (selectedIds.Count > 5)
                    {
                        info.AppendLine($"  ... and {selectedIds.Count - 5} more");
                    }
                }
                else
                {
                    info.AppendLine("No elements selected.");
                    info.AppendLine("Tip: Select elements before running this command to see their details.");
                }

                // --- Step 5: Add Revit version info ---
                info.AppendLine();
#if REVIT2024
                info.AppendLine("Built for: Revit 2024 (.NET Framework 4.8)");
#elif REVIT2025
                info.AppendLine("Built for: Revit 2025 (.NET 8.0)");
#elif REVIT2026
                info.AppendLine("Built for: Revit 2026 (.NET 8.0)");
#else
                info.AppendLine("Built for: Unknown Revit version");
#endif
                info.AppendLine($"Add-in Version: {System.Reflection.Assembly.GetExecutingAssembly().GetName().Version}");

                // --- Step 6: Display results ---
                TaskDialog dialog = new TaskDialog("Starter Kit - Document Info")
                {
                    MainInstruction = "Document Summary",
                    MainContent = info.ToString(),
                    CommonButtons = TaskDialogCommonButtons.Close,
                    DefaultButton = TaskDialogResult.Close,
                    FooterText = "RevitStarterKit by BIMOps"
                };

                dialog.Show();

                return Result.Succeeded;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                // User cancelled an operation (e.g., selection picking)
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                // Set the error message - Revit will display it to the user
                message = $"An error occurred: {ex.Message}";

                // Log the full exception for debugging
                System.Diagnostics.Debug.WriteLine($"[StarterKit] SampleCommand error: {ex}");

                return Result.Failed;
            }
        }
    }
}
