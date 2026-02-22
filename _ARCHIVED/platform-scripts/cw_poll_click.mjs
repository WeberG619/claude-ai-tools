import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

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
      // Click the $1.18/6min survey card using JS click
      L("=== CLICKING $1.18/6min SURVEY ===");
      let r = await eval_(`
        (function() {
          var cards = document.querySelectorAll('.SurveyCard_container__2jge-');
          for (var i = 0; i < cards.length; i++) {
            var text = cards[i].textContent;
            if (text.includes('1.18') && text.includes('6 Minutes')) {
              cards[i].click();
              return 'clicked $1.18/6min card';
            }
          }
          // Fallback: try $1.15/10min with 1 qualification
          for (var i = 0; i < cards.length; i++) {
            var text = cards[i].textContent;
            if (text.includes('1.15') && text.includes('1 Qualification')) {
              cards[i].click();
              return 'clicked $1.15/10min card';
            }
          }
          // Fallback: click first short survey with 1 qualification
          for (var i = 0; i < cards.length; i++) {
            var text = cards[i].textContent;
            if (text.includes('1 Qualification') && (text.includes('6 Min') || text.includes('5 Min') || text.includes('4 Min'))) {
              cards[i].click();
              return 'clicked card: ' + text.substring(0, 80);
            }
          }
          return 'no matching card found';
        })()
      `);
      L("Click: " + r);
      await sleep(5000);

      // Check what happened - might have opened a new tab or modal
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("URL: " + url);
      L("Page: " + pageText.substring(0, 500));

      // Check for new tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      let tabInfo = allTabs.map(t => ({ type: t.type, url: t.url.substring(0, 120) }));
      L("All tabs: " + JSON.stringify(tabInfo));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_done.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

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
