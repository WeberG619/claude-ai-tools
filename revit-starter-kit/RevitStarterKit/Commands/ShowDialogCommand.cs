// ============================================================================
// ShowDialogCommand.cs - Launch WPF Dialog from Revit
//
// Demonstrates how to properly show a WPF window from a Revit command.
// Key points:
//   - The transaction is Manual because the dialog may trigger model changes
//   - The WPF window must be shown as a modal dialog (ShowDialog, not Show)
//   - Data is passed to the dialog via constructor or properties
//   - Results are read back from the dialog after it closes
// ============================================================================

using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitStarterKit.UI;

namespace RevitStarterKit.Commands
{
    /// <summary>
    /// Opens the sample WPF dialog window. This command acts as the bridge
    /// between the Revit ribbon button and the WPF UI layer.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class ShowDialogCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            UIApplication uiApp = commandData.Application;
            UIDocument uiDoc = uiApp.ActiveUIDocument;

            if (uiDoc == null)
            {
                TaskDialog.Show("Starter Kit", "Please open a document first.");
                return Result.Cancelled;
            }

            Document doc = uiDoc.Document;

            try
            {
                // Gather category names for the dialog's combo box
                List<string> categoryNames = new FilteredElementCollector(doc)
                    .WhereElementIsNotElementType()
                    .Where(e => e.Category != null
                             && e.Category.CategoryType == CategoryType.Model)
                    .Select(e => e.Category.Name)
                    .Distinct()
                    .OrderBy(n => n)
                    .ToList();

                // Create and show the WPF dialog
                MainWindow dialog = new MainWindow(categoryNames)
                {
                    DocumentTitle = doc.Title
                };

                // ShowDialog blocks until the window is closed.
                // The return value indicates OK (true) or Cancel (false/null).
                bool? dialogResult = dialog.ShowDialog();

                if (dialogResult != true)
                {
                    return Result.Cancelled;
                }

                // Read the user's selections from the dialog
                string selectedCategory = dialog.SelectedCategory;
                bool includeTypes = dialog.IncludeTypeParameters;
                string filterText = dialog.FilterText;

                // Do something with the results
                int count = 0;

                using (Transaction tx = new Transaction(doc, "Starter Kit - Process Selection"))
                {
                    tx.Start();

                    // Example: collect elements of the selected category
                    FilteredElementCollector collector = new FilteredElementCollector(doc)
                        .WhereElementIsNotElementType();

                    List<Element> matchingElements = collector
                        .Where(e => e.Category != null
                                 && e.Category.Name == selectedCategory)
                        .ToList();

                    // Apply text filter if provided
                    if (!string.IsNullOrWhiteSpace(filterText))
                    {
                        matchingElements = matchingElements
                            .Where(e => e.Name.IndexOf(filterText, StringComparison.OrdinalIgnoreCase) >= 0)
                            .ToList();
                    }

                    count = matchingElements.Count;

                    // Example: set a parameter value on matching elements
                    // Uncomment and modify for your use case:
                    //
                    // foreach (Element elem in matchingElements)
                    // {
                    //     Parameter markParam = elem.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
                    //     if (markParam != null && !markParam.IsReadOnly)
                    //     {
                    //         markParam.Set("Processed by StarterKit");
                    //     }
                    // }

                    tx.Commit();
                }

                TaskDialog.Show("Starter Kit",
                    $"Found {count:N0} elements in category '{selectedCategory}'." +
                    (string.IsNullOrWhiteSpace(filterText) ? "" : $"\nFilter: \"{filterText}\""));

                return Result.Succeeded;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                message = $"Dialog command failed: {ex.Message}";
                System.Diagnostics.Debug.WriteLine($"[StarterKit] ShowDialogCommand error: {ex}");
                return Result.Failed;
            }
        }
    }
}
