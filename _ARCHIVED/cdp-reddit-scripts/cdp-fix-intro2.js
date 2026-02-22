// Fix: prepend intro via innerHTML manipulation
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return 'no body comp';
    var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
    if (!bodyDiv) return 'no editable';

    // Check current first element
    var firstEl = bodyDiv.querySelector(':scope > *');
    var firstText = firstEl ? firstEl.textContent.substring(0, 50) : 'none';

    // If intro already there, skip
    if (firstText.startsWith('I kept hitting')) return 'intro already present';

    // Prepend via innerHTML
    var intro = '<p class="first:mt-0 last:mb-0" dir="auto"><span>I kept hitting the same walls with Claude Code:</span></p>';
    bodyDiv.innerHTML = intro + bodyDiv.innerHTML;
    bodyDiv.dispatchEvent(new Event('input', { bubbles: true }));

    var newFirst = bodyDiv.querySelector(':scope > *');
    return 'done: ' + (newFirst ? newFirst.textContent.substring(0, 60) : 'empty');
})();