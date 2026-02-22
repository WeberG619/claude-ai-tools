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

  // Close stale survey tabs
  for (let t of tabs) {
    if (t.type === "page" && (t.url.includes('insights-today') || t.url.includes('decipherinc') || t.url.includes('purespectrum') || t.url.includes('samplicio'))) {
      try { await (await fetch(`${CDP_HTTP}/json/close/${t.id}`)).text(); } catch(e) {}
      L("Closed: " + t.url.substring(0, 40));
    }
  }

  // Find clickworker tab - navigate to job page
  const cwTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (cwTab) {
    const ws2 = new WebSocket(cwTab.webSocketDebuggerUrl);
    ws2.addEventListener("open", () => {
      ws2.send(JSON.stringify({ id: 1, method: "Page.navigate", params: { url: "https://workplace.clickworker.com/en/workplace/jobs/1079435/edit" } }));
      setTimeout(() => ws2.close(), 2000);
    });
    await sleep(3000);
  }

  // Now work with the BitLabs iframe
  await sleep(3000);
  let tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const blFrame = tabs2.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
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

      // Navigate to offerwall
      await eval_(`window.location.href = 'https://web.bitlabs.ai/surveys'`);
      await sleep(3000);

      let pageText = await eval_(`document.body.innerText`);

      // If still on opened survey page, click "Find another"
      if (pageText.includes('Find another')) {
        await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, a');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.includes('Find another')) { btns[i].click(); return; }
            }
          })()
        `);
        await sleep(3000);
        pageText = await eval_(`document.body.innerText`);
      }

      // Find surveys sorted by best $/minute rate
      await eval_(`window.scrollTo(0, 0)`);
      await sleep(500);

      let allCards = await eval_(`
        (function() {
          var results = [];
          var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
          items.forEach(function(el) {
            var text = el.textContent.trim();
            var priceMatch = text.match(/(\\d+\\.\\d+)\\s*USD/);
            var timeMatch = text.match(/(\\d+)\\s*minutes?/);
            if (priceMatch && timeMatch) {
              var price = parseFloat(priceMatch[1]);
              var mins = parseInt(timeMatch[1]);
              var rate = price / Math.max(mins, 1);
              var rect = el.getBoundingClientRect();
              if (rect.width > 100 && rect.height > 30) {
                results.push({ price: price, mins: mins, rate: Math.round(rate * 100) / 100, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
          });
          // Sort by rate ($/min) descending
          return JSON.stringify(results.sort(function(a,b) { return b.rate - a.rate; }));
        })()
      `);

      let cards = JSON.parse(allCards);
      L("Top surveys by rate:");
      cards.slice(0, 10).forEach(function(c) {
        L("  $" + c.price + " / " + c.mins + "min = $" + c.rate + "/min" + (c.y > 0 && c.y < 700 ? " [visible]" : " [off-screen y=" + c.y + "]"));
      });

      // Try clicking the best rate survey that's visible
      let target = cards.find(c => c.y > 0 && c.y < 700);
      if (!target && cards.length > 0) {
        // Scroll to best one
        target = cards[0];
        await eval_(`window.scrollTo(0, ${Math.max(0, target.y - 300)})`);
        await sleep(500);
        // Re-find
        let newCards = await eval_(`
          (function() {
            var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
            for (var i = 0; i < items.length; i++) {
              if (items[i].textContent.includes('${target.price.toFixed(2)} USD')) {
                var r = items[i].getBoundingClientRect();
                if (r.y > 0 && r.y < 700) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
              }
            }
            return null;
          })()
        `);
        if (newCards) {
          let nc = JSON.parse(newCards);
          target.x = nc.x;
          target.y = nc.y;
        }
      }

      if (target) {
        L("\nClicking: $" + target.price + " / " + target.mins + "min at (" + target.x + "," + target.y + ")");
        fire("Input.dispatchMouseEvent", { type: "mousePressed", x: target.x, y: target.y, button: "left", clickCount: 1 });
        await sleep(100);
        fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", clickCount: 1 });
        await sleep(3000);

        let afterText = await eval_(`document.body.innerText.substring(0, 800)`);
        L("After click:\n" + afterText.substring(0, 400));

        // Handle qualification
        for (let q = 0; q < 5; q++) {
          let qt = await eval_(`document.body.innerText.substring(0, 1000)`);
          if (qt.includes('Start survey') || qt.includes('Start Survey')) {
            // Click Start
            let sb = await eval_(`
              (function() {
                var btns = document.querySelectorAll('button, a');
                for (var i = 0; i < btns.length; i++) {
                  if (btns[i].textContent.trim().includes('Start')) {
                    var r = btns[i].getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
                  }
                }
                return null;
              })()
            `);
            if (sb) {
              let s = JSON.parse(sb);
              L("Clicking Start Survey");
              fire("Input.dispatchMouseEvent", { type: "mousePressed", x: s.x, y: s.y, button: "left", clickCount: 1 });
              await sleep(100);
              fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: s.x, y: s.y, button: "left", clickCount: 1 });
              await sleep(5000);
            }
            break;
          }
          if (qt.includes('Question') || qt.includes('profile')) {
            // Answer qualification - just pick first/best option
            await eval_(`
              (function() {
                var inputs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
                if (inputs.length > 0) {
                  var label = document.querySelector('label[for="' + inputs[0].id + '"]');
                  if (label) label.click(); else inputs[0].click();
                }
              })()
            `);
            // Click Continue
            await eval_(`
              (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                  if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return; }
                }
              })()
            `);
            await sleep(2000);
          }
        }

        // Check for new tabs
        let finalTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
        for (let t of finalTabs) {
          if (t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('reddit') && !t.url.includes('upwork') && !t.url.includes('chrome://') && t.url.startsWith('http')) {
            L("Survey tab: " + t.title + " - " + t.url.substring(0, 80));
          }
        }

        let finalText = await eval_(`document.body.innerText.substring(0, 400)`);
        L("Final BL: " + finalText.substring(0, 200));
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
