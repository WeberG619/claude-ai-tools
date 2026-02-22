// Deep search for Post/Submit button
(function() {
    var results = {};

    // Check shadow roots of all custom elements
    var customElements = document.querySelectorAll('*');
    var shadowButtons = [];
    for (var i = 0; i < customElements.length; i++) {
        var el = customElements[i];
        if (el.shadowRoot) {
            var btns = el.shadowRoot.querySelectorAll('button');
            for (var j = 0; j < btns.length; j++) {
                var text = btns[j].textContent.trim();
                if (text === 'Post' || text === 'Submit' || text === 'Publish') {
                    shadowButtons.push({
                        parentTag: el.tagName,
                        text: text,
                        disabled: btns[j].disabled,
                        type: btns[j].type
                    });
                }
            }
        }
    }
    results.shadowButtons = shadowButtons;

    // Check the Apply button
    var applyBtn = null;
    var buttons = document.querySelectorAll('button');
    for (var k = 0; k < buttons.length; k++) {
        if (buttons[k].textContent.trim() === 'Apply') {
            applyBtn = {
                text: 'Apply',
                class: buttons[k].className.substring(0, 80),
                parent: buttons[k].parentElement ? buttons[k].parentElement.tagName : '',
                grandparent: buttons[k].parentElement && buttons[k].parentElement.parentElement ? buttons[k].parentElement.parentElement.tagName : ''
            };
        }
    }
    results.applyButton = applyBtn;

    // Check form elements
    var forms = document.querySelectorAll('form');
    results.forms = [];
    forms.forEach(function(form, i) {
        var submitBtns = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        results.forms.push({
            action: form.action.substring(0, 80),
            submitCount: submitBtns.length,
            submitTexts: Array.from(submitBtns).map(function(b) { return b.textContent.trim().substring(0, 30); })
        });
    });

    // Look for faceplate-form or shreddit-form
    var formComp = document.querySelector('faceplate-form, shreddit-post-creation, [data-testid="post-creation-form"]');
    if (formComp) {
        results.formComp = formComp.tagName;
        if (formComp.shadowRoot) {
            var innerBtns = formComp.shadowRoot.querySelectorAll('button');
            results.formCompButtons = Array.from(innerBtns).map(function(b) { return b.textContent.trim().substring(0, 30); });
        }
    }

    // Check for "Save Draft" which we saw near Post
    var saveDraft = null;
    for (var m = 0; m < buttons.length; m++) {
        if (buttons[m].textContent.trim().includes('Save Draft') || buttons[m].textContent.trim().includes('Draft')) {
            saveDraft = {
                text: buttons[m].textContent.trim(),
                parent: buttons[m].parentElement ? buttons[m].parentElement.tagName + '.' + buttons[m].parentElement.className.substring(0, 40) : ''
            };
        }
    }
    results.saveDraft = saveDraft;

    return JSON.stringify(results, null, 2);
})();