// Scroll to Post button and click it
(function() {
    // Find ALL buttons, even those not in viewport
    var buttons = document.querySelectorAll('button');
    var postBtns = [];
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === 'Post') {
            postBtns.push(buttons[i]);
        }
    }

    if (postBtns.length === 0) {
        // Check for buttons with "Post" text in any form
        var allBtns = [];
        for (var j = 0; j < buttons.length; j++) {
            if (buttons[j].textContent.trim().length < 30) {
                allBtns.push(buttons[j].textContent.trim() + ' [' + buttons[j].tagName + ']');
            }
        }
        return JSON.stringify({error: 'no Post button found', buttons: allBtns.slice(0, 20)});
    }

    // Scroll to it and click
    var btn = postBtns[0];
    btn.scrollIntoView({behavior: 'instant', block: 'center'});

    // Small delay then click (return true to indicate we'll click)
    btn.click();

    return JSON.stringify({
        clicked: true,
        text: btn.textContent.trim(),
        disabled: btn.disabled,
        type: btn.type,
        count: postBtns.length
    });
})();