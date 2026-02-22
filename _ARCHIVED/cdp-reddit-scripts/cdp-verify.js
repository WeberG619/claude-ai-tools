// Verify Reddit form content
(function() {
    var result = {};

    // Check title
    var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
    if (titleComp && titleComp.shadowRoot) {
        var textarea = titleComp.shadowRoot.querySelector('textarea');
        if (textarea) {
            result.titleValue = textarea.value;
        }
    }

    // Check body
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (bodyComp) {
        var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
        if (bodyDiv) {
            result.bodyText = bodyDiv.textContent.substring(0, 200);
            result.bodyHTML = bodyDiv.innerHTML.substring(0, 200);
            result.bodyLength = bodyDiv.innerHTML.length;
        }
    }

    // Check if Post button is enabled
    var postBtn = document.querySelector('button[type="submit"], [slot="submit-button"]');
    if (postBtn) {
        result.postBtnText = postBtn.textContent.trim();
        result.postBtnDisabled = postBtn.disabled;
    }

    // Scroll form into view
    if (titleComp) {
        titleComp.scrollIntoView({behavior: 'instant', block: 'start'});
    }

    return JSON.stringify(result, null, 2);
})();