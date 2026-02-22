// Fill Reddit post form - using shadow DOM for title
(function() {
    var result = {title: false, body: false};

    // SET TITLE - access textarea inside shadow root
    var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
    if (titleComp && titleComp.shadowRoot) {
        var textarea = titleComp.shadowRoot.querySelector('textarea');
        if (textarea) {
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeSetter.call(textarea, "I gave Claude Code persistent memory, 17 sub-agents, and desktop automation - here's how");
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            result.title = true;
        }
    }

    // SET BODY - find the visible contenteditable div inside shreddit-composer
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (bodyComp) {
        var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
        if (bodyDiv) {
            bodyDiv.focus();
            bodyDiv.innerHTML = '<p>I kept hitting the same walls with Claude Code:</p>' +
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
            bodyDiv.dispatchEvent(new Event('input', { bubbles: true }));
            result.body = true;
        }
    }

    return JSON.stringify(result);
})();