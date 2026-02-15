import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 25000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const blFrame = tabs.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
  if (!blFrame) { L("No BL iframe"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blFrame.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result?.value; };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Wait for surveys to load
      await sleep(3000);

      let fullText = await eval_(`document.body.innerText`);
      L("Full page text:\n" + fullText.substring(0, 2000));

      // Check DOM for survey cards
      let cardInfo = await eval_(`
        (function() {
          var allEls = document.querySelectorAll('*');
          var surveyEls = [];
          for (var i = 0; i < allEls.length; i++) {
            var t = allEls[i].textContent.trim();
            if (t.includes('USD') && t.length < 200) {
              var rect = allEls[i].getBoundingClientRect();
              if (rect.width > 50 && rect.height > 30) {
                surveyEls.push({
                  tag: allEls[i].tagName,
                  text: t.substring(0, 80),
                  class: (allEls[i].className || '').substring(0, 50),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  w: Math.round(rect.width),
                  h: Math.round(rect.height)
                });
              }
            }
          }
          // Also check full body HTML for survey data
          var html = document.body.innerHTML;
          var usdMatches = [];
          var re = /(\d+\.\d+)\s*USD/g;
          var match;
          while ((match = re.exec(html)) !== null) {
            usdMatches.push(match[1]);
          }
          return JSON.stringify({ elements: surveyEls.slice(0, 20), usdPrices: usdMatches });
        })()
      `);
      L("\nCards: " + cardInfo);

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
