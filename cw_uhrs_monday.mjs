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
  L("=== CURRENT TABS ===");
  tabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 100)));

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
      // First reactivate UHRS access from Clickworker
      L("=== REACTIVATING UHRS ACCESS ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/51749/edit'`);
      await sleep(8000);

      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("CW page:\n" + pageText.substring(0, 800));

      // Now navigate to UHRS marketplace
      L("\n=== NAVIGATING TO UHRS MARKETPLACE ===");
      await eval_(`window.location.href = 'https://www.uhrs.ai/marketplace'`);
      await sleep(10000);

      let url = await eval_(`window.location.href`);
      pageText = await eval_(`document.body.innerText.substring(0, 6000)`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 5000));

      // Get task counts
      let counts = await eval_(`
        (function() {
          var text = document.body.innerText;
          var m = text.match(/All\\s*(\\d+)/);
          return m ? 'All: ' + m[1] : 'count not found';
        })()
      `);
      L("\nTask count: " + counts);

      // If there are tasks, get their details
      let taskList = await eval_(`
        (function() {
          var cards = document.querySelectorAll('[class*="card"], [class*="hit"], [class*="task"], [class*="app"], [class*="item"]');
          var results = [];
          for (var i = 0; i < cards.length; i++) {
            var t = cards[i].textContent.trim().replace(/\\s+/g, ' ');
            if (t.length > 30 && t.length < 500 && (t.includes('$') || t.includes('cent') || t.includes('HIT') || t.includes('hits'))) {
              results.push(t.substring(0, 250));
            }
          }
          return JSON.stringify(results.slice(0, 20));
        })()
      `);
      L("\nTask cards: " + taskList);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_monday.png', Buffer.from(ss.data, 'base64'));
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
