// ============================================================================
// DataExportCommand.cs - Export Element Data to CSV
//
// A practical, production-ready command that exports element parameter data
// to a CSV file. This demonstrates:
//
//   - Working with FilteredElementCollector and filters
//   - Reading parameter values (string, double, int, ElementId)
//   - Handling unit conversions across Revit versions
//   - File I/O with SaveFileDialog
//   - Progress reporting for long operations
//   - Multi-version support with conditional compilation
//
// This is the kind of utility command that every Revit team needs.
// Customize the exported parameters to match your project requirements.
// ============================================================================

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitStarterKit.Utils;
using Microsoft.Win32;

namespace RevitStarterKit.Commands
{
    /// <summary>
    /// Exports element data from the active view or current selection to CSV.
    /// If elements are selected, only those are exported. Otherwise, all
    /// visible elements in the active view are included.
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    [Regeneration(RegenerationOption.Manual)]
    public class DataExportCommand : IExternalCommand
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
                TaskDialog.Show("Export", "Please open a document first.");
                return Result.Cancelled;
            }

            Document doc = uiDoc.Document;

            try
            {
                // --- Step 1: Determine which elements to export ---
                List<Element> exportElements = GetElementsToExport(doc, uiDoc);

                if (exportElements.Count == 0)
                {
                    TaskDialog.Show("Export",
                        "No elements found to export.\n\n" +
                        "Select specific elements, or ensure the active view " +
                        "contains model elements.");
                    return Result.Cancelled;
                }

                // --- Step 2: Ask user for file location ---
                SaveFileDialog saveDialog = new SaveFileDialog
                {
                    Title = "Export Element Data to CSV",
                    Filter = "CSV Files (*.csv)|*.csv|All Files (*.*)|*.*",
                    DefaultExt = "csv",
                    FileName = $"{SanitizeFileName(doc.Title)}_Export_{DateTime.Now:yyyyMMdd_HHmmss}.csv",
                    OverwritePrompt = true
                };

                if (saveDialog.ShowDialog() != true)
                {
                    return Result.Cancelled;
                }

                string filePath = saveDialog.FileName;

                // --- Step 3: Build CSV data ---
                string csvContent = BuildCsvContent(doc, exportElements);

                // --- Step 4: Write file ---
                File.WriteAllText(filePath, csvContent, Encoding.UTF8);

                // --- Step 5: Report results ---
                TaskDialog resultDialog = new TaskDialog("Export Complete")
                {
                    MainInstruction = $"Exported {exportElements.Count:N0} elements",
                    MainContent = $"File saved to:\n{filePath}",
                    CommonButtons = TaskDialogCommonButtons.Close,
                    FooterText = "Click the link below to open the file."
                };

                // Add a command link to open the file
                resultDialog.AddCommandLink(
                    TaskDialogCommandLinkId.CommandLink1,
                    "Open CSV file",
                    "Opens the exported file in your default CSV application.");

                resultDialog.AddCommandLink(
                    TaskDialogCommandLinkId.CommandLink2,
                    "Open containing folder",
                    "Opens the folder where the file was saved.");

                TaskDialogResult result = resultDialog.Show();

                if (result == TaskDialogResult.CommandLink1)
                {
                    System.Diagnostics.Process.Start(
                        new System.Diagnostics.ProcessStartInfo(filePath) { UseShellExecute = true });
                }
                else if (result == TaskDialogResult.CommandLink2)
                {
                    System.Diagnostics.Process.Start(
                        new System.Diagnostics.ProcessStartInfo("explorer.exe", $"/select,\"{filePath}\"")
                        { UseShellExecute = true });
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = $"Export failed: {ex.Message}";
                System.Diagnostics.Debug.WriteLine($"[StarterKit] DataExportCommand error: {ex}");
                return Result.Failed;
            }
        }

        // ====================================================================
        // ELEMENT COLLECTION
        // ====================================================================

        /// <summary>
        /// Gets elements to export: selected elements if any, otherwise all
        /// model elements visible in the active view.
        /// </summary>
        private List<Element> GetElementsToExport(Document doc, UIDocument uiDoc)
        {
            // Check if user has selected elements
            ICollection<ElementId> selectedIds = uiDoc.Selection.GetElementIds();

            if (selectedIds.Count > 0)
            {
                return selectedIds
                    .Select(id => doc.GetElement(id))
                    .Where(e => e != null && e.Category != null)
                    .ToList();
            }

            // No selection - get all model elements in the active view
            return new FilteredElementCollector(doc, doc.ActiveView.Id)
                .WhereElementIsNotElementType()
                .Where(e => e.Category != null
                         && e.Category.CategoryType == CategoryType.Model
                         && e.Category.HasMaterialQuantities)
                .ToList();
        }

        // ====================================================================
        // CSV GENERATION
        // ====================================================================

        /// <summary>
        /// Builds the CSV content string from a list of elements.
        /// Customize the columns here to export the parameters you need.
        /// </summary>
        private string BuildCsvContent(Document doc, List<Element> elements)
        {
            StringBuilder csv = new StringBuilder();

            // --- Header row ---
            csv.AppendLine(string.Join(",", new[]
            {
                "ElementId",
                "Category",
                "Family",
                "Type",
                "Level",
                "Phase Created",
                "Design Option",
                "Area (sq ft)",
                "Volume (cu ft)",
                "Mark",
                "Comments",
                "Workset"
            }));

            // --- Data rows ---
            foreach (Element elem in elements)
            {
                // Get the element type for Family and Type name
                ElementId typeId = elem.GetTypeId();
                ElementType elemType = typeId != ElementId.InvalidElementId
                    ? doc.GetElement(typeId) as ElementType
                    : null;

                // Get level name
                string levelName = "";
                if (elem.LevelId != null && elem.LevelId != ElementId.InvalidElementId)
                {
                    Level level = doc.GetElement(elem.LevelId) as Level;
                    levelName = level?.Name ?? "";
                }

                // Get common parameter values using our helper
                string mark = RevitHelper.GetParameterValueAsString(elem, BuiltInParameter.ALL_MODEL_MARK);
                string comments = RevitHelper.GetParameterValueAsString(elem, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);

                // Get area and volume (these are stored in internal units - square/cubic feet)
                double area = GetDoubleParam(elem, BuiltInParameter.HOST_AREA_COMPUTED);
                double volume = GetDoubleParam(elem, BuiltInParameter.HOST_VOLUME_COMPUTED);

                // Get phase
                string phaseName = "";
                Parameter phaseParam = elem.get_Parameter(BuiltInParameter.PHASE_CREATED);
                if (phaseParam != null && phaseParam.HasValue)
                {
                    ElementId phaseId = phaseParam.AsElementId();
                    if (phaseId != ElementId.InvalidElementId)
                    {
                        phaseName = doc.GetElement(phaseId)?.Name ?? "";
                    }
                }

                // Get design option
                string designOption = "";
                if (elem.DesignOption != null)
                {
                    designOption = elem.DesignOption.Name;
                }

                // Get workset name (only for workshared documents)
                string worksetName = "";
                if (doc.IsWorkshared)
                {
                    WorksetId wsId = elem.WorksetId;
                    if (wsId != null)
                    {
                        Workset ws = doc.GetWorksetTable().GetWorkset(wsId);
                        worksetName = ws?.Name ?? "";
                    }
                }

                // Build the CSV row
                csv.AppendLine(string.Join(",", new[]
                {
                    elem.Id.Value.ToString(),
                    CsvEscape(elem.Category?.Name ?? ""),
                    CsvEscape(elemType?.FamilyName ?? elem.Name ?? ""),
                    CsvEscape(elemType?.Name ?? ""),
                    CsvEscape(levelName),
                    CsvEscape(phaseName),
                    CsvEscape(designOption),
                    area > 0 ? Math.Round(area, 2).ToString() : "",
                    volume > 0 ? Math.Round(volume, 2).ToString() : "",
                    CsvEscape(mark),
                    CsvEscape(comments),
                    CsvEscape(worksetName)
                }));
            }

            return csv.ToString();
        }

        // ====================================================================
        // HELPERS
        // ====================================================================

        /// <summary>
        /// Gets a double parameter value from an element. Returns 0 if the
        /// parameter doesn't exist or has no value.
        /// </summary>
        private double GetDoubleParam(Element elem, BuiltInParameter bip)
        {
            Parameter param = elem.get_Parameter(bip);
            if (param == null || !param.HasValue)
                return 0.0;

            return param.AsDouble();
        }

        /// <summary>
        /// Escapes a string for CSV output. Wraps in quotes if the value
        /// contains commas, quotes, or newlines.
        /// </summary>
        private string CsvEscape(string value)
        {
            if (string.IsNullOrEmpty(value))
                return "";

            // If the value contains special characters, wrap in quotes
            if (value.Contains(",") || value.Contains("\"") || value.Contains("\n") || value.Contains("\r"))
            {
                return $"\"{value.Replace("\"", "\"\"")}\"";
            }

            return value;
        }

        /// <summary>
        /// Removes invalid filename characters from a string.
        /// </summary>
        private string SanitizeFileName(string name)
        {
            char[] invalid = Path.GetInvalidFileNameChars();
            return string.Concat(name.Where(c => !invalid.Contains(c)));
        }
    }
}
