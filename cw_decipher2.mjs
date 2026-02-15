import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 20000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes('decipherinc'));
  if (!tab) { L("No decipher tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      // Debug: examine radio structure
      let radioDebug = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input[type="radio"]').forEach(function(el) {
            var rect = el.getBoundingClientRect();
            results.push({
              id: el.id || 'NO_ID',
              name: el.name,
              value: el.value,
              checked: el.checked,
              visible: rect.width > 0,
              x: Math.round(rect.x), y: Math.round(rect.y),
              w: Math.round(rect.width), h: Math.round(rect.height),
              parentTag: el.parentElement ? el.parentElement.tagName : 'none',
              parentClass: el.parentElement ? (el.parentElement.className || '').substring(0, 60) : '',
              label: el.parentElement ? el.parentElement.textContent.trim().substring(0, 80) : '',
              outerHTML: el.outerHTML.substring(0, 200)
            });
          });
          // Also check for label elements
          var labels = [];
          document.querySelectorAll('label').forEach(function(l) {
            labels.push({ for: l.getAttribute('for'), text: l.textContent.trim().substring(0, 60) });
          });
          return JSON.stringify({ radios: results, labels: labels });
        })()
      `);
      L("Radio debug: " + radioDebug);

      // Also check the full HTML around the form
      let formHTML = await eval_(`
        (function() {
          var form = document.querySelector('form');
          return form ? form.innerHTML.substring(0, 1500) : 'no form';
        })()
      `);
      L("\nForm HTML:\n" + formHTML.substring(0, 800));

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
