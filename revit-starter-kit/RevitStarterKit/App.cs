// ============================================================================
// App.cs - Revit External Application Entry Point
//
// This is the main entry point for your Revit add-in. It implements
// IExternalApplication, which Revit calls on startup and shutdown.
//
// What this file does:
//   - Creates a custom ribbon tab with panels and buttons
//   - Registers all commands so they appear in the Revit UI
//   - Handles application-level startup/shutdown logic
//
// To add a new command:
//   1. Create a class implementing IExternalCommand in the Commands folder
//   2. Add a button for it in the CreateRibbonPanel() method below
// ============================================================================

using System;
using System.IO;
using System.Reflection;
using System.Windows.Media.Imaging;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitStarterKit
{
    /// <summary>
    /// Revit external application. This class is instantiated by Revit on startup
    /// and provides the hooks for ribbon UI creation and cleanup.
    /// </summary>
    public class App : IExternalApplication
    {
        /// <summary>
        /// The name of the custom ribbon tab. Change this to your company/product name.
        /// </summary>
        internal const string TabName = "Starter Kit";

        /// <summary>
        /// The name of the ribbon panel within the custom tab.
        /// </summary>
        internal const string PanelName = "Tools";

        /// <summary>
        /// Static reference to the controlled application, available throughout the add-in.
        /// Useful for subscribing to application-level events.
        /// </summary>
        internal static UIControlledApplication CachedUiApp { get; private set; }

        /// <summary>
        /// Path to the executing assembly. Used to locate the DLL for command registration
        /// and to find resource files (icons, etc.) relative to the add-in.
        /// </summary>
        internal static string AssemblyPath => Assembly.GetExecutingAssembly().Location;

        /// <summary>
        /// Directory containing the executing assembly.
        /// </summary>
        internal static string AssemblyDirectory => Path.GetDirectoryName(AssemblyPath);

        // ====================================================================
        // STARTUP
        // ====================================================================

        /// <summary>
        /// Called by Revit when the application is loaded. This is where you
        /// create your ribbon UI and subscribe to any application-level events.
        /// </summary>
        /// <param name="application">The Revit UI controlled application.</param>
        /// <returns>Result.Succeeded if initialization completes without error.</returns>
        public Result OnStartup(UIControlledApplication application)
        {
            CachedUiApp = application;

            try
            {
                // Create the ribbon tab and panels
                CreateRibbonTab(application);

                // Subscribe to application-level events if needed
                // application.ControlledApplication.DocumentOpened += OnDocumentOpened;
                // application.ControlledApplication.DocumentClosing += OnDocumentClosing;

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Starter Kit - Error",
                    $"Failed to initialize add-in:\n\n{ex.Message}");
                return Result.Failed;
            }
        }

        // ====================================================================
        // SHUTDOWN
        // ====================================================================

        /// <summary>
        /// Called by Revit when the application is being unloaded (Revit closing).
        /// Clean up any resources, unsubscribe from events, etc.
        /// </summary>
        /// <param name="application">The Revit UI controlled application.</param>
        /// <returns>Result.Succeeded.</returns>
        public Result OnShutdown(UIControlledApplication application)
        {
            // Unsubscribe from events
            // application.ControlledApplication.DocumentOpened -= OnDocumentOpened;

            return Result.Succeeded;
        }

        // ====================================================================
        // RIBBON UI CREATION
        // ====================================================================

        /// <summary>
        /// Creates the ribbon tab, panels, and buttons for the add-in.
        /// Modify this method to add or reorganize your ribbon UI.
        /// </summary>
        private void CreateRibbonTab(UIControlledApplication application)
        {
            // --- Create a custom tab ---
            // If you prefer to add to an existing tab, skip this and use
            // application.CreateRibbonPanel("Add-Ins", PanelName) instead.
            application.CreateRibbonTab(TabName);

            // --- Create the main Tools panel ---
            RibbonPanel toolsPanel = application.CreateRibbonPanel(TabName, PanelName);

            // --- Sample Command Button ---
            PushButtonData sampleBtnData = new PushButtonData(
                name: "cmdSampleCommand",
                text: "Sample\nCommand",
                assemblyName: AssemblyPath,
                className: "RevitStarterKit.Commands.SampleCommand")
            {
                ToolTip = "Runs a sample command that displays information about the active view.",
                LongDescription = "This is a starter command that demonstrates the basic structure " +
                                  "of a Revit IExternalCommand. It retrieves data from the active " +
                                  "document and displays it in a TaskDialog.",
#if REVIT2026
                AvailabilityClassName = null // Available always in 2026+
#endif
            };

            // Set button icon (32x32 for large, 16x16 for small)
            // If you have icon files in Resources/, uncomment and adjust:
            // sampleBtnData.LargeImage = LoadBitmapImage("Resources/sample_32.png");
            // sampleBtnData.Image = LoadBitmapImage("Resources/sample_16.png");

            toolsPanel.AddItem(sampleBtnData);

            // --- Data Export Command Button ---
            PushButtonData exportBtnData = new PushButtonData(
                name: "cmdDataExport",
                text: "Export\nto CSV",
                assemblyName: AssemblyPath,
                className: "RevitStarterKit.Commands.DataExportCommand")
            {
                ToolTip = "Exports element data from the current view or selection to a CSV file.",
                LongDescription = "Collects elements from the active view and exports their " +
                                  "parameter data (category, type, level, area, volume) to " +
                                  "a CSV file. Supports both selected elements and all elements " +
                                  "in the active view."
            };

            toolsPanel.AddItem(exportBtnData);

            // --- Separator ---
            toolsPanel.AddSeparator();

            // --- Show Dialog Button ---
            PushButtonData dialogBtnData = new PushButtonData(
                name: "cmdShowDialog",
                text: "Show\nDialog",
                assemblyName: AssemblyPath,
                className: "RevitStarterKit.Commands.ShowDialogCommand")
            {
                ToolTip = "Opens the sample WPF dialog window.",
                LongDescription = "Demonstrates how to launch a WPF window from a Revit command, " +
                                  "pass data between the dialog and Revit, and handle user input."
            };

            toolsPanel.AddItem(dialogBtnData);

            // =================================================================
            // ADDING MORE BUTTONS - EXAMPLES
            // =================================================================
            //
            // --- Stacked buttons (2 or 3 small buttons stacked vertically) ---
            // PushButtonData btn1 = new PushButtonData("cmd1", "Button 1", AssemblyPath, "Namespace.Class1");
            // PushButtonData btn2 = new PushButtonData("cmd2", "Button 2", AssemblyPath, "Namespace.Class2");
            // PushButtonData btn3 = new PushButtonData("cmd3", "Button 3", AssemblyPath, "Namespace.Class3");
            // toolsPanel.AddStackedItems(btn1, btn2, btn3);
            //
            // --- Pull-down (dropdown) button ---
            // PulldownButtonData pullData = new PulldownButtonData("pullMenu", "More Tools");
            // PulldownButton pullBtn = toolsPanel.AddItem(pullData) as PulldownButton;
            // pullBtn.AddPushButton(new PushButtonData("sub1", "Sub Command 1", AssemblyPath, "Namespace.SubCmd1"));
            // pullBtn.AddPushButton(new PushButtonData("sub2", "Sub Command 2", AssemblyPath, "Namespace.SubCmd2"));
            //
            // --- Split button (default action + dropdown) ---
            // SplitButtonData splitData = new SplitButtonData("splitBtn", "Split");
            // SplitButton splitBtn = toolsPanel.AddItem(splitData) as SplitButton;
            // splitBtn.AddPushButton(new PushButtonData("main", "Main Action", AssemblyPath, "Namespace.Main"));
            // splitBtn.AddPushButton(new PushButtonData("alt", "Alt Action", AssemblyPath, "Namespace.Alt"));
        }

        // ====================================================================
        // HELPERS
        // ====================================================================

        /// <summary>
        /// Loads a BitmapImage from a path relative to the assembly directory.
        /// Use this to set button icons from embedded or adjacent image files.
        /// </summary>
        /// <param name="relativePath">Path relative to the assembly location.</param>
        /// <returns>A BitmapImage, or null if the file doesn't exist.</returns>
        internal static BitmapImage LoadBitmapImage(string relativePath)
        {
            string fullPath = Path.Combine(AssemblyDirectory, relativePath);

            if (!File.Exists(fullPath))
                return null;

            BitmapImage image = new BitmapImage();
            image.BeginInit();
            image.UriSource = new Uri(fullPath, UriKind.Absolute);
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.EndInit();
            image.Freeze(); // Required for cross-thread access in WPF

            return image;
        }

        // ====================================================================
        // EVENT HANDLERS (uncomment and customize as needed)
        // ====================================================================

        // private void OnDocumentOpened(object sender, Autodesk.Revit.DB.Events.DocumentOpenedEventArgs e)
        // {
        //     // Runs every time a document is opened in Revit
        //     Document doc = e.Document;
        //     // Your logic here...
        // }

        // private void OnDocumentClosing(object sender, Autodesk.Revit.DB.Events.DocumentClosingEventArgs e)
        // {
        //     // Runs every time a document is about to close
        //     Document doc = e.Document;
        //     // Your logic here...
        // }
    }
}
