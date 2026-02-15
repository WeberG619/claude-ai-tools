const { app, BrowserWindow, BrowserView, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');

// Server endpoints
const WS_URL = 'ws://127.0.0.1:8890/ws';  // Use IPv4 explicitly (localhost resolves to IPv6 on WSL)
const STATUS_FILE = 'D:\\_CLAUDE-TOOLS\\agent-team\\agent_status.json';

let mainWindow;
let browserView;
let lastActivityTime = 0;
let connectionStatus = 'disconnected';
let ws = null;
let reconnectTimer = null;

function createWindow() {
    // Create the main window (full screen on primary monitor)
    mainWindow = new BrowserWindow({
        width: 2560,
        height: 1440,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        frame: true,
        title: 'Agent Team v2.1 - Live Dashboard'
    });

    // Load the dashboard HTML
    mainWindow.loadFile('dashboard.html');

    // DevTools for debugging
    mainWindow.webContents.openDevTools({ mode: 'detach' });

    // Create the embedded browser view for the "Live View" area
    browserView = new BrowserView({
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.setBrowserView(browserView);

    // Position the browser view (adjust based on your layout)
    // Left panel: 280px, Right panel: 320px, Header: ~120px
    const bounds = mainWindow.getBounds();
    browserView.setBounds({
        x: 280,
        y: 170,  // Below header and mode indicator
        width: bounds.width - 280 - 320,
        height: bounds.height - 170 - 40
    });

    browserView.setAutoResize({ width: true, height: true });

    // Load a default page
    browserView.webContents.loadURL('https://github.com');

    // Start monitoring for activity changes
    startActivityMonitor();

    // Handle window resize
    mainWindow.on('resize', () => {
        const bounds = mainWindow.getBounds();
        browserView.setBounds({
            x: 280,
            y: 170,
            width: bounds.width - 280 - 320,
            height: bounds.height - 170 - 40
        });
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function connectWebSocket() {
    console.log('Connecting to WebSocket:', WS_URL);

    try {
        ws = new WebSocket(WS_URL);

        ws.on('open', () => {
            console.log('✓ WebSocket connected');
            connectionStatus = 'connected';
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('connection-status', 'connected');
            }
            // Clear any reconnect timer
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        });

        ws.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                handleWebSocketMessage(msg);
            } catch (e) {
                console.error('Error parsing WebSocket message:', e.message);
            }
        });

        ws.on('close', () => {
            console.log('WebSocket disconnected, will reconnect...');
            connectionStatus = 'disconnected';
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('connection-status', 'disconnected');
            }
            // Reconnect after 2 seconds
            reconnectTimer = setTimeout(connectWebSocket, 2000);
        });

        ws.on('error', (err) => {
            console.error('WebSocket error:', err.message);
            // Will trigger close event and reconnect
        });

    } catch (e) {
        console.error('Failed to create WebSocket:', e.message);
        // Retry connection
        reconnectTimer = setTimeout(connectWebSocket, 2000);
    }
}

function handleWebSocketMessage(msg) {
    console.log('WebSocket message:', msg.type);

    switch (msg.type) {
        case 'init':
            // Initial state from server
            if (msg.data.status) {
                handleActivityData(msg.data.status);
            }
            break;

        case 'agent_status':
            handleActivityData(msg.data);
            break;

        case 'activity':
            handleActivityData({ activity: msg.data });
            break;

        case 'session_state':
            // Forward session state to renderer
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('session-state', msg.data);
            }
            break;

        case 'reasoning':
            // Forward reasoning updates to renderer
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('reasoning-update', msg.data);
            }
            break;

        case 'parallel_start':
            // Forward parallel build notification
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('parallel-start', msg.data);
            }
            break;

        case 'execution_result':
            // Forward execution result to renderer
            console.log('>>> EXECUTION RESULT <<<');
            console.log('Action:', msg.data.action_type);
            console.log('Success:', msg.data.success);
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('execution-result', msg.data);
            }
            break;

        case 'execution_mode':
            // Forward execution mode change to renderer
            console.log('>>> EXECUTION MODE CHANGE <<<');
            console.log('Enabled:', msg.data.enabled);
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('execution-mode', msg.data);
            }
            break;

        case 'approval_request':
            // Forward approval request to renderer
            console.log('>>> APPROVAL REQUEST <<<');
            console.log('Action:', msg.data.action_type);
            console.log('Content:', msg.data.content?.substring(0, 50));
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('approval-request', msg.data);
            }
            break;

        case 'approval_response':
            // Forward approval response to renderer
            if (mainWindow && mainWindow.webContents) {
                mainWindow.webContents.send('approval-response', msg.data);
            }
            break;
    }
}

