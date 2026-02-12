/**
 * WhatsApp Gateway for Claude Code
 * Full-featured assistant matching Telegram capabilities.
 *
 * Setup:
 * 1. npm install
 * 2. node server.js
 * 3. Scan QR code with WhatsApp on your phone
 * 4. Send a message to yourself or the linked number
 *
 * Commands:
 * Fast (instant):  /quick, /email, /revit, /apps, /screenshot, /help
 * Claude (10-30s): /ask <question>, /status, or just type normally
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ============================================
// CONFIGURATION
// ============================================

// Add your phone number here - format: 1234567890@c.us (no + or country code dash)
// Send a test message first to see your number in the logs
const ALLOWED_NUMBERS = [
    '17865879726@c.us',  // Weber's phone
];

// LOCKED DOWN - only Weber's number can interact
const ALLOW_ALL = false;

// Timeout for Claude responses (ms)
const CLAUDE_TIMEOUT = 120000;

// Paths
const LOG_FILE = 'D:\\_CLAUDE-TOOLS\\whatsapp-gateway\\conversations.log';
const LIVE_STATE_FILE = 'D:\\_CLAUDE-TOOLS\\system-bridge\\live_state.json';
const SCREENSHOT_DIR = 'D:\\';

// ============================================
// FAST COMMAND HANDLERS (No Claude needed)
// ============================================

function readLiveState() {
    try {
        if (fs.existsSync(LIVE_STATE_FILE)) {
            return JSON.parse(fs.readFileSync(LIVE_STATE_FILE, 'utf8'));
        }
    } catch (e) {
        console.error('Error reading live state:', e);
    }
    return {};
}

function getSystemStatusFast() {
    const state = readLiveState();
    const system = state.system || {};
    const apps = state.applications || [];
    const revit = state.revit || {};

    const appNames = apps
        .filter(a => a.MainWindowTitle)
        .map(a => a.ProcessName)
        .slice(0, 5);

    let revitStatus = 'Not running';
    for (const app of apps) {
        if (app.ProcessName === 'Revit') {
            revitStatus = (app.MainWindowTitle || 'Running').substring(0, 50);
            break;
        }
    }

    const now = new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

    return `📊 *System Status*

💻 *Resources*
• CPU: ${system.cpu_percent || 0}%
• Memory: ${system.memory_percent || 0}% (${Math.round((system.memory_used_gb || 0))}GB / ${system.memory_total_gb || 0}GB)

🏗️ *Revit*: ${revitStatus}

📱 *Active Apps*: ${apps.length}
${appNames.join(', ')}${apps.length > 5 ? '...' : ''}

⏰ Updated: ${now}`;
}

function getEmailStatusFast() {
    const state = readLiveState();
    const email = state.email || {};

    let msg = `📧 *Email Status*

• Unread: ${email.unread_count || 0}
• Urgent: ${email.urgent_count || 0}
• Needs Response: ${email.needs_response_count || 0}
• Last Check: ${(email.last_check || 'Unknown').substring(0, 16)}`;

    const alerts = email.alerts || [];
    if (alerts.length > 0) {
        msg += '\n\n*Alerts:*';
        for (const a of alerts.slice(0, 3)) {
            const subj = (a.subject || '?').substring(0, 40);
            const frm = (a.from || '?').split('<')[0].substring(0, 20);
            msg += `\n• ${frm}: ${subj}`;
        }
    }

    return msg;
}

function getRevitStatusFast() {
    const state = readLiveState();
    const apps = state.applications || [];

    for (const app of apps) {
        if (app.ProcessName === 'Revit') {
            return `🏗️ *Revit Status*

✅ Running
📄 ${app.MainWindowTitle || 'Unknown'}
🖥️ Monitor: ${app.Monitor || '?'}`;
        }
    }

    return `🏗️ *Revit Status*

❌ Not running`;
}

function getAppsFast() {
    const state = readLiveState();
    const apps = state.applications || [];

    let msg = '📱 *Running Apps*\n';
    for (const app of apps) {
        const name = app.ProcessName || '?';
        const title = (app.MainWindowTitle || '').substring(0, 30);
        const monitor = app.Monitor || '?';
        if (title) {
            msg += `\n• *${name}* (${monitor})\n  ${title}`;
        }
    }

    return msg.substring(0, 4000);
}

function getHelpMessage() {
    return `👋 *Weber Assistant - WhatsApp*

*Fast Commands* (instant):
/quick - System snapshot
/email - Email status
/revit - Revit status
/apps - Running apps
/screenshot [left|center|right] - Get screenshot
/help - This message

*Claude Commands* (10-30s):
/status - Detailed status via Claude
/ask <question> - Ask Claude anything

Or just type normally to chat with Claude.`;
}

async function takeScreenshot(monitor = 'center') {
    return new Promise((resolve, reject) => {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const winPath = `D:\\temp_wa_screenshot_${timestamp}.png`;

        // Monitor coordinates (from your 3-monitor setup)
        let coords;
        switch (monitor.toLowerCase()) {
            case 'all':
                coords = { left: -5120, top: 0, width: 7680, height: 1440 };
                break;
            case 'right':
                coords = { left: 0, top: 0, width: 2560, height: 1440 };
                break;
            case 'left':
                coords = { left: -5120, top: 0, width: 2560, height: 1440 };
                break;
            case 'center':
            default:
                coords = { left: -2560, top: 0, width: 2560, height: 1440 };
                break;
        }

        const psScript = `
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$left = ${coords.left}
$top = ${coords.top}
$width = ${coords.width}
$height = ${coords.height}
$bmp = New-Object Drawing.Bitmap($width, $height)
$graphics = [Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($left, $top, 0, 0, [Drawing.Size]::new($width, $height))
$bmp.Save("${winPath.replace(/\\/g, '\\\\')}")
$graphics.Dispose()
$bmp.Dispose()
Write-Host "OK"
`;

        try {
            execSync(`powershell.exe -Command "${psScript.replace(/\n/g, ' ')}"`, { timeout: 15000 });

            // Convert Windows path to WSL path for reading
            const linuxPath = winPath.replace('D:\\', '/mnt/d/').replace(/\\/g, '/');

            if (fs.existsSync(linuxPath)) {
                resolve({ winPath, linuxPath });
            } else if (fs.existsSync(winPath)) {
                resolve({ winPath, linuxPath: winPath });
            } else {
                reject(new Error('Screenshot file not created'));
            }
        } catch (e) {
            reject(e);
        }
    });
}

// ============================================
// CLAUDE QUERY
// ============================================

async function queryClaude(message, context = '') {
    return new Promise((resolve, reject) => {
        const chunks = [];
        const fullPrompt = context ? `[Context: ${context}]\n\n${message}` : message;

        const claude = spawn('claude', ['-p', fullPrompt, '--output-format', 'text'], {
            shell: true,
            timeout: CLAUDE_TIMEOUT
        });

        claude.stdout.on('data', (data) => chunks.push(data));
        claude.stderr.on('data', (data) => console.error('Claude stderr:', data.toString()));

        claude.on('close', (code) => {
            const output = Buffer.concat(chunks).toString().trim();
            if (code === 0 && output) {
                const truncated = output.length > 4000
                    ? output.substring(0, 4000) + '\n\n...(truncated)'
                    : output;
                resolve(truncated);
            } else {
                resolve('No response from Claude. Please try again.');
            }
        });

        claude.on('error', (error) => {
            console.error('Failed to start Claude:', error);
            reject(error);
        });

        setTimeout(() => {
            claude.kill();
            resolve('Request timed out. Try a simpler question.');
        }, CLAUDE_TIMEOUT);
    });
}

// ============================================
// LOGGING
// ============================================

function logConversation(sender, message, response) {
    const timestamp = new Date().toISOString();
    const logEntry = `
${'='.repeat(60)}
Time: ${timestamp}
From: ${sender}
Message: ${message}
Response: ${response.substring(0, 500)}${response.length > 500 ? '...' : ''}
`;

    try {
        fs.appendFileSync(LOG_FILE, logEntry, 'utf8');
    } catch (error) {
        console.error('Failed to log conversation:', error);
    }
}

// ============================================
// CLIENT SETUP
// ============================================

console.log('='.repeat(60));
console.log('WHATSAPP GATEWAY FOR CLAUDE - FULL FEATURED');
console.log('='.repeat(60));

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: 'D:\\_CLAUDE-TOOLS\\whatsapp-gateway\\.wwebjs_auth'
    }),
    puppeteer: {
        headless: true,
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

// ============================================
// EVENT HANDLERS
// ============================================

client.on('qr', (qr) => {
    console.log('\n📱 Scan this QR code with WhatsApp:\n');
    qrcode.generate(qr, { small: true });
    console.log('\nOpen WhatsApp > Settings > Linked Devices > Link a Device\n');
});

client.on('ready', () => {
    console.log('\n' + '='.repeat(60));
    console.log('✅ WhatsApp client is ready!');
    console.log('');
    console.log('Fast commands: /quick /email /revit /apps /screenshot /help');
    console.log('Claude commands: /ask <question> /status');
    console.log('Or just type normally to chat with Claude.');
    console.log('');
    if (ALLOWED_NUMBERS.length === 0 && !ALLOW_ALL) {
        console.log('⚠️  WARNING: No allowed numbers configured!');
        console.log('Send a test message to see your number in the logs.');
    }
    console.log('='.repeat(60) + '\n');
});

client.on('authenticated', () => {
    console.log('🔐 Authenticated successfully!');
});

client.on('auth_failure', (msg) => {
    console.error('❌ Authentication failed:', msg);
});

client.on('disconnected', (reason) => {
    console.log('🔌 Client disconnected:', reason);
    console.log('Attempting to reconnect...');
    setTimeout(() => client.initialize(), 5000);
});

// ============================================
// MESSAGE HANDLER
// ============================================

client.on('message', async (msg) => {
    const sender = msg.from;
    const messageBody = msg.body.trim();

    console.log(`[${new Date().toISOString()}] From: ${sender}`);
    console.log(`Message: ${messageBody.substring(0, 50)}...`);

    // Security check
    if (!ALLOW_ALL && ALLOWED_NUMBERS.length > 0 && !ALLOWED_NUMBERS.includes(sender)) {
        console.log(`🚫 Ignoring unauthorized: ${sender}`);
        console.log('Add this number to ALLOWED_NUMBERS to enable.');
        return;
    }

    // Ignore groups
    if (sender.includes('@g.us')) {
        console.log('Ignoring group message');
        return;
    }

    // Ignore status broadcasts
    if (sender === 'status@broadcast') return;

    const chat = await msg.getChat();
    let response = '';

    try {
        // Parse commands
        const lowerMsg = messageBody.toLowerCase();

        // FAST COMMANDS (instant, no Claude)
        if (lowerMsg === '/quick' || lowerMsg === '/q') {
            response = getSystemStatusFast();

        } else if (lowerMsg === '/email' || lowerMsg === '/e') {
            response = getEmailStatusFast();

        } else if (lowerMsg === '/revit' || lowerMsg === '/r') {
            response = getRevitStatusFast();

        } else if (lowerMsg === '/apps' || lowerMsg === '/a') {
            response = getAppsFast();

        } else if (lowerMsg === '/help' || lowerMsg === '/h' || lowerMsg === '/start') {
            response = getHelpMessage();

        } else if (lowerMsg.startsWith('/screenshot') || lowerMsg.startsWith('/ss')) {
            // Screenshot command
            const parts = messageBody.split(' ');
            const monitor = parts[1] || 'center';

            if (!['left', 'center', 'right', 'all'].includes(monitor.toLowerCase())) {
                await msg.reply('Usage: /screenshot [left|center|right|all]\nDefault: center');
                return;
            }

            await msg.reply(`📸 Capturing ${monitor} monitor...`);

            try {
                const { linuxPath, winPath } = await takeScreenshot(monitor);
                const media = MessageMedia.fromFilePath(linuxPath);
                await chat.sendMessage(media, {
                    caption: `🖥️ ${monitor.charAt(0).toUpperCase() + monitor.slice(1)} monitor\n⏰ ${new Date().toLocaleTimeString()}`
                });

                // Cleanup
                try { fs.unlinkSync(linuxPath); } catch (e) {}

                logConversation(sender, messageBody, '[Screenshot sent]');
                return;
            } catch (e) {
                console.error('Screenshot error:', e);
                await msg.reply('❌ Screenshot failed. Try again.');
                return;
            }

        // CLAUDE COMMANDS (slower)
        } else if (lowerMsg === '/status' || lowerMsg === '/s') {
            await chat.sendStateTyping();
            await msg.reply('⏳ Getting detailed status from Claude...');
            response = await queryClaude('Give me a brief system status - what\'s running, memory usage, any issues?', 'WhatsApp status request');

        } else if (lowerMsg.startsWith('/ask ')) {
            const question = messageBody.substring(5).trim();
            if (!question) {
                await msg.reply('Usage: /ask <your question>');
                return;
            }
            await chat.sendStateTyping();
            await msg.reply('⏳ Asking Claude...');
            response = await queryClaude(question, 'WhatsApp question');

        } else {
            // Regular message - send to Claude
            await chat.sendStateTyping();
            response = await queryClaude(messageBody, 'Message from WhatsApp');
        }

        // Send response
        if (response) {
            await msg.reply(response);
            logConversation(sender, messageBody, response);
        }

    } catch (error) {
        console.error('Error processing message:', error);
        await msg.reply('❌ Error processing your request. Please try again.');
    }
});

// ============================================
// LOCAL SEND API (localhost only)
// ============================================

const http = require('http');

const apiServer = http.createServer(async (req, res) => {
    // Only allow localhost
    const remoteIp = req.socket.remoteAddress;
    if (remoteIp !== '127.0.0.1' && remoteIp !== '::1' && remoteIp !== '::ffff:127.0.0.1') {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const data = JSON.parse(body);
                const to = data.to || ALLOWED_NUMBERS[0]; // Default: Weber
                const message = data.message || '';

                if (!message) {
                    res.writeHead(400);
                    res.end(JSON.stringify({ error: 'No message provided' }));
                    return;
                }

                await client.sendMessage(to, message);
                console.log(`[API] Sent to ${to}: ${message.substring(0, 50)}...`);
                res.writeHead(200);
                res.end(JSON.stringify({ ok: true, to, message: message.substring(0, 50) }));
            } catch (e) {
                console.error('[API] Send error:', e);
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: 'ok', ready: client.info ? true : false }));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

const API_PORT = 18790;

// ============================================
// STARTUP
// ============================================

console.log('Initializing WhatsApp client...');
console.log('This may take a minute on first run.\n');

client.on('ready', () => {
    // Start the local send API after client is ready
    apiServer.listen(API_PORT, '127.0.0.1', () => {
        console.log(`\n📡 Send API ready: http://127.0.0.1:${API_PORT}/send`);
        console.log(`   POST {"message": "text"} to send to Weber`);
        console.log(`   GET /health for status check\n`);
    });
});

client.initialize().catch(err => {
    console.error('Failed to initialize:', err);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n👋 Shutting down...');
    apiServer.close();
    await client.destroy();
    process.exit(0);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
});
