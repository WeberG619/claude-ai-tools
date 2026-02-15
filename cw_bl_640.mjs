import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 45000);

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

      // Check if we need to go back to survey list
      let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      if (pageText.includes('child') || pageText.includes('Question')) {
        // Navigate back to surveys
        await eval_(`window.location.href = 'https://web.bitlabs.ai/surveys'`);
        await sleep(3000);
      }

      // Scroll down to find $6.40 survey
      await eval_(`window.scrollTo(0, 500)`);
      await sleep(1000);

      // Find a $6.40 survey card
      let card = await eval_(`
        (function() {
          var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
          for (var i = 0; i < items.length; i++) {
            var text = items[i].textContent.trim();
            if (text.includes('6.40 USD') || text.includes('6.4 USD')) {
              var rect = items[i].getBoundingClientRect();
              if (rect.y > 0 && rect.y < 700 && rect.width > 100) {
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.replace(/\\n/g, ' ').substring(0, 60) });
              }
            }
          }
          // Try scrolling more
          return null;
        })()
      `);

      if (!card) {
        await eval_(`window.scrollTo(0, 1000)`);
        await sleep(500);
        card = await eval_(`
          (function() {
            var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
            for (var i = 0; i < items.length; i++) {
              var text = items[i].textContent.trim();
              if (text.includes('6.40 USD') || text.includes('6.4 USD')) {
                var rect = items[i].getBoundingClientRect();
                if (rect.y > 0 && rect.y < 700 && rect.width > 100) {
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.replace(/\\n/g, ' ').substring(0, 60) });
                }
              }
            }
            return null;
          })()
        `);
      }

      if (!card) {
        await eval_(`window.scrollTo(0, 1500)`);
        await sleep(500);
        card = await eval_(`
          (function() {
            var items = document.querySelectorAll('[class*="cursor-pointer"][class*="rounded"]');
            for (var i = 0; i < items.length; i++) {
              var text = items[i].textContent.trim();
              if (text.includes('6.40 USD') || text.includes('6.4 USD')) {
                var rect = items[i].getBoundingClientRect();
                if (rect.y > 0 && rect.y < 700 && rect.width > 100) {
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.replace(/\\n/g, ' ').substring(0, 60) });
                }
              }
            }
            // Fallback: find ANY high-value card
            var best = null;
            for (var i = 0; i < items.length; i++) {
              var text = items[i].textContent;
              var match = text.match(/(\\d+\\.\\d+)\\s*USD/);
              if (match) {
                var price = parseFloat(match[1]);
                var rect = items[i].getBoundingClientRect();
                if (price >= 1.5 && rect.y > 0 && rect.y < 700 && rect.width > 100) {
                  if (!best || price > best.price) {
                    best = { price: price, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.replace(/\\n/g, ' ').substring(0, 60) };
                  }
                }
              }
            }
            return best ? JSON.stringify(best) : null;
          })()
        `);
      }

      if (!card) { L("No good survey found visible"); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

      let c = JSON.parse(card);
      L("Clicking: " + c.text + " at (" + c.x + "," + c.y + ")");
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: c.x, y: c.y, button: "left", clickCount: 1 });
      await sleep(100);
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: c.x, y: c.y, button: "left", clickCount: 1 });
      await sleep(3000);

      // Handle qualification
      for (let q = 0; q < 5; q++) {
        let qt = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("Q" + q + ": " + qt.substring(0, 200));

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
            L("Clicking Start Survey!");
            fire("Input.dispatchMouseEvent", { type: "mousePressed", x: s.x, y: s.y, button: "left", clickCount: 1 });
            await sleep(100);
            fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: s.x, y: s.y, button: "left", clickCount: 1 });
            await sleep(5000);
          }
          break;
        }

        if (qt.includes('Offerwall') && !qt.includes('Question')) {
          L("Back to offerwall - didn't qualify");
          break;
        }

        // Answer qualification question
        if (qt.includes('Question') || qt.includes('profile')) {
          let lower = qt.toLowerCase();
          // Click appropriate option
          await eval_(`
            (function() {
              var inputs = document.querySelectorAll('input[type="checkbox"]');
              // Try to find matching answer
              var labels = document.querySelectorAll('label');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim();
                // Skip if it asks about children
                if (t === '1' || t.includes('Self') || t.includes('Architecture') || t.includes('Construction')) {
                  labels[i].click();
                  return 'clicked: ' + t;
                }
              }
              // Default: click first
              if (inputs.length > 0) {
                var lbl = document.querySelector('label[for="' + inputs[0].id + '"]');
                if (lbl) lbl.click(); else inputs[0].click();
              }
            })()
          `);
          // Click Continue
          await eval_(`
            (function() {
              var btns = document.querySelectorAll('button');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); }
              }
            })()
          `);
          await sleep(2000);
        }
      }

      // Check for new survey tabs
      let finalTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      for (let t of finalTabs) {
        if (t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('reddit') && !t.url.includes('upwork') && !t.url.includes('chrome://') && t.url.startsWith('http')) {
          L("Survey tab: " + t.title + " - " + t.url.substring(0, 80));
        }
      }

      let finalText = await eval_(`document.body.innerText.substring(0, 400)`);
      L("Final: " + finalText.substring(0, 200));

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
