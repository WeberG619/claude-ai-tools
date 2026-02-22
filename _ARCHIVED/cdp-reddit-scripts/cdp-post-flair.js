// Find and interact with post flair (not user flair)
(function() {
    var results = {};

    // Look for r-post-flairs-modal or post flair picker
    var flairModal = document.querySelector('r-post-flairs-modal');
    results.modalExists = !!flairModal;

    // Find the "Add flair and tags" trigger
    var faceTrackers = document.querySelectorAll('faceplate-tracker');
    var flairTracker = null;
    faceTrackers.forEach(function(ft) {
        var text = ft.textContent.trim();
        if (text.includes('flair') && text.includes('tag')) {
            flairTracker = ft;
        }
    });

    if (flairTracker) {
        results.trackerFound = true;
        results.trackerText = flairTracker.textContent.trim().substring(0, 50);
        // Click it
        flairTracker.click();
        results.trackerClicked = true;
    }

    // Also look for any element with "Add flair" text that's clickable
    var allEls = document.querySelectorAll('button, a, [role="button"], [tabindex="0"], span, div');
    for (var i = 0; i < allEls.length; i++) {
        var text = allEls[i].textContent.trim();
        if (text.includes('Add flair and tags') && allEls[i] !== flairTracker) {
            results.altFound = {
                tag: allEls[i].tagName,
                text: text.substring(0, 60),
                class: (allEls[i].className || '').toString().substring(0, 60)
            };
            allEls[i].click();
            results.altClicked = true;
            break;
        }
    }

    return JSON.stringify(results, null, 2);
})();