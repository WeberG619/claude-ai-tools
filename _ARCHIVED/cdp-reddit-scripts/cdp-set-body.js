// Set Reddit body using execCommand (works with contenteditable)
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return JSON.stringify({error: "no body component"});

    var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
    if (!bodyDiv) return JSON.stringify({error: "no contenteditable"});

    // Focus and select all existing content
    bodyDiv.focus();

    // Clear existing content
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);

    // Build the HTML content
    var html = '<p>I kept hitting the same walls with Claude Code:</p>' +
        '<ul>' +
        '<li>It forgets everything between sessions</li>' +
        '<li>It can\'t touch desktop apps (Excel, Word, browser)</li>' +
        '<li>No way to enforce safety checks before destructive actions</li>' +
        '<li>Sub-agents start from zero context every time</li>' +
        '</ul>' +
        '<p>So I built <strong>Agent Forge</strong> - an open-source framework that plugs into Claude Code using only its native extension points (CLAUDE.md, MCP servers, hooks). No forks, no patches.</p>' +
        '<p><strong>What it actually does:</strong></p>' +
        '<ul>' +
        '<li><strong>Persistent memory via SQLite</strong> - corrections, decisions, and preferences survive across sessions</li>' +
        '<li><strong>17 specialized sub-agents</strong> (code review, architecture, security, DevOps, etc.)</li>' +
        '<li><strong>Desktop automation</strong> - Excel, Word, PowerPoint, browser control</li>' +
        '<li><strong>Common sense engine</strong> that checks actions against past mistakes before executing</li>' +
        '<li><strong>22 slash commands</strong> for real workflows</li>' +
        '</ul>' +
        '<p>The whole thing installs with <code>git clone</code> + <code>./install.sh</code> and works immediately.</p>' +
        '<p>I built this because I\'m a BIM automation specialist, not a software engineer. I needed AI agents that actually work in real professional workflows - not demos, not toys.</p>' +
        '<p>I want honest feedback. Tell me it\'s good or tell me it\'s garbage. My opinion doesn\'t count - I built it.</p>' +
        '<p>GitHub: <a href="https://github.com/WeberG619/agent-forge">https://github.com/WeberG619/agent-forge</a></p>' +
        '<p>Full write-up: <a href="https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae">https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae</a></p>' +
        '<p>Happy to answer any questions about the implementation.</p>';

    // Insert HTML using execCommand
    var success = document.execCommand('insertHTML', false, html);

    // Verify
    var finalText = bodyDiv.textContent.substring(0, 100);
    return JSON.stringify({execCommandResult: success, bodyPreview: finalText, bodyLen: bodyDiv.textContent.length});
})();