# Revit Recorder MCP

Records Revit sessions using FFmpeg (no OBS needed), logs MCP calls, and generates narration with Andrew voice (Edge TTS).

## Features

- **FFmpeg Recording**: Records screen in background - no GUI app required
- **Auto-Detect Revit**: Automatically finds which monitor Revit is on and records that monitor
- **MCP Call Logging**: Tracks every Revit MCP call with timestamps during recording
- **Markers**: Add bookmarks (highlight, cut, narrate, important, error) for editing
- **Andrew Voice**: Generates narration scripts and audio using Edge TTS

## Prerequisites

1. **FFmpeg** (already installed at `C:\Program Files\ffmpeg-...\bin\ffmpeg.exe`)
2. **Python 3.10+**
3. **Dependencies**: `pip install edge-tts mcp`

## No Setup Required

Unlike OBS-based recording, this runs entirely in the background using FFmpeg.
Just start a recording and it captures the Revit monitor automatically.

## Available Tools

| Tool | Description |
|------|-------------|
| `recorder_connect` | Connect to OBS WebSocket |
| `recorder_start` | Start recording (auto-detects Revit project) |
| `recorder_stop` | Stop recording |
| `recorder_status` | Check recording status and system state |
| `recorder_log_mcp` | Log an MCP call with timestamp |
| `recorder_add_marker` | Add a marker (highlight, cut, narrate, important, error) |
| `recorder_list_sessions` | List recent recording sessions |
| `recorder_get_session` | Get session details |
| `recorder_get_mcp_calls` | Get all MCP calls in a session |
| `recorder_get_markers` | Get all markers in a session |
| `recorder_generate_narration_script` | Generate narration script for Andrew voice |

## Usage Workflow

### 1. Start Recording
```
recorder_connect()  # Connect to OBS
recorder_start(project_name="My Revit Project")  # Begin recording
```

### 2. During Work
The server automatically detects Revit activity. As you work, you can:
- Log MCP calls with `recorder_log_mcp`
- Add markers with `recorder_add_marker` for key moments

### 3. Stop & Generate
```
recorder_stop()  # End recording
recorder_generate_narration_script(session_id=1)  # Create narration
```

### 4. Generate Audio
```bash
python narrator.py generate --script recordings/narration_session_1.txt --voice andrew
```

## Narration Voices

- **andrew** (default): Warm, professional male voice
- **guy**: Friendly male voice
- **jenny**: Clear female voice
- **aria**: Engaging female voice

## File Structure

```
revit-recorder-mcp/
├── server.py           # MCP server
├── narrator.py         # Edge TTS narration generator
├── sessions.db         # SQLite database for sessions/calls/markers
├── recordings/         # Video files (via OBS)
│   └── audio/          # Generated narration audio
└── requirements.txt
```

## Session Database Schema

- **sessions**: Recording sessions with start/end times, file paths
- **mcp_calls**: MCP method calls with timestamps and parameters
- **markers**: Bookmarks for editing (highlights, cuts, narration points)
