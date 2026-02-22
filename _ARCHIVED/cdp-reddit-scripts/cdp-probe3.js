// Find the Reddit title input
(function() {
    var results = {};

    // Check shadow DOM - Reddit uses web components
    var shredditPost = document.querySelector('shreddit-post-creation, shreddit-composer, faceplate-form');
    results.hasShreddit = !!shredditPost;

    // Check all fieldsets
    var fieldsets = document.querySelectorAll('fieldset');
    results.fieldsets = [];
    fieldsets.forEach(function(fs, i) {
        var legend = fs.querySelector('legend');
        results.fieldsets.push({
            index: i,
            legendText: legend ? legend.textContent.trim().substring(0, 50) : '',
            className: fs.className.substring(0, 100),
            isVisible: fs.offsetParent !== null,
            height: fs.offsetHeight,
            innerHTML: fs.innerHTML.substring(0, 200)
        });
    });

    // Look for any element with "title" in placeholder, aria-label, or name
    var allInputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    results.titleRelated = [];
    allInputs.forEach(function(el) {
        var ph = el.placeholder || el.getAttribute('aria-label') || el.getAttribute('data-placeholder') || '';
        var name = el.name || '';
        if (ph.toLowerCase().includes('title') || name.toLowerCase().includes('title')) {
            results.titleRelated.push({
                tag: el.tagName,
                type: el.type || '',
                placeholder: ph,
                name: name,
                isVisible: el.offsetParent !== null
            });
        }
    });

    // Check for the actual visible title area
    var titleArea = document.querySelector('[slot="title"]');
    results.hasTitleSlot = !!titleArea;
    if (titleArea) {
        results.titleSlotTag = titleArea.tagName;
        results.titleSlotContent = titleArea.innerHTML.substring(0, 200);
    }

    // Look at visible form structure
    var form = document.querySelector('form');
    if (form) {
        results.formAction = form.action || '';
        var visibleChildren = [];
        for (var i = 0; i < form.children.length; i++) {
            var child = form.children[i];
            if (child.offsetParent !== null) {
                visibleChildren.push({
                    tag: child.tagName,
                    class: child.className.substring(0, 80)
                });
            }
        }
        results.visibleFormChildren = visibleChildren;
    }

    // Try to find title through the page structure
    var h = document.querySelector('h2');
    results.h2text = h ? h.textContent.trim() : '';

    // Try looking for title in the first visible fieldset
    var visibleFieldsets = Array.from(fieldsets).filter(function(f) { return f.offsetParent !== null; });
    results.visibleFieldsetCount = visibleFieldsets.length;
    if (visibleFieldsets.length > 0) {
        var first = visibleFieldsets[0];
        var innerInputs = first.querySelectorAll('input, textarea, [contenteditable="true"]');
        results.firstVisibleFieldsetInputs = [];
        innerInputs.forEach(function(inp) {
            results.firstVisibleFieldsetInputs.push({
                tag: inp.tagName,
                type: inp.type || '',
                placeholder: inp.placeholder || inp.getAttribute('aria-label') || '',
                isVisible: inp.offsetParent !== null,
                contentEditable: inp.contentEditable,
                height: inp.offsetHeight
            });
        });
    }

    return JSON.stringify(results, null, 2);
})();