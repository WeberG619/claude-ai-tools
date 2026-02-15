const { app, BrowserWindow, BrowserView, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;
let browserView;

// Status file path
const STATUS_FILE = path.join(__dirname, '..', 'agent_status.json');

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        backgroundColor: '#F5F7FA',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        title: 'Office Command Center'
    });

    // Create BrowserView for web content (emails, calendar, etc.)
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
    // Poll status file every 300ms
    setInterval(() => {
        try {
            if (fs.existsSync(STATUS_FILE)) {
                const data = fs.readFileSync(STATUS_FILE, 'utf8');
                const status = JSON.parse(data);

                // Send to renderer
                if (mainWindow && mainWindow.webContents) {
                    mainWindow.webContents.send('agent-status', status);
                }

                // Handle activity-based view switching
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

    // Switch views based on activity type
    if (activity.type === 'email_compose' && activity.url) {
        // Show Gmail in browser view
        mainWindow.setBrowserView(browserView);
        browserView.setBounds({
            x: 350,
            y: 200,
            width: mainWindow.getBounds().width - 370,
            height: mainWindow.getBounds().height - 220
        });
        browserView.webContents.loadURL(activity.url);
    }
    else if (activity.type === 'calendar_view') {
        // Show calendar panel
        mainWindow.setBrowserView(null);
        mainWindow.webContents.send('show-panel', 'calendar');
    }
    else if (activity.type === 'task_view') {
        // Show task panel
        mainWindow.setBrowserView(null);
        mainWindow.webContents.send('show-panel', 'tasks');
    }
    else if (activity.type === 'research_view') {
        // Show research panel
        mainWindow.setBrowserView(null);
        mainWindow.webContents.send('show-panel', 'research');
    }
    else {
        // Default office view
        mainWindow.setBrowserView(null);
        mainWindow.webContents.send('show-panel', 'office');
    }
}

// IPC handlers
ipcMain.on('open-gmail', (event, url) => {
    if (browserView) {
        mainWindow.setBrowserView(browserView);
        browserView.setBounds({
            x: 350,
            y: 200,
            width: mainWindow.getBounds().width - 370,
            height: mainWindow.getBounds().height - 220
        });
        browserView.webContents.loadURL(url || 'https://mail.google.com');
    }
});

ipcMain.on('open-calendar', (event) => {
    if (browserView) {
        mainWindow.setBrowserView(browserView);
        browserView.setBounds({
            x: 350,
            y: 200,
            width: mainWindow.getBounds().width - 370,
            height: mainWindow.getBounds().height - 220
        });
        browserView.webContents.loadURL('https://calendar.google.com');
    }
});

ipcMain.on('close-browser', (event) => {
    mainWindow.setBrowserView(null);
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
