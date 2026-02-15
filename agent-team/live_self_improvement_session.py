#!/usr/bin/env python3
"""
Live Self-Improvement Session - Agents improve their own codebase
Everything is displayed live in the Electron dashboard.
"""

import sys
import time
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/agent-team')

from visual_session import VisualDevTeamChat

def run_live_session():
    """Run a live session where agents improve themselves."""

    chat = VisualDevTeamChat()

    # === INTRODUCTION ===
    print("\n" + "="*60)
    print("  LIVE SELF-IMPROVEMENT SESSION")
    print("="*60 + "\n")

    chat.narrator.explains(
        "Welcome to the Agent Team live session. "
        "Today, the team will be improving their own codebase. "
        "Everything you see is happening in real time."
    )
    time.sleep(3)

    # === PLANNING PHASE ===
    chat.planner.thinks(
        "Let's assess what we can improve. "
        "I'm thinking we should enhance our dashboard capabilities."
    )
    time.sleep(2)

    # Show GitHub search in the live browser
    chat.researcher.says(
        "Let me search for best practices in Electron dashboard design."
    )
    chat.visual.show_github_search("electron dashboard real-time updates best practices", open_real_browser=False)
    time.sleep(4)

    chat.researcher.says(
        "Found several patterns. WebSocket connections, IPC optimization, "
        "and efficient state management are key themes."
    )
    time.sleep(2)

    # === ANALYSIS PHASE ===
    chat.critic.questions(
        "What specific improvements should we prioritize? "
        "We should focus on the most impactful changes."
    )
    time.sleep(2)

    chat.planner.decides(
        "Three priorities: First, add smooth transitions between view modes. "
        "Second, improve the activity log formatting. "
        "Third, add a connection status indicator."
    )
    time.sleep(2)

    # === BUILDING PHASE ===
    chat.builder.says(
        "I'll start with the view transitions. Let me write the CSS animations."
    )
    time.sleep(1)

    # Show code being written live
    transition_css = '''/* Smooth view transitions */
.content-overlay {
    transition: opacity 0.3s ease-in-out,
                transform 0.3s ease-in-out;
    opacity: 0;
    transform: translateY(10px);
}

.content-overlay.visible {
    opacity: 1;
    transform: translateY(0);
}

/* Terminal typing animation */
.terminal-content .typing-cursor {
    display: inline-block;
    width: 10px;
    height: 20px;
    background: #00ff00;
    animation: blink 0.7s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Code syntax highlight fade-in */
.code-content pre {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Agent card pulse when speaking */
.agent-card.speaking {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.4);
    }
    50% {
        box-shadow: 0 0 0 10px rgba(63, 185, 80, 0);
    }
}'''

    chat.visual.show_code_typing("dashboard-transitions.css", transition_css, "css")
    time.sleep(8)

    chat.builder.says(
        "Transitions are ready. Now for the activity log improvements."
    )
    time.sleep(1)

    # Show more code
    activity_log_js = '''// Enhanced activity log with categories and icons
function addActivity(activity) {
    const log = document.getElementById('activityLog');

    const categoryColors = {
        'browser_navigate': '#58a6ff',  // Blue
        'terminal_run': '#a371f7',       // Purple
        'code_write': '#3fb950',         // Green
        'thinking': '#d29922'            // Yellow
    };

    const icons = {
        'browser_navigate': '🌐',
        'terminal_run': '⚡',
        'code_write': '💻',
        'thinking': '💭',
        'code_read': '📖',
        'file_create': '📄'
    };

    const item = document.createElement('div');
    item.className = 'activity-item';
    item.style.borderLeft = `3px solid ${categoryColors[activity.type] || '#8b949e'}`;

    const time = new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    item.innerHTML = `
        <div class="activity-time">${time}</div>
        <div class="activity-message">
            <span class="activity-icon">${icons[activity.type] || '📌'}</span>
            ${getActivityMessage(activity)}
        </div>
    `;

    // Slide-in animation
    item.style.opacity = '0';
    item.style.transform = 'translateX(-20px)';
    log.insertBefore(item, log.firstChild);

    requestAnimationFrame(() => {
        item.style.transition = 'all 0.3s ease';
        item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
    });

    // Keep only last 50 entries
    while (log.children.length > 50) {
        log.removeChild(log.lastChild);
    }
}'''

    chat.visual.show_code_typing("activity-log-enhanced.js", activity_log_js, "javascript")
    time.sleep(10)

    # === REVIEW PHASE ===
    chat.critic.says(
        "The animations look smooth. I'd suggest adding a connection status indicator "
        "so users know when the dashboard is receiving updates."
    )
    time.sleep(2)

    chat.builder.agrees(
        "Good idea. Let me add a status indicator to the header."
    )
    time.sleep(1)

    # Show terminal command
    chat.visual.show_terminal(
        "git diff --stat",
        " dashboard.html      | 45 +++++++++++++++++++++++++++++\n" +
        " main.js             | 12 ++++++++\n" +
        " styles/animate.css  | 38 ++++++++++++++++++++++++\n" +
        " 3 files changed, 95 insertions(+)"
    )
    time.sleep(3)

    # === DOCUMENTATION ===
    chat.researcher.says(
        "Let me look at how other projects document their dashboard features."
    )
    chat.visual.show_website("https://electron.build/", "Electron Builder Docs", open_real_browser=False)
    time.sleep(4)

    chat.narrator.explains(
        "The team has made significant progress. "
        "They've added smooth transitions, enhanced the activity log, "
        "and improved the visual feedback system."
    )
    time.sleep(2)

    # === WRAP UP ===
    chat.planner.says(
        "Excellent work everyone. The dashboard is now more polished and responsive."
    )
    time.sleep(2)

    chat.builder.says(
        "I'll commit these changes and we can iterate further in the next session."
    )

    chat.visual.show_terminal(
        "git add -A && git commit -m 'feat: enhance dashboard with smooth transitions and better activity log'",
        "[main abc1234] feat: enhance dashboard with smooth transitions and better activity log\n" +
        " 3 files changed, 95 insertions(+)\n" +
        " create mode 100644 styles/animate.css"
    )
    time.sleep(3)

    chat.narrator.explains(
        "And that's a wrap on this session. "
        "The Agent Team continuously improves, learning from each iteration. "
        "Thanks for watching."
    )
    time.sleep(2)

    print("\n" + "="*60)
    print("  SESSION COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_live_session()