function handleActivityData(data) {
    const activity = data.activity;
    const activityTime = data.activity_timestamp || data.timestamp || Date.now() / 1000;

    // Process even if timestamp hasn't changed (WebSocket means it's new)
    console.log('=== ACTIVITY RECEIVED ===');
    console.log('Agent:', data.agent);
    console.log('Type:', activity?.type || 'speaking');

    // CRITICAL: Control BrowserView visibility DIRECTLY based on activity type
    // This ensures terminal/code views are visible (BrowserView covers HTML content)

    if (activity && activity.type === 'browser_navigate' && activity.url) {
        // BROWSER MODE: Show BrowserView
        console.log('>>> BROWSER MODE: Showing BrowserView <<<');
        console.log('URL:', activity.url);
        mainWindow.setBrowserView(browserView);
        browserView.webContents.loadURL(activity.url);
    }
    else if (activity && activity.type === 'code_write') {
        // CODE MODE: Hide BrowserView so HTML overlay is visible
        console.log('>>> CODE MODE: Hiding BrowserView <<<');
        console.log('File:', activity.file_path);
        mainWindow.setBrowserView(null);  // MUST hide BrowserView first!
        if (mainWindow && mainWindow.webContents) {
            mainWindow.webContents.send('code-display', activity);
        }
    }
    else if (activity && activity.type === 'terminal_run') {
        // TERMINAL MODE: Hide BrowserView so HTML overlay is visible
        console.log('>>> TERMINAL MODE: Hiding BrowserView <<<');
        console.log('Command:', activity.command);
        mainWindow.setBrowserView(null);  // MUST hide BrowserView first!
        if (mainWindow && mainWindow.webContents) {
            mainWindow.webContents.send('terminal-display', activity);
        }
    }
    else if (activity && activity.type === 'file_open' && activity.file_path) {
        // FILE MODE: Show file viewer
        console.log('>>> FILE MODE <<<');
        showFileInView(activity.file_path);
    }

    // Send ALL updates to dashboard renderer (for agent status, etc.)
    if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send('activity-update', data);
    }

    lastActivityTime = activityTime;
}

function startActivityMonitor() {
    console.log('Starting activity monitor with WebSocket + file fallback');

    // Primary: WebSocket connection
    connectWebSocket();

    // ALWAYS poll file as backup (not just when disconnected)
    // This ensures reliability even if WebSocket has issues
    let lastFileHash = '';

    setInterval(() => {
        try {
            if (fs.existsSync(STATUS_FILE)) {
                const content = fs.readFileSync(STATUS_FILE, 'utf8');

                // Use content hash to detect changes (more reliable than timestamp)
                const hash = require('crypto').createHash('md5').update(content).digest('hex');

                if (hash !== lastFileHash) {
                    lastFileHash = hash;
                    const data = JSON.parse(content);
                    console.log('File changed, activity:', data.activity?.type);
                    handleActivityData(data);
                }
            }
        } catch (e) {
            // Ignore file read errors
        }
    }, 300); // Check every 300ms for responsiveness
}

// Navigate browser view via IPC
ipcMain.on('navigate', (event, url) => {
    if (browserView && url) {
        browserView.webContents.loadURL(url);
    }
});

// Show/hide browser view based on activity type
ipcMain.on('set-view-mode', (event, mode) => {
    console.log('=== SET VIEW MODE:', mode, '===');
    if (mode === 'browser') {
        console.log('Showing BrowserView');
        mainWindow.setBrowserView(browserView);
    } else {
        console.log('HIDING BrowserView for mode:', mode);
        mainWindow.setBrowserView(null);
    }
});

