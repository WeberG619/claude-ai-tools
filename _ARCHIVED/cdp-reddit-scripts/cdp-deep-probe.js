// Deep probe shreddit-composer shadow DOM
(function() {
    var bodyComp = document.querySelector('shreddit-composer[name="body"]');
    if (!bodyComp) return JSON.stringify({error: 'no body comp'});

    var result = {};
    result.hasShadow = !!bodyComp.shadowRoot;

    if (bodyComp.shadowRoot) {
        var shadowChildren = [];
        var walk = function(node, depth) {
            if (depth > 4) return;
            for (var i = 0; i < node.children.length; i++) {
                var child = node.children[i];
                var info = {
                    tag: child.tagName,
                    class: (child.className || '').toString().substring(0, 60),
                    role: child.getAttribute('role') || '',
                    ce: child.contentEditable,
                    visible: child.offsetParent !== null,
                    depth: depth
                };
                if (child.shadowRoot) info.hasShadow = true;
                shadowChildren.push(info);
                walk(child, depth + 1);
            }
        };
        walk(bodyComp.shadowRoot, 0);
        result.shadowTree = shadowChildren;
    }

    // Also check light DOM children
    var lightChildren = [];
    var walkLight = function(node, depth) {
        if (depth > 3) return;
        for (var i = 0; i < node.children.length; i++) {
            var child = node.children[i];
            lightChildren.push({
                tag: child.tagName,
                class: (child.className || '').toString().substring(0, 60),
                role: child.getAttribute('role') || '',
                ce: child.contentEditable,
                visible: child.offsetParent !== null,
                depth: depth
            });
            walkLight(child, depth + 1);
        }
    };
    walkLight(bodyComp, 0);
    result.lightTree = lightChildren;

    return JSON.stringify(result, null, 2);
})();