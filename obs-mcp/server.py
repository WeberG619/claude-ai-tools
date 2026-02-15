#!/usr/bin/env python3
"""
OBS MCP Server - Control OBS Studio via WebSocket
================================================
Allows Claude to start/stop recordings, switch scenes, and more.
"""

import json
import sys
import os
from datetime import datetime
from typing import Optional

# MCP protocol handling
def send_response(id: Optional[int], result: dict):
    response = {"jsonrpc": "2.0", "id": id, "result": result}
    print(json.dumps(response), flush=True)

def send_error(id: Optional[int], code: int, message: str):
    response = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    print(json.dumps(response), flush=True)

def send_notification(method: str, params: dict):
    notification = {"jsonrpc": "2.0", "method": method, "params": params}
    print(json.dumps(notification), flush=True)

# OBS Connection - auto-detect WSL2 host IP
def _detect_obs_host():
    """Get the Windows host IP from WSL2, fallback to localhost."""
    default = "localhost"
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    return line.split()[1]
    except Exception:
        pass
    return default

OBS_HOST = os.environ.get("OBS_HOST", _detect_obs_host())
OBS_PORT = int(os.environ.get("OBS_PORT", "4455"))
OBS_PASSWORD = os.environ.get("OBS_PASSWORD", "2GwO1bvUqSIy3V2X")

obs_client = None

def get_obs():
    """Get or create OBS WebSocket connection."""
    global obs_client
    if obs_client is None:
        try:
            import obsws_python as obs
            obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
        except Exception as e:
            raise ConnectionError(f"Cannot connect to OBS: {e}. Make sure OBS is running and WebSocket is enabled (Tools → WebSocket Server Settings)")
    return obs_client

def close_obs():
    """Close OBS connection."""
    global obs_client
    if obs_client:
        try:
            obs_client.disconnect()
        except:
            pass
        obs_client = None

# Tool implementations
def obs_status():
    """Get OBS status including recording/streaming state."""
    try:
        client = get_obs()

        # Get various status info
        record_status = client.get_record_status()
        stream_status = client.get_stream_status()
        scene = client.get_current_program_scene()

        return {
            "connected": True,
            "recording": record_status.output_active,
            "recording_paused": record_status.output_paused,
            "recording_time": record_status.output_timecode if record_status.output_active else None,
            "recording_bytes": record_status.output_bytes if record_status.output_active else None,
            "streaming": stream_status.output_active,
            "stream_time": stream_status.output_timecode if stream_status.output_active else None,
            "current_scene": scene.current_program_scene_name
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

def obs_start_recording():
    """Start OBS recording."""
    try:
        client = get_obs()
        client.start_record()
        return {"success": True, "message": "Recording started"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_stop_recording():
    """Stop OBS recording and return the file path."""
    try:
        client = get_obs()
        result = client.stop_record()
        return {
            "success": True,
            "message": "Recording stopped",
            "output_path": result.output_path if hasattr(result, 'output_path') else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_pause_recording():
    """Pause OBS recording."""
    try:
        client = get_obs()
        client.pause_record()
        return {"success": True, "message": "Recording paused"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_resume_recording():
    """Resume OBS recording."""
    try:
        client = get_obs()
        client.resume_record()
        return {"success": True, "message": "Recording resumed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_start_streaming():
    """Start OBS streaming."""
    try:
        client = get_obs()
        client.start_stream()
        return {"success": True, "message": "Streaming started"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_stop_streaming():
    """Stop OBS streaming."""
    try:
        client = get_obs()
        client.stop_stream()
        return {"success": True, "message": "Streaming stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_get_scenes():
    """Get list of available scenes."""
    try:
        client = get_obs()
        scenes = client.get_scene_list()
        return {
            "current_scene": scenes.current_program_scene_name,
            "scenes": [s["sceneName"] for s in scenes.scenes]
        }
    except Exception as e:
        return {"error": str(e)}

def obs_switch_scene(scene_name: str):
    """Switch to a specific scene."""
    try:
        client = get_obs()
        client.set_current_program_scene(scene_name)
        return {"success": True, "message": f"Switched to scene: {scene_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_screenshot(source: Optional[str] = None, file_path: Optional[str] = None):
    """Take a screenshot of the current output or specific source."""
    try:
        client = get_obs()

        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"D:/Users/Weber/Videos/obs_screenshot_{timestamp}.png"

        # Convert to Windows path if needed
        win_path = file_path.replace("/mnt/d/", "D:/").replace("/mnt/c/", "C:/")

        if source:
            client.save_source_screenshot(source, "png", win_path, 1920, 1080, 100)
        else:
            # Screenshot the current program output
            scene = client.get_current_program_scene()
            client.save_source_screenshot(scene.current_program_scene_name, "png", win_path, 1920, 1080, 100)

        return {"success": True, "file_path": win_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_get_audio_sources():
    """Get list of audio sources and their volumes."""
    try:
        client = get_obs()
        inputs = client.get_input_list()

        audio_sources = []
        for inp in inputs.inputs:
            try:
                vol = client.get_input_volume(inp["inputName"])
                mute = client.get_input_mute(inp["inputName"])
                audio_sources.append({
                    "name": inp["inputName"],
                    "kind": inp["inputKind"],
                    "volume_db": vol.input_volume_db,
                    "volume_mul": vol.input_volume_mul,
                    "muted": mute.input_muted
                })
            except:
                pass  # Not an audio source

        return {"audio_sources": audio_sources}
    except Exception as e:
        return {"error": str(e)}

def obs_set_volume(source_name: str, volume_db: float):
    """Set volume for an audio source in dB."""
    try:
        client = get_obs()
        client.set_input_volume(source_name, vol_db=volume_db)
        return {"success": True, "message": f"Set {source_name} volume to {volume_db} dB"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_toggle_mute(source_name: str):
    """Toggle mute for an audio source."""
    try:
        client = get_obs()
        client.toggle_input_mute(source_name)
        mute = client.get_input_mute(source_name)
        return {"success": True, "muted": mute.input_muted}
    except Exception as e:
        return {"success": False, "error": str(e)}

def obs_get_recording_folder():
    """Get the current recording output folder."""
    try:
        client = get_obs()
        settings = client.get_record_directory()
        return {"recording_folder": settings.record_directory}
    except Exception as e:
        return {"error": str(e)}

def obs_set_recording_folder(folder_path: str):
    """Set the recording output folder."""
    try:
        client = get_obs()
        # Convert WSL path to Windows path
        win_path = folder_path.replace("/mnt/d/", "D:\\").replace("/mnt/c/", "C:\\").replace("/", "\\")
        client.set_record_directory(win_path)
        return {"success": True, "recording_folder": win_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

# MCP Tool definitions
TOOLS = [
    {
        "name": "obs_status",
        "description": "Get OBS status including recording state, streaming state, and current scene",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_start_recording",
        "description": "Start OBS recording",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_stop_recording",
        "description": "Stop OBS recording. Returns the path to the recorded file.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_pause_recording",
        "description": "Pause the current OBS recording",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_resume_recording",
        "description": "Resume a paused OBS recording",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_start_streaming",
        "description": "Start OBS streaming to configured service",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_stop_streaming",
        "description": "Stop OBS streaming",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_get_scenes",
        "description": "Get list of available OBS scenes",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_switch_scene",
        "description": "Switch to a specific OBS scene",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene_name": {
                    "type": "string",
                    "description": "Name of the scene to switch to"
                }
            },
            "required": ["scene_name"]
        }
    },
    {
        "name": "obs_screenshot",
        "description": "Take a screenshot of the current OBS output",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Optional: specific source to screenshot"
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional: path to save screenshot (defaults to Videos folder)"
                }
            },
            "required": []
        }
    },
    {
        "name": "obs_get_audio_sources",
        "description": "Get list of audio sources and their current volumes",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_set_volume",
        "description": "Set volume for an audio source",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_name": {
                    "type": "string",
                    "description": "Name of the audio source"
                },
                "volume_db": {
                    "type": "number",
                    "description": "Volume in dB (0 = full, -inf = silent)"
                }
            },
            "required": ["source_name", "volume_db"]
        }
    },
    {
        "name": "obs_toggle_mute",
        "description": "Toggle mute for an audio source",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_name": {
                    "type": "string",
                    "description": "Name of the audio source to mute/unmute"
                }
            },
            "required": ["source_name"]
        }
    },
    {
        "name": "obs_get_recording_folder",
        "description": "Get the current recording output folder",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "obs_set_recording_folder",
        "description": "Set the recording output folder",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Path to the folder for recordings"
                }
            },
            "required": ["folder_path"]
        }
    }
]

