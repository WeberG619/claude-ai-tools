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

  // Find BitLabs iframe
  const blFrame = tabs.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
  if (blFrame) {
    L("BitLabs iframe found: " + blFrame.url.substring(0, 80));

    const ws = new WebSocket(blFrame.webSocketDebuggerUrl);
    ws.addEventListener("error", () => { L("WS error on iframe"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

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

        // Check current state
        let iframeUrl = await eval_(`window.location.href`);
        let iframeText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'no body'`);
        L("Iframe URL: " + iframeUrl);
        L("Iframe text: " + iframeText.substring(0, 800));

        // Check if we can see surveys
        if (iframeText.includes('USD') || iframeText.includes('$')) {
          L("\nSurveys available!");
          // Find survey prices and click the best one
          let surveys = await eval_(`
            (function() {
              var results = [];
              var items = document.querySelectorAll('[class*="survey"], [class*="card"], [class*="offer"]');
              items.forEach(function(el) {
                var text = el.textContent;
                var priceMatch = text.match(/(\\d+\\.\\d+)\\s*USD/);
                if (priceMatch) {
                  var rect = el.getBoundingClientRect();
                  results.push({ price: parseFloat(priceMatch[1]), text: text.trim().substring(0, 60), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              });
              return JSON.stringify(results.sort(function(a,b) { return b.price - a.price; }));
            })()
          `);
          L("Surveys: " + surveys);
        } else if (iframeText.includes('Find another') || iframeText.includes('back')) {
          // Click find another survey
          let btn = await eval_(`
            (function() {
              var btns = document.querySelectorAll('button, a');
              for (var i = 0; i < btns.length; i++) {
                var t = btns[i].textContent.trim().toLowerCase();
                if (t.includes('find') || t.includes('another') || t.includes('back') || t.includes('survey')) {
                  var r = btns[i].getBoundingClientRect();
                  if (r.width > 20) return JSON.stringify({ text: btns[i].textContent.trim(), x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
                }
              }
              return null;
            })()
          `);
          if (btn) {
            let b = JSON.parse(btn);
            L("Clicking: " + b.text);
            fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
            await sleep(100);
            fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
            await sleep(3000);
            let afterText = await eval_(`document.body.innerText.substring(0, 1000)`);
            L("After click: " + afterText.substring(0, 500));
          }
        }

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
    // Try the clickworker tab and look for iframes
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
      const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result?.value; };
      const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

      (async () => {
        await send("DOM.enable");
        await send("Runtime.enable");

        // Check for Start button or iframe
        let pageInfo = await eval_(`
          (function() {
            var iframes = document.querySelectorAll('iframe');
            var iframeInfo = [];
            iframes.forEach(function(f) { iframeInfo.push(f.src.substring(0, 80)); });

            var btns = [];
            document.querySelectorAll('button, a, input[type="submit"]').forEach(function(b) {
              var t = b.textContent.trim();
              if (t.includes('Start') || t.includes('Begin') || t.includes('Go')) {
                var r = b.getBoundingClientRect();
                btns.push({ text: t.substring(0, 30), x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
              }
            });

            return JSON.stringify({ iframes: iframeInfo, buttons: btns, text: document.body.innerText.substring(0, 500) });
          })()
        `);
        L("Page info: " + pageInfo);

        let info = JSON.parse(pageInfo);

        // If there's a Start button, click it
        if (info.buttons.length > 0) {
          let b = info.buttons[0];
          L("Clicking Start: " + b.text);
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
          await sleep(5000);

          // Recheck for bitlabs iframe
          let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          let newBl = newTabs.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
          L("After start, bitlabs iframe: " + (newBl ? newBl.url.substring(0, 60) : 'not found'));
        }

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
