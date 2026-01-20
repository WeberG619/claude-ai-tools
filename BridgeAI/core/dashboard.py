#!/usr/bin/env python3
"""
BridgeAI Command Center Dashboard
==================================
A beautiful web interface to control everything.
"""

from flask import Flask, jsonify, request, render_template_string
import json
import os
import socket
import psutil
import threading
import time
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Configuration
SERVICES = {
    'hub': {'name': 'Smart Hub', 'port': 5000, 'url': 'http://localhost:5000'},
    'brain': {'name': 'AI Brain', 'port': 5001, 'url': 'http://localhost:5001'},
    'ollama': {'name': 'Local AI', 'port': 11434, 'url': 'http://localhost:11434'},
}

DEVICES = {
    'samsung_tv': {'name': 'Samsung TV', 'ip': '192.168.1.150', 'port': 8001},
    'lg_tv': {'name': 'LG TV', 'ip': '192.168.1.46', 'port': 3001},
    'main_pc': {'name': 'Main PC', 'ip': '192.168.1.51', 'port': 445},
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BridgeAI Command Center</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg-dark: #0a0a1a;
            --bg-card: #12122a;
            --bg-hover: #1a1a3a;
            --accent: #00d4ff;
            --accent-dim: #0088aa;
            --success: #00ff88;
            --warning: #ffaa00;
            --danger: #ff4444;
            --text: #ffffff;
            --text-dim: #888899;
        }

        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, var(--bg-card) 0%, #1a1a4a 100%);
            border-radius: 16px;
            border: 1px solid var(--accent-dim);
        }

        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, var(--accent), #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: var(--text-dim);
            font-size: 1.1em;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }

        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #2a2a4a;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 212, 255, 0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #2a2a4a;
        }

        .card-title {
            font-size: 1.3em;
            font-weight: 600;
        }

        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .status-online { background: var(--success); color: #000; }
        .status-offline { background: var(--danger); color: #fff; }
        .status-warning { background: var(--warning); color: #000; }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat {
            background: var(--bg-hover);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }

        .stat-value {
            font-size: 1.8em;
            font-weight: 700;
            color: var(--accent);
        }

        .stat-label {
            font-size: 0.85em;
            color: var(--text-dim);
            margin-top: 5px;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .device-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            background: var(--bg-hover);
            border-radius: 10px;
        }

        .device-name {
            font-weight: 500;
        }

        .device-ip {
            color: var(--text-dim);
            font-size: 0.9em;
        }

        .btn-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 15px;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn:hover { transform: scale(1.05); }
        .btn:active { transform: scale(0.95); }

        .btn-primary { background: var(--accent); color: #000; }
        .btn-success { background: var(--success); color: #000; }
        .btn-danger { background: var(--danger); color: #fff; }
        .btn-secondary { background: #3a3a5a; color: #fff; }

        .console {
            background: #000;
            border-radius: 10px;
            padding: 15px;
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 15px;
        }

        .console-line {
            padding: 3px 0;
            border-bottom: 1px solid #1a1a1a;
        }

        .console-time { color: var(--text-dim); }
        .console-msg { color: var(--accent); }
        .console-error { color: var(--danger); }

        .input-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .input-group input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            background: var(--bg-hover);
            color: var(--text);
            font-size: 1em;
        }

        .input-group input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .progress-bar {
            height: 8px;
            background: #2a2a4a;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--success));
            transition: width 0.3s;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading { animation: pulse 1.5s infinite; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 BridgeAI Command Center</h1>
        <p class="subtitle">Your Personal AI System • Dell PC Hub</p>
    </div>

    <div class="grid">
        <!-- System Status -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📊 System Status</span>
                <span class="status-badge status-online" id="system-status">Online</span>
            </div>
            <div class="stat-grid">
                <div class="stat">
                    <div class="stat-value" id="cpu-usage">--</div>
                    <div class="stat-label">CPU Usage</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="memory-usage">--</div>
                    <div class="stat-label">Memory</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="disk-free">--</div>
                    <div class="stat-label">Disk Free</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="uptime">--</div>
                    <div class="stat-label">Uptime</div>
                </div>
            </div>
        </div>

        <!-- Services -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">⚡ Services</span>
            </div>
            <div class="device-list" id="services-list">
                <div class="device-item loading">Loading services...</div>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" onclick="restartAll()">Restart All</button>
                <button class="btn btn-secondary" onclick="refreshServices()">Refresh</button>
            </div>
        </div>

        <!-- Network Devices -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📡 Network Devices</span>
            </div>
            <div class="device-list" id="devices-list">
                <div class="device-item loading">Scanning network...</div>
            </div>
        </div>

        <!-- TV Control -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📺 TV Control</span>
            </div>
            <div class="btn-group">
                <button class="btn btn-success" onclick="tvCommand('samsung', 'power')">Samsung Power</button>
                <button class="btn btn-success" onclick="tvCommand('lg', 'power')">LG Power</button>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="tvCommand('samsung', 'vol_up')">Vol +</button>
                <button class="btn btn-secondary" onclick="tvCommand('samsung', 'vol_down')">Vol -</button>
                <button class="btn btn-secondary" onclick="tvCommand('samsung', 'mute')">Mute</button>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="tvCommand('lg', 'netflix')">Netflix</button>
                <button class="btn btn-secondary" onclick="tvCommand('lg', 'youtube')">YouTube</button>
            </div>
        </div>

        <!-- AI Brain -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">🧠 AI Brain</span>
                <span class="status-badge" id="brain-status">Checking...</span>
            </div>
            <div class="input-group">
                <input type="text" id="brain-input" placeholder="Ask the AI anything..." onkeypress="if(event.key==='Enter')askBrain()">
                <button class="btn btn-primary" onclick="askBrain()">Ask</button>
            </div>
            <div class="console" id="brain-console">
                <div class="console-line">
                    <span class="console-time">[Ready]</span>
                    <span class="console-msg">AI Brain ready for commands...</span>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">⚡ Quick Actions</span>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" onclick="runAction('cleanup')">🧹 Cleanup</button>
                <button class="btn btn-primary" onclick="runAction('backup')">💾 Backup</button>
                <button class="btn btn-primary" onclick="runAction('optimize')">🚀 Optimize</button>
                <button class="btn btn-danger" onclick="runAction('restart')">🔄 Restart Hub</button>
            </div>
        </div>

        <!-- Activity Log -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📜 Activity Log</span>
            </div>
            <div class="console" id="activity-log">
                <div class="console-line">
                    <span class="console-time">[System]</span>
                    <span class="console-msg">Dashboard loaded</span>
                </div>
            </div>
        </div>

        <!-- Memory Stats -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">💭 Brain Memory</span>
            </div>
            <div class="stat-grid">
                <div class="stat">
                    <div class="stat-value" id="memory-count">--</div>
                    <div class="stat-label">Memories</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="pattern-count">--</div>
                    <div class="stat-label">Patterns</div>
                </div>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="viewMemories()">View Memories</button>
                <button class="btn btn-secondary" onclick="clearOldMemories()">Clean Old</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';

        function log(msg, type = 'msg') {
            const logEl = document.getElementById('activity-log');
            const time = new Date().toLocaleTimeString();
            const className = type === 'error' ? 'console-error' : 'console-msg';
            logEl.innerHTML = `<div class="console-line"><span class="console-time">[${time}]</span> <span class="${className}">${msg}</span></div>` + logEl.innerHTML;
        }

        async function fetchJSON(url, options = {}) {
            try {
                const resp = await fetch(url, options);
                return await resp.json();
            } catch (e) {
                return { error: e.message };
            }
        }

        async function refreshSystem() {
            const data = await fetchJSON('/api/system');
            if (!data.error) {
                document.getElementById('cpu-usage').textContent = data.cpu + '%';
                document.getElementById('memory-usage').textContent = data.memory + '%';
                document.getElementById('disk-free').textContent = data.disk_free + ' GB';
                document.getElementById('uptime').textContent = data.uptime;
            }
        }

        async function refreshServices() {
            const data = await fetchJSON('/api/services');
            const list = document.getElementById('services-list');

            if (data.error) {
                list.innerHTML = '<div class="device-item">Error loading services</div>';
                return;
            }

            list.innerHTML = Object.entries(data).map(([key, svc]) => `
                <div class="device-item">
                    <div>
                        <div class="device-name">${svc.name}</div>
                        <div class="device-ip">Port ${svc.port}</div>
                    </div>
                    <span class="status-badge ${svc.online ? 'status-online' : 'status-offline'}">
                        ${svc.online ? 'Online' : 'Offline'}
                    </span>
                </div>
            `).join('');
        }

        async function refreshDevices() {
            const data = await fetchJSON('/api/devices');
            const list = document.getElementById('devices-list');

            if (data.error) {
                list.innerHTML = '<div class="device-item">Error scanning network</div>';
                return;
            }

            list.innerHTML = Object.entries(data).map(([key, dev]) => `
                <div class="device-item">
                    <div>
                        <div class="device-name">${dev.name}</div>
                        <div class="device-ip">${dev.ip}</div>
                    </div>
                    <span class="status-badge ${dev.online ? 'status-online' : 'status-offline'}">
                        ${dev.online ? 'Online' : 'Offline'}
                    </span>
                </div>
            `).join('');
        }

        async function tvCommand(device, cmd) {
            log(`Sending ${cmd} to ${device}...`);
            const data = await fetchJSON(`/api/tv/${device}/${cmd}`, { method: 'POST' });
            if (data.error) {
                log(`Error: ${data.error}`, 'error');
            } else {
                log(`${device}: ${data.message || 'Done'}`);
            }
        }

        async function askBrain() {
            const input = document.getElementById('brain-input');
            const text = input.value.trim();
            if (!text) return;

            const consoleEl = document.getElementById('brain-console');
            const time = new Date().toLocaleTimeString();

            consoleEl.innerHTML = `<div class="console-line"><span class="console-time">[${time}]</span> <span class="console-msg">You: ${text}</span></div>` + consoleEl.innerHTML;

            input.value = '';

            const data = await fetchJSON('/api/brain/think', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const responseTime = new Date().toLocaleTimeString();
            if (data.error) {
                consoleEl.innerHTML = `<div class="console-line"><span class="console-time">[${responseTime}]</span> <span class="console-error">Error: ${data.error}</span></div>` + consoleEl.innerHTML;
            } else {
                consoleEl.innerHTML = `<div class="console-line"><span class="console-time">[${responseTime}]</span> <span class="console-msg">AI: ${data.response || 'Done'}</span></div>` + consoleEl.innerHTML;
            }
        }

        async function runAction(action) {
            log(`Running ${action}...`);
            const data = await fetchJSON(`/api/action/${action}`, { method: 'POST' });
            if (data.error) {
                log(`Error: ${data.error}`, 'error');
            } else {
                log(`${action}: ${data.message || 'Complete'}`);
            }
        }

        async function checkBrainStatus() {
            const data = await fetchJSON('/api/brain/status');
            const badge = document.getElementById('brain-status');

            if (data.error || !data.running) {
                badge.textContent = 'Offline';
                badge.className = 'status-badge status-offline';
            } else {
                badge.textContent = 'Online';
                badge.className = 'status-badge status-online';

                document.getElementById('memory-count').textContent = data.memory_count || '--';
            }
        }

        function restartAll() {
            if (confirm('Restart all BridgeAI services?')) {
                runAction('restart_all');
            }
        }

        function viewMemories() {
            window.open('/memories', '_blank');
        }

        function clearOldMemories() {
            if (confirm('Clear old low-importance memories?')) {
                runAction('clear_old_memories');
            }
        }

        // Initial load
        refreshSystem();
        refreshServices();
        refreshDevices();
        checkBrainStatus();

        // Auto-refresh
        setInterval(refreshSystem, 10000);
        setInterval(refreshServices, 30000);
        setInterval(refreshDevices, 60000);
        setInterval(checkBrainStatus, 30000);
    </script>
</body>
</html>
"""

def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/system')
def system_status():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:/')
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        return jsonify({
            'cpu': round(cpu, 1),
            'memory': round(memory, 1),
            'disk_free': round(disk.free / (1024**3), 1),
            'disk_total': round(disk.total / (1024**3), 1),
            'uptime': f"{hours}h {minutes}m"
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/services')
def services_status():
    result = {}
    for key, svc in SERVICES.items():
        result[key] = {
            'name': svc['name'],
            'port': svc['port'],
            'online': check_port('localhost', svc['port'])
        }
    return jsonify(result)

@app.route('/api/devices')
def devices_status():
    result = {}
    for key, dev in DEVICES.items():
        result[key] = {
            'name': dev['name'],
            'ip': dev['ip'],
            'online': check_port(dev['ip'], dev['port'])
        }
    return jsonify(result)

@app.route('/api/tv/<device>/<command>', methods=['POST'])
def tv_control(device, command):
    try:
        import urllib.request
        url = f"http://localhost:5000/api/{device}/{command}"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return jsonify(json.loads(resp.read().decode()))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/brain/status')
def brain_status():
    try:
        import urllib.request
        with urllib.request.urlopen('http://localhost:5001/status', timeout=5) as resp:
            data = json.loads(resp.read().decode())
            data['running'] = True
            return jsonify(data)
    except:
        return jsonify({'running': False})

@app.route('/api/brain/think', methods=['POST'])
def brain_think():
    try:
        import urllib.request
        data = request.get_json() or {}
        req_data = json.dumps(data).encode()
        req = urllib.request.Request(
            'http://localhost:5001/think',
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return jsonify(json.loads(resp.read().decode()))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/action/<action>', methods=['POST'])
def run_action(action):
    try:
        if action == 'cleanup':
            # Run cleanup
            import shutil
            temp = Path('C:/Windows/Temp')
            count = 0
            for f in temp.glob('*'):
                try:
                    if f.is_file():
                        f.unlink()
                        count += 1
                except:
                    pass
            return jsonify({'message': f'Cleaned {count} temp files'})

        elif action == 'backup':
            # Backup brain memory
            import shutil
            src = Path('C:/BridgeAI/data/brain_memory.db')
            if src.exists():
                dst = Path(f'C:/BridgeAI/Backups/brain_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
                dst.parent.mkdir(exist_ok=True)
                shutil.copy2(src, dst)
                return jsonify({'message': f'Backed up to {dst.name}'})
            return jsonify({'message': 'No database to backup'})

        elif action == 'optimize':
            # Optimize memory
            import sqlite3
            db = Path('C:/BridgeAI/data/brain_memory.db')
            if db.exists():
                with sqlite3.connect(db) as conn:
                    conn.execute('VACUUM')
                return jsonify({'message': 'Memory optimized'})
            return jsonify({'message': 'No database found'})

        elif action == 'restart_all':
            # This would restart services
            return jsonify({'message': 'Restart initiated (manual restart required)'})

        else:
            return jsonify({'error': f'Unknown action: {action}'})

    except Exception as e:
        return jsonify({'error': str(e)})

def main():
    print()
    print("=" * 50)
    print("  BridgeAI Command Center Dashboard")
    print("=" * 50)
    print()
    print("  Dashboard: http://localhost:5002")
    print()
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=5002, debug=False)

if __name__ == '__main__':
    main()
