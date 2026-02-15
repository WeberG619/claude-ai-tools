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

      // Find the highest value survey card and click it
      let surveyCards = await eval_(`
        (function() {
          // Find all survey card elements that contain USD
          var cards = [];
          // Look for the clickable survey items
          var allEls = document.querySelectorAll('[class*="survey"], [class*="card"], [class*="item"], [class*="offer"], a, button, div');
          for (var i = 0; i < allEls.length; i++) {
            var el = allEls[i];
            var text = el.textContent.trim();
            var match = text.match(/(\\d+\\.\\d+)\\s*USD/);
            if (match && text.length < 100) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 50 && rect.height > 20 && rect.width < 800) {
                cards.push({
                  price: parseFloat(match[1]),
                  text: text.replace(/\\n/g, ' ').substring(0, 60),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  w: Math.round(rect.width),
                  h: Math.round(rect.height),
                  tag: el.tagName,
                  cls: (el.className || '').toString().substring(0, 50)
                });
              }
            }
          }
          // Deduplicate by position
          var unique = [];
          cards.forEach(function(c) {
            var dup = unique.find(function(u) { return Math.abs(u.y - c.y) < 20; });
            if (!dup) unique.push(c);
            else if (c.w < dup.w) { // prefer smaller (more specific) element
              var idx = unique.indexOf(dup);
              unique[idx] = c;
            }
          });
          return JSON.stringify(unique.sort(function(a,b) { return b.price - a.price; }));
        })()
      `);
      L("Survey cards: " + surveyCards);

      let cards = JSON.parse(surveyCards);
      if (cards.length === 0) {
        L("No survey cards found!");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(1);
      }

      // Pick the best survey - prefer highest price that's reachable on screen
      let target = cards[0]; // highest price
      L("Clicking survey: $" + target.price + " at (" + target.x + "," + target.y + ") - " + target.text);

      // May need to scroll to it first
      if (target.y > 600) {
        await eval_(`window.scrollTo(0, ${target.y - 300})`);
        await sleep(500);
        // Re-get position after scroll
        let newPos = await eval_(`
          (function() {
            var allEls = document.querySelectorAll('[class*="survey"], [class*="card"], [class*="item"], div');
            for (var i = 0; i < allEls.length; i++) {
              if (allEls[i].textContent.includes('${target.price.toFixed(2)} USD') && allEls[i].textContent.length < 100) {
                var r = allEls[i].getBoundingClientRect();
                if (r.width > 50 && r.height > 20 && r.width < 800) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
              }
            }
            return null;
          })()
        `);
        if (newPos) {
          let np = JSON.parse(newPos);
          target.x = np.x;
          target.y = np.y;
          L("Scrolled, new pos: (" + target.x + "," + target.y + ")");
        }
      }

      // Click the survey card
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: target.x, y: target.y, button: "left", clickCount: 1 });
      await sleep(100);
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", clickCount: 1 });
      await sleep(3000);

      // Check what happened
      let afterText = await eval_(`document.body.innerText.substring(0, 800)`);
      L("\nAfter click:\n" + afterText.substring(0, 500));

      // Check if "Start survey" button appeared
      if (afterText.includes('Start') || afterText.includes('qualification')) {
        // Look for Start Survey button
        let startBtn = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, a');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (t.includes('Start') && t.includes('survey')) {
                var r = btns[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: t });
              }
            }
            return null;
          })()
        `);
        if (startBtn) {
          let sb = JSON.parse(startBtn);
          L("Clicking Start: " + sb.text);
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: sb.x, y: sb.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: sb.x, y: sb.y, button: "left", clickCount: 1 });
          await sleep(5000);

          // Check for new tabs
          let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          let newSurveyTab = newTabs.find(t => t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('bitlabs') && !t.url.includes('reddit') && !t.url.includes('upwork') && t.url.includes('http'));
          if (newSurveyTab) {
            L("New survey tab: " + newSurveyTab.url.substring(0, 80));
          }
          let afterStart = await eval_(`document.body.innerText.substring(0, 500)`);
          L("After start: " + afterStart.substring(0, 300));
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
