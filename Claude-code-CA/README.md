# AI-Enhanced Automation Assistant

A complete AI-powered system that understands natural language commands and executes them intelligently. It learns from experience, adapts to failures, and improves over time.

## 🚀 Quick Start

1. **Setup** (one-time):
   ```powershell
   .\setup_ai_assistant.ps1
   ```

2. **Run**:
   ```powershell
   .\Start-AIAssistant.ps1
   ```

3. **Your Copilot Issue**:
   ```powershell
   .\Start-AIAssistant.ps1 "Close the Copilot dialog in PowerPoint"
   ```

## 🎯 Features

### Natural Language Understanding
- Just tell it what you want in plain English
- No need to know technical commands
- Examples:
  - "Close that annoying dialog in PowerPoint"
  - "Take a screenshot and save it"
  - "Create a new presentation about AI"
  - "Open Excel and make a budget spreadsheet"

### Intelligent Automation
- **Computer Vision**: Sees what's on your screen and finds UI elements
- **Multiple Click Methods**: Tries different approaches until one works
- **Error Recovery**: Learns from failures and tries alternative solutions
- **Memory System**: Remembers what worked before and improves

### Learning Capabilities
- Stores every interaction in a database
- Learns successful patterns
- Improves success rate over time
- Suggests better approaches based on past experience

## 📝 Usage Examples

### Interactive Mode
Just run without arguments for a conversation:
```powershell
.\Start-AIAssistant.ps1
```

Then type commands like:
- "Close the Copilot dialog"
- "Take a screenshot"
- "Open notepad and type Hello World"
- "Find all Python files in this folder"

### Direct Command
Execute a single task:
```powershell
.\Start-AIAssistant.ps1 "Your command here"
```

### API Mode
Get JSON output for integration:
```powershell
.\Start-AIAssistant.ps1 --api "Take a screenshot"
```

### Disable Learning
For testing without saving experiences:
```powershell
.\Start-AIAssistant.ps1 --no-learn
```

## 🔧 Architecture

### Core Components

1. **AI Orchestrator** (`ai_orchestrator.py`)
   - Natural language understanding
   - Task planning and execution
   - Intent recognition

2. **Screen Analyzer** (`screen_analyzer.py`)
   - Computer vision for UI detection
   - OCR for text extraction
   - Element finding and verification

3. **PowerShell Executor** (`powershell_executor.py`)
   - Safe UI automation
   - Application control
   - System integration

4. **AI Memory** (`ai_memory.py`)
   - Experience storage
   - Pattern learning
   - Performance analysis

5. **Safe UI Automation** (`safe_ui_automation.ps1`)
   - Non-blocking click methods
   - Window detection
   - Keyboard safety

## 📊 Special Commands

While in interactive mode:
- `status` - Show system status and performance
- `analyze` - Display detailed performance analysis
- `learn` - Toggle learning mode on/off
- `exit` - Quit the assistant

## 🛠️ Troubleshooting

### PowerPoint Copilot Dialog Won't Close?

The AI Assistant will:
1. Try clicking the X button at known coordinates
2. Send ESC key combinations
3. Try alternative closing methods
4. Learn what works for next time

Just run:
```powershell
.\Start-AIAssistant.ps1 "Close the Copilot dialog in PowerPoint"
```

### OCR Not Working?

Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki

The system works without it but with limited text recognition.

### Python Dependencies Issues?

Make sure virtual environment is activated:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 🧠 How It Works

1. **You speak naturally**: "Close that dialog"
2. **AI understands intent**: Recognizes UI automation task
3. **Plans actions**: Capture screen → Find dialog → Click close → Verify
4. **Executes with fallbacks**: Tries multiple methods if needed
5. **Learns from result**: Stores experience for future use
6. **Improves over time**: Uses successful patterns

## 📈 Performance Tracking

The system tracks:
- Success rates over time
- Common errors and solutions
- Most effective patterns
- Performance metrics

View with the `analyze` command in interactive mode.

## 🔐 Safety Features

- **No keyboard blocking**: Your keyboard always works
- **Safe clicking**: Multiple verification methods
- **Error boundaries**: Graceful failure handling
- **Undo support**: Tracks all actions taken

## 🎨 Customization

### Add New Capabilities

1. Create a new executor module
2. Register it in `ai_assistant.py`
3. Add intent patterns in `ai_orchestrator.py`

### Train for Specific Tasks

The system automatically learns from use, but you can:
- Provide consistent phrasing for better recognition
- Use successful commands repeatedly to reinforce patterns
- Give feedback when tasks complete

## 📚 Advanced Usage

### Batch Operations
Create a script with multiple commands:
```powershell
$commands = @(
    "Open PowerPoint",
    "Create new presentation",
    "Add slide about AI benefits",
    "Save as AI_Presentation.pptx"
)

foreach ($cmd in $commands) {
    .\Start-AIAssistant.ps1 $cmd
    Start-Sleep -Seconds 2
}
```

### Integration with Other Tools
The API mode enables integration:
```python
import subprocess
import json

result = subprocess.run(
    ['powershell', './Start-AIAssistant.ps1', '--api', 'Take screenshot'],
    capture_output=True,
    text=True
)
data = json.loads(result.stdout)
```

## 🤝 Contributing

The system is designed to be extensible. Add new:
- Intent patterns
- Executors
- UI templates
- Recovery strategies

## 📄 License

This AI Assistant is provided as-is for automation purposes.

---

**Remember**: The more you use it, the smarter it gets! 🚀