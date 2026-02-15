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
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Click "Earn" to navigate to surveys list
      let earnBtn = await eval_(`
        (function() {
          var links = document.querySelectorAll('a, button, div, span');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim();
            if (t === 'Earn' || t === 'Offerwall') {
              var r = links[i].getBoundingClientRect();
              if (r.width > 10 && r.height > 10) {
                return JSON.stringify({ text: t, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
              }
            }
          }
          return null;
        })()
      `);
      if (earnBtn) {
        let b = JSON.parse(earnBtn);
        L("Clicking: " + b.text + " at (" + b.x + "," + b.y + ")");
        fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
        await sleep(100);
        fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
        await sleep(3000);
      }

      // Check page and full HTML
      let text = await eval_(`document.body.innerText`);
      L("Text after click:\n" + text.substring(0, 1000));

      let html = await eval_(`document.body.innerHTML.substring(0, 5000)`);
      L("\nHTML:\n" + html.substring(0, 2000));

      // Also check URL
      let url = await eval_(`window.location.href`);
      L("\nURL: " + url);

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
