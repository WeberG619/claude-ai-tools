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
  const blTab = tabs.find(t => t.url.includes('bitlabs') && t.url.includes('surveys'));
  if (!blTab) { L("No BitLabs surveys tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blTab.webSocketDebuggerUrl);
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

      // Find the $4.25 survey card and click it
      let cardInfo = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.includes('4.25') && t.includes('USD') && t.length < 50) {
              // Found the price text, find the clickable parent
              var el = all[i];
              while (el && el !== document.body) {
                var style = window.getComputedStyle(el);
                if (style.cursor === 'pointer' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
                  var rect = el.getBoundingClientRect();
                  if (rect.width > 50 && rect.height > 30) {
                    return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) });
                  }
                }
                el = el.parentElement;
              }
              // If no cursor-pointer parent, use the element itself
              var rect = all[i].getBoundingClientRect();
              return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), noCursor: true });
            }
          }
          return 'not found';
        })()
      `);
      L("Card: " + cardInfo);

      if (cardInfo === 'not found') {
        L("$4.25 survey not found. Listing all surveys...");
        let surveys = await eval_(`
          (function() {
            var results = [];
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.match(/^\\d+\\.\\d+ USD$/) && parseFloat(t) >= 2.0) {
                var parent = all[i].closest('[class*="cursor"]') || all[i].parentElement;
                var rect = parent ? parent.getBoundingClientRect() : all[i].getBoundingClientRect();
                results.push({ price: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
            return JSON.stringify(results);
          })()
        `);
        L("High-value surveys: " + surveys);
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        ws.close();
        process.exit(0);
        return;
      }

      let ci = JSON.parse(cardInfo);
      // Scroll into view if needed
      if (ci.y > 800) {
        await eval_(`window.scrollBy(0, ${ci.y - 400})`);
        await sleep(500);
        // Re-check position after scroll
        let newInfo = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.includes('4.25') && t.includes('USD') && t.length < 50) {
                var el = all[i];
                while (el && el !== document.body) {
                  var style = window.getComputedStyle(el);
                  if (style.cursor === 'pointer') {
                    var rect = el.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                  }
                  el = el.parentElement;
                }
                var rect = all[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
            return 'not found';
          })()
        `);
        ci = JSON.parse(newInfo);
      }

      L("Clicking $4.25 at (" + ci.x + ", " + ci.y + ")");
      await cdpClick(ci.x, ci.y);
      await sleep(5000);

      // Check what happened
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nURL: " + url);
      L("Page:\n" + pageText.substring(0, 2000));

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
