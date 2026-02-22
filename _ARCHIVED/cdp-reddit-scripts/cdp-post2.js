// Find and click the correct Post button
(function() {
    var buttons = document.querySelectorAll('button');
    var candidates = [];
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        candidates.push({
            text: text.substring(0, 40),
            class: (buttons[i].className || '').substring(0, 60),
            visible: buttons[i].offsetParent !== null,
            type: buttons[i].type || '',
            height: buttons[i].offsetHeight,
            width: buttons[i].offsetWidth
        });
    }

    // Filter to just visible ones with "Post" text
    var postButtons = [];
    for (var j = 0; j < buttons.length; j++) {
        if (buttons[j].textContent.trim() === 'Post' && buttons[j].offsetParent !== null) {
            postButtons.push({
                index: j,
                text: buttons[j].textContent.trim(),
                class: buttons[j].className.substring(0, 80),
                parent: buttons[j].parentElement ? buttons[j].parentElement.className.substring(0, 60) : '',
                rect: buttons[j].getBoundingClientRect()
            });
        }
    }

    return JSON.stringify({totalButtons: buttons.length, postButtons: postButtons, allVisible: candidates.filter(function(c) { return c.visible && c.text.length < 20; })});
})();