// Probe Reddit post form elements
(function() {
    var results = {};
    results.url = location.href;

    // Check for textarea elements
    var textareas = document.querySelectorAll('textarea');
    results.textareas = [];
    textareas.forEach(function(ta) {
        results.textareas.push({
            name: ta.name || '',
            placeholder: ta.placeholder || '',
            tagName: ta.tagName
        });
    });

    // Check for input elements
    var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
    results.inputs = [];
    inputs.forEach(function(inp) {
        results.inputs.push({
            name: inp.name || '',
            placeholder: inp.placeholder || '',
            tagName: inp.tagName,
            type: inp.type || ''
        });
    });

    // Check for contenteditable
    var editables = document.querySelectorAll('[contenteditable="true"]');
    results.editables = [];
    editables.forEach(function(ed) {
        results.editables.push({
            tagName: ed.tagName,
            className: ed.className.substring(0, 100),
            placeholder: ed.getAttribute('data-placeholder') || '',
            role: ed.getAttribute('role') || ''
        });
    });

    // Check for any rich text editor containers
    results.hasDraftEditor = !!document.querySelector('.DraftEditor-root');
    results.hasRTE = !!document.querySelector('[data-rte]');
    results.hasProseMirror = !!document.querySelector('.ProseMirror');
    results.hasTipTap = !!document.querySelector('.tiptap');

    return JSON.stringify(results, null, 2);
})();