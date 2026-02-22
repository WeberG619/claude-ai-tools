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
      // Clear the search box first
      await eval_(`
        (function() {
          var input = document.querySelector('input[name="qualification-search"]');
          if (input) {
            var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(input, '');
            input.dispatchEvent(new Event('input', { bubbles: true }));
          }
        })()
      `);
      await sleep(1000);

      // Find all checkbox labels and their associated text to map checkbox -> option
      L("=== MAPPING CHECKBOXES TO OPTIONS ===");
      let mapping = await eval_(`
        (function() {
          var checkboxes = document.querySelectorAll('input[type="checkbox"][name^="answers"]');
          var results = [];
          checkboxes.forEach(function(cb, i) {
            // The label wraps the checkbox, so find the label text
            var label = cb.closest('label');
            var text = '';
            if (label) {
              // Get the text content excluding the checkbox itself
              var divs = label.querySelectorAll('div');
              divs.forEach(function(d) {
                var t = d.textContent.trim();
                if (t.length > 1 && t.length < 80 && !t.includes('\\n')) text = t;
              });
            }
            if (!text) text = 'checkbox_' + i;
            results.push({ index: i, value: cb.value.substring(0, 20), text: text, checked: cb.checked });
          });
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      L(mapping);

      // Find Architecture checkbox and click it using .click() on the input directly
      L("\n=== CHECKING ARCHITECTURE CHECKBOX ===");
      let checkResult = await eval_(`
        (function() {
          var checkboxes = document.querySelectorAll('input[type="checkbox"][name^="answers"]');
          for (var i = 0; i < checkboxes.length; i++) {
            var label = checkboxes[i].closest('label');
            if (label && label.textContent.trim().includes('Architecture') && !label.textContent.trim().includes('/')) {
              // Found Architecture checkbox - try .click()
              checkboxes[i].click();
              return 'clicked checkbox ' + i + ' checked=' + checkboxes[i].checked + ' value=' + checkboxes[i].value.substring(0, 20);
            }
          }
          // Try finding by text match on innerText
          for (var i = 0; i < checkboxes.length; i++) {
            var parent = checkboxes[i].parentElement;
            while (parent && parent !== document.body) {
              if (parent.textContent.trim() === 'Architecture') {
                checkboxes[i].click();
                return 'clicked by parent text ' + i + ' checked=' + checkboxes[i].checked;
              }
              parent = parent.parentElement;
            }
          }
          return 'Architecture checkbox not found';
        })()
      `);
      L("Check result: " + checkResult);
      await sleep(1500);

      // Verify checkbox state
      let verified = await eval_(`
        (function() {
          var checked = [];
          document.querySelectorAll('input[type="checkbox"]:checked').forEach(function(cb) {
            var label = cb.closest('label');
            checked.push(label ? label.textContent.trim().substring(0, 40) : cb.value);
          });
          return JSON.stringify(checked);
        })()
      `);
      L("Checked boxes: " + verified);

      // Check Continue button state
      let btnState = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              return 'disabled=' + btns[i].disabled + ' aria-disabled=' + btns[i].getAttribute('aria-disabled') + ' classes=' + btns[i].className.substring(0, 100);
            }
          }
          return 'no Continue btn';
        })()
      `);
      L("Continue button: " + btnState);

      // If checkbox didn't work via .click(), try setting checked property directly + dispatch change
      if (verified === '[]') {
        L("\nCheckbox not checked, trying direct property set...");
        await eval_(`
          (function() {
            var checkboxes = document.querySelectorAll('input[type="checkbox"][name^="answers"]');
            for (var i = 0; i < checkboxes.length; i++) {
              var label = checkboxes[i].closest('label');
              if (label && label.textContent.includes('Architecture') && label.textContent.trim().length < 20) {
                // Set checked directly
                var nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked').set;
                nativeSetter.call(checkboxes[i], true);
                checkboxes[i].dispatchEvent(new Event('change', { bubbles: true }));
                checkboxes[i].dispatchEvent(new Event('input', { bubbles: true }));
                // Also try React's synthetic event
                checkboxes[i].dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return 'set checked=true and dispatched';
              }
            }
            return 'not found';
          })()
        `);
        await sleep(1500);

        verified = await eval_(`
          (function() {
            var checked = [];
            document.querySelectorAll('input[type="checkbox"]:checked').forEach(function(cb) {
              var label = cb.closest('label');
              checked.push(label ? label.textContent.trim().substring(0, 40) : cb.value);
            });
            return JSON.stringify(checked);
          })()
        `);
        L("After direct set - checked: " + verified);
      }

      // Click Continue
      L("\n=== CLICKING CONTINUE ===");
      await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              btns[i].disabled = false;
              btns[i].removeAttribute('aria-disabled');
              btns[i].click();
              return 'forced click';
            }
          }
        })()
      `);
      await sleep(4000);

      // Check what page we're on
      let finalPage = await eval_(`document.body.innerText.substring(0, 2000)`);
      let finalUrl = await eval_(`window.location.href`);
      L("\nURL: " + finalUrl);
      L("Page:\n" + finalPage.substring(0, 1500));

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
