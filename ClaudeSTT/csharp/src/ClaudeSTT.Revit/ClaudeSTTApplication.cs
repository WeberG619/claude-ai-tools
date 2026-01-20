using System;
using System.IO;
using System.Reflection;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;
using ClaudeSTT.Core;

namespace ClaudeSTT.Revit
{
    public class ClaudeSTTApplication : IExternalApplication
    {
        private static PythonSTTService _sttService;
        private static VoiceCommandManager _commandManager;
        private static RevitCommandContext _context;
        
        public Result OnStartup(UIControlledApplication application)
        {
            try
            {
                CreateRibbonPanel(application);
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Claude STT Error", $"Failed to initialize: {ex.Message}");
                return Result.Failed;
            }
        }
        
        public Result OnShutdown(UIControlledApplication application)
        {
            _sttService?.Stop();
            _sttService?.Dispose();
            return Result.Succeeded;
        }
        
        private void CreateRibbonPanel(UIControlledApplication application)
        {
            var tabName = "Claude Voice";
            
            try
            {
                application.CreateRibbonTab(tabName);
            }
            catch { }
            
            var panel = application.CreateRibbonPanel(tabName, "Voice Commands");
            
            var assemblyPath = Assembly.GetExecutingAssembly().Location;
            
            var startButtonData = new PushButtonData(
                "StartClaudeSTT",
                "Start\nListening",
                assemblyPath,
                "ClaudeSTT.Revit.StartCommand"
            )
            {
                ToolTip = "Start Claude voice recognition",
                LongDescription = "Say 'Claude' or 'Hey Claude' to activate voice commands",
                Image = LoadImage("microphone_16.png"),
                LargeImage = LoadImage("microphone_32.png")
            };
            
            var stopButtonData = new PushButtonData(
                "StopClaudeSTT",
                "Stop\nListening",
                assemblyPath,
                "ClaudeSTT.Revit.StopCommand"
            )
            {
                ToolTip = "Stop Claude voice recognition",
                Image = LoadImage("stop_16.png"),
                LargeImage = LoadImage("stop_32.png")
            };
            
            panel.AddItem(startButtonData);
            panel.AddItem(stopButtonData);
            
            panel.AddSeparator();
            
            var helpButtonData = new PushButtonData(
                "ClaudeSTTHelp",
                "Voice\nCommands",
                assemblyPath,
                "ClaudeSTT.Revit.HelpCommand"
            )
            {
                ToolTip = "Show available voice commands",
                Image = LoadImage("help_16.png"),
                LargeImage = LoadImage("help_32.png")
            };
            
            panel.AddItem(helpButtonData);
        }
        
        private BitmapSource LoadImage(string imageName)
        {
            try
            {
                var assembly = Assembly.GetExecutingAssembly();
                var stream = assembly.GetManifestResourceStream($"ClaudeSTT.Revit.Resources.{imageName}");
                
                if (stream != null)
                {
                    var image = new BitmapImage();
                    image.BeginInit();
                    image.StreamSource = stream;
                    image.EndInit();
                    return image;
                }
            }
            catch { }
            
            return null;
        }
        
        internal static void StartService(UIApplication uiApp)
        {
            if (_sttService != null && _sttService.IsRunning)
            {
                TaskDialog.Show("Claude STT", "Voice recognition is already running");
                return;
            }
            
            var pythonPath = GetPythonPath();
            var scriptPath = GetScriptPath();
            
            _sttService = new PythonSTTService(pythonPath, scriptPath);
            _commandManager = new VoiceCommandManager(_sttService);
            _context = new RevitCommandContext(uiApp);
            
            _commandManager.SetContext(_context);
            
            RegisterCommands();
            
            _sttService.WakeWordDetected += (s, e) =>
            {
                _context.LogInfo("Wake word detected - Ready for commands");
            };
            
            _sttService.TranscriptionReceived += (s, e) =>
            {
                _context.LogInfo($"Heard: {e.Text}");
            };
            
            _sttService.Start();
            
            TaskDialog.Show("Claude STT", "Voice recognition started.\nSay 'Claude' to activate.");
        }
        
        internal static void StopService()
        {
            if (_sttService == null || !_sttService.IsRunning)
            {
                TaskDialog.Show("Claude STT", "Voice recognition is not running");
                return;
            }
            
            _sttService.Stop();
            _sttService.Dispose();
            _sttService = null;
            _commandManager = null;
            
            TaskDialog.Show("Claude STT", "Voice recognition stopped");
        }
        
        private static void RegisterCommands()
        {
            _commandManager.RegisterCommand(new SelectWallCommand());
            _commandManager.RegisterCommand(new ZoomExtentsCommand());
            _commandManager.RegisterCommand(new CreateWallCommand());
            _commandManager.RegisterCommand(new DeleteSelectedCommand());
            _commandManager.RegisterCommand(new UndoCommand());
            
            _commandManager.RegisterCommand(new SimpleVoiceCommand(
                "select all",
                "Selects all elements in view",
                (text, ctx) =>
                {
                    var revitCtx = ctx as RevitCommandContext;
                    revitCtx?.ExecuteInRevitContext(app =>
                    {
                        var doc = app.ActiveUIDocument.Document;
                        var collector = new FilteredElementCollector(doc, app.ActiveUIDocument.ActiveView.Id)
                            .WhereElementIsNotElementType();
                        app.ActiveUIDocument.Selection.SetElementIds(collector.ToElementIds());
                    });
                },
                "select everything"
            ));
        }
        
        private static string GetPythonPath()
        {
            var pythonPath = Environment.GetEnvironmentVariable("CLAUDE_STT_PYTHON");
            if (!string.IsNullOrEmpty(pythonPath) && File.Exists(pythonPath))
                return pythonPath;
                
            return "python";
        }
        
        private static string GetScriptPath()
        {
            var assemblyDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            return Path.Combine(assemblyDir, "python", "ipc_server.py");
        }
    }
}