#!/usr/bin/env python3
"""
BridgeAI Samsung TV MCP Server
Control Samsung Smart TVs over local network
"""

import subprocess
import json
import socket
import sys
import os
import base64
import time

sys.path.insert(0, '/mnt/d/_MCP-SERVERS')

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("bridgeai-samsung-tv")

# Configuration - update these for your TV
TV_CONFIG = {
    "ip": None,  # Will be discovered or set manually
    "mac": None,  # For Wake-on-LAN
    "port": 8002,  # Samsung WebSocket port (8001 for older TVs)
    "name": "BridgeAI"  # Name shown on TV when connecting
}

def get_tv_ip():
    """Get TV IP from config or try to discover"""
    if TV_CONFIG["ip"]:
        return TV_CONFIG["ip"]
    # Try to load from saved config
    config_path = os.path.join(os.path.dirname(__file__), "tv_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            saved = json.load(f)
            return saved.get("ip")
    return None


def save_tv_config(ip: str, mac: str = None):
    """Save TV configuration"""
    config_path = os.path.join(os.path.dirname(__file__), "tv_config.json")
    config = {"ip": ip}
    if mac:
        config["mac"] = mac
    with open(config_path, "w") as f:
        json.dump(config, f)
    TV_CONFIG["ip"] = ip
    if mac:
        TV_CONFIG["mac"] = mac


@mcp.tool()
def discover_samsung_tvs() -> str:
    """
    Scan local network for Samsung TVs.
    Returns list of found TVs with their IP addresses.
    """
    try:
        # Use SSDP to discover Samsung TVs
        cmd = """
        $results = @()
        $ips = 1..254 | ForEach-Object { "192.168.1.$_" }

        # Quick scan for Samsung TV ports
        foreach ($ip in $ips) {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $connect = $tcp.BeginConnect($ip, 8001, $null, $null)
            $wait = $connect.AsyncWaitHandle.WaitOne(100, $false)
            if ($wait -and $tcp.Connected) {
                $results += @{ip=$ip; port=8001}
            }
            $tcp.Close()

            $tcp = New-Object System.Net.Sockets.TcpClient
            $connect = $tcp.BeginConnect($ip, 8002, $null, $null)
            $wait = $connect.AsyncWaitHandle.WaitOne(100, $false)
            if ($wait -and $tcp.Connected) {
                $results += @{ip=$ip; port=8002}
            }
            $tcp.Close()
        }
        $results | ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=120
        )

        output = result.stdout.strip()
        if output and '[' in output:
            return output
        elif output and '{' in output:
            return '[' + output + ']'
        else:
            return json.dumps({
                "found": [],
                "message": "No Samsung TVs found. Make sure TV is on and connected to same network.",
                "tip": "You can manually set the TV IP with set_tv_ip tool"
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_tv_ip(ip_address: str, mac_address: str = None) -> str:
    """
    Manually set your Samsung TV's IP address.
    Optionally set MAC address for Wake-on-LAN.

    Args:
        ip_address: TV's IP address (e.g., "192.168.1.100")
        mac_address: TV's MAC address for turning on (e.g., "AA:BB:CC:DD:EE:FF")
    """
    save_tv_config(ip_address, mac_address)
    return json.dumps({
        "success": True,
        "ip": ip_address,
        "mac": mac_address,
        "message": f"TV configured at {ip_address}"
    })


@mcp.tool()
def get_tv_info() -> str:
    """
    Get information about the configured Samsung TV.
    """
    ip = get_tv_ip()
    if not ip:
        return json.dumps({
            "error": "No TV configured",
            "tip": "Use set_tv_ip to configure your TV, or discover_samsung_tvs to find it"
        })

    try:
        # Try to get TV info via REST API
        import urllib.request
        url = f"http://{ip}:8001/api/v2/"
        req = urllib.request.Request(url, headers={'User-Agent': 'BridgeAI'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({
            "configured_ip": ip,
            "status": "Could not connect",
            "error": str(e),
            "tip": "Make sure TV is on and connected to network"
        })


@mcp.tool()
def wake_tv() -> str:
    """
    Turn on Samsung TV using Wake-on-LAN.
    Requires MAC address to be configured.
    """
    config_path = os.path.join(os.path.dirname(__file__), "tv_config.json")
    mac = None

    if os.path.exists(config_path):
        with open(config_path) as f:
            saved = json.load(f)
            mac = saved.get("mac")

    if not mac:
        return json.dumps({
            "error": "MAC address not configured",
            "tip": "Use set_tv_ip with mac_address parameter to enable Wake-on-LAN"
        })

    try:
        # Send Wake-on-LAN magic packet
        mac_bytes = bytes.fromhex(mac.replace(':', '').replace('-', ''))
        magic_packet = b'\xff' * 6 + mac_bytes * 16

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, ('255.255.255.255', 9))
        sock.close()

        return json.dumps({
            "success": True,
            "message": "Wake-on-LAN packet sent. TV should turn on in a few seconds."
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def send_tv_key(key: str) -> str:
    """
    Send a remote control key to the TV.

    Common keys:
    - Power: KEY_POWER, KEY_POWEROFF
    - Navigation: KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ENTER
    - Volume: KEY_VOLUP, KEY_VOLDOWN, KEY_MUTE
    - Channels: KEY_CHUP, KEY_CHDOWN
    - Playback: KEY_PLAY, KEY_PAUSE, KEY_STOP, KEY_REWIND, KEY_FF
    - Apps: KEY_HOME, KEY_SOURCE, KEY_MENU, KEY_RETURN, KEY_EXIT
    - Numbers: KEY_0 through KEY_9

    Args:
        key: The key to send (e.g., "KEY_POWER")
    """
    ip = get_tv_ip()
    if not ip:
        return json.dumps({"error": "No TV configured. Use set_tv_ip first."})

    try:
        import websocket

        # Encode app name for Samsung TV
        app_name = base64.b64encode("BridgeAI".encode()).decode()

        # Connect to TV WebSocket
        url = f"wss://{ip}:8002/api/v2/channels/samsung.remote.control?name={app_name}"

        ws = websocket.create_connection(url, sslopt={"cert_reqs": 0}, timeout=10)

        # Send key command
        cmd = {
            "method": "ms.remote.control",
            "params": {
                "Cmd": "Click",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey"
            }
        }

        ws.send(json.dumps(cmd))
        time.sleep(0.5)
        ws.close()

        return json.dumps({
            "success": True,
            "key_sent": key,
            "message": f"Sent {key} to TV"
        })

    except ImportError:
        # Fallback without websocket library - use PowerShell
        return send_key_powershell(ip, key)
    except Exception as e:
        return json.dumps({"error": str(e), "tip": "Make sure TV is on and connected"})


def send_key_powershell(ip: str, key: str) -> str:
    """Fallback method using PowerShell for WebSocket"""
    try:
        app_name = base64.b64encode("BridgeAI".encode()).decode()

        ps_cmd = f"""
        $url = "wss://{ip}:8002/api/v2/channels/samsung.remote.control?name={app_name}"

        # Ignore SSL errors for local network
        [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {{ $true }}

        $ws = New-Object System.Net.WebSockets.ClientWebSocket
        $ws.Options.RemoteCertificateValidationCallback = {{ $true }}

        $uri = [System.Uri]::new($url)
        $ct = [System.Threading.CancellationToken]::None

        $ws.ConnectAsync($uri, $ct).Wait()

        $cmd = @{{
            method = "ms.remote.control"
            params = @{{
                Cmd = "Click"
                DataOfCmd = "{key}"
                Option = "false"
                TypeOfRemote = "SendRemoteKey"
            }}
        }} | ConvertTo-Json -Compress

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($cmd)
        $segment = [System.ArraySegment[byte]]::new($bytes)
        $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()

        Start-Sleep -Milliseconds 500
        $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct).Wait()

        "success"
        """

        result = subprocess.run(
            ["powershell.exe", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15
        )

        if "success" in result.stdout:
            return json.dumps({"success": True, "key_sent": key})
        else:
            return json.dumps({"error": result.stderr or "Failed to send key"})

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def tv_power_off() -> str:
    """Turn off the Samsung TV."""
    return send_tv_key("KEY_POWER")


@mcp.tool()
def tv_volume_up() -> str:
    """Increase TV volume."""
    return send_tv_key("KEY_VOLUP")


@mcp.tool()
def tv_volume_down() -> str:
    """Decrease TV volume."""
    return send_tv_key("KEY_VOLDOWN")


@mcp.tool()
def tv_mute() -> str:
    """Mute/unmute TV."""
    return send_tv_key("KEY_MUTE")


@mcp.tool()
def tv_home() -> str:
    """Go to TV home screen."""
    return send_tv_key("KEY_HOME")


@mcp.tool()
def tv_source() -> str:
    """Open TV source/input selection."""
    return send_tv_key("KEY_SOURCE")


@mcp.tool()
def open_tv_app(app_name: str) -> str:
    """
    Open an app on the Samsung TV.

    Common apps: Netflix, YouTube, Prime Video, Disney+, Hulu, HBO Max

    Args:
        app_name: Name of the app to open
    """
    # App IDs for common apps (these vary by TV model/region)
    app_ids = {
        "netflix": "11101200001",
        "youtube": "111299001912",
        "prime": "3201512006785",
        "amazon": "3201512006785",
        "disney": "3201901017640",
        "disney+": "3201901017640",
        "hulu": "3201601007625",
        "hbo": "3201601007230",
        "spotify": "3201606009684",
    }

    ip = get_tv_ip()
    if not ip:
        return json.dumps({"error": "No TV configured"})

    app_id = app_ids.get(app_name.lower())
    if not app_id:
        return json.dumps({
            "error": f"Unknown app: {app_name}",
            "available": list(app_ids.keys())
        })

    try:
        import urllib.request

        url = f"http://{ip}:8001/api/v2/applications/{app_id}"
        req = urllib.request.Request(url, method='POST', headers={'User-Agent': 'BridgeAI'})

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.dumps({
                "success": True,
                "app": app_name,
                "message": f"Opening {app_name} on TV"
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
