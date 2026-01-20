# Claude STT - Real-time Speech-to-Text for Revit

A voice command system for Autodesk Revit with "Claude" wake word activation, real-time speech recognition, and natural language command processing.

## Features

- **Wake Word Activation**: Say "Claude" or "Hey Claude" to activate
- **Real-time Transcription**: Powered by Faster Whisper for accurate speech recognition
- **Voice Activity Detection**: Smart detection of speech start/stop
- **Natural Language Commands**: Execute Revit commands using natural speech
- **GPU Acceleration**: Optional CUDA support for faster processing
- **Windows Optimized**: Built specifically for Windows environments

## Architecture

The system consists of two main components:

1. **Python STT Engine** (`/python`): Handles audio capture, VAD, wake word detection, and transcription
2. **C# Revit Plugin** (`/csharp`): Integrates with Revit API and processes voice commands

Communication between components uses Windows Named Pipes for low-latency IPC.

## Installation

### Prerequisites

- Windows 10/11
- Python 3.8+ 
- .NET Framework 4.8
- Autodesk Revit 2024+
- Visual Studio 2019+ (for building C# components)
- CUDA Toolkit (optional, for GPU acceleration)

### Python Setup

1. Install Python dependencies:
```bash
cd ClaudeSTT/python
pip install -r requirements.txt
```

2. Download Whisper model (happens automatically on first run):
```bash
python example.py
```

### Revit Plugin Setup

1. Build the C# solution:
```bash
cd ClaudeSTT/csharp
msbuild ClaudeSTT.sln /p:Configuration=Release
```

2. Copy plugin files to Revit:
```
Copy ClaudeSTT.Revit.dll to: %APPDATA%\Autodesk\Revit\Addins\2024\
Copy ClaudeSTT.Core.dll to: %APPDATA%\Autodesk\Revit\Addins\2024\
Copy ClaudeSTT.addin to: %APPDATA%\Autodesk\Revit\Addins\2024\
```

3. Copy Python files:
```
Copy entire python folder to: %APPDATA%\Autodesk\Revit\Addins\2024\ClaudeSTT\python\
```

## Usage

### In Revit

1. Start Revit - you'll see a new "Claude Voice" tab
2. Click "Start Listening" to begin voice recognition
3. Say "Claude" to activate voice commands
4. Speak your command clearly
5. Click "Stop Listening" when done

### Available Commands

- **"Select wall"** - Selects all walls in current view
- **"Select all"** - Selects all elements in view
- **"Create wall"** - Starts wall creation (pick points)
- **"Delete selected"** - Deletes selected elements
- **"Zoom extents"** - Fits view to all elements
- **"Undo"** - Undoes last action

### Standalone Testing

Test the Python STT engine standalone:
```bash
cd ClaudeSTT/python
python example.py
```

## Configuration

### Environment Variables

- `CLAUDE_STT_PYTHON`: Path to Python executable (if not in PATH)
- `PORCUPINE_ACCESS_KEY`: API key for Porcupine wake word detection (optional)

### Model Selection

Edit `model_size` in code:
- `"tiny"` - Fastest, least accurate
- `"base"` - Good balance (default)
- `"small"` - Better accuracy
- `"medium"` - Best accuracy, slower

### GPU Acceleration

To enable GPU:
1. Install CUDA Toolkit
2. Install GPU version: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
3. Change `device="cuda"` in code

## Extending

### Adding New Voice Commands

1. Create a new command class:
```csharp
public class MyCommand : BaseVoiceCommand
{
    public MyCommand()
    {
        CommandText = "my command";
        Description = "Does something";
        Aliases = new[] { "alternate phrase" };
    }
    
    public override void Execute(string transcription, ICommandContext context)
    {
        // Your command logic here
    }
}
```

2. Register in `ClaudeSTTApplication.RegisterCommands()`:
```csharp
_commandManager.RegisterCommand(new MyCommand());
```

## Troubleshooting

### "No microphone found"
- Check Windows sound settings
- Ensure microphone permissions are granted

### "Wake word not detected"
- Speak clearly and directly
- Try "Hey Claude" for better detection
- Check microphone volume levels

### "Commands not executing"
- Ensure Revit has an active document open
- Check command is spoken after wake word activation
- Review Revit journal file for errors

### Performance Issues
- Use smaller Whisper model
- Enable GPU acceleration if available
- Adjust VAD sensitivity settings

## License

MIT License - See LICENSE file for details