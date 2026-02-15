#!/usr/bin/env python3
"""
Web Chat Interface for Claude Code
Access your AI assistant from any browser, including mobile.

Setup:
1. pip install flask
2. python server.py
3. Open http://localhost:5555 in browser

For remote access:
- Tailscale: tailscale serve 5555
- ngrok: ngrok http 5555

Security:
- AUTH_TOKEN required for all requests
- Bookmark the URL with token: http://localhost:5555?token=YOUR_TOKEN
"""

import os
import sys
import subprocess
import asyncio
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response
import json

# Add gateway to path for security filter
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
try:
    from security_filter import SecurityFilter
    SECURITY_ENABLED = True
    security_filter = SecurityFilter(strict_mode=True)
except ImportError:
    SECURITY_ENABLED = False
    security_filter = None
    print("WARNING: Security filter not available")

# ============================================
# CONFIGURATION
# ============================================

# Secure token - keep this secret!
AUTH_TOKEN = os.getenv("WEBCHAT_TOKEN", "mDtQP460ym6iOHQmtMvASMCYFbfCRe1nurFEPVitDp0")

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5555

# Timeout for Claude (seconds)
CLAUDE_TIMEOUT = 120

# ============================================
# APP SETUP
# ============================================

app = Flask(__name__)

# ============================================
# HTML TEMPLATE
# ============================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Claude Assistant</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: #16213e;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #0f3460;
        }

        .header h1 {
            font-size: 1.2rem;
            color: #e94560;
        }

        .status {
            font-size: 0.8rem;
            color: #4ade80;
        }

        .status.offline {
            color: #f87171;
        }

        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.4;
            word-wrap: break-word;
            white-space: pre-wrap;
        }

        .message.user {
            background: #e94560;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }

        .message.claude {
            background: #16213e;
            color: #eee;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            border: 1px solid #0f3460;
        }

        .message.system {
            background: #0f3460;
            color: #94a3b8;
            align-self: center;
            font-size: 0.85rem;
            padding: 8px 16px;
        }

        .message code {
            background: #0d1117;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Fira Code', monospace;
            font-size: 0.9em;
        }

        .message pre {
            background: #0d1117;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
        }

        .input-area {
            background: #16213e;
            padding: 15px 20px;
            display: flex;
            gap: 10px;
            border-top: 1px solid #0f3460;
        }

        #input {
            flex: 1;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            border-radius: 24px;
            padding: 12px 20px;
            color: #eee;
            font-size: 16px;
            outline: none;
        }

        #input:focus {
            border-color: #e94560;
        }

        #input::placeholder {
            color: #64748b;
        }

        button {
            background: #e94560;
            border: none;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.1s;
        }

        button:active {
            transform: scale(0.95);
        }

        button:disabled {
            background: #4a4a6a;
            cursor: not-allowed;
        }

        button svg {
            width: 24px;
            height: 24px;
            fill: white;
        }

        .typing {
            display: flex;
            gap: 4px;
            padding: 8px;
        }

        .typing span {
            width: 8px;
            height: 8px;
            background: #64748b;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }

        .typing span:nth-child(1) { animation-delay: -0.32s; }
        .typing span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        .quick-actions {
            display: flex;
            gap: 8px;
            padding: 10px 20px;
            overflow-x: auto;
            background: #16213e;
        }

        .quick-btn {
            background: #0f3460;
            border: none;
            border-radius: 16px;
            padding: 8px 16px;
            color: #94a3b8;
            font-size: 0.85rem;
            cursor: pointer;
            white-space: nowrap;
        }

        .quick-btn:hover {
            background: #1a4a7a;
            color: #eee;
        }

        /* Voice Controls */
        .voice-controls {
            display: flex;
            gap: 8px;
            padding: 0 20px 10px;
            background: #16213e;
        }

        .voice-btn {
            background: #0f3460;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }

        .voice-btn:hover {
            background: #1a4a7a;
        }

        .voice-btn.active {
            background: #e94560;
            animation: pulse 1.5s infinite;
        }

        .voice-btn.enabled {
            background: #4ade80;
        }

        .voice-btn svg {
            width: 20px;
            height: 20px;
            fill: white;
        }

        .voice-label {
            font-size: 0.75rem;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(233, 69, 96, 0.4); }
            50% { box-shadow: 0 0 0 10px rgba(233, 69, 96, 0); }
        }

        .listening-indicator {
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: #e94560;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9rem;
            display: none;
            z-index: 100;
            animation: pulse 1.5s infinite;
        }

        .listening-indicator.show {
            display: block;
        }

        #micBtn {
            background: #0f3460;
        }

        #micBtn.recording {
            background: #e94560;
            animation: pulse 1.5s infinite;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Claude Assistant</h1>
        <span class="status" id="status">Connected</span>
    </div>

    <div class="quick-actions">
        <button class="quick-btn" onclick="quickSend('System status')">Status</button>
        <button class="quick-btn" onclick="quickSend('Check Revit connection')">Revit</button>
        <button class="quick-btn" onclick="quickSend('Check my email')">Email</button>
        <button class="quick-btn" onclick="quickSend('What tasks are pending?')">Tasks</button>
    </div>

    <div class="voice-controls">
        <span class="voice-label">Voice:</span>
        <button class="voice-btn" id="speakerBtn" onclick="toggleSpeaker()" title="Toggle voice responses">
            <svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
        </button>
        <button class="voice-btn" id="micBtn" onclick="toggleMic()" title="Voice input (hold or click)">
            <svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/></svg>
        </button>
        <span class="voice-label" id="voiceStatus">Speaker: Off</span>
    </div>

    <div class="listening-indicator" id="listeningIndicator">
        🎤 Listening...
    </div>

    <div id="messages">
        <div class="message system">Connected to Claude. Send a message to begin.</div>
    </div>

    <div class="input-area">
        <input type="text" id="input" placeholder="Ask Claude anything..." autocomplete="off">
        <button id="sendBtn" onclick="send()">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
    </div>

    <script>
        const TOKEN = new URLSearchParams(window.location.search).get('token') || '{{ token }}';
        const messagesDiv = document.getElementById('messages');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        const statusEl = document.getElementById('status');

        let isLoading = false;

        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = `message ${type}`;

            // Basic markdown-like formatting
            let formatted = text
                .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

            div.innerHTML = formatted;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function showTyping() {
            const div = document.createElement('div');
            div.className = 'message claude';
            div.id = 'typing';
            div.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function hideTyping() {
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }

        async function send() {
            const msg = input.value.trim();
            if (!msg || isLoading) return;

            input.value = '';
            addMessage(msg, 'user');

            isLoading = true;
            sendBtn.disabled = true;
            showTyping();

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg, token: TOKEN})
                });

                const data = await res.json();
                hideTyping();

                if (data.error) {
                    addMessage('Error: ' + data.error, 'system');
                    if (data.error === 'Unauthorized') {
                        statusEl.textContent = 'Auth Failed';
                        statusEl.classList.add('offline');
                    }
                } else {
                    addMessage(data.response, 'claude');
                }
            } catch (err) {
                hideTyping();
                addMessage('Connection error: ' + err.message, 'system');
                statusEl.textContent = 'Offline';
                statusEl.classList.add('offline');
            }

            isLoading = false;
            sendBtn.disabled = false;
            input.focus();
        }

        function quickSend(msg) {
            input.value = msg;
            send();
        }

        // Enter to send
        input.addEventListener('keypress', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        });

        // Focus input on load
        input.focus();

        // ============================================
        // VOICE FUNCTIONALITY
        // ============================================

        let speakerEnabled = false;
        let isRecording = false;
        let recognition = null;

        // Check for speech synthesis support
        const speechSynthesis = window.speechSynthesis;
        const hasTTS = 'speechSynthesis' in window;

        // Check for speech recognition support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const hasSTT = !!SpeechRecognition;

        if (hasSTT) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                isRecording = true;
                document.getElementById('micBtn').classList.add('recording');
                document.getElementById('listeningIndicator').classList.add('show');
            };

            recognition.onend = () => {
                isRecording = false;
                document.getElementById('micBtn').classList.remove('recording');
                document.getElementById('listeningIndicator').classList.remove('show');
            };

            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }

                // Show interim results in input
                if (interimTranscript) {
                    input.value = interimTranscript;
                }

                // Send final result
                if (finalTranscript) {
                    input.value = finalTranscript;
                    send();
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                isRecording = false;
                document.getElementById('micBtn').classList.remove('recording');
                document.getElementById('listeningIndicator').classList.remove('show');

                if (event.error === 'not-allowed') {
                    addMessage('Microphone access denied. Please allow microphone access in your browser.', 'system');
                }
            };
        }

        function toggleSpeaker() {
            speakerEnabled = !speakerEnabled;
            const btn = document.getElementById('speakerBtn');
            const status = document.getElementById('voiceStatus');

            if (speakerEnabled) {
                btn.classList.add('enabled');
                status.textContent = 'Speaker: On';
                // Test voice
                speak('Voice responses enabled');
            } else {
                btn.classList.remove('enabled');
                status.textContent = 'Speaker: Off';
                speechSynthesis.cancel();
            }
        }

        function toggleMic() {
            if (!hasSTT) {
                addMessage('Speech recognition not supported in this browser. Try Chrome.', 'system');
                return;
            }

            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }

        function speak(text) {
            if (!hasTTS || !speakerEnabled) return;

            // Cancel any ongoing speech
            speechSynthesis.cancel();

            // Clean text for speech (remove markdown, code blocks, etc.)
            const cleanText = text
                .replace(/```[\s\S]*?```/g, 'code block omitted')
                .replace(/`[^`]+`/g, '')
                .replace(/\*\*([^*]+)\*\*/g, '$1')
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                .replace(/#{1,6}\s/g, '')
                .replace(/\n+/g, '. ')
                .substring(0, 1000); // Limit length

            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            // Try to get a good English voice
            const voices = speechSynthesis.getVoices();
            const preferredVoice = voices.find(v =>
                v.name.includes('Google') ||
                v.name.includes('Microsoft') ||
                v.name.includes('David') ||
                v.name.includes('Zira')
            ) || voices.find(v => v.lang.startsWith('en'));

            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }

            speechSynthesis.speak(utterance);
        }

        // Load voices (needed for Chrome)
        if (hasTTS) {
            speechSynthesis.getVoices();
            speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
        }

        // Modify addMessage to speak Claude responses
        const originalAddMessage = addMessage;
        addMessage = function(text, type) {
            originalAddMessage(text, type);
            if (type === 'claude' && speakerEnabled) {
                speak(text);
            }
        };

        // ============================================
        // END VOICE FUNCTIONALITY
        // ============================================

        // Check connection
        async function checkConnection() {
            try {
                const res = await fetch('/health');
                if (res.ok) {
                    statusEl.textContent = 'Connected';
                    statusEl.classList.remove('offline');
                }
            } catch {
                statusEl.textContent = 'Offline';
                statusEl.classList.add('offline');
            }
        }

        setInterval(checkConnection, 30000);
    </script>
</body>
</html>
'''

MANIFEST = {
    "name": "Claude Assistant",
    "short_name": "Claude",
    "description": "Personal AI Assistant",
    "start_url": "/?token=" + AUTH_TOKEN,
    "display": "standalone",
    "background_color": "#1a1a2e",
    "theme_color": "#e94560",
    "icons": []
}

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Serve the chat interface"""
    token = request.args.get('token', '')
    return render_template_string(HTML_TEMPLATE, token=token)


@app.route('/manifest.json')
def manifest():
    """PWA manifest"""
    return jsonify(MANIFEST)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.json

    # Auth check
    if data.get('token') != AUTH_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    # SECURITY: Check for prompt injection
    if SECURITY_ENABLED and security_filter:
        is_safe, reason = security_filter.check(message, "web-chat")
        if not is_safe:
            return jsonify({
                'response': f"⚠️ Message blocked for security:\n{reason}\n\nIf this was legitimate, please rephrase your request."
            })
        # Sanitize
        message = security_filter.sanitize(message)

    # Query Claude
    try:
        result = subprocess.run(
            ['claude', '-p', message, '--output-format', 'text'],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT
        )

        response = result.stdout.strip()
        if not response:
            response = "No response from Claude."

        # Log the conversation
        log_conversation(message, response)

        return jsonify({'response': response})

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Request timed out'}), 504
    except FileNotFoundError:
        return jsonify({'error': 'Claude CLI not found'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def log_conversation(message: str, response: str):
    """Log to file"""
    log_file = "/mnt/d/_CLAUDE-TOOLS/web-chat/conversations.log"
    timestamp = datetime.now().isoformat()
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] User: {message[:100]}\n")
            f.write(f"[{timestamp}] Claude: {response[:200]}...\n")
    except:
        pass


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*60)
    print("CLAUDE WEB CHAT SERVER")
    print("="*60)
    print(f"\nLocal URL:   http://localhost:{PORT}?token={AUTH_TOKEN}")
    print(f"\nFor mobile access, use one of:")
    print(f"  - Tailscale: tailscale serve {PORT}")
    print(f"  - ngrok: ngrok http {PORT}")
    print(f"\nAuth Token: {AUTH_TOKEN}")
    print(f"\nBookmark this URL on your phone for quick access!")
    print("="*60)
    print("\nServer starting...\n")

    app.run(host=HOST, port=PORT, debug=False)
