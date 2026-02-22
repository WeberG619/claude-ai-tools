// Use synthetic paste event with DataTransfer to set Reddit body
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return JSON.stringify({error: 'no body comp'});

    var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
    if (!bodyDiv) return JSON.stringify({error: 'no editable'});

    bodyDiv.focus();

    var htmlContent = '<p>I kept hitting the same walls with Claude Code:</p>' +
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

    var plainText = 'I kept hitting the same walls with Claude Code:\n\n' +
        '- It forgets everything between sessions\n' +
        '- It can\'t touch desktop apps (Excel, Word, browser)\n' +
        '- No way to enforce safety checks before destructive actions\n' +
        '- Sub-agents start from zero context every time\n\n' +
        'So I built Agent Forge - an open-source framework that plugs into Claude Code using only its native extension points (CLAUDE.md, MCP servers, hooks). No forks, no patches.\n\n' +
        'What it actually does:\n\n' +
        '- Persistent memory via SQLite - corrections, decisions, and preferences survive across sessions\n' +
        '- 17 specialized sub-agents (code review, architecture, security, DevOps, etc.)\n' +
        '- Desktop automation - Excel, Word, PowerPoint, browser control\n' +
        '- Common sense engine that checks actions against past mistakes before executing\n' +
        '- 22 slash commands for real workflows\n\n' +
        'The whole thing installs with git clone + ./install.sh and works immediately.\n\n' +
        'I built this because I\'m a BIM automation specialist, not a software engineer. I needed AI agents that actually work in real professional workflows - not demos, not toys.\n\n' +
        'I want honest feedback. Tell me it\'s good or tell me it\'s garbage. My opinion doesn\'t count - I built it.\n\n' +
        'GitHub: https://github.com/WeberG619/agent-forge\n\n' +
        'Full write-up: https://dev.to/weberg619/i-built-a-production-agent-framework-for-claude-code-17-sub-agents-persistent-memory-and-3nae\n\n' +
        'Happy to answer any questions about the implementation.';

    // Method 1: Try DataTransfer paste event
    try {
        var dt = new DataTransfer();
        dt.setData('text/html', htmlContent);
        dt.setData('text/plain', plainText);

        var pasteEvent = new ClipboardEvent('paste', {
            bubbles: true,
            cancelable: true,
            clipboardData: dt
        });

        bodyDiv.dispatchEvent(pasteEvent);
    } catch(e) {
        // If ClipboardEvent fails, try InputEvent
    }

    // Check if it worked
    var result1 = bodyDiv.textContent.length;

    // Method 2: If paste didn't work, try InputEvent with insertFromPaste
    if (result1 === 0) {
        try {
            var dt2 = new DataTransfer();
            dt2.setData('text/html', htmlContent);
            dt2.setData('text/plain', plainText);

            var inputEvent = new InputEvent('beforeinput', {
                inputType: 'insertFromPaste',
                data: null,
                dataTransfer: dt2,
                bubbles: true,
                cancelable: true,
                composed: true
            });

            bodyDiv.dispatchEvent(inputEvent);
        } catch(e2) {}
    }

    var result2 = bodyDiv.textContent.length;

    // Method 3: Try setting via the shreddit-composer component API
    if (result2 === 0) {
        // Check if the component has a value property or setter
        var props = [];
        for (var p in bodyComp) {
            if (typeof bodyComp[p] === 'function' && (p.includes('set') || p.includes('value') || p.includes('content') || p.includes('text'))) {
                props.push(p);
            }
        }
        // Also check attributes
        var attrs = [];
        for (var i = 0; i < bodyComp.attributes.length; i++) {
            attrs.push(bodyComp.attributes[i].name);
        }

        return JSON.stringify({
            method1_len: result1,
            method2_len: result2,
            componentMethods: props,
            componentAttrs: attrs
        });
    }

    return JSON.stringify({
        method1_len: result1,
        method2_len: result2,
        success: true
    });
})();