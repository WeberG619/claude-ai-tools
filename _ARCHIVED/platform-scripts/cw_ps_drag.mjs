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
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
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

    const cdpClick = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(100);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Analyze the drag-and-drop DOM
      let dragInfo = await eval_(`
        (function() {
          var results = {};
          // Find draggable elements
          results.draggables = [];
          document.querySelectorAll('[draggable="true"], [class*="drag"], [class*="number"]').forEach(function(el) {
            var rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.width < 200) {
              results.draggables.push({
                tag: el.tagName,
                text: el.textContent.trim().substring(0, 30),
                classes: (el.className || '').substring(0, 80),
                draggable: el.draggable,
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
              });
            }
          });
          // Find drop targets (square box)
          results.dropTargets = [];
          document.querySelectorAll('[class*="drop"], [class*="target"], [class*="box"], [class*="square"]').forEach(function(el) {
            var rect = el.getBoundingClientRect();
            if (rect.width > 20 && rect.width < 300) {
              results.dropTargets.push({
                tag: el.tagName,
                text: el.textContent.trim().substring(0, 30),
                classes: (el.className || '').substring(0, 80),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
              });
            }
          });
          // Also find all elements with text "79"
          results.num79 = [];
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            if (all[i].textContent.trim() === '79' && all[i].children.length === 0) {
              var rect = all[i].getBoundingClientRect();
              results.num79.push({
                tag: all[i].tagName,
                classes: (all[i].className || '').substring(0, 80),
                draggable: all[i].draggable,
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
              });
            }
          }
          // Get outer HTML around drag area
          var dragContainer = document.querySelector('[class*="drag-drop"], [class*="dnd"]');
          results.containerHTML = dragContainer ? dragContainer.outerHTML.substring(0, 500) : 'no drag-drop container';
          // Full body classes
          results.bodyHTML = document.body.innerHTML.substring(document.body.innerHTML.indexOf('drag'), document.body.innerHTML.indexOf('drag') + 500);
          return JSON.stringify(results);
        })()
      `);
      L("Drag info:\n" + dragInfo);

      // Also get a broader DOM view
      let pageHTML = await eval_(`
        (function() {
          var html = document.body.innerHTML;
          var idx = html.indexOf('79');
          if (idx >= 0) return html.substring(Math.max(0, idx - 300), idx + 500);
          return 'no 79 found in HTML';
        })()
      `);
      L("\nHTML around 79:\n" + pageHTML.substring(0, 800));

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
