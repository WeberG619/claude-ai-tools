# 🎯 HOW DROP ZONES WORK - Simple Guide

## 🔄 The Basic Concept:

```
You Drop File → Zone Watches → Processes File → Creates Output
     ↓              ↓               ↓                ↓
  request.txt    Every 3 sec    Runs handler    Generated code
```

## 📁 Step-by-Step Instructions:

### 1️⃣ Start the Monitor
- **Find on Desktop**: "Revit Drop Zones.bat"
- **Double-click it**
- A black command window opens showing:
  ```
  REVIT DROP ZONE MONITOR - Development Assistant
  Active Drop Zones:
  📁 revit_code_generator: Generate Revit add-in code
  📁 revit_error_debugger: Debug and fix Revit API errors
  ...
  Watching every 3 seconds...
  ```
- **KEEP THIS WINDOW OPEN!** (minimize it)

### 2️⃣ Create a Test File
- Open Notepad
- Type this:
  ```
  Create a Revit tool that counts all doors and shows the total
  ```
- Save as: `test.txt`

### 3️⃣ Drop the File
- Open Windows Explorer
- Navigate to: `D:\claude-code-revit\revit_zones\code_generator\`
- **DRAG AND DROP** your `test.txt` file into this folder

### 4️⃣ Watch the Magic (within 3 seconds)
- The monitor window will show:
  ```
  📄 Processing: test.txt in revit_code_generator
  🔧 Running generate_revit_code...
  ✅ Processed successfully!
  📁 Output in: processed/
  ```

### 5️⃣ Find Your Generated Code
- Look in: `D:\claude-code-revit\revit_zones\code_generator\processed\`
- You'll find:
  - `GeneratedAddin_[timestamp].cs` - Your generated code!
  - `test_[timestamp].txt` - Your original file (moved here)

---

## 🗂️ Where Everything Is:

```
D:\claude-code-revit\
├── 📁 revit_zones\
│   ├── 📂 code_generator\        ← DROP REQUEST FILES HERE
│   │   └── 📁 processed\         ← FIND GENERATED CODE HERE
│   ├── 📂 error_debugger\        ← DROP ERROR FILES HERE
│   │   └── 📁 processed\         ← FIND FIXED CODE HERE
│   └── 📂 api_explorer\
│       └── 📁 processed\
├── 📁 dev_zones\
│   ├── 📂 test_generator\        ← DROP .CS FILES HERE
│   │   └── 📁 processed\         ← FIND TEST CODE HERE
│   └── 📂 doc_builder\           ← DROP CODE HERE
│       └── 📁 processed\         ← FIND DOCS HERE
└── 🔧 start_dropzone_monitor.bat
```

---

## 💡 Visual Guide:

### For Code Generation:
```
1. Write what you want in text file
2. Drop in: code_generator folder
3. Get: Complete C# code in processed folder
```

### For Error Fixing:
```
1. Copy error + code to text file
2. Drop in: error_debugger folder  
3. Get: Fixed code in processed folder
```

### For Tests:
```
1. Drop your .cs file
2. Drop in: test_generator folder
3. Get: Unit tests in processed folder
```

---

## ❓ Common Issues:

**"I don't see any output"**
- Check the `processed` subfolder, not the main folder
- Make sure monitor window is still running
- Wait 3-5 seconds after dropping file

**"Where do I drop files?"**
- NOT in the base folder
- Drop in the specific zone folder (code_generator, error_debugger, etc.)

**"File disappeared but no output"**
- Check if it moved to `processed` folder
- Look for error messages in monitor window

---

## 🎬 Quick Test Right Now:

1. **Open Notepad**
2. **Type**: `Create a tool to renumber all doors`
3. **Save as**: `door_tool.txt`
4. **Drop in**: `D:\claude-code-revit\revit_zones\code_generator\`
5. **Check**: `D:\claude-code-revit\revit_zones\code_generator\processed\`

The file will be processed and code will be generated!