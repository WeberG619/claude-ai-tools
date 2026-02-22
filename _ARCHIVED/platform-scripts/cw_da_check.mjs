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
      // Check available projects
      L("=== CHECKING AVAILABLE PROJECTS ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/workers/projects'`);
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + url);
      L("Projects page:\n" + pageText.substring(0, 2000));

      // Check profile/settings
      L("\n=== CHECKING PROFILE ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/workers/profile'`);
      await sleep(3000);

      url = await eval_(`window.location.href`);
      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + url);
      L("Profile:\n" + pageText.substring(0, 2000));

      // Check fields
      let fields = await eval_(`
        (function() {
          var inputs = [];
          document.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function(i) {
            inputs.push({
              type: i.type || i.tagName.toLowerCase(),
              name: i.name || '',
              id: i.id || '',
              value: (i.value||'').substring(0,50),
              placeholder: (i.placeholder||'').substring(0,50),
              label: i.labels && i.labels[0] ? i.labels[0].textContent.trim().substring(0,50) : ''
            });
          });
          return JSON.stringify(inputs);
        })()
      `);
      L("\nFields: " + fields);

      // Check transfer/earnings page
      L("\n=== CHECKING EARNINGS ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/workers/transfers'`);
      await sleep(3000);

      pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Earnings:\n" + pageText.substring(0, 1000));

      // Check inbox
      L("\n=== CHECKING INBOX ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/workers/inbox'`);
      await sleep(3000);

      pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Inbox:\n" + pageText.substring(0, 1000));

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
