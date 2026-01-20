# BridgeAI Smart Hub - All-in-One Installer
# Copy this file to your Dell PC and run it as Administrator

Write-Host ""
Write-Host "=============================================="
Write-Host "  BridgeAI Smart Hub - All-in-One Installer"
Write-Host "=============================================="
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create BridgeAI folder
$hubPath = "C:\BridgeAI"
Write-Host "[1/6] Creating BridgeAI folder..." -ForegroundColor Cyan
if (!(Test-Path $hubPath)) {
    New-Item -Path $hubPath -ItemType Directory | Out-Null
}
Write-Host "  Created $hubPath" -ForegroundColor Green

# Check/Install Python
Write-Host ""
Write-Host "[2/6] Checking Python..." -ForegroundColor Cyan
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  Python not found. Installing..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --silent --accept-package-agreements
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "  Python found!" -ForegroundColor Green
}

# Install Python packages
Write-Host ""
Write-Host "[3/6] Installing Python packages..." -ForegroundColor Cyan
pip install flask pywebostv websocket-client requests --quiet 2>$null
Write-Host "  Packages installed!" -ForegroundColor Green

# Create the hub server script
Write-Host ""
Write-Host "[4/6] Creating hub server..." -ForegroundColor Cyan

$hubScript = @'
#!/usr/bin/env python3
"""
BridgeAI Smart Hub Server
A web-based control panel for your smart home devices
Access from anywhere via Tailscale
"""

from flask import Flask, jsonify, request, render_template_string
import json
import os
import socket
import base64
import ssl

app = Flask(__name__)

# Device configurations
DEVICES = {
    "samsung_tv": {
        "name": "Samsung TV (Living Room)",
        "ip": "192.168.1.150",
        "mac": "68:72:c3:36:93:96",
        "type": "samsung"
    },
    "lg_tv": {
        "name": "LG TV",
        "ip": "192.168.1.46",
        "type": "lg",
        "config_path": os.path.join(os.path.dirname(__file__), "lg_config.json")
    }
}

