// Open flair modal and list available flairs
(function() {
    // Find the flair modal component
    var flairModal = document.querySelector('r-post-flairs-modal');
    if (flairModal) {
        // Try to open it
        flairModal.setAttribute('open', '');
        // Also try clicking nearby trigger
    }

    // Find the "Add flair and tags" clickable area
    var tracker = document.querySelector('faceplate-tracker[noun="flair_and_tags"]') ||
                  document.querySelector('[id*="flair"]') ||
                  document.querySelector('button[id*="flair"]');

    // Try to find by scrolling through all clickable elements near "Add flair"
    var clickables = document.querySelectorAll('button, a, [role="button"], [tabindex]');
    for (var i = 0; i < clickables.length; i++) {
        var text = clickables[i].textContent.trim();
        if (text.includes('Add flair') || text.includes('flair and tag')) {
            clickables[i].click();
            return 'clicked: ' + clickables[i].tagName + ' | ' + text.substring(0, 50);
        }
    }

    // Try opening the modal directly
    if (flairModal) {
        try {
            flairModal.open = true;
            return 'set modal open=true';
        } catch(e) {}
    }

    return 'nothing found to click';
})();