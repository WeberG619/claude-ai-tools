const { app, BrowserWindow, BrowserView, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;
let browserView;

// Status file path
const STATUS_FILE = path.join(__dirname, '..', 'agent_status.json');
const OUTPUT_DIR = path.join(__dirname, '..', 'output');

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        backgroundColor: '#1a1a2e',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        title: 'Creative Studio'
    });

    // Create BrowserView for previewing presentations
    browserView = new BrowserView({
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.loadFile('index.html');

    // Start watching status file
    watchStatusFile();
}

function watchStatusFile() {
    setInterval(() => {
        try {
            if (fs.existsSync(STATUS_FILE)) {
                const data = fs.readFileSync(STATUS_FILE, 'utf8');
                const status = JSON.parse(data);

                if (mainWindow && mainWindow.webContents) {
                    mainWindow.webContents.send('agent-status', status);
                }

                handleActivityData(status);
            }
        } catch (err) {
            // Ignore parse errors
        }
    }, 300);
}

function handleActivityData(status) {
    const activity = status.activity;
    if (!activity) return;

    // Send activity type to renderer for view switching
    if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send('activity-update', activity);
    }
}

// IPC handlers
ipcMain.on('preview-presentation', (event, htmlPath) => {
    if (browserView && fs.existsSync(htmlPath)) {
        mainWindow.setBrowserView(browserView);
        browserView.setBounds({
            x: 350,
            y: 150,
            width: mainWindow.getBounds().width - 370,
            height: mainWindow.getBounds().height - 170
        });
        browserView.webContents.loadFile(htmlPath);
    }
});

ipcMain.on('close-preview', (event) => {
    mainWindow.setBrowserView(null);
});

ipcMain.on('open-output-folder', (event) => {
    if (fs.existsSync(OUTPUT_DIR)) {
        shell.openPath(OUTPUT_DIR);
    }
});

ipcMain.on('open-in-browser', (event, filePath) => {
    if (fs.existsSync(filePath)) {
        shell.openExternal(`file://${filePath}`);
    }
});

// Watch for new presentations
ipcMain.on('get-presentations', (event) => {
    try {
        if (fs.existsSync(OUTPUT_DIR)) {
            const files = fs.readdirSync(OUTPUT_DIR)
                .filter(f => f.endsWith('.html'))
                .map(f => ({
                    name: f,
                    path: path.join(OUTPUT_DIR, f),
                    created: fs.statSync(path.join(OUTPUT_DIR, f)).mtime
                }))
                .sort((a, b) => b.created - a.created);
            event.reply('presentations-list', files);
        }
    } catch (err) {
        console.error('Error listing presentations:', err);
    }
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
