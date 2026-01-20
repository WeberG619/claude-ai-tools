using System;

namespace ClaudeSTT.Core
{
    public interface IVoiceCommand
    {
        string CommandText { get; }
        string Description { get; }
        string[] Aliases { get; }
        bool CanExecute(string transcription);
        void Execute(string transcription, ICommandContext context);
    }

    public interface ICommandContext
    {
        object ActiveDocument { get; }
        object Application { get; }
        void ShowMessage(string message);
        void LogInfo(string message);
        void LogError(string message);
    }

    public interface ISTTService
    {
        event EventHandler<TranscriptionEventArgs> TranscriptionReceived;
        event EventHandler<WakeWordEventArgs> WakeWordDetected;
        event EventHandler RecordingStarted;
        event EventHandler RecordingStopped;
        
        void Start();
        void Stop();
        bool IsRunning { get; }
        void SendCommand(string command);
    }

    public class TranscriptionEventArgs : EventArgs
    {
        public string Text { get; set; }
        public DateTime Timestamp { get; set; }
        public double Confidence { get; set; }
    }

    public class WakeWordEventArgs : EventArgs
    {
        public string WakeWord { get; set; }
        public DateTime Timestamp { get; set; }
    }
}