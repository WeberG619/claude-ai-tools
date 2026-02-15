import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 90000);

(async () => {
  // Check all tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("=== CURRENT TABS ===");
  tabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

  const pageTab = tabs.find(t => t.type === "page" && (t.url.includes('clickworker') || t.url.includes('workplace')));
  if (!pageTab) {
    // Use any page tab
    const anyPage = tabs.find(t => t.type === "page");
    if (!anyPage) { L("No page tabs!"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
    L("\nUsing: " + anyPage.url);
    const ws = new WebSocket(anyPage.webSocketDebuggerUrl);
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
        // Navigate to BitLabs job
        await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1079435/edit'`);
        await sleep(8000);

        let url = await eval_(`window.location.href`);
        let text = await eval_(`document.body.innerText.substring(0, 1500)`);
        L("\nURL: " + url);
        L("Page:\n" + text.substring(0, 1000));

        // Check for BitLabs iframe
        let allTabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
        L("\nAll targets:");
        allTabs2.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

        let blTarget = allTabs2.find(t => t.url.includes('bitlabs'));
        if (blTarget) {
          L("\nBitLabs iframe found: " + blTarget.url);
          // Connect and check state
          const ws2 = new WebSocket(blTarget.webSocketDebuggerUrl);
          await new Promise((res, rej) => { ws2.addEventListener("open", res); ws2.addEventListener("error", rej); setTimeout(rej, 5000); });
          let id2 = 0;
          const pending2 = new Map();
          ws2.addEventListener("message", e => {
            const m = JSON.parse(e.data);
            if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
          });
          const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
          const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

          let blUrl = await eval2(`window.location.href`);
          let blText = await eval2(`document.body.innerText.substring(0, 3000)`);
          L("\nBitLabs URL: " + blUrl);
          L("BitLabs content:\n" + blText.substring(0, 2000));
          ws2.close();
        } else {
          L("\nNo BitLabs iframe found after navigation");
        }

        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
      })().catch(e => { L("Error: " + e.message); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });
    });
    return;
  }

  L("\nUsing clickworker tab: " + pageTab.url);
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
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1079435/edit'`);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      let text = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nURL: " + url);
      L("Page:\n" + text.substring(0, 1000));

      let allTabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
      allTabs2.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

      let blTarget = allTabs2.find(t => t.url.includes('bitlabs'));
      if (blTarget) {
        L("\nBitLabs iframe: " + blTarget.url);
        const ws2 = new WebSocket(blTarget.webSocketDebuggerUrl);
        await new Promise((res, rej) => { ws2.addEventListener("open", res); ws2.addEventListener("error", rej); setTimeout(rej, 5000); });
        let id2 = 0;
        const pending2 = new Map();
        ws2.addEventListener("message", e => {
          const m = JSON.parse(e.data);
          if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
        });
        const eval2 = async (expr) => { const r = await (new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method: "Runtime.evaluate", params: { expression: expr, returnByValue: true, awaitPromise: true } })); })); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

        let blText = await eval2(`document.body.innerText.substring(0, 3000)`);
        L("\nBitLabs content:\n" + blText.substring(0, 2000));
        ws2.close();
      }

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => { L("Error: " + e.message); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });
  });
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
