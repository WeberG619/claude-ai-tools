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
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (!pageTab) { L("No clickworker tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
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
      // Navigate to BitLabs job
      L("=== OPENING BITLABS (Job 1079435) ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1079435/edit'`);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 2000));

      // Check for iframe targets
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

      // Find BitLabs iframe target
      let blTarget = allTabs.find(t =>
        t.url.includes('bitlabs') ||
        t.url.includes('sdk.') ||
        (t.type === 'iframe' && !t.url.includes('clickworker') && t.url.length > 20)
      );

      if (blTarget) {
        L("\n=== FOUND BITLABS TARGET ===");
        L("URL: " + blTarget.url);
        try {
          const ws2 = new WebSocket(blTarget.webSocketDebuggerUrl);
          await new Promise((res, rej) => {
            ws2.addEventListener("open", res);
            ws2.addEventListener("error", rej);
            setTimeout(rej, 5000);
          });
          let id2 = 0;
          const pending2 = new Map();
          ws2.addEventListener("message", e => {
            const m = JSON.parse(e.data);
            if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
          });
          const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
          const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

          let blUrl = await eval2(`window.location.href`);
          let blText = await eval2(`document.body.innerText.substring(0, 4000)`);
          L("\nBitLabs URL: " + blUrl);
          L("BitLabs content:\n" + blText.substring(0, 3000));

          // Screenshot the iframe
          const ss2 = await send2("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
          writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs_iframe.png', Buffer.from(ss2.data, 'base64'));
          L("\nBitLabs iframe screenshot saved");

          ws2.close();
        } catch(e) { L("BitLabs iframe error: " + e.message); }
      } else {
        L("\nNo BitLabs iframe target. Checking other targets...");
        let otherTargets = allTabs.filter(t => !t.url.includes('clickworker') && t.url.length > 10 && t.type !== 'worker');
        otherTargets.forEach(t => L("  Other: " + t.type + " - " + t.url.substring(0, 150)));
      }

      // Screenshot main page
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs.png', Buffer.from(ss.data, 'base64'));

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
