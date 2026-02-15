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
  // List all tabs to see what's open
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("=== ALL TABS ===");
  tabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 120) + " | " + (t.title || '').substring(0, 50)));

  // Check samplicio tab
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (surveyTab) {
    L("\nSamplicio tab found: " + surveyTab.url.substring(0, 100));

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

        let url = await eval_(`window.location.href`);
        L("URL: " + url);

        let pageText = await eval_(`document.body ? document.body.innerText.substring(0, 3000) : 'body is null'`);
        L("Page:\n" + pageText.substring(0, 2000));

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
    // Check other tabs that might be the survey
    const otherTab = tabs.find(t => t.type === "page" && !t.url.includes('chrome') && !t.url.includes('newtab'));
    if (otherTab) {
      L("\nNo samplicio tab. Checking: " + otherTab.url);
      const ws = new WebSocket(otherTab.webSocketDebuggerUrl);
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
          let url = await eval_(`window.location.href`);
          let text = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
          L("URL: " + url);
          L("Text:\n" + text.substring(0, 1000));

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
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    }
  }
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