# HTML Template for control panel
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BridgeAI Smart Hub</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .device-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .device-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        .device-name { font-size: 1.3em; margin-bottom: 15px; }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-bottom: 15px;
        }
        .status.online { background: #2ecc71; }
        .status.offline { background: #e74c3c; }
        .controls { display: flex; flex-wrap: wrap; gap: 10px; }
        .btn {
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.1s, opacity 0.1s;
        }
        .btn:hover { transform: scale(1.05); }
        .btn:active { transform: scale(0.95); opacity: 0.8; }
        .btn-power { background: #e74c3c; color: white; }
        .btn-power.on { background: #2ecc71; }
        .btn-vol { background: #3498db; color: white; }
        .btn-nav { background: #9b59b6; color: white; }
        .btn-app { background: #f39c12; color: white; }
        .info { margin-top: 15px; font-size: 0.9em; opacity: 0.7; }
        #log {
            max-width: 1200px;
            margin: 30px auto;
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 0.9em;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <h1>BridgeAI Smart Hub</h1>

    <div class="device-grid">
        <div class="device-card">
            <div class="device-name">Samsung TV</div>
            <span class="status" id="samsung-status">Checking...</span>
            <div class="controls">
                <button class="btn btn-power" onclick="sendCommand('samsung', 'power')">Power</button>
                <button class="btn btn-vol" onclick="sendCommand('samsung', 'vol_up')">Vol+</button>
                <button class="btn btn-vol" onclick="sendCommand('samsung', 'vol_down')">Vol-</button>
                <button class="btn btn-vol" onclick="sendCommand('samsung', 'mute')">Mute</button>
            </div>
            <div class="controls" style="margin-top:10px">
                <button class="btn btn-nav" onclick="sendCommand('samsung', 'home')">Home</button>
                <button class="btn btn-nav" onclick="sendCommand('samsung', 'back')">Back</button>
                <button class="btn btn-nav" onclick="sendCommand('samsung', 'enter')">OK</button>
            </div>
            <div class="info" id="samsung-info"></div>
        </div>

        <div class="device-card">
            <div class="device-name">LG TV</div>
            <span class="status" id="lg-status">Checking...</span>
            <div class="controls">
                <button class="btn btn-power" onclick="sendCommand('lg', 'power')">Power</button>
                <button class="btn btn-vol" onclick="sendCommand('lg', 'vol_up')">Vol+</button>
                <button class="btn btn-vol" onclick="sendCommand('lg', 'vol_down')">Vol-</button>
                <button class="btn btn-vol" onclick="sendCommand('lg', 'mute')">Mute</button>
            </div>
            <div class="controls" style="margin-top:10px">
                <button class="btn btn-nav" onclick="sendCommand('lg', 'home')">Home</button>
                <button class="btn btn-nav" onclick="sendCommand('lg', 'back')">Back</button>
                <button class="btn btn-nav" onclick="sendCommand('lg', 'enter')">OK</button>
            </div>
            <div class="controls" style="margin-top:10px">
                <button class="btn btn-app" onclick="sendCommand('lg', 'netflix')">Netflix</button>
                <button class="btn btn-app" onclick="sendCommand('lg', 'youtube')">YouTube</button>
            </div>
            <div class="info" id="lg-info"></div>
        </div>
    </div>

    <div id="log">Hub ready. Waiting for commands...</div>

    <script>
        function log(msg) {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML = '[' + time + '] ' + msg + '<br>' + logEl.innerHTML;
        }

        async function sendCommand(device, cmd) {
            log('Sending ' + cmd + ' to ' + device + '...');
            try {
                const resp = await fetch('/api/' + device + '/' + cmd, {method: 'POST'});
                const data = await resp.json();
                log(device + ': ' + (data.message || data.error || 'Done'));
            } catch(e) {
                log('Error: ' + e.message);
            }
        }

        async function checkStatus() {
            for (const device of ['samsung', 'lg']) {
                try {
                    const resp = await fetch('/api/' + device + '/status');
                    const data = await resp.json();
                    const statusEl = document.getElementById(device + '-status');
                    const infoEl = document.getElementById(device + '-info');

                    if (data.online) {
                        statusEl.textContent = 'Online';
                        statusEl.className = 'status online';
                        if (data.info) {
                            infoEl.textContent = data.info;
                        }
                    } else {
                        statusEl.textContent = 'Offline';
                        statusEl.className = 'status offline';
                    }
                } catch(e) {
                    document.getElementById(device + '-status').textContent = 'Error';
                }
            }
        }

        checkStatus();
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
"""

# ============ Samsung TV Functions ============

def samsung_send_key(key):
    """Send a key command to Samsung TV"""
    import websocket
    tv_ip = DEVICES["samsung_tv"]["ip"]
    name = base64.b64encode("BridgeAI".encode()).decode()
    url = f"wss://{tv_ip}:8002/api/v2/channels/samsung.remote.control?name={name}"

    try:
        ws = websocket.create_connection(url, timeout=5, sslopt={"cert_reqs": ssl.CERT_NONE})
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
        ws.close()
        return True
    except Exception as e:
        return False

def samsung_wake():
    """Wake Samsung TV via WOL"""
    mac = DEVICES["samsung_tv"]["mac"]
    mac_bytes = bytes.fromhex(mac.replace(':', '').replace('-', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, ('255.255.255.255', 9))
    sock.sendto(magic_packet, ('192.168.1.255', 9))
    sock.close()
    return True

def samsung_is_online():
    """Check if Samsung TV is online"""
    ip = DEVICES["samsung_tv"]["ip"]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((ip, 8001))
        sock.close()
        return True
    except:
        return False

# ============ LG TV Functions ============

def lg_get_client():
    """Get connected LG TV client"""
    from pywebostv.connection import WebOSClient

    config_path = DEVICES["lg_tv"]["config_path"]
    store = {}

    if os.path.exists(config_path):
        with open(config_path) as f:
            data = json.load(f)
            store = data.get("store", {})

    client = WebOSClient(DEVICES["lg_tv"]["ip"])
    client.connect()

    for status in client.register(store):
        if status == WebOSClient.REGISTERED:
            break

    return client

def lg_send_command(cmd):
    """Send command to LG TV"""
    try:
        from pywebostv.controls import MediaControl, SystemControl, ApplicationControl, InputControl

        client = lg_get_client()

        if cmd == "vol_up":
            MediaControl(client).volume_up()
        elif cmd == "vol_down":
            MediaControl(client).volume_down()
        elif cmd == "mute":
            MediaControl(client).mute(True)
        elif cmd == "power":
            SystemControl(client).power_off()
        elif cmd == "home":
            InputControl(client).home()
        elif cmd == "back":
            InputControl(client).back()
        elif cmd == "enter":
            InputControl(client).ok()
        elif cmd == "netflix":
            ApplicationControl(client).launch("netflix")
        elif cmd == "youtube":
            ApplicationControl(client).launch("youtube.leanback.v4")

        return True
    except Exception as e:
        print(f"LG error: {e}")
        return False

def lg_is_online():
    """Check if LG TV is online"""
    ip = DEVICES["lg_tv"]["ip"]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((ip, 3001))
        sock.close()
        return True
    except:
        return False

def lg_get_info():
    """Get current LG TV info"""
    try:
        from pywebostv.controls import ApplicationControl, MediaControl
        client = lg_get_client()
        app = ApplicationControl(client).get_current()
        vol = MediaControl(client).get_volume()
        return f"App: {app}, Vol: {vol.get('volume', '?')}"
    except:
        return None

# ============ API Routes ============

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/samsung/status')
def samsung_status():
    online = samsung_is_online()
    return jsonify({"online": online, "device": "samsung"})

@app.route('/api/samsung/<cmd>', methods=['POST'])
def samsung_command(cmd):
    key_map = {
        "power": "KEY_POWER",
        "vol_up": "KEY_VOLUP",
        "vol_down": "KEY_VOLDOWN",
        "mute": "KEY_MUTE",
        "home": "KEY_HOME",
        "back": "KEY_RETURN",
        "enter": "KEY_ENTER",
        "up": "KEY_UP",
        "down": "KEY_DOWN",
        "left": "KEY_LEFT",
        "right": "KEY_RIGHT"
    }

    if cmd == "wake":
        samsung_wake()
        return jsonify({"message": "Wake-on-LAN sent"})

    if cmd == "power" and not samsung_is_online():
        samsung_wake()
        return jsonify({"message": "Sending Wake-on-LAN to turn on"})

    key = key_map.get(cmd)
    if key:
        success = samsung_send_key(key)
        return jsonify({"message": f"Sent {cmd}", "success": success})

    return jsonify({"error": f"Unknown command: {cmd}"}), 400

@app.route('/api/lg/status')
def lg_status():
    online = lg_is_online()
    info = lg_get_info() if online else None
    return jsonify({"online": online, "device": "lg", "info": info})

@app.route('/api/lg/<cmd>', methods=['POST'])
def lg_command(cmd):
    valid_commands = ["power", "vol_up", "vol_down", "mute", "home", "back", "enter", "netflix", "youtube"]

    if cmd in valid_commands:
        success = lg_send_command(cmd)
        return jsonify({"message": f"Sent {cmd}", "success": success})

    return jsonify({"error": f"Unknown command: {cmd}"}), 400

@app.route('/api/health')
def health():
    return jsonify({
        "status": "running",
        "hub": "BridgeAI",
        "devices": list(DEVICES.keys())
    })

if __name__ == '__main__':
    print()
    print("=" * 50)
    print("  BridgeAI Smart Hub")
    print("=" * 50)
    print()
    print("  Local:     http://localhost:5000")

    # Try to get Tailscale IP
    try:
        import subprocess
        ts_ip = subprocess.check_output(["tailscale", "ip", "-4"], text=True).strip()
        print(f"  Tailscale: http://{ts_ip}:5000")
    except:
        pass

    print()
    print("  Devices:")
    for dev_id, dev in DEVICES.items():
        print(f"    - {dev['name']} ({dev['ip']})")
    print()
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
'@

$hubScript | Out-File -FilePath "$hubPath\hub_server.py" -Encoding utf8
Write-Host "  Hub server created!" -ForegroundColor Green

# Create empty LG config file
$lgConfig = @'
{
    "store": {}
}
'@
$lgConfig | Out-File -FilePath "$hubPath\lg_config.json" -Encoding utf8

# Configure firewall
Write-Host ""
Write-Host "[5/6] Configuring firewall..." -ForegroundColor Cyan
New-NetFirewallRule -DisplayName "BridgeAI Hub" -Direction Inbound -Port 5000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null
Write-Host "  Firewall configured!" -ForegroundColor Green

# Create auto-start task
Write-Host ""
Write-Host "[6/6] Creating auto-start task..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "$hubPath\hub_server.py" -WorkingDirectory $hubPath
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName "BridgeAI Hub" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "BridgeAI Hub" -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Write-Host "  Auto-start enabled!" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "=============================================="
Write-Host "  Installation Complete!"
Write-Host "=============================================="
Write-Host ""
Write-Host "Your BridgeAI Hub is installed at: $hubPath"
Write-Host ""
Write-Host "To start the hub now, run:"
Write-Host "  python C:\BridgeAI\hub_server.py" -ForegroundColor Green
Write-Host ""
Write-Host "Or just restart this computer - it will start automatically!"
Write-Host ""

# Ask to start now
$start = Read-Host "Start BridgeAI Hub now? (Y/N)"
if ($start -eq "Y" -or $start -eq "y") {
    Write-Host ""
    Write-Host "Starting BridgeAI Hub..." -ForegroundColor Cyan
    Start-Process python -ArgumentList "$hubPath\hub_server.py" -WorkingDirectory $hubPath
    Write-Host ""
    Write-Host "Hub is running! Open a browser and go to:"
    Write-Host "  http://localhost:5000" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Next step: Install Tailscale from https://tailscale.com/download"
Write-Host "This will let you access your hub from anywhere!"
Write-Host ""
Read-Host "Press Enter to exit"
