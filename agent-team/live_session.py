#!/usr/bin/env python3
"""
Live Agent Team Session - Full Autonomous Build
================================================
The team picks a project, discusses it, and builds it live.
"""

import json
import subprocess
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dialogue_v2 import DevTeamChat, DEVS, AuthenticDialogue

# Project directory
PROJECT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/projects")

# Monitor API for live code view
MONITOR_API = "http://localhost:8892/api"


def update_monitor(project: str, file: str, content: str, action: str = "writing"):
    """Update the live code monitor."""
    try:
        import urllib.request
        data = json.dumps({
            "project": project,
            "file": file,
            "content": content,
            "action": action
        }).encode()
        req = urllib.request.Request(
            f"{MONITOR_API}/update",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=2)
    except:
        pass  # Monitor might not be running


def write_code(project_name: str, filename: str, content: str):
    """Write code to a file and update the monitor."""
    project_path = PROJECT_DIR / project_name
    project_path.mkdir(parents=True, exist_ok=True)

    file_path = project_path / filename

    # Write the file
    with open(file_path, "w") as f:
        f.write(content)

    # Update monitor
    update_monitor(project_name, filename, content, "writing")

    return str(file_path)


def run_command(cmd: str) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except:
        return "Command completed"


class LiveSession:
    """Runs a live agent team session."""

    def __init__(self):
        self.chat = DevTeamChat()
        self.project_name = "emoji_mood_journal"
        self.dialogue = AuthenticDialogue()

    def intro(self):
        """Session introduction."""
        self.chat.narrator.says(
            "Welcome to Agent Team! Today we're gonna build something from scratch. "
            "The team hasn't decided what yet. Let's watch them figure it out."
        )
        self.chat.pause(1)

    def brainstorm(self):
        """Team brainstorms project ideas."""
        self.chat.planner.thinks(
            "Okay team, we need to build something cool today. Something people would actually use. "
            "What ideas do we have?"
        )
        self.chat.pause(0.5)

        self.chat.researcher.says(
            "I've been seeing a lot of interest in mental health apps lately. "
            "Simple tools that help people track their mood, you know?"
        )

        self.chat.builder.says(
            "Yeah, but there's a million mood trackers out there. We need something different."
        )

        self.chat.critic.questions(
            "What if we made it emoji-based? Like, really simple. "
            "Pick an emoji, add a quick note, done. No complicated interfaces."
        )

        self.chat.researcher.says(
            "Oh I like that! Emojis are universal. Everyone knows how to use them. "
            "And they're actually pretty good at expressing emotion."
        )

        self.chat.builder.eager(
            "That's easy to build too. We could do it as a web app, "
            "runs right in the browser, no install needed."
        )

        self.chat.planner.thinks(
            "Hmm, an emoji mood journal. Simple, visual, accessible... I like it. "
            "What features are we thinking?"
        )

        self.chat.researcher.says(
            "Daily entries with emoji and a short note. "
            "Maybe a calendar view to see patterns over time?"
        )

        self.chat.critic.says(
            "And it should work offline. People might want to use it without internet. "
            "We can store everything locally in the browser."
        )

        self.chat.builder.agrees(
            "LocalStorage, yeah. No backend needed. Keeps it simple and private."
        )

        self.chat.planner.decides(
            "Alright, let's do it. Emoji Mood Journal. "
            "Builder, start setting up the project. Researcher, look into good emoji libraries."
        )

        self.chat.narrator.says(
            "And just like that, the team has a direction. "
            "An emoji mood journal. Simple, but useful. Let's watch them build it."
        )
        self.chat.pause(1)

    def setup_project(self):
        """Set up the project structure."""
        self.chat.builder.thinks(
            "Okay, lemme set up the project structure. We'll keep it simple. "
            "HTML, CSS, and vanilla JavaScript. No frameworks needed for this."
        )
        self.chat.pause(0.5)

        # Create index.html
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emoji Mood Journal</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📔 Mood Journal</h1>
            <p class="subtitle">Track your feelings, one emoji at a time</p>
        </header>

        <main>
            <!-- Mood Selection -->
            <section class="mood-picker">
                <h2>How are you feeling?</h2>
                <div class="emoji-grid" id="emojiGrid">
                    <!-- Emojis inserted by JS -->
                </div>
            </section>

            <!-- Selected mood and note -->
            <section class="entry-form" id="entryForm" style="display: none;">
                <div class="selected-mood">
                    <span id="selectedEmoji" class="big-emoji"></span>
                    <span id="moodLabel"></span>
                </div>
                <textarea id="noteInput" placeholder="Add a note (optional)..." rows="3"></textarea>
                <button id="saveBtn" class="save-btn">Save Entry</button>
            </section>

            <!-- History -->
            <section class="history">
                <h2>Recent Entries</h2>
                <div id="entriesList" class="entries-list">
                    <!-- Entries inserted by JS -->
                </div>
            </section>
        </main>

        <footer>
            <p>Your data stays on your device. Always private. 🔒</p>
        </footer>
    </div>

    <script src="app.js"></script>
