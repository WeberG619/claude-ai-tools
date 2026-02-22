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

  // Close the screenout tab first
  const screenoutTab = tabs.find(t => t.url.includes('screenout'));
  if (screenoutTab) {
    L("Closing screenout tab...");
    const ws = new WebSocket(screenoutTab.webSocketDebuggerUrl);
    ws.addEventListener("open", () => {
      ws.send(JSON.stringify({ id: 1, method: "Page.close" }));
    });
    await sleep(1000);
  }

  // Find BitLabs iframe
  const blTab = tabs.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
  if (!blTab) {
    // Try the job page and navigate to BitLabs
    const jobTab = tabs.find(t => t.url.includes('1079435'));
    if (jobTab) {
      L("Found BitLabs job tab. Reloading...");
      const ws = new WebSocket(jobTab.webSocketDebuggerUrl);
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
          let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
          L("Job page URL: " + url);
          L("Page:\n" + pageText.substring(0, 1000));

          // Reload the page to refresh BitLabs
          await eval_(`window.location.reload()`);
          await sleep(5000);

          // Now check for BitLabs iframe in new tabs
          let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          let blFrame = newTabs.find(t => t.url.includes('bitlabs'));
          if (blFrame) {
            L("\nBitLabs iframe found: " + blFrame.url.substring(0, 80));
          } else {
            L("\nBitLabs iframe not found after reload. Tabs:");
            newTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 80)));
          }

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
    } else {
      L("No BitLabs tab found");
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    }
  } else {
    L("BitLabs iframe still active: " + blTab.url.substring(0, 80));
    const ws = new WebSocket(blTab.webSocketDebuggerUrl);
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
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("BitLabs URL: " + url);
        L("Content:\n" + pageText.substring(0, 2000));

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
  }
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
