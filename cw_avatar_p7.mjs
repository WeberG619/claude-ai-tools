import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    (async () => {
      // Enter age: 51 (born 1974, now 2026)
      let r = await eval_(`
        (function() {
          var input = document.getElementById('v_63');
          if (input) {
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, '51');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return 'age: ' + input.value;
          }
          return 'not found';
        })()
      `);
      L("Age: " + r);

      // Select Male
      r = await eval_(`
        (function() {
          var radio = document.getElementById('v_64x1');
          if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change', { bubbles: true })); return 'Male selected'; }
          return 'not found';
        })()
      `);
      L("Gender: " + r);

      // AI experience: 5 out of 7 (relatively experienced)
      r = await eval_(`
        (function() {
          var radio = document.getElementById('v_65x5');
          if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change', { bubbles: true })); return 'AI experience: 5'; }
          return 'not found';
        })()
      `);
      L("AI exp: " + r);
      await sleep(500);

      // Submit
      r = await eval_(`
        (function() {
          var form = document.querySelector('form');
          if (form) { form.submit(); return 'submitted'; }
          return 'no form';
        })()
      `);
      L("Submit: " + r);
      await sleep(5000);

      // Read next page - hopefully the code!
      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("PAGE TEXT:");
      L(pageText);

      // Check for code
      let codeMatch = pageText.match(/(?:code|Code|CODE)[:\s]+([A-Za-z0-9]+)/);
      if (codeMatch) {
        L("*** FOUND CODE: " + codeMatch[1] + " ***");
      }

      // Also look for any code-like string
      let allCodes = pageText.match(/\b[A-Z0-9]{6,10}\b/g);
      if (allCodes) {
        L("Potential codes: " + allCodes.join(', '));
      }

      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return {
              type: i.type || '', name: i.name || '', id: i.id || '',
              value: (i.value || '').substring(0, 80),
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 120) : ''
            };
          }).slice(0, 30));
        })()
      `);
      L("FORM: " + formJson);

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