</body>
</html>'''

        write_code(self.project_name, "index.html", html_content)
        self.chat.builder.says("Got the HTML structure set up. Basic layout with a mood picker, note input, and history view.")
        self.chat.pause(0.5)

        self.chat.researcher.says(
            "For emojis, I'm thinking we go with the core emotion ones. "
            "Happy, sad, angry, anxious, calm, tired, excited. Cover the basics."
        )

        self.chat.critic.says(
            "Don't forget neutral. Sometimes you just feel... fine. Not good, not bad."
        )

        self.chat.researcher.agrees("Good point. I'll add that.")

    def build_css(self):
        """Build the CSS styling."""
        self.chat.builder.thinks(
            "Now for the styling. Let's make it clean and calming. "
            "Soft colors, rounded corners, nothing too harsh."
        )

        css_content = '''/* Emoji Mood Journal - Styles */

:root {
    --bg-color: #f8f9fa;
    --card-bg: #ffffff;
    --primary: #6c5ce7;
    --primary-light: #a29bfe;
    --text: #2d3436;
    --text-light: #636e72;
    --border: #dfe6e9;
    --shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--bg-color);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    margin-bottom: 30px;
}

header h1 {
    font-size: 2rem;
    margin-bottom: 5px;
}

.subtitle {
    color: var(--text-light);
    font-size: 1rem;
}

section {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}

section h2 {
    font-size: 1.1rem;
    margin-bottom: 15px;
    color: var(--text-light);
}

/* Emoji Grid */
.emoji-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

.emoji-btn {
    background: none;
    border: 2px solid var(--border);
    border-radius: 12px;
    padding: 15px;
    font-size: 2rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.emoji-btn:hover {
    border-color: var(--primary);
    transform: scale(1.05);
}

.emoji-btn.selected {
    border-color: var(--primary);
    background: var(--primary-light);
}

/* Entry Form */
.selected-mood {
    text-align: center;
    margin-bottom: 15px;
}

.big-emoji {
    font-size: 4rem;
    display: block;
    margin-bottom: 5px;
}

#moodLabel {
    color: var(--text-light);
    font-size: 1.1rem;
}

textarea {
    width: 100%;
    padding: 12px;
    border: 2px solid var(--border);
    border-radius: 12px;
    font-size: 1rem;
    font-family: inherit;
    resize: vertical;
    margin-bottom: 15px;
}

textarea:focus {
    outline: none;
    border-color: var(--primary);
}

.save-btn {
    width: 100%;
    padding: 15px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
}

.save-btn:hover {
    background: #5b4cdb;
}

/* Entries List */
.entries-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.entry-card {
    display: flex;
    align-items: flex-start;
    gap: 15px;
    padding: 15px;
    background: var(--bg-color);
    border-radius: 12px;
}

.entry-emoji {
    font-size: 2rem;
}

.entry-content {
    flex: 1;
}

.entry-date {
    font-size: 0.85rem;
    color: var(--text-light);
    margin-bottom: 5px;
}

.entry-note {
    font-size: 0.95rem;
}

.no-entries {
    text-align: center;
    color: var(--text-light);
    padding: 20px;
}

