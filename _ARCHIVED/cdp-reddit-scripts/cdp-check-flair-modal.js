// Check what's in the flair modal
(function() {
    var modal = document.querySelector('r-post-flairs-modal');
    if (!modal) return 'no modal';

    var result = {
        hasShadow: !!modal.shadowRoot,
        isOpen: modal.hasAttribute('open'),
        visible: modal.offsetParent !== null || modal.offsetHeight > 0
    };

    // Check shadow root for flair options
    if (modal.shadowRoot) {
        var items = modal.shadowRoot.querySelectorAll('li, button, [role="option"], [role="radio"], label, faceplate-radio');
        result.itemCount = items.length;
        result.items = [];
        items.forEach(function(item, i) {
            if (i < 20) {
                result.items.push({
                    tag: item.tagName,
                    text: item.textContent.trim().substring(0, 60),
                    class: (item.className || '').toString().substring(0, 40)
                });
            }
        });

        // Also check for any visible content
        var allVisible = modal.shadowRoot.querySelectorAll('*');
        var visibleTexts = [];
        allVisible.forEach(function(el) {
            if (el.children.length === 0 && el.textContent.trim().length > 0 && el.textContent.trim().length < 50) {
                visibleTexts.push(el.textContent.trim());
            }
        });
        result.texts = visibleTexts.slice(0, 20);
    }

    // Check light DOM children
    var lightItems = modal.querySelectorAll('*');
    result.lightChildren = [];
    lightItems.forEach(function(item, i) {
        if (i < 10) {
            result.lightChildren.push({
                tag: item.tagName,
                text: item.textContent.trim().substring(0, 40)
            });
        }
    });

    return JSON.stringify(result, null, 2);
})();