# Tool dispatcher
TOOL_HANDLERS = {
    "obs_status": lambda args: obs_status(),
    "obs_start_recording": lambda args: obs_start_recording(),
    "obs_stop_recording": lambda args: obs_stop_recording(),
    "obs_pause_recording": lambda args: obs_pause_recording(),
    "obs_resume_recording": lambda args: obs_resume_recording(),
    "obs_start_streaming": lambda args: obs_start_streaming(),
    "obs_stop_streaming": lambda args: obs_stop_streaming(),
    "obs_get_scenes": lambda args: obs_get_scenes(),
    "obs_switch_scene": lambda args: obs_switch_scene(args["scene_name"]),
    "obs_screenshot": lambda args: obs_screenshot(args.get("source"), args.get("file_path")),
    "obs_get_audio_sources": lambda args: obs_get_audio_sources(),
    "obs_set_volume": lambda args: obs_set_volume(args["source_name"], args["volume_db"]),
    "obs_toggle_mute": lambda args: obs_toggle_mute(args["source_name"]),
    "obs_get_recording_folder": lambda args: obs_get_recording_folder(),
    "obs_set_recording_folder": lambda args: obs_set_recording_folder(args["folder_path"]),
}

def handle_request(request: dict):
    """Handle incoming MCP request."""
    method = request.get("method")
    id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        send_response(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "obs-mcp",
                "version": "1.0.0"
            }
        })

    elif method == "notifications/initialized":
        pass  # No response needed

    elif method == "tools/list":
        send_response(id, {"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name in TOOL_HANDLERS:
            try:
                result = TOOL_HANDLERS[tool_name](arguments)
                send_response(id, {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                })
            except Exception as e:
                send_response(id, {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                    "isError": True
                })
        else:
            send_error(id, -32601, f"Unknown tool: {tool_name}")

    else:
        if id is not None:
            send_error(id, -32601, f"Unknown method: {method}")

def main():
    """Main MCP server loop."""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            handle_request(request)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

    close_obs()

if __name__ == "__main__":
    main()
