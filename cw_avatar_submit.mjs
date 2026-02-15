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
      // Check the full HTML of the form/page for clues
      let r = await eval_(`
        (function() {
          var form = document.querySelector('form');
          if (form) {
            return form.innerHTML.substring(0, 3000);
          }
          return 'no form';
        })()
      `);
      L("FORM HTML: " + r);

      // Check if there's a hidden timer/countdown preventing submission
      r = await eval_(`
        (function() {
          var btn = document.getElementById('os');
          if (btn) {
            return 'disabled: ' + btn.disabled + ', text: ' + btn.textContent.trim() +
                   ', class: ' + btn.className + ', style: ' + btn.style.cssText;
          }
          return 'no btn';
        })()
      `);
      L("Button state: " + r);

      // Check for error messages
      r = await eval_(`
        (function() {
          var errors = document.querySelectorAll('.error, .alert, .warning, [class*="error"], [class*="alert"]');
          return Array.from(errors).map(function(e) { return e.textContent.trim().substring(0, 100); }).join(' | ');
        })()
      `);
      L("Errors: " + r);

      // Try: ensure radio is checked and submit form directly
      r = await eval_(`
        (function() {
          var radio = document.getElementById('v_228x1');
          radio.checked = true;

          var form = document.querySelector('form');
          if (form) {
            form.submit();
            return 'form submitted directly';
          }
          return 'no form';
        })()
      `);
      L("Direct submit: " + r);
      await sleep(5000);

      // Read result
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("PAGE TEXT AFTER SUBMIT:");
      L(pageText);

      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return {
              type: i.type || '', name: i.name || '', id: i.id || '',
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 80) : ''
            };
          }).slice(0, 40));
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
