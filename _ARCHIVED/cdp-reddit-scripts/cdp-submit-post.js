// Click the Post button inside r-post-form-submit-button shadow DOM
(function() {
    var submitComp = document.querySelector('r-post-form-submit-button');
    if (!submitComp) return JSON.stringify({error: 'no submit component'});
    if (!submitComp.shadowRoot) return JSON.stringify({error: 'no shadow root'});

    var btn = submitComp.shadowRoot.querySelector('button');
    if (!btn) return JSON.stringify({error: 'no button in shadow'});

    // Scroll into view first
    submitComp.scrollIntoView({behavior: 'instant', block: 'center'});

    // Click it
    btn.click();

    return JSON.stringify({
        clicked: true,
        text: btn.textContent.trim(),
        disabled: btn.disabled
    });
})();