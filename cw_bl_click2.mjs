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

      // Scroll to top first
      await eval_(`window.scrollTo(0, 0)`);
      await sleep(500);

      // Find all visible survey cards with prices - get the ones currently visible
      let cards = await eval_(`
        (function() {
          var results = [];
          var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
          items.forEach(function(el) {
            var text = el.textContent.trim();
            var priceMatch = text.match(/(\\d+\\.\\d+)\\s*USD/);
            var timeMatch = text.match(/(\\d+)\\s*minutes?/);
            if (priceMatch) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 100 && rect.height > 50 && rect.y > -10 && rect.y < 800) {
                results.push({
                  price: parseFloat(priceMatch[1]),
                  mins: timeMatch ? parseInt(timeMatch[1]) : 0,
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  visible: true
                });
              }
            }
          });
          return JSON.stringify(results.sort(function(a,b) { return b.price - a.price; }));
        })()
      `);
      L("Visible cards: " + cards);

      let cardList = JSON.parse(cards);
      if (cardList.length === 0) {
        L("No visible cards. Scrolling down...");
        await eval_(`window.scrollTo(0, 300)`);
        await sleep(1000);
        cards = await eval_(`
          (function() {
            var results = [];
            var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
            items.forEach(function(el) {
              var text = el.textContent.trim();
              var priceMatch = text.match(/(\\d+\\.\\d+)\\s*USD/);
              if (priceMatch) {
                var rect = el.getBoundingClientRect();
                if (rect.width > 100 && rect.height > 50 && rect.y > 0 && rect.y < 800) {
                  results.push({ price: parseFloat(priceMatch[1]), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              }
            });
            return JSON.stringify(results.sort(function(a,b) { return b.price - a.price; }));
          })()
        `);
        cardList = JSON.parse(cards);
        L("After scroll: " + cards);
      }

      if (cardList.length > 0) {
        // Click the highest-priced visible one
        let target = cardList[0];
        L("Clicking $" + target.price + " at (" + target.x + "," + target.y + ")");
        fire("Input.dispatchMouseEvent", { type: "mousePressed", x: target.x, y: target.y, button: "left", clickCount: 1 });
        await sleep(100);
        fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", clickCount: 1 });
        await sleep(3000);

        // Check result
        let afterText = await eval_(`document.body.innerText.substring(0, 800)`);
        L("\nAfter click:\n" + afterText.substring(0, 400));

        // Look for Start Survey or Qualification questions
        if (afterText.includes('Start survey') || afterText.includes('Start Survey')) {
          let startBtn = await eval_(`
            (function() {
              var btns = document.querySelectorAll('button, a');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim().includes('Start')) {
                  var r = btns[i].getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: btns[i].textContent.trim() });
                }
              }
              return null;
            })()
          `);
          if (startBtn) {
            let sb = JSON.parse(startBtn);
            L("Clicking: " + sb.text);
            fire("Input.dispatchMouseEvent", { type: "mousePressed", x: sb.x, y: sb.y, button: "left", clickCount: 1 });
            await sleep(100);
            fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: sb.x, y: sb.y, button: "left", clickCount: 1 });
            await sleep(5000);

            let finalText = await eval_(`document.body.innerText.substring(0, 500)`);
            L("After start: " + finalText.substring(0, 300));

            // Check for new tab
            let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
            for (let t of newTabs) {
              if (t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('reddit') && !t.url.includes('upwork') && !t.url.includes('chrome://') && t.url.startsWith('http')) {
                L("Survey tab: " + t.title + " - " + t.url.substring(0, 80));
              }
            }
          }
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
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
