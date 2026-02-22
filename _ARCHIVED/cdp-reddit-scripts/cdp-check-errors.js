// Check for error messages and validation issues
(function() {
    var results = {};

    // Look for error messages
    var errors = document.querySelectorAll('[class*="error"], [class*="Error"], [data-testid*="error"], [role="alert"]');
    results.errorElements = [];
    errors.forEach(function(el) {
        if (el.textContent.trim().length > 0 && el.textContent.trim().length < 200) {
            results.errorElements.push({
                tag: el.tagName,
                text: el.textContent.trim(),
                visible: el.offsetParent !== null
            });
        }
    });

    // Check for validation messages in shadow roots
    var customEls = document.querySelectorAll('*');
    var validationMsgs = [];
    for (var i = 0; i < customEls.length; i++) {
        if (customEls[i].shadowRoot) {
            var alerts = customEls[i].shadowRoot.querySelectorAll('[role="alert"], [class*="error"], [class*="helper"]');
            alerts.forEach(function(a) {
                if (a.textContent.trim().length > 0) {
                    validationMsgs.push({
                        parent: customEls[i].tagName,
                        text: a.textContent.trim().substring(0, 100)
                    });
                }
            });
        }
    }
    results.validationMsgs = validationMsgs;

    // Check for toast/snackbar messages
    var toasts = document.querySelectorAll('[class*="toast"], [class*="snackbar"], [class*="notification"], faceplate-toast');
    results.toasts = [];
    toasts.forEach(function(t) {
        results.toasts.push({tag: t.tagName, text: t.textContent.trim().substring(0, 100)});
    });

    // Check flair status
    var flairText = '';
    var flairElements = document.querySelectorAll('[class*="flair"], [data-testid*="flair"]');
    flairElements.forEach(function(f) {
        if (f.textContent.trim().length > 0 && f.textContent.trim().length < 100) {
            flairText += f.textContent.trim() + ' | ';
        }
    });
    results.flairText = flairText;

    // Check for any modal/dialog that might have appeared
    var modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"]');
    results.modals = [];
    modals.forEach(function(m) {
        if (m.offsetParent !== null || m.offsetHeight > 0) {
            results.modals.push({
                tag: m.tagName,
                text: m.textContent.trim().substring(0, 200)
            });
        }
    });

    return JSON.stringify(results, null, 2);
})();