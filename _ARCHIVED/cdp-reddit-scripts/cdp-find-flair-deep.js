// Deep search for "Add flair" element
(function() {
    var results = [];

    // Search all elements including shadow DOMs
    function searchInNode(node, depth, path) {
        if (depth > 5) return;
        var children = node.children || node.childNodes;
        for (var i = 0; i < children.length; i++) {
            var el = children[i];
            if (el.nodeType !== 1) continue; // skip text nodes

            var text = '';
            // Get direct text content (not from children)
            for (var j = 0; j < el.childNodes.length; j++) {
                if (el.childNodes[j].nodeType === 3) {
                    text += el.childNodes[j].textContent;
                }
            }
            text = text.trim();

            if (text.toLowerCase().includes('flair') || text.toLowerCase().includes('add flair')) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 60),
                    class: (el.className || '').toString().substring(0, 40),
                    path: path + '>' + el.tagName,
                    hasRect: el.getBoundingClientRect().width > 0
                });
            }

            // Check shadow root
            if (el.shadowRoot) {
                searchInNode(el.shadowRoot, depth + 1, path + '>' + el.tagName + '#shadow');
            }

            searchInNode(el, depth + 1, path + '>' + el.tagName);
        }
    }

    searchInNode(document.body, 0, 'body');

    // Also find by querySelector looking for specific patterns
    var postFlairBtn = document.querySelector('#post-composer_flair-and-tags button, [id*="flair"] button');
    if (postFlairBtn) {
        results.push({special: true, tag: postFlairBtn.tagName, text: postFlairBtn.textContent.trim().substring(0, 60)});
    }

    // Check post-composer_flair-and-tags
    var flairSection = document.getElementById('post-composer_flair-and-tags');
    if (flairSection) {
        results.push({
            id: 'post-composer_flair-and-tags',
            tag: flairSection.tagName,
            text: flairSection.textContent.trim().substring(0, 100),
            visible: flairSection.offsetParent !== null,
            rect: {
                x: flairSection.getBoundingClientRect().x,
                y: flairSection.getBoundingClientRect().y,
                w: flairSection.getBoundingClientRect().width,
                h: flairSection.getBoundingClientRect().height
            }
        });
    }

    return JSON.stringify(results.slice(0, 15), null, 2);
})();