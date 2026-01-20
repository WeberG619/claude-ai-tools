using System;
using System.Text;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace ClaudeSTT.Revit
{
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class StartCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                ClaudeSTTApplication.StartService(commandData.Application);
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
    
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class StopCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                ClaudeSTTApplication.StopService();
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
    
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class HelpCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Claude Voice Commands for Revit");
            sb.AppendLine("================================");
            sb.AppendLine();
            sb.AppendLine("Wake Word: Say 'Claude' or 'Hey Claude' to activate");
            sb.AppendLine();
            sb.AppendLine("Available Commands:");
            sb.AppendLine("• Select wall / Select walls - Selects all walls in view");
            sb.AppendLine("• Select all - Selects all elements in view");
            sb.AppendLine("• Create wall / Draw wall - Creates a wall by picking points");
            sb.AppendLine("• Delete / Delete selected - Deletes selected elements");
            sb.AppendLine("• Zoom extents / Zoom all - Fits view to all elements");
            sb.AppendLine("• Undo - Undoes the last action");
            sb.AppendLine();
            sb.AppendLine("Tips:");
            sb.AppendLine("• Speak clearly after the wake word");
            sb.AppendLine("• Wait for the listening indicator");
            sb.AppendLine("• Commands work in the active view");
            
            TaskDialog.Show("Claude Voice Commands", sb.ToString());
            
            return Result.Succeeded;
        }
    }
}