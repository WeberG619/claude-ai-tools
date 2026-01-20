using System;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ClaudeSTT.Core;

namespace ClaudeSTT.Revit
{
    public class RevitCommandContext : ICommandContext
    {
        private readonly UIApplication _uiApp;
        private readonly ExternalEvent _externalEvent;
        private readonly RevitEventHandler _eventHandler;
        
        public object ActiveDocument => _uiApp?.ActiveUIDocument?.Document;
        public object Application => _uiApp;
        
        public RevitCommandContext(UIApplication uiApp)
        {
            _uiApp = uiApp;
            _eventHandler = new RevitEventHandler();
            _externalEvent = ExternalEvent.Create(_eventHandler);
        }
        
        public void ShowMessage(string message)
        {
            _eventHandler.EnqueueAction(() =>
            {
                TaskDialog.Show("Claude Voice Command", message);
            });
            _externalEvent.Raise();
        }
        
        public void LogInfo(string message)
        {
            Console.WriteLine($"[INFO] {DateTime.Now:HH:mm:ss} - {message}");
        }
        
        public void LogError(string message)
        {
            Console.WriteLine($"[ERROR] {DateTime.Now:HH:mm:ss} - {message}");
        }
        
        public void ExecuteInRevitContext(Action<UIApplication> action)
        {
            _eventHandler.EnqueueAction(() => action(_uiApp));
            _externalEvent.Raise();
        }
    }
    
    public class RevitEventHandler : IExternalEventHandler
    {
        private readonly Queue<Action> _actionQueue = new Queue<Action>();
        private readonly object _lock = new object();
        
        public void EnqueueAction(Action action)
        {
            lock (_lock)
            {
                _actionQueue.Enqueue(action);
            }
        }
        
        public void Execute(UIApplication app)
        {
            Action action = null;
            lock (_lock)
            {
                if (_actionQueue.Count > 0)
                    action = _actionQueue.Dequeue();
            }
            
            action?.Invoke();
        }
        
        public string GetName()
        {
            return "Claude Voice Command Handler";
        }
    }
}