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
      // Page should still be on the avatar survey job
      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      // Check page for code field
      let r = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"]');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return { name: i.name, id: i.id, value: i.value };
          }));
        })()
      `);
      L("Text fields: " + r);

      // Enter code with comma
      r = await eval_(`
        (function() {
          var input = document.querySelector('input[name*="code"]');
          if (input) {
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, 'lsdfuj3847,');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return 'entered: ' + input.value;
          }
          return 'not found';
        })()
      `);
      L("Code with comma: " + r);

      // Make sure consent is checked
      r = await eval_(`
        (function() {
          var cb = document.querySelector('input[type="checkbox"]');
          if (cb) {
            if (!cb.checked) {
              cb.checked = true;
              cb.click();
            }
            return 'consent: ' + cb.checked;
          }
          return 'no checkbox';
        })()
      `);
      L("Consent: " + r);
      await sleep(300);

      // Submit
      r = await eval_(`
        (function() {
          var btn = document.querySelector('input[type="submit"][name="submit_job"]');
          if (btn) { btn.click(); return 'submitted'; }
          return 'no submit';
        })()
      `);
      L("Submit: " + r);
      await sleep(5000);

      // Check result
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Result: " + pageText.substring(0, 800));

      // Check balance
      r = await eval_(`
        (function() {
          var text = document.body.innerText;
          var match = text.match(/Account balance \\$ ([\\d.]+)/);
          return match ? match[1] : 'unknown';
        })()
      `);
      L("Balance: $" + r);

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
