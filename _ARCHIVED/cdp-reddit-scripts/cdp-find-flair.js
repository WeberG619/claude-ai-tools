// Find flair-related elements
(function() {
    var results = [];
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var text = el.textContent.trim();
        if (text.length < 50 && (text.toLowerCase().includes('flair') || text.toLowerCase().includes('tag'))) {
            if (el.offsetParent !== null || el.offsetHeight > 0) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 40),
                    class: (el.className || '').toString().substring(0, 50),
                    visible: true
                });
            }
        }
    }
    // Also check for the specific button
    var btn = document.querySelector('[data-testid*="flair"], [id*="flair"], faceplate-tracker[noun="flair"]');
    if (btn) results.push({special: true, tag: btn.tagName, text: btn.textContent.trim().substring(0, 40)});

    return JSON.stringify(results.slice(0, 10));
})();