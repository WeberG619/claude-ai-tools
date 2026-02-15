// ============================================================================
// RevitHelper.cs - Common Revit API Helper Methods
//
// A collection of utility methods that you'll use constantly when building
// Revit add-ins. These handle the most common operations:
//
//   - Parameter reading (string, double, int, ElementId)
//   - Unit conversion (internal units <-> display units)
//   - Element selection and collection
//   - Transaction management
//   - Element filtering shortcuts
//
// Usage: Call these as static methods, e.g.:
//   string value = RevitHelper.GetParameterValueAsString(element, BuiltInParameter.ALL_MODEL_MARK);
//   List<Element> walls = RevitHelper.GetElementsOfCategory(doc, BuiltInCategory.OST_Walls);
//
// Version Compatibility:
//   Methods use conditional compilation (#if REVIT2024, etc.) where the API
//   differs between Revit versions, particularly for unit conversion.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;

namespace RevitStarterKit.Utils
{
    /// <summary>
    /// Static helper methods for common Revit API operations.
    /// </summary>
    public static class RevitHelper
    {
        // ====================================================================
        // PARAMETER READING
        // ====================================================================

        /// <summary>
        /// Gets a built-in parameter value as a string. Handles null checks,
        /// missing parameters, and type conversion. This is the safest way
        /// to read parameter values.
        /// </summary>
        /// <param name="element">The element to read from.</param>
        /// <param name="bip">The built-in parameter to read.</param>
        /// <returns>The parameter value as a string, or empty string if not found.</returns>
        public static string GetParameterValueAsString(Element element, BuiltInParameter bip)
        {
            if (element == null)
                return string.Empty;

            Parameter param = element.get_Parameter(bip);
            return GetParameterValueAsString(param);
        }

        /// <summary>
        /// Gets a named parameter value as a string. Searches instance parameters first,
        /// then type parameters.
        /// </summary>
        /// <param name="element">The element to read from.</param>
        /// <param name="parameterName">The parameter name to search for.</param>
        /// <returns>The parameter value as a string, or empty string if not found.</returns>
        public static string GetParameterValueAsString(Element element, string parameterName)
        {
            if (element == null || string.IsNullOrEmpty(parameterName))
                return string.Empty;

            // Try instance parameter first
            Parameter param = element.LookupParameter(parameterName);

            // Fall back to type parameter
            if (param == null)
            {
                ElementId typeId = element.GetTypeId();
                if (typeId != null && typeId != ElementId.InvalidElementId)
                {
                    Element elemType = element.Document.GetElement(typeId);
                    param = elemType?.LookupParameter(parameterName);
                }
            }

            return GetParameterValueAsString(param);
        }

        /// <summary>
        /// Converts a Parameter to its string representation, handling all
        /// storage types (String, Integer, Double, ElementId).
        /// </summary>
        public static string GetParameterValueAsString(Parameter param)
        {
            if (param == null || !param.HasValue)
                return string.Empty;

            switch (param.StorageType)
            {
                case StorageType.String:
                    return param.AsString() ?? string.Empty;

                case StorageType.Integer:
                    // For Yes/No parameters, return "Yes" or "No"
#if REVIT2024
                    if (param.Definition.ParameterType == ParameterType.YesNo)
                        return param.AsInteger() == 1 ? "Yes" : "No";
#else
                    // Revit 2025+ uses ForgeTypeId for parameter type checking
                    if (param.Definition.GetDataType() == SpecTypeId.Boolean.YesNo)
                        return param.AsInteger() == 1 ? "Yes" : "No";
#endif
                    return param.AsInteger().ToString();

                case StorageType.Double:
                    // Return the value as displayed in Revit (with units applied)
                    return param.AsValueString() ?? param.AsDouble().ToString("F4");

                case StorageType.ElementId:
                    ElementId id = param.AsElementId();
                    if (id == null || id == ElementId.InvalidElementId)
                        return string.Empty;
                    // Try to get the element name
                    Element refElem = param.Element?.Document?.GetElement(id);
                    return refElem?.Name ?? id.Value.ToString();

                default:
                    return string.Empty;
            }
        }

        /// <summary>
        /// Gets a parameter's double value in internal Revit units (feet, radians).
        /// Returns the default value if the parameter is missing.
        /// </summary>
        public static double GetParameterDouble(Element element, BuiltInParameter bip, double defaultValue = 0.0)
        {
            Parameter param = element?.get_Parameter(bip);
            if (param == null || !param.HasValue || param.StorageType != StorageType.Double)
                return defaultValue;

            return param.AsDouble();
        }

