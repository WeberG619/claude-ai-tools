// Prepend the missing intro paragraph to the Reddit body
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return 'no body comp';

    var bodyDiv = bodyComp.querySelector('[contenteditable="true"][role="textbox"]');
    if (!bodyDiv) return 'no editable';

    // Create the intro paragraph
    var intro = document.createElement('p');
    intro.className = 'first:mt-0 last:mb-0';
    intro.setAttribute('dir', 'auto');
    intro.innerHTML = '<span>I kept hitting the same walls with Claude Code:</span>';

    // Insert before the first child
    bodyDiv.insertBefore(intro, bodyDiv.firstChild);

    // Dispatch input event
    bodyDiv.dispatchEvent(new Event('input', { bubbles: true }));

    return 'intro added, first child: ' + bodyDiv.firstChild.textContent.substring(0, 60);
})();