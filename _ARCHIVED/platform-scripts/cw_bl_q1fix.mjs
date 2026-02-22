import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const blTarget = tabs.find(t => t.url.includes('bitlabs'));
  if (!blTarget) { L("No BitLabs target"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blTarget.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      // First, understand the DOM structure of the options
      L("=== ANALYZING OPTION DOM STRUCTURE ===");
      let structure = await eval_(`
        (function() {
          // Find the "Architecture" text and trace its DOM tree
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim() === 'Architecture') {
              var el = node.parentElement;
              var chain = [];
              for (var i = 0; i < 8; i++) {
                if (!el) break;
                chain.push({
                  tag: el.tagName,
                  classes: (el.className || '').substring(0, 100),
                  id: el.id || '',
                  role: el.getAttribute('role') || '',
                  onclick: el.onclick ? 'yes' : 'no',
                  tabindex: el.getAttribute('tabindex') || '',
                  childCount: el.children.length
                });
                el = el.parentElement;
              }
              return JSON.stringify(chain);
            }
          }
          return 'Architecture text not found';
        })()
      `);
      L("DOM chain from Architecture text:");
      try {
        let chain = JSON.parse(structure);
        chain.forEach((c, i) => L("  " + i + ": <" + c.tag + "> classes=" + c.classes + " role=" + c.role + " onclick=" + c.onclick + " tabindex=" + c.tabindex));
      } catch(e) { L(structure); }

      // Also check for inputs/checkboxes/radios
      let inputs = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input, [type="checkbox"], [type="radio"], [role="checkbox"], [role="radio"], [role="option"], [role="listbox"]').forEach(function(el) {
            results.push({
              tag: el.tagName,
              type: el.type || '',
              role: el.getAttribute('role') || '',
              name: el.name || '',
              value: (el.value || '').substring(0, 50),
              checked: el.checked || false,
              classes: (el.className || '').substring(0, 60)
            });
          });
          return JSON.stringify(results.slice(0, 20));
        })()
      `);
      L("\nInputs/controls: " + inputs);

      // Try clicking Architecture using different strategies
      L("\n=== CLICKING ARCHITECTURE ===");

      // Strategy 1: Find the option container and dispatch proper events
      let clickResult = await eval_(`
        (function() {
          // Find Architecture text node
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim() === 'Architecture') {
              var el = node.parentElement;
              // Try clicking each parent up the chain
              for (var i = 0; i < 6; i++) {
                if (!el) break;
                // Dispatch full click event sequence
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));

                // Check if it has role or tabindex (likely interactive)
                if (el.getAttribute('role') || el.getAttribute('tabindex') || el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'LABEL') {
                  return 'dispatched events on: <' + el.tagName + '> classes=' + (el.className||'').substring(0,60) + ' role=' + (el.getAttribute('role')||'');
                }
                el = el.parentElement;
              }
              return 'dispatched on all parents but none had role/tabindex';
            }
          }
          return 'Architecture not found';
        })()
      `);
      L("Click result: " + clickResult);
      await sleep(2000);

      // Check if anything changed
      let afterClick = await eval_(`
        (function() {
          // Check for any selected/checked state
          var selected = document.querySelectorAll('[aria-selected="true"], [aria-checked="true"], .selected, [class*="selected"], [class*="active"], [class*="checked"], input:checked');
          var results = [];
          selected.forEach(function(el) {
            results.push(el.tagName + ': ' + el.textContent.trim().substring(0, 50) + ' classes=' + (el.className||'').substring(0,60));
          });
          // Also check the page state
          var questionText = '';
          var qEl = document.querySelector('[class*="question"], h1, h2, h3');
          if (qEl) questionText = qEl.textContent.trim().substring(0, 100);
          return JSON.stringify({ selected: results, question: questionText });
        })()
      `);
      L("After click state: " + afterClick);

      // Strategy 2: If still on Q1, try using the search box
      let stillQ1 = await eval_(`document.body.innerText.includes('Question 1/4')`);
      if (stillQ1) {
        L("\nStill on Q1, trying search box approach...");
        let searchResult = await eval_(`
          (function() {
            // Find search/input box
            var inputs = document.querySelectorAll('input[type="text"], input[type="search"], input:not([type]), [contenteditable]');
            if (inputs.length === 0) return 'no search box found';
            var input = inputs[0];
            // Type "Architecture" in the search
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(input, 'Architecture');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return 'typed in search: ' + input.tagName + ' type=' + (input.type||'') + ' classes=' + (input.className||'').substring(0,60);
          })()
        `);
        L("Search: " + searchResult);
        await sleep(2000);

        // Now click the filtered Architecture option
        let filteredClick = await eval_(`
          (function() {
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while (node = walker.nextNode()) {
              if (node.textContent.trim() === 'Architecture') {
                var el = node.parentElement;
                // Go up to find clickable container
                for (var i = 0; i < 6; i++) {
                  if (!el) break;
                  el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
                  el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
                  el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                  el = el.parentElement;
                }
                return 'clicked Architecture parents';
              }
            }
            return 'Architecture not visible after filter';
          })()
        `);
        L("Filtered click: " + filteredClick);
        await sleep(2000);
      }

      // Check state and try Continue button
      let currentState = await eval_(`document.body.innerText.substring(0, 500)`);
      L("\nCurrent page: " + currentState.substring(0, 300));

      // Try clicking Continue
      let contResult = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              // Check if button is disabled
              var disabled = btns[i].disabled || btns[i].getAttribute('aria-disabled') === 'true' || btns[i].classList.contains('disabled');
              btns[i].click();
              return 'clicked Continue (disabled=' + disabled + ') classes=' + (btns[i].className||'').substring(0,80);
            }
          }
          return 'no Continue button';
        })()
      `);
      L("Continue: " + contResult);
      await sleep(3000);

      // Final check
      let finalPage = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nFinal page:\n" + finalPage.substring(0, 1000));

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => {
      L("Error: " + e.message);
      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    });
  });
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