        /// <summary>
        /// Gets a parameter's integer value. Returns the default value if missing.
        /// </summary>
        public static int GetParameterInt(Element element, BuiltInParameter bip, int defaultValue = 0)
        {
            Parameter param = element?.get_Parameter(bip);
            if (param == null || !param.HasValue || param.StorageType != StorageType.Integer)
                return defaultValue;

            return param.AsInteger();
        }

        // ====================================================================
        // PARAMETER WRITING
        // ====================================================================

        /// <summary>
        /// Sets a parameter value safely. Checks for null, read-only, and type mismatches.
        /// Must be called inside an active transaction.
        /// </summary>
        /// <returns>True if the parameter was set successfully.</returns>
        public static bool SetParameterValue(Element element, BuiltInParameter bip, string value)
        {
            Parameter param = element?.get_Parameter(bip);
            if (param == null || param.IsReadOnly)
                return false;

            if (param.StorageType == StorageType.String)
            {
                param.Set(value);
                return true;
            }

            return false;
        }

        /// <summary>
        /// Sets a parameter value by parameter name. Searches instance parameters first.
        /// Must be called inside an active transaction.
        /// </summary>
        public static bool SetParameterValue(Element element, string parameterName, string value)
        {
            Parameter param = element?.LookupParameter(parameterName);
            if (param == null || param.IsReadOnly)
                return false;

            if (param.StorageType == StorageType.String)
            {
                param.Set(value);
                return true;
            }

            return false;
        }

        // ====================================================================
        // UNIT CONVERSION
        // ====================================================================

        /// <summary>
        /// Converts a value from internal Revit units (feet) to the specified unit.
        /// Handles API differences between Revit 2024 and 2025+.
        /// </summary>
        /// <example>
        /// double meters = RevitHelper.ConvertFromInternal(lengthInFeet, UnitGroup.Length);
        /// </example>
        public static double ConvertFromInternal(double internalValue, ForgeTypeId unitTypeId)
        {
            return UnitUtils.ConvertFromInternalUnits(internalValue, unitTypeId);
        }

        /// <summary>
        /// Converts a value to internal Revit units (feet) from the specified unit.
        /// </summary>
        public static double ConvertToInternal(double displayValue, ForgeTypeId unitTypeId)
        {
            return UnitUtils.ConvertToInternalUnits(displayValue, unitTypeId);
        }

        /// <summary>
        /// Converts feet to millimeters (the most common conversion in Revit development).
        /// </summary>
        public static double FeetToMm(double feet)
        {
            return UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Millimeters);
        }

        /// <summary>
        /// Converts millimeters to feet (internal Revit units).
        /// </summary>
        public static double MmToFeet(double mm)
        {
            return UnitUtils.ConvertToInternalUnits(mm, UnitTypeId.Millimeters);
        }

