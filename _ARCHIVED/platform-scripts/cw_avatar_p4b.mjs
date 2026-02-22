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
      // Check current state
      let r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[name="v_228"]');
          return JSON.stringify(Array.from(radios).map(function(r) {
            return { id: r.id, value: r.value, checked: r.checked };
          }));
        })()
      `);
      L("Radios state: " + r);

      // Click the label for the radio instead
      r = await eval_(`
        (function() {
          var radio = document.getElementById('v_228x1');
          if (radio) {
            // Check the radio
            radio.checked = true;
            // Fire all events
            radio.dispatchEvent(new Event('change', { bubbles: true }));
            radio.dispatchEvent(new Event('input', { bubbles: true }));
            radio.dispatchEvent(new MouseEvent('click', { bubbles: true }));

            // Also try clicking the label
            var label = radio.labels && radio.labels[0];
            if (label) label.click();

            return 'checked: ' + radio.checked + ', value: ' + radio.value;
          }
          return 'not found';
        })()
      `);
      L("Radio click: " + r);
      await sleep(1000);

      // Check if checked now
      r = await eval_(`
        (function() {
          var radio = document.getElementById('v_228x1');
          return radio ? 'checked: ' + radio.checked : 'not found';
        })()
      `);
      L("Check state: " + r);

      // Try submitting the form directly
      r = await eval_(`
        (function() {
          var form = document.querySelector('form');
          if (form) {
            return 'form action: ' + form.action + ', method: ' + form.method;
          }
          return 'no form';
        })()
      `);
      L("Form: " + r);

      // Click Continue button
      r = await eval_(`
        (function() {
          var btn = document.getElementById('os');
          if (btn) {
            btn.click();
            return 'clicked, type: ' + btn.type + ', tag: ' + btn.tagName;
          }
          var submit = document.querySelector('button[type="submit"], input[type="submit"]');
          if (submit) {
            submit.click();
            return 'clicked alt: ' + submit.tagName;
          }
          return 'no button';
        })()
      `);
      L("Submit: " + r);
      await sleep(4000);

      // Read next page
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("PAGE TEXT:");
      L(pageText);

      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return {
              tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '',
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
