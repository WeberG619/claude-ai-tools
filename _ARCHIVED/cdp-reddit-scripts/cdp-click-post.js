// Find and click the correct Post button on Reddit submit page
(function() {
    // Look for visible buttons with "Post" text
    var buttons = document.querySelectorAll('button');
    var found = [];
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === 'Post' && buttons[i].offsetParent !== null) {
            found.push({
                index: i,
                text: text,
                disabled: buttons[i].disabled,
                type: buttons[i].type || 'none',
                rect: {
                    x: buttons[i].getBoundingClientRect().x,
                    y: buttons[i].getBoundingClientRect().y,
                    w: buttons[i].getBoundingClientRect().width,
                    h: buttons[i].getBoundingClientRect().height
                }
            });
        }
    }

    // Also check for flair requirement
    var flairRequired = false;
    var allText = document.body.innerText;
    if (allText.includes('Add flair and tags*') || allText.includes('flair is required')) {
        flairRequired = true;
    }

    if (found.length > 0) {
        // Click the first visible Post button
        buttons[found[0].index].click();
        return JSON.stringify({clicked: true, button: found[0], flairRequired: flairRequired, totalFound: found.length});
    }

    // List all visible buttons for debugging
    var allButtons = [];
    for (var j = 0; j < buttons.length; j++) {
        if (buttons[j].offsetParent !== null && buttons[j].textContent.trim().length > 0 && buttons[j].textContent.trim().length < 30) {
            allButtons.push(buttons[j].textContent.trim());
        }
    }

    return JSON.stringify({clicked: false, flairRequired: flairRequired, visibleButtons: allButtons});
})();