        /// <summary>
        /// Converts feet to meters.
        /// </summary>
        public static double FeetToMeters(double feet)
        {
            return UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Meters);
        }

        /// <summary>
        /// Converts square feet (internal) to square meters.
        /// </summary>
        public static double SqFeetToSqMeters(double sqFeet)
        {
            return UnitUtils.ConvertFromInternalUnits(sqFeet, UnitTypeId.SquareMeters);
        }

        // ====================================================================
        // ELEMENT SELECTION
        // ====================================================================

        /// <summary>
        /// Gets the currently selected elements in the active document.
        /// Returns an empty list if nothing is selected.
        /// </summary>
        public static List<Element> GetSelectedElements(UIDocument uiDoc)
        {
            if (uiDoc == null)
                return new List<Element>();

            Document doc = uiDoc.Document;
            ICollection<ElementId> ids = uiDoc.Selection.GetElementIds();

            return ids
                .Select(id => doc.GetElement(id))
                .Where(e => e != null)
                .ToList();
        }

        /// <summary>
        /// Gets selected elements of a specific type. For example:
        /// var walls = RevitHelper.GetSelectedElements&lt;Wall&gt;(uiDoc);
        /// </summary>
        public static List<T> GetSelectedElements<T>(UIDocument uiDoc) where T : Element
        {
            return GetSelectedElements(uiDoc).OfType<T>().ToList();
        }

        /// <summary>
        /// Prompts the user to pick a single element. Returns null if cancelled.
        /// </summary>
        /// <param name="uiDoc">The active UI document.</param>
        /// <param name="prompt">Message displayed in the status bar.</param>
        /// <returns>The picked element, or null if the user pressed Escape.</returns>
        public static Element PickElement(UIDocument uiDoc, string prompt = "Select an element")
        {
            try
            {
                Reference reference = uiDoc.Selection.PickObject(
                    ObjectType.Element, prompt);
                return uiDoc.Document.GetElement(reference);
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                return null;
            }
        }

        /// <summary>
        /// Prompts the user to pick multiple elements. Returns an empty list if cancelled.
        /// </summary>
        public static List<Element> PickElements(UIDocument uiDoc, string prompt = "Select elements")
        {
            try
            {
                IList<Reference> references = uiDoc.Selection.PickObjects(
                    ObjectType.Element, prompt);
                return references
                    .Select(r => uiDoc.Document.GetElement(r))
                    .Where(e => e != null)
                    .ToList();
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                return new List<Element>();
            }
        }

        // ====================================================================
        // ELEMENT COLLECTION (FilteredElementCollector shortcuts)
        // ====================================================================

        /// <summary>
        /// Gets all element instances of a specific category in the document.
        /// This is the most common collector operation.
        /// </summary>
        /// <example>
        /// var walls = RevitHelper.GetElementsOfCategory(doc, BuiltInCategory.OST_Walls);
        /// var doors = RevitHelper.GetElementsOfCategory(doc, BuiltInCategory.OST_Doors);
        /// </example>
        public static List<Element> GetElementsOfCategory(Document doc, BuiltInCategory category)
        {
            return new FilteredElementCollector(doc)
                .OfCategory(category)
                .WhereElementIsNotElementType()
                .ToList();
        }

        /// <summary>
        /// Gets all element instances of a specific category in a specific view.
        /// Use this when you only want visible elements.
        /// </summary>
        public static List<Element> GetElementsOfCategory(Document doc, BuiltInCategory category, ElementId viewId)
        {
            return new FilteredElementCollector(doc, viewId)
                .OfCategory(category)
                .WhereElementIsNotElementType()
                .ToList();
        }

        /// <summary>
        /// Gets all element types (not instances) of a category.
        /// Useful for getting wall types, floor types, etc.
        /// </summary>
        public static List<ElementType> GetTypesOfCategory(Document doc, BuiltInCategory category)
        {
            return new FilteredElementCollector(doc)
                .OfCategory(category)
                .WhereElementIsElementType()
                .Cast<ElementType>()
                .ToList();
        }

        /// <summary>
        /// Gets all elements of a specific class. For example:
        /// var levels = RevitHelper.GetElementsOfClass&lt;Level&gt;(doc);
        /// var grids = RevitHelper.GetElementsOfClass&lt;Grid&gt;(doc);
        /// </summary>
        public static List<T> GetElementsOfClass<T>(Document doc) where T : Element
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(T))
                .Cast<T>()
                .ToList();
        }

        /// <summary>
        /// Gets all levels in the document, sorted by elevation.
        /// </summary>
        public static List<Level> GetLevelsSorted(Document doc)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .Cast<Level>()
                .OrderBy(l => l.Elevation)
                .ToList();
        }

        /// <summary>
        /// Gets all views of a specific type (floor plans, sections, 3D views, etc.).
        /// Excludes view templates.
        /// </summary>
        public static List<View> GetViewsOfType(Document doc, ViewType viewType)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(View))
                .Cast<View>()
                .Where(v => v.ViewType == viewType && !v.IsTemplate)
                .OrderBy(v => v.Name)
                .ToList();
        }

        // ====================================================================
        // TRANSACTION HELPERS
        // ====================================================================

        /// <summary>
        /// Executes an action inside a transaction. Handles start, commit, and
        /// rollback automatically. This is the recommended pattern for simple
        /// modifications.
        /// </summary>
        /// <example>
        /// RevitHelper.ExecuteInTransaction(doc, "Set Marks", () =>
        /// {
        ///     foreach (var wall in walls)
        ///     {
        ///         wall.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set("Done");
        ///     }
        /// });
        /// </example>
        /// <returns>True if the transaction committed successfully.</returns>
        public static bool ExecuteInTransaction(Document doc, string transactionName, Action action)
        {
            using (Transaction tx = new Transaction(doc, transactionName))
            {
                tx.Start();

                try
                {
                    action();
                    tx.Commit();
                    return true;
                }
                catch
                {
                    if (tx.HasStarted() && !tx.HasEnded())
                    {
                        tx.RollBack();
                    }
                    throw; // Re-throw so the caller can handle it
                }
            }
        }

        /// <summary>
        /// Executes an action inside a transaction and returns a result.
        /// </summary>
        /// <example>
        /// int count = RevitHelper.ExecuteInTransaction(doc, "Count Modified", () =>
        /// {
        ///     int modified = 0;
        ///     // ... modify elements ...
        ///     return modified;
        /// });
        /// </example>
        public static T ExecuteInTransaction<T>(Document doc, string transactionName, Func<T> func)
        {
            using (Transaction tx = new Transaction(doc, transactionName))
            {
                tx.Start();

                try
                {
                    T result = func();
                    tx.Commit();
                    return result;
                }
                catch
                {
                    if (tx.HasStarted() && !tx.HasEnded())
                    {
                        tx.RollBack();
                    }
                    throw;
                }
            }
        }

        /// <summary>
        /// Executes an action inside a transaction group (multiple sub-transactions).
        /// Useful when you need to perform several independent modifications that
        /// should be undone as a single operation.
        /// </summary>
        public static bool ExecuteInTransactionGroup(Document doc, string groupName, Action action)
        {
            using (TransactionGroup tg = new TransactionGroup(doc, groupName))
            {
                tg.Start();

                try
                {
                    action();
                    tg.Assimilate();
                    return true;
                }
                catch
                {
                    if (tg.HasStarted() && !tg.HasEnded())
                    {
                        tg.RollBack();
                    }
                    throw;
                }
            }
        }

        // ====================================================================
        // GEOMETRY HELPERS
        // ====================================================================

        /// <summary>
        /// Gets the bounding box center point of an element.
        /// Returns null if the element has no bounding box.
        /// </summary>
        public static XYZ GetElementCenter(Element element)
        {
            BoundingBoxXYZ bbox = element.get_BoundingBox(null);
            if (bbox == null)
                return null;

            return (bbox.Min + bbox.Max) / 2.0;
        }

        /// <summary>
        /// Gets the location point of an element (for point-based elements like
        /// columns, furniture, etc.). Returns null for line-based elements.
        /// </summary>
        public static XYZ GetLocationPoint(Element element)
        {
            LocationPoint locPoint = element.Location as LocationPoint;
            return locPoint?.Point;
        }

        /// <summary>
        /// Gets the location curve of a line-based element (walls, beams, pipes, etc.).
        /// Returns null for point-based elements.
        /// </summary>
        public static Curve GetLocationCurve(Element element)
        {
            LocationCurve locCurve = element.Location as LocationCurve;
            return locCurve?.Curve;
        }

        // ====================================================================
        // FAMILY HELPERS
        // ====================================================================

        /// <summary>
        /// Gets the family name for an element instance.
        /// Works for both system families (walls, floors) and loadable families (doors, windows).
        /// </summary>
        public static string GetFamilyName(Element element)
        {
            if (element == null) return string.Empty;

            // For FamilyInstance (loadable families)
            if (element is FamilyInstance fi)
            {
                return fi.Symbol?.Family?.Name ?? string.Empty;
            }

            // For system families, get the type name
            ElementId typeId = element.GetTypeId();
            if (typeId != null && typeId != ElementId.InvalidElementId)
            {
                ElementType elemType = element.Document.GetElement(typeId) as ElementType;
                return elemType?.FamilyName ?? string.Empty;
            }

            return string.Empty;
        }

        /// <summary>
        /// Gets the type name for an element instance.
        /// </summary>
        public static string GetTypeName(Element element)
        {
            if (element == null) return string.Empty;

            ElementId typeId = element.GetTypeId();
            if (typeId != null && typeId != ElementId.InvalidElementId)
            {
                return element.Document.GetElement(typeId)?.Name ?? string.Empty;
            }

            return string.Empty;
        }

        // ====================================================================
        // MISCELLANEOUS
        // ====================================================================

        /// <summary>
        /// Checks if a document is a family document (as opposed to a project document).
        /// </summary>
        public static bool IsFamilyDocument(Document doc)
        {
            return doc?.IsFamilyDocument ?? false;
        }

        /// <summary>
        /// Gets the active view, or null if no document is open.
        /// </summary>
        public static View GetActiveView(UIDocument uiDoc)
        {
            return uiDoc?.Document?.ActiveView;
        }

        /// <summary>
        /// Shows a simple message using TaskDialog. Convenience wrapper.
        /// </summary>
        public static void ShowMessage(string title, string message)
        {
            TaskDialog.Show(title, message);
        }

        /// <summary>
        /// Shows a Yes/No confirmation dialog. Returns true if the user clicked Yes.
        /// </summary>
        public static bool Confirm(string title, string message)
        {
            TaskDialog td = new TaskDialog(title)
            {
                MainContent = message,
                CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
                DefaultButton = TaskDialogResult.No
            };

            return td.Show() == TaskDialogResult.Yes;
        }

        /// <summary>
        /// Gets a unique identifier string for an element that persists across sessions.
        /// Uses the UniqueId property, which is stable (unlike ElementId which can change).
        /// </summary>
        public static string GetStableId(Element element)
        {
            return element?.UniqueId ?? string.Empty;
        }

        /// <summary>
        /// Finds an element by its UniqueId string.
        /// </summary>
        public static Element FindByUniqueId(Document doc, string uniqueId)
        {
            if (doc == null || string.IsNullOrEmpty(uniqueId))
                return null;

            return doc.GetElement(uniqueId);
        }
    }
}
