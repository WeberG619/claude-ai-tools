// Probe Reddit web components shadow DOM
(function() {
    var results = {};

    // Title component
    var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
    if (titleComp) {
        results.titleFound = true;
        results.titleHasShadow = !!titleComp.shadowRoot;
        results.titleValue = titleComp.value || titleComp.getAttribute('value') || '';
        results.titleMethods = [];

        // Check if it has a value property
        var desc = Object.getOwnPropertyDescriptor(titleComp, 'value') ||
                   Object.getOwnPropertyDescriptor(Object.getPrototypeOf(titleComp), 'value');
        results.titleHasValueProp = !!desc;
        results.titleHasValueSetter = !!(desc && desc.set);

        // Look inside shadow root for textarea/input
        if (titleComp.shadowRoot) {
            var innerTextarea = titleComp.shadowRoot.querySelector('textarea');
            var innerInput = titleComp.shadowRoot.querySelector('input');
            results.shadowHasTextarea = !!innerTextarea;
            results.shadowHasInput = !!innerInput;
            if (innerTextarea) {
                results.shadowTextareaName = innerTextarea.name || '';
                results.shadowTextareaVisible = innerTextarea.offsetParent !== null;
                results.shadowTextareaHeight = innerTextarea.offsetHeight;
            }
            if (innerInput) {
                results.shadowInputName = innerInput.name || '';
            }
            // All shadow children
            results.shadowChildren = [];
            var kids = titleComp.shadowRoot.children;
            for (var i = 0; i < kids.length; i++) {
                results.shadowChildren.push({
                    tag: kids[i].tagName,
                    class: (kids[i].className || '').substring(0, 80)
                });
            }
        }
    } else {
        results.titleFound = false;
    }

    // Body component
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (bodyComp) {
        results.bodyFound = true;
        results.bodyHasShadow = !!bodyComp.shadowRoot;
        // The contenteditable div we found earlier
        var bodyEditable = bodyComp.querySelector('[contenteditable="true"]');
        results.bodyEditableFound = !!bodyEditable;
        if (bodyEditable) {
            results.bodyEditableHeight = bodyEditable.offsetHeight;
            results.bodyEditableVisible = bodyEditable.offsetParent !== null;
        }
    }

    return JSON.stringify(results, null, 2);
})();