// Handle file opening from file browser
ipcMain.on('open-file', (event, filePath) => {
    console.log('Opening file from browser:', filePath);
    showFileInView(filePath);
});

// Handle approval response from renderer
ipcMain.on('approve-action', async (event, data) => {
    console.log('Sending approval:', data.action_id, data.approved);
    try {
        const http = require('http');
        const postData = JSON.stringify({
            action_id: data.action_id,
            approved: data.approved
        });

        const options = {
            hostname: '127.0.0.1',  // IPv4 explicit
            port: 8890,
            path: '/api/approve',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            console.log('Approval response status:', res.statusCode);
        });

        req.on('error', (e) => {
            console.error('Approval request error:', e.message);
        });

        req.write(postData);
        req.end();
    } catch (e) {
        console.error('Failed to send approval:', e);
    }
});

// Handle execution mode toggle from renderer
ipcMain.on('set-execution-mode', async (event, enabled) => {
    console.log('Setting execution mode:', enabled);
    try {
        const http = require('http');
        const postData = JSON.stringify({ enabled });

        const options = {
            hostname: '127.0.0.1',  // IPv4 explicit
            port: 8890,
            path: '/api/execution-mode',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            console.log('Execution mode response status:', res.statusCode);
        });

        req.on('error', (e) => {
            console.error('Execution mode request error:', e.message);
        });

        req.write(postData);
        req.end();
    } catch (e) {
        console.error('Failed to set execution mode:', e);
    }
});

// File viewer window
let fileViewerWindow = null;

function showFileInView(filePath) {
    // Create or reuse file viewer BrowserView
    if (!fileViewerWindow) {
        fileViewerWindow = new BrowserView({
            webPreferences: {
                nodeIntegration: true,
                contextIsolation: false
            }
        });
    }

    // Load the file viewer with the file path
    const viewerPath = path.join(__dirname, 'viewers', 'file-viewer.html');
    fileViewerWindow.webContents.loadFile(viewerPath, {
        query: { file: filePath }
    });

    // Position it in the main content area
    mainWindow.setBrowserView(fileViewerWindow);
    const bounds = mainWindow.getBounds();
    fileViewerWindow.setBounds({
        x: 280,
        y: 170,
        width: bounds.width - 280 - 320,
        height: bounds.height - 170 - 40
    });
    fileViewerWindow.setAutoResize({ width: true, height: true });

    console.log('Opening file:', filePath);
}

// Cleanup function to stop all agent processes when app closes
function cleanupProcesses() {
    console.log('=== CLEANUP: Stopping all agent processes ===');
    const { execSync } = require('child_process');

    try {
        // Kill agent team processes
        execSync('pkill -9 -f "run_team" 2>/dev/null || true', { stdio: 'ignore' });
        execSync('pkill -9 -f "autonomous" 2>/dev/null || true', { stdio: 'ignore' });

        // Kill voice/TTS processes
        execSync('pkill -9 -f "speak.py" 2>/dev/null || true', { stdio: 'ignore' });
        execSync('pkill -9 -f "edge-tts" 2>/dev/null || true', { stdio: 'ignore' });
        execSync('pkill -9 -f "mpv" 2>/dev/null || true', { stdio: 'ignore' });
        execSync('pkill -9 -f "voice-mcp" 2>/dev/null || true', { stdio: 'ignore' });

        // Kill monitor server
        execSync('pkill -9 -f "monitor/server.py" 2>/dev/null || true', { stdio: 'ignore' });

        console.log('=== CLEANUP: All processes stopped ===');
    } catch (e) {
        console.log('Cleanup error (non-fatal):', e.message);
    }
}

app.whenReady().then(createWindow);

app.on('before-quit', () => {
    console.log('App quitting - running cleanup...');
    cleanupProcesses();
});

app.on('window-all-closed', () => {
    cleanupProcesses();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
