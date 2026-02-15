// ============================================================================
// MainWindow.xaml.cs - WPF Dialog Code-Behind
//
// This is the code-behind for the sample WPF dialog. It handles:
//   - Initialization with data from the Revit command
//   - User interaction events (button clicks, combo box changes)
//   - Exposing properties for the command to read after dialog closes
//
// Architecture Note:
//   This starter kit uses code-behind for simplicity. For larger add-ins,
//   consider using MVVM (Model-View-ViewModel) pattern with data binding.
//   The code-behind approach is perfectly fine for simple dialogs and is
//   easier to understand for developers new to WPF.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Windows;

namespace RevitStarterKit.UI
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml.
    /// The calling command creates this window, passes in data, shows it as
    /// a modal dialog, and reads back the user's selections.
    /// </summary>
    public partial class MainWindow : Window
    {
        // ====================================================================
        // PROPERTIES - Read by the calling command after dialog closes
        // ====================================================================

        /// <summary>
        /// The category selected by the user in the combo box.
        /// </summary>
        public string SelectedCategory { get; private set; }

        /// <summary>
        /// Whether the user wants type parameters included.
        /// </summary>
        public bool IncludeTypeParameters { get; private set; }

        /// <summary>
        /// Optional text filter entered by the user.
        /// </summary>
        public string FilterText { get; private set; }

        /// <summary>
        /// Whether to process only selected elements.
        /// </summary>
        public bool SelectedOnly { get; private set; }

        /// <summary>
        /// The document title, set by the calling command for display.
        /// </summary>
        public string DocumentTitle
        {
            get => txtDocumentName.Text;
            set => txtDocumentName.Text = $"Document: {value}";
        }

        // ====================================================================
        // CONSTRUCTOR
        // ====================================================================

        /// <summary>
        /// Creates a new MainWindow dialog with the given category names.
        /// </summary>
        /// <param name="categoryNames">
        /// List of category names to populate the combo box.
        /// Typically gathered from a FilteredElementCollector before showing the dialog.
        /// </param>
        public MainWindow(List<string> categoryNames)
        {
            InitializeComponent();

            // Populate the category combo box
            if (categoryNames != null && categoryNames.Count > 0)
            {
                foreach (string name in categoryNames)
                {
                    cmbCategory.Items.Add(name);
                }

                // Pre-select "Walls" if available, otherwise the first item.
                // This is a UX convenience - users expect a sensible default.
                int wallIndex = categoryNames.IndexOf("Walls");
                cmbCategory.SelectedIndex = wallIndex >= 0 ? wallIndex : 0;
            }

            // Focus the category combo box on load
            Loaded += (s, e) => cmbCategory.Focus();
        }

        /// <summary>
        /// Parameterless constructor for XAML designer support.
        /// Not used at runtime.
        /// </summary>
        public MainWindow()
        {
            InitializeComponent();
        }

        // ====================================================================
        // EVENT HANDLERS
        // ====================================================================

        /// <summary>
        /// OK button click - validates input and closes with DialogResult = true.
        /// </summary>
        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            // Validate: a category must be selected
            if (cmbCategory.SelectedItem == null && string.IsNullOrWhiteSpace(cmbCategory.Text))
            {
                MessageBox.Show(
                    "Please select a category before continuing.",
                    "Validation",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                cmbCategory.Focus();
                return;
            }

            // Store values for the calling command to read
            SelectedCategory = cmbCategory.SelectedItem?.ToString() ?? cmbCategory.Text;
            IncludeTypeParameters = chkIncludeTypes.IsChecked == true;
            SelectedOnly = chkSelectedOnly.IsChecked == true;
            FilterText = txtFilter.Text?.Trim();

            // Close the dialog with a positive result
            DialogResult = true;
            Close();
        }

        /// <summary>
        /// Cancel button click - closes with DialogResult = false.
        /// </summary>
        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        /// <summary>
        /// Updates the status text when the category selection changes.
        /// </summary>
        private void CmbCategory_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (cmbCategory.SelectedItem != null)
            {
                txtStatus.Text = $"Ready to process '{cmbCategory.SelectedItem}' elements.";
            }
        }
    }
}
