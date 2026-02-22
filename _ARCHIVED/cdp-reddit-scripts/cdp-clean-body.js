// Clean set Reddit body - replace everything with correct content once
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return 'no body comp';
    var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
    if (!bodyDiv) return 'no editable';

    bodyDiv.innerHTML = '<p class="first:mt-0 last:mb-0" dir="auto"><span>I kept hitting the same walls with Claude Code:</span></p>' +
        '<ul>' +
        '<li><span>It forgets everything between sessions</span></li>' +
        '<li><span>It can\'t touch desktop apps (Excel, Word, browser)</span></li>' +
        '<li><span>No way to enforce safety checks before destructive actions</span></li>' +
        '<li><span>Sub-agents start from zero context every time</span></li>' +
        '</ul>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>So I built </span><strong>Agent Forge</strong><span> - an open-source framework that plugs into Claude Code using only its native extension points (CLAUDE.md, MCP servers, hooks). No forks, no patches.</span></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><strong>What it actually does:</strong></p>' +
        '<ul>' +
        '<li><strong>Persistent memory via SQLite</strong><span> - corrections, decisions, and preferences survive across sessions</span></li>' +
        '<li><strong>17 specialized sub-agents</strong><span> (code review, architecture, security, DevOps, etc.)</span></li>' +
        '<li><strong>Desktop automation</strong><span> - Excel, Word, PowerPoint, browser control</span></li>' +
        '<li><strong>Common sense engine</strong><span> that checks actions against past mistakes before executing</span></li>' +
        '<li><strong>22 slash commands</strong><span> for real workflows</span></li>' +
        '</ul>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>The whole thing installs with </span><code><span class="code">git clone</span></code><span> + </span><code><span class="code">./install.sh</span></code><span> and works immediately.</span></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>I built this because I\'m a BIM automation specialist, not a software engineer. I needed AI agents that actually work in real professional workflows - not demos, not toys.</span></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>I want honest feedback. Tell me it\'s good or tell me it\'s garbage. My opinion doesn\'t count - I built it.</span></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>GitHub: </span><a href="https://github.com/WeberG619/agent-forge"><span>https://github.com/WeberG619/agent-forge</span></a></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>Full write-up: </span><a href="https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae"><span>https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae</span></a></p>' +
        '<p class="first:mt-0 last:mb-0" dir="auto"><span>Happy to answer any questions about the implementation.</span></p>';

    bodyDiv.dispatchEvent(new Event('input', { bubbles: true }));

    // Scroll to top
    var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
    if (titleComp) titleComp.scrollIntoView({block: 'start'});

    return JSON.stringify({childCount: bodyDiv.children.length, htmlLen: bodyDiv.innerHTML.length, firstText: bodyDiv.children[0].textContent.substring(0, 60)});
})();