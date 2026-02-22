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
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); tabs.forEach(t => L(t.type + ": " + t.url.substring(0, 80))); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
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

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body ? document.body.innerText.substring(0, 3000) : 'loading'`);
      L("URL: " + url);
      L("\nPage:\n" + pageText.substring(0, 2500));

      // Check for form elements
      let formInfo = await eval_(`
        (function() {
          var results = {};
          results.forms = document.querySelectorAll('form').length;
          results.radios = document.querySelectorAll('input[type="radio"]').length;
          results.checkboxes = document.querySelectorAll('input[type="checkbox"]').length;
          results.buttons = [];
          document.querySelectorAll('button, input[type="submit"], a.btn, [class*="btn"]').forEach(function(b) {
            var rect = b.getBoundingClientRect();
            if (rect.width > 0) {
              results.buttons.push({ text: b.textContent.trim().substring(0, 40), tag: b.tagName, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          });
          results.selects = document.querySelectorAll('select').length;
          results.textInputs = document.querySelectorAll('input[type="text"], textarea').length;
          return JSON.stringify(results);
        })()
      `);
      L("\nForm info: " + formInfo);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

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
