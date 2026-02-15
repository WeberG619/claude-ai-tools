import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 50000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();

  // Close stale survey/screenout tabs
  for (let t of tabs) {
    if (t.type === "page" && (t.url.includes('termination') || t.url.includes('screenout') || t.url.includes('insights-today') || t.url.includes('purespectrum'))) {
      try { await (await fetch(`${CDP_HTTP}/json/close/${t.id}`)).text(); L("Closed: " + t.url.substring(0, 50)); } catch(e) {}
    }
  }

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

      // Click "Find another survey"
      let findBtn = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, a');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.includes('Find another')) {
              var r = btns[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
            }
          }
          return null;
        })()
      `);
      if (findBtn) {
        let b = JSON.parse(findBtn);
        L("Clicking Find another survey at (" + b.x + "," + b.y + ")");
        fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
        await sleep(100);
        fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
        await sleep(4000);
      }

      // Wait for survey list
      let text = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("After find:\n" + text.substring(0, 300));

      if (text.includes('USD')) {
        // Scroll to find $6.40 or highest value
        await eval_(`window.scrollTo(0, 0)`);
        await sleep(500);

        // Try multiple scroll positions to find the best survey
        let bestCard = null;
        for (let scroll = 0; scroll <= 2000; scroll += 500) {
          await eval_(`window.scrollTo(0, ${scroll})`);
          await sleep(300);

          let card = await eval_(`
            (function() {
              var best = null;
              var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
              items.forEach(function(el) {
                var text = el.textContent.trim();
                var match = text.match(/(\\d+\\.\\d+)\\s*USD/);
                if (match) {
                  var price = parseFloat(match[1]);
                  var rect = el.getBoundingClientRect();
                  if (rect.y > 0 && rect.y < 700 && rect.width > 100 && price >= 1.0) {
                    if (!best || price > best.price) {
                      best = { price: price, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.replace(/\\n/g, ' ').substring(0, 50) };
                    }
                  }
                }
              });
              return best ? JSON.stringify(best) : null;
            })()
          `);
          if (card) {
            let c = JSON.parse(card);
            if (!bestCard || c.price > bestCard.price) {
              bestCard = c;
              if (c.price >= 5) break; // Good enough, click it
            }
          }
        }

        if (bestCard) {
          // Scroll back to the best card
          await eval_(`window.scrollTo(0, 0)`);
          await sleep(300);
          for (let scroll = 0; scroll <= 2000; scroll += 300) {
            await eval_(`window.scrollTo(0, ${scroll})`);
            await sleep(200);
            let visible = await eval_(`
              (function() {
                var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
                for (var i = 0; i < items.length; i++) {
                  if (items[i].textContent.includes('${bestCard.price.toFixed(2)} USD')) {
                    var r = items[i].getBoundingClientRect();
                    if (r.y > 50 && r.y < 650) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
                  }
                }
                return null;
              })()
            `);
            if (visible) {
              let v = JSON.parse(visible);
              bestCard.x = v.x;
              bestCard.y = v.y;
              break;
            }
          }

          L("Best: $" + bestCard.price + " - " + bestCard.text);
          L("Clicking at (" + bestCard.x + "," + bestCard.y + ")");
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: bestCard.x, y: bestCard.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: bestCard.x, y: bestCard.y, button: "left", clickCount: 1 });
          await sleep(3000);

          let afterClick = await eval_(`document.body.innerText.substring(0, 600)`);
          L("After click:\n" + afterClick.substring(0, 400));

          // Handle qualification + Start Survey
          for (let q = 0; q < 5; q++) {
            let qt = await eval_(`document.body.innerText.substring(0, 800)`);
            if (qt.includes('Start survey') || qt.includes('PROFILE MATCHES') || qt.includes('qualified')) {
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
                L("START SURVEY!");
                fire("Input.dispatchMouseEvent", { type: "mousePressed", x: s.x, y: s.y, button: "left", clickCount: 1 });
                await sleep(100);
                fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: s.x, y: s.y, button: "left", clickCount: 1 });
                await sleep(5000);
              }
              break;
            }
            if (qt.includes('Offerwall') && !qt.includes('Question')) {
              L("Disqualified");
              break;
            }
            // Answer qualification
            if (qt.includes('Question') || qt.includes('profile')) {
              let lower = qt.toLowerCase();
              // Smart answering
              if (lower.includes('child') || lower.includes('kid')) {
                L("Children question - answering None/NA");
                await eval_(`
                  (function() {
                    var labels = document.querySelectorAll('label');
                    for (var i = 0; i < labels.length; i++) {
                      var t = labels[i].textContent.trim().toLowerCase();
                      if (t === 'none' || t === 'none of the above' || t.includes('no child') || t === 'n/a' || t.includes('not applicable') || t.includes('prefer not')) {
                        labels[i].click(); return;
                      }
                    }
                  })()
                `);
              } else {
                // Default: first option
                await eval_(`
                  (function() {
                    var inputs = document.querySelectorAll('input[type="checkbox"]');
                    if (inputs.length > 0) {
                      var lbl = document.querySelector('label[for="' + inputs[0].id + '"]');
                      if (lbl) lbl.click(); else inputs[0].click();
                    }
                  })()
                `);
              }
              // Click Continue
              await eval_(`
                (function() {
                  var btns = document.querySelectorAll('button');
                  for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim() === 'Continue') btns[i].click();
                  }
                })()
              `);
              await sleep(2000);
            }
          }

          // Check new tabs
          await sleep(2000);
          let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          for (let t of newTabs) {
            if (t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('reddit') && !t.url.includes('upwork') && t.url.startsWith('http')) {
              L("NEW SURVEY TAB: " + t.url.substring(0, 80));
            }
          }
        } else {
          L("No surveys $1+ found visible");
        }
      } else {
        L("No survey prices visible");
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
