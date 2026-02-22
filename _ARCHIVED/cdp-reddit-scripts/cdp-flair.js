// Click "Add flair and tags" and check available flairs
(function() {
    // Find the flair button
    var flairBtn = null;
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].textContent.includes('flair') || buttons[i].textContent.includes('Flair')) {
            flairBtn = buttons[i];
            break;
        }
    }

    // Also check for the "Add flair and tags" element
    if (!flairBtn) {
        var allElements = document.querySelectorAll('[class*="flair"], [data-testid*="flair"], faceplate-tracker[action*="flair"]');
        if (allElements.length > 0) flairBtn = allElements[0];
    }

    if (!flairBtn) {
        // Try finding by text content
        var spans = document.querySelectorAll('span, div, button, a');
        for (var j = 0; j < spans.length; j++) {
            if (spans[j].textContent.trim() === 'Add flair and tags') {
                flairBtn = spans[j];
                break;
            }
        }
    }

    if (flairBtn) {
        flairBtn.click();
        return JSON.stringify({found: true, text: flairBtn.textContent.trim().substring(0, 50), tag: flairBtn.tagName});
    }

    return JSON.stringify({found: false});
})();