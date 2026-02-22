// Deeper probe of Reddit contenteditable elements
(function() {
    var editables = document.querySelectorAll('[contenteditable="true"][role="textbox"]');
    var results = [];
    editables.forEach(function(ed, i) {
        var parent = ed.parentElement;
        var grandparent = parent ? parent.parentElement : null;
        var greatgp = grandparent ? grandparent.parentElement : null;

        // Look for nearby labels or headers
        var closestLabel = '';
        var node = ed;
        for (var j = 0; j < 5; j++) {
            node = node.parentElement;
            if (!node) break;
            var label = node.querySelector('label, h2, h3, [class*="title"], [class*="label"]');
            if (label) {
                closestLabel = label.textContent.trim().substring(0, 50);
                break;
            }
        }

        // Check for placeholder text via pseudo-elements or attributes
        var computedBefore = '';
        try {
            computedBefore = window.getComputedStyle(ed, '::before').content;
        } catch(e) {}

        results.push({
            index: i,
            className: ed.className.substring(0, 120),
            parentClass: parent ? parent.className.substring(0, 120) : '',
            grandparentTag: grandparent ? grandparent.tagName : '',
            currentText: ed.textContent.substring(0, 50),
            innerHTML: ed.innerHTML.substring(0, 100),
            closestLabel: closestLabel,
            pseudoBefore: computedBefore,
            offsetHeight: ed.offsetHeight,
            offsetWidth: ed.offsetWidth,
            isVisible: ed.offsetParent !== null
        });
    });
    return JSON.stringify(results, null, 2);
})();