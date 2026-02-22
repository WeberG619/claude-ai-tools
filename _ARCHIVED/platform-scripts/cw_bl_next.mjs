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
  // Find clickworker tab
  const cwTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (!cwTab) { L("No CW tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("Current URL: " + url);
      L("Page: " + pageText.substring(0, 300));

      // Close other survey tabs
      for (let t of tabs) {
        if (t.type === "page" && (t.url.includes('purespectrum') || t.url.includes('decipherinc') || t.url.includes('samplicio'))) {
          L("Closing tab: " + t.url.substring(0, 50));
          try { await (await fetch(`${CDP_HTTP}/json/close/${t.id}`)).text(); } catch(e) {}
        }
      }

      // If on screenout page, click "Back to Joblist"
      if (pageText.includes('Screenout') || pageText.includes('screened out')) {
        let backBtn = await eval_(`
          (function() {
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {
              if (links[i].textContent.trim().includes('Back to Job')) {
                var r = links[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), href: links[i].href });
              }
            }
            return null;
          })()
        `);
        if (backBtn) {
          let b = JSON.parse(backBtn);
          L("Clicking Back to Joblist...");
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
          await sleep(3000);
        }
      }

      // Navigate to the BitLabs job
      let newUrl = await eval_(`window.location.href`);
      L("After: " + newUrl);

      // If on job page, check for survey iframe
      let newPage = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("Page: " + newPage.substring(0, 500));

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
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
