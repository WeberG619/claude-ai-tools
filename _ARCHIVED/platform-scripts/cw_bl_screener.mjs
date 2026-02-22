import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 60000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
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
      await send("DOM.enable");
      await send("Runtime.enable");

      // Get the screener.min.js source to understand the validation
      let screenerJS = await eval_(`
        (function() {
          var scripts = document.querySelectorAll('script[src*="screener"]');
          if (scripts.length === 0) return 'no screener script found';
          return scripts[0].src;
        })()
      `);
      L("Screener script URL: " + screenerJS);

      // Fetch and dump the screener JS
      let jsContent = await eval_(`
        new Promise(function(resolve) {
          var xhr = new XMLHttpRequest();
          xhr.open('GET', 'https://www.samplicio.us/s/includes/js/screener.min.js?v=2023-04-26', true);
          xhr.onload = function() { resolve(xhr.responseText); };
          xhr.onerror = function() { resolve('error fetching'); };
          xhr.send();
        })
      `);
      L("Screener JS length: " + jsContent.length);
      // Look for relevant parts
      L("\n=== SCREENER JS (first 3000 chars) ===");
      L(jsContent.substring(0, 3000));

      // Also look for checkbox/change/disabled handling
      let patterns = ['change', 'disabled', 'checkbox', 'checked', 'btnContinue', 'submit-btn', 'exclusive'];
      patterns.forEach(p => {
        let idx = jsContent.indexOf(p);
        if (idx >= 0) {
          L("\n--- Pattern '" + p + "' at index " + idx + " ---");
          L(jsContent.substring(Math.max(0, idx - 100), idx + 200));
        }
      });

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
