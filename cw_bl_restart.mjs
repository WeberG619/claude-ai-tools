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
  // Find the Clickworker tab (any)
  const cwTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (!cwTab) { L("No Clickworker tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(cwTab.webSocketDebuggerUrl);
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

      // Navigate to BitLabs job
      L("Navigating to BitLabs job 1079435...");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1079435/edit'`);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      // Wait for BitLabs iframe to load
      await sleep(5000);

      // Check for BitLabs iframe
      let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      let blFrame = newTabs.find(t => t.url.includes('bitlabs'));
      if (blFrame) {
        L("BitLabs iframe found: " + blFrame.url.substring(0, 80));

        // Connect to BitLabs iframe
        const ws2 = new WebSocket(blFrame.webSocketDebuggerUrl);
        await new Promise(r => ws2.addEventListener("open", r));

        let id2 = 0;
        const pending2 = new Map();
        ws2.addEventListener("message", e => {
          const m = JSON.parse(e.data);
          if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
        });
        const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
        const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

        await send2("DOM.enable");
        await send2("Runtime.enable");

        let blUrl = await eval2(`window.location.href`);
        let blText = await eval2(`document.body.innerText.substring(0, 3000)`);
        L("\nBitLabs URL: " + blUrl);
        L("Content:\n" + blText.substring(0, 2500));

        ws2.close();
      } else {
        L("No BitLabs iframe found. Tabs:");
        newTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 80)));

        let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("CW page:\n" + pageText);
      }

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
