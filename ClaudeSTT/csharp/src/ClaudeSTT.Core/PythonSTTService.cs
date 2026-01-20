using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace ClaudeSTT.Core
{
    public class PythonSTTService : ISTTService, IDisposable
    {
        private Process _pythonProcess;
        private NamedPipeServerStream _pipeServer;
        private CancellationTokenSource _cancellationTokenSource;
        private Task _messageTask;
        private bool _isRunning;
        
        public event EventHandler<TranscriptionEventArgs> TranscriptionReceived;
        public event EventHandler<WakeWordEventArgs> WakeWordDetected;
        public event EventHandler RecordingStarted;
        public event EventHandler RecordingStopped;
        
        public bool IsRunning => _isRunning;
        
        private readonly string _pythonPath;
        private readonly string _scriptPath;
        private readonly string _pipeName;
        
        public PythonSTTService(string pythonPath = "python", string scriptPath = null)
        {
            _pythonPath = pythonPath;
            _scriptPath = scriptPath ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "python", "ipc_server.py");
            _pipeName = $"ClaudeSTT_{Guid.NewGuid():N}";
        }
        
        public void Start()
        {
            if (_isRunning) return;
            
            _cancellationTokenSource = new CancellationTokenSource();
            
            _pipeServer = new NamedPipeServerStream(_pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Message);
            
            StartPythonProcess();
            
            _messageTask = Task.Run(async () => await ProcessMessages(_cancellationTokenSource.Token));
            
            _isRunning = true;
        }
        
        public void Stop()
        {
            if (!_isRunning) return;
            
            _cancellationTokenSource?.Cancel();
            
            SendCommand("STOP");
            
            _pythonProcess?.WaitForExit(5000);
            _pythonProcess?.Kill();
            _pythonProcess?.Dispose();
            
            _pipeServer?.Dispose();
            
            _messageTask?.Wait(5000);
            
            _isRunning = false;
        }
        
        public void SendCommand(string command)
        {
            if (!_isRunning || !_pipeServer.IsConnected) return;
            
            try
            {
                var message = new { type = "command", data = command };
                var json = JsonConvert.SerializeObject(message);
                var bytes = Encoding.UTF8.GetBytes(json);
                
                _pipeServer.Write(bytes, 0, bytes.Length);
                _pipeServer.Flush();
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error sending command: {ex.Message}");
            }
        }
        
        private void StartPythonProcess()
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = _pythonPath,
                Arguments = $"\"{_scriptPath}\" --pipe-name {_pipeName}",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            
            _pythonProcess = new Process { StartInfo = startInfo };
            _pythonProcess.OutputDataReceived += (s, e) => Debug.WriteLine($"Python: {e.Data}");
            _pythonProcess.ErrorDataReceived += (s, e) => Debug.WriteLine($"Python Error: {e.Data}");
            
            _pythonProcess.Start();
            _pythonProcess.BeginOutputReadLine();
            _pythonProcess.BeginErrorReadLine();
            
            _pipeServer.WaitForConnection();
        }
        
        private async Task ProcessMessages(CancellationToken cancellationToken)
        {
            var buffer = new byte[4096];
            
            while (!cancellationToken.IsCancellationRequested && _pipeServer.IsConnected)
            {
                try
                {
                    var bytesRead = await _pipeServer.ReadAsync(buffer, 0, buffer.Length, cancellationToken);
                    if (bytesRead > 0)
                    {
                        var json = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        ProcessMessage(json);
                    }
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"Error reading from pipe: {ex.Message}");
                    await Task.Delay(100, cancellationToken);
                }
            }
        }
        
        private void ProcessMessage(string json)
        {
            try
            {
                dynamic message = JsonConvert.DeserializeObject(json);
                string type = message.type;
                
                switch (type)
                {
                    case "transcription":
                        TranscriptionReceived?.Invoke(this, new TranscriptionEventArgs
                        {
                            Text = message.data.text,
                            Timestamp = DateTime.Now,
                            Confidence = message.data.confidence ?? 1.0
                        });
                        break;
                        
                    case "wake_word":
                        WakeWordDetected?.Invoke(this, new WakeWordEventArgs
                        {
                            WakeWord = message.data.wake_word,
                            Timestamp = DateTime.Now
                        });
                        break;
                        
                    case "recording_started":
                        RecordingStarted?.Invoke(this, EventArgs.Empty);
                        break;
                        
                    case "recording_stopped":
                        RecordingStopped?.Invoke(this, EventArgs.Empty);
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error processing message: {ex.Message}");
            }
        }
        
        public void Dispose()
        {
            Stop();
        }
    }
}