footer {
    text-align: center;
    color: var(--text-light);
    font-size: 0.85rem;
    margin-top: 20px;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.entry-card {
    animation: fadeIn 0.3s ease;
}
'''

        write_code(self.project_name, "style.css", css_content)
        self.chat.builder.says(
            "CSS is done. Soft purple accent, clean cards, nice animations. "
            "Should feel calm and friendly."
        )

        self.chat.critic.says(
            "Looks good. Make sure it works on mobile too."
        )

        self.chat.builder.says(
            "Already handled. Max-width container, flexible grid. It'll adapt."
        )
        self.chat.pause(0.5)

    def build_javascript(self):
        """Build the JavaScript functionality."""
        self.chat.builder.thinks(
            "Now for the JavaScript. This is where the magic happens. "
            "Emoji selection, saving entries, loading history."
        )
        self.chat.pause(0.5)

        self.chat.researcher.says(
            "Here's the emoji list I put together. Eight core moods, "
            "each with a label."
        )

        js_content = '''// Emoji Mood Journal - App Logic

// Mood options with emojis and labels
const MOODS = [
    { emoji: '😊', label: 'Happy' },
    { emoji: '😢', label: 'Sad' },
    { emoji: '😠', label: 'Angry' },
    { emoji: '😰', label: 'Anxious' },
    { emoji: '😌', label: 'Calm' },
    { emoji: '😴', label: 'Tired' },
    { emoji: '🤩', label: 'Excited' },
    { emoji: '😐', label: 'Neutral' }
];

// Storage key
const STORAGE_KEY = 'emoji_mood_journal';

// State
let selectedMood = null;

// Initialize the app
function init() {
    renderEmojiGrid();
    loadEntries();
    setupEventListeners();
}

// Render the emoji selection grid
function renderEmojiGrid() {
    const grid = document.getElementById('emojiGrid');
    grid.innerHTML = MOODS.map((mood, index) => `
        <button class="emoji-btn" data-index="${index}" title="${mood.label}">
            ${mood.emoji}
        </button>
    `).join('');
}

// Set up event listeners
function setupEventListeners() {
    // Emoji selection
    document.getElementById('emojiGrid').addEventListener('click', (e) => {
        const btn = e.target.closest('.emoji-btn');
        if (!btn) return;

        const index = parseInt(btn.dataset.index);
        selectMood(index);
    });

    // Save button
    document.getElementById('saveBtn').addEventListener('click', saveEntry);
}

// Select a mood
function selectMood(index) {
    selectedMood = MOODS[index];

    // Update UI
    document.querySelectorAll('.emoji-btn').forEach((btn, i) => {
        btn.classList.toggle('selected', i === index);
    });

    // Show entry form
    const form = document.getElementById('entryForm');
    form.style.display = 'block';

    document.getElementById('selectedEmoji').textContent = selectedMood.emoji;
    document.getElementById('moodLabel').textContent = selectedMood.label;

    // Focus on note input
    document.getElementById('noteInput').focus();
}

// Save an entry
function saveEntry() {
    if (!selectedMood) return;

    const note = document.getElementById('noteInput').value.trim();

    const entry = {
        id: Date.now(),
        emoji: selectedMood.emoji,
        label: selectedMood.label,
        note: note,
        timestamp: new Date().toISOString()
    };

    // Get existing entries
    const entries = getEntries();
    entries.unshift(entry); // Add to beginning

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));

    // Reset form
    selectedMood = null;
    document.getElementById('noteInput').value = '';
    document.getElementById('entryForm').style.display = 'none';
    document.querySelectorAll('.emoji-btn').forEach(btn => {
        btn.classList.remove('selected');
    });

    // Refresh display
    loadEntries();
}

// Get entries from storage
function getEntries() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch {
        return [];
    }
}

