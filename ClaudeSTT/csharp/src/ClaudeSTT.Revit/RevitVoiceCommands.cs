using System;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using ClaudeSTT.Core;

namespace ClaudeSTT.Revit
{
    public class SelectWallCommand : BaseVoiceCommand
    {
        public SelectWallCommand()
        {
            CommandText = "select wall";
            Description = "Selects walls in the current view";
            Aliases = new[] { "select walls", "pick wall", "pick walls" };
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            var revitContext = context as RevitCommandContext;
            revitContext?.ExecuteInRevitContext(app =>
            {
                var doc = app.ActiveUIDocument.Document;
                var collector = new FilteredElementCollector(doc, app.ActiveUIDocument.ActiveView.Id)
                    .OfClass(typeof(Wall))
                    .WhereElementIsNotElementType();
                    
                var walls = collector.ToElementIds();
                if (walls.Any())
                {
                    app.ActiveUIDocument.Selection.SetElementIds(walls);
                    context.ShowMessage($"Selected {walls.Count} wall(s)");
                }
                else
                {
                    context.ShowMessage("No walls found in current view");
                }
            });
        }
    }
    
    public class ZoomExtentsCommand : BaseVoiceCommand
    {
        public ZoomExtentsCommand()
        {
            CommandText = "zoom extents";
            Description = "Zooms to fit all elements in view";
            Aliases = new[] { "zoom all", "fit all", "zoom fit" };
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            var revitContext = context as RevitCommandContext;
            revitContext?.ExecuteInRevitContext(app =>
            {
                var uiView = app.ActiveUIDocument.GetOpenUIViews()
                    .FirstOrDefault(v => v.ViewId == app.ActiveUIDocument.ActiveView.Id);
                    
                uiView?.ZoomToFit();
                context.LogInfo("Zoomed to extents");
            });
        }
    }
    
    public class CreateWallCommand : BaseVoiceCommand
    {
        public CreateWallCommand()
        {
            CommandText = "create wall";
            Description = "Creates a wall by picking two points";
            Aliases = new[] { "draw wall", "add wall", "new wall" };
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            var revitContext = context as RevitCommandContext;
            revitContext?.ExecuteInRevitContext(app =>
            {
                try
                {
                    var doc = app.ActiveUIDocument.Document;
                    var selection = app.ActiveUIDocument.Selection;
                    
                    var pt1 = selection.PickPoint("Pick first point for wall");
                    var pt2 = selection.PickPoint("Pick second point for wall");
                    
                    var line = Line.CreateBound(pt1, pt2);
                    
                    using (var trans = new Transaction(doc, "Create Wall by Voice"))
                    {
                        trans.Start();
                        
                        var level = app.ActiveUIDocument.ActiveView.GenLevel;
                        if (level != null)
                        {
                            Wall.Create(doc, line, level.Id, false);
                            trans.Commit();
                            context.ShowMessage("Wall created successfully");
                        }
                        else
                        {
                            trans.RollBack();
                            context.ShowMessage("Could not determine level");
                        }
                    }
                }
                catch (Autodesk.Revit.Exceptions.OperationCanceledException)
                {
                    context.LogInfo("Wall creation cancelled");
                }
                catch (Exception ex)
                {
                    context.LogError($"Error creating wall: {ex.Message}");
                }
            });
        }
    }
    
    public class DeleteSelectedCommand : BaseVoiceCommand
    {
        public DeleteSelectedCommand()
        {
            CommandText = "delete selected";
            Description = "Deletes selected elements";
            Aliases = new[] { "delete", "remove selected", "delete selection" };
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            var revitContext = context as RevitCommandContext;
            revitContext?.ExecuteInRevitContext(app =>
            {
                var doc = app.ActiveUIDocument.Document;
                var selection = app.ActiveUIDocument.Selection;
                var selectedIds = selection.GetElementIds();
                
                if (selectedIds.Any())
                {
                    using (var trans = new Transaction(doc, "Delete by Voice"))
                    {
                        trans.Start();
                        doc.Delete(selectedIds);
                        trans.Commit();
                        context.ShowMessage($"Deleted {selectedIds.Count} element(s)");
                    }
                }
                else
                {
                    context.ShowMessage("No elements selected");
                }
            });
        }
    }
    
    public class UndoCommand : BaseVoiceCommand
    {
        public UndoCommand()
        {
            CommandText = "undo";
            Description = "Undoes the last action";
            Aliases = new[] { "undo last", "revert" };
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            var revitContext = context as RevitCommandContext;
            revitContext?.ExecuteInRevitContext(app =>
            {
                var doc = app.ActiveUIDocument.Document;
                if (doc.CanUndo())
                {
                    doc.Undo();
                    context.LogInfo("Undo executed");
                }
                else
                {
                    context.ShowMessage("Nothing to undo");
                }
            });
        }
    }
}