// Click the Post button
(function() {
    // Find Post button
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === 'Post') {
            buttons[i].click();
            return 'clicked Post button';
        }
    }
    // Try finding submit button
    var submit = document.querySelector('button[type="submit"]');
    if (submit) {
        submit.click();
        return 'clicked submit: ' + submit.textContent.trim();
    }
    return 'Post button not found';
})();