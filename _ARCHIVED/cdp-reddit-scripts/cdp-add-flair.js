// Click "Add flair and tags" to open flair picker
(function() {
    var flairBtn = null;
    var allElements = document.querySelectorAll('button, span, div, a');
    for (var i = 0; i < allElements.length; i++) {
        var text = allElements[i].textContent.trim();
        if (text === 'Add flair and tags' || text === 'Add flair and tags*') {
            flairBtn = allElements[i];
            break;
        }
    }
    if (flairBtn) {
        flairBtn.click();
        return 'clicked: ' + flairBtn.tagName + ' - ' + flairBtn.textContent.trim();
    }
    return 'flair button not found';
})();