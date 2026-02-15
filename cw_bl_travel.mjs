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

    const cdpClick = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(100);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Type answer into the text field
      L("=== ANSWERING TRAVEL QUESTION ===");
      let answer = "I would love to visit Italy, especially Rome and Florence. I would explore the ancient architecture including the Colosseum and the Pantheon, visit the Vatican, and enjoy authentic Italian cuisine. As someone who works in architecture, seeing these historic buildings in person would be incredibly inspiring.";

      // Find the text input/textarea
      let inputInfo = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('textarea, input[type="text"], input:not([type]), [contenteditable="true"]');
          var results = [];
          inputs.forEach(function(inp) {
            var rect = inp.getBoundingClientRect();
            results.push({
              tag: inp.tagName,
              type: inp.type || '',
              name: inp.name || '',
              placeholder: inp.placeholder || '',
              classes: (inp.className || '').substring(0, 80),
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2)
            });
          });
          return JSON.stringify(results);
        })()
      `);
      L("Inputs: " + inputInfo);

      // Set value in the input
      let setResult = await eval_(`
        (function() {
          var answer = ${JSON.stringify(answer)};
          // Try textarea first
          var textarea = document.querySelector('textarea');
          if (textarea) {
            var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
            setter.call(textarea, answer);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            return 'textarea set: ' + textarea.value.substring(0, 50);
          }
          // Try text input
          var input = document.querySelector('input[type="text"], input:not([type="checkbox"]):not([type="radio"]):not([type="search"]):not([type="hidden"])');
          if (input) {
            var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(input, answer);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return 'input set: ' + input.value.substring(0, 50);
          }
          return 'no input found';
        })()
      `);
      L("Set result: " + setResult);
      await sleep(1500);

      // Click Continue
      let contPos = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              btns[i].scrollIntoView({ block: 'center' });
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled });
            }
          }
          return 'none';
        })()
      `);
      L("Continue: " + contPos);
      if (contPos !== 'none') {
        let cp = JSON.parse(contPos);
        await cdpClick(cp.x, cp.y);
        await sleep(5000);
      }

      // Check result - should redirect to actual survey
      let newUrl = await eval_(`window.location.href`);
      let newPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nAfter qualification URL: " + newUrl);
      L("Page:\n" + newPage.substring(0, 2000));

      // Check all targets for survey redirect
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 200)));

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