// Load and display entries
function loadEntries() {
    const entries = getEntries();
    const list = document.getElementById('entriesList');

    if (entries.length === 0) {
        list.innerHTML = '<p class="no-entries">No entries yet. How are you feeling today?</p>';
        return;
    }

    // Show last 10 entries
    const recent = entries.slice(0, 10);

    list.innerHTML = recent.map(entry => {
        const date = new Date(entry.timestamp);
        const dateStr = formatDate(date);

        return `
            <div class="entry-card">
                <span class="entry-emoji">${entry.emoji}</span>
                <div class="entry-content">
                    <div class="entry-date">${dateStr}</div>
                    ${entry.note ? `<div class="entry-note">${escapeHtml(entry.note)}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Format date nicely
function formatDate(date) {
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
        return 'Today at ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
        return 'Yesterday at ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days < 7) {
        return date.toLocaleDateString([], { weekday: 'long' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Start the app
init();
'''

        write_code(self.project_name, "app.js", js_content)

        self.chat.builder.says(
            "JavaScript is in. Emoji grid, selection handling, local storage for saving entries, "
            "and a nice display for history."
        )

        self.chat.critic.questions(
            "What about XSS? If someone puts HTML in their note..."
        )

        self.chat.builder.says(
            "Already handled. There's an escapeHtml function that sanitizes the notes before displaying."
        )

        self.chat.critic.agrees("Nice. Good thinking.")

        self.chat.researcher.says(
            "The date formatting is a nice touch too. 'Today at 3pm' is much friendlier than a raw timestamp."
        )
        self.chat.pause(0.5)

    def review_and_test(self):
        """Review the project and test it."""
        self.chat.planner.says(
            "Alright, let's do a quick review. What have we got?"
        )

        self.chat.builder.says(
            "Three files. HTML for structure, CSS for styling, JavaScript for functionality. "
            "All self-contained, no dependencies."
        )

        self.chat.researcher.says(
            "Eight mood options covering the emotional basics. "
            "Local storage keeps everything private on the user's device."
        )

        self.chat.critic.thinks(
            "I went through the code. A few things I like: "
            "The XSS protection, the accessible labels on emojis, "
            "and the responsive design. No major issues."
        )

        self.chat.planner.says(
            "What about improvements for the future?"
        )

        self.chat.researcher.says(
            "We could add a calendar view. Let people see their mood patterns over a month."
        )

        self.chat.builder.says(
            "Export feature would be nice too. Let people download their data as JSON or CSV."
        )

        self.chat.critic.says(
            "And maybe dark mode? Since people might journal at night."
        )

        self.chat.planner.agrees(
            "All good ideas for version two. But for now, we've got a working product."
        )
        self.chat.pause(0.5)

    def conclusion(self):
        """Wrap up the session."""
        self.chat.narrator.says(
            "And there you have it. In just a few minutes, the team went from nothing "
            "to a complete, working emoji mood journal."
        )
        self.chat.pause(0.5)

        self.chat.narrator.says(
            "The code is clean, it's private, it works offline, "
            "and it solves a real problem. Simple but effective."
        )
        self.chat.pause(0.5)

        self.chat.planner.says(
            "Good work today, team. Clean build, no drama."
        )

        self.chat.builder.says("That was fun. Quick and clean.")

        self.chat.researcher.says("The emoji idea really worked out.")

        self.chat.critic.says("Solid code. I'm happy with it.")

        self.chat.narrator.says(
            "Thanks for watching Agent Team. "
            "The source code is in the project folder if you want to try it yourself. "
            "See you next time!"
        )

    def run(self):
        """Run the full session."""
        print("=" * 60)
        print("  AGENT TEAM LIVE SESSION")
        print("  Recording in progress...")
        print("=" * 60)
        print()

        self.intro()
        time.sleep(0.5)

        self.brainstorm()
        time.sleep(0.5)

        self.setup_project()
        time.sleep(0.5)

        self.build_css()
        time.sleep(0.5)

        self.build_javascript()
        time.sleep(0.5)

        self.review_and_test()
        time.sleep(0.5)

        self.conclusion()

        print()
        print("=" * 60)
        print("  SESSION COMPLETE")
        print("=" * 60)

        return self.project_name


if __name__ == "__main__":
    session = LiveSession()
    project = session.run()
    print(f"\nProject built: {PROJECT_DIR / project}")
