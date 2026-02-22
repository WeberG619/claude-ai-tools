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
      // Refresh the UHRS marketplace
      L("=== REFRESHING UHRS MARKETPLACE ===");
      await eval_(`window.location.href = 'https://www.uhrs.ai/marketplace'`);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 6000)`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 5000));

      // Check task counts
      let counts = await eval_(`
        (function() {
          var text = document.body.innerText;
          var categories = ['All', 'New', 'Image annotation', 'Search relevance', 'Video annotation',
                           'Speech transcription', 'Text annotation', 'Product Testing', 'Other'];
          var results = {};
          categories.forEach(function(cat) {
            var re = new RegExp(cat + '\\\\s*(\\\\d+)', 'i');
            var m = text.match(re);
            if (m) results[cat] = parseInt(m[1]);
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nTask counts: " + counts);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_refresh.png', Buffer.from(ss.data, 'base64'));
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
