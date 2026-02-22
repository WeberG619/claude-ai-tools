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
  const pageTab = tabs.find(t => t.type === "page");
  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
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
      L("=== NAVIGATING TO PROFILE ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/me'`);
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 3000));

      // Get all form fields
      let fields = await eval_(`
        (function() {
          var inputs = [];
          document.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function(i) {
            var label = '';
            if (i.labels && i.labels[0]) label = i.labels[0].textContent.trim();
            if (!label) {
              var prev = i.previousElementSibling;
              if (prev) label = prev.textContent.trim();
            }
            inputs.push({
              type: i.type || i.tagName.toLowerCase(),
              name: i.name || '',
              id: i.id || '',
              value: (i.value||'').substring(0,80),
              placeholder: (i.placeholder||'').substring(0,50),
              label: label.substring(0, 60)
            });
          });
          return JSON.stringify(inputs);
        })()
      `);
      L("\nForm fields: " + fields);

      // Check for skill checkboxes or selection elements
      let skills = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input[type="checkbox"], [class*="skill"], [class*="tag"], [class*="chip"]').forEach(function(el) {
            var t = el.textContent ? el.textContent.trim() : '';
            var l = el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '';
            var checked = el.checked !== undefined ? el.checked : null;
            results.push({ text: (t || l).substring(0, 60), checked: checked });
          });
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      L("\nSkill elements: " + skills);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_da_me.png', Buffer.from(ss.data, 'base64'));
      L("\nScreenshot saved");

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
