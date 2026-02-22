// Properly verify Reddit form content
(function() {
    var result = {};

    // Title
    var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
    if (titleComp && titleComp.shadowRoot) {
        var textarea = titleComp.shadowRoot.querySelector('textarea');
        result.title = textarea ? textarea.value : 'not found';
    }

    // Body - check the contenteditable div directly
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (bodyComp) {
        var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
        if (bodyDiv) {
            result.bodyInnerText = bodyDiv.innerText.substring(0, 300);
            result.bodyChildCount = bodyDiv.children.length;
            result.firstChildTag = bodyDiv.children[0] ? bodyDiv.children[0].tagName : 'none';
            result.firstChildText = bodyDiv.children[0] ? bodyDiv.children[0].textContent.substring(0, 100) : 'none';
            result.htmlLength = bodyDiv.innerHTML.length;
        }
    }

    // Scroll to show the title
    if (titleComp) titleComp.scrollIntoView({block: 'start'});

    return JSON.stringify(result, null, 2);
})();