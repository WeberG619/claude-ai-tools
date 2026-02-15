import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const blTarget = tabs.find(t => t.url.includes('bitlabs'));
  if (!blTarget) { L("No BitLabs target"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blTarget.webSocketDebuggerUrl);
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

      // Scroll down to find the $6.40 survey and click it
      L("=== FINDING $6.40 SURVEY ===");

      // First scroll to make sure it's visible
      let scrollResult = await eval_(`
        (function() {
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim().includes('6.40')) {
              var el = node.parentElement;
              // Go up to find the card
              for (var i = 0; i < 8; i++) {
                if (!el) break;
                if ((el.className||'').includes('cursor-pointer')) {
                  el.scrollIntoView({ block: 'center' });
                  var rect = el.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) });
                }
                el = el.parentElement;
              }
              // Fallback
              var textEl = node.parentElement;
              textEl.scrollIntoView({ block: 'center' });
              var rect = textEl.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), fallback: true });
            }
          }
          return 'not found';
        })()
      `);
      L("Card position: " + scrollResult);

      if (scrollResult === 'not found') {
        L("$6.40 not found, checking current surveys...");
        // List top surveys by price
        let surveys = await eval_(`
          (function() {
            var text = document.body.innerText;
            var matches = [];
            var lines = text.split('\\n');
            for (var i = 0; i < lines.length; i++) {
              var m = lines[i].match(/(\\d+\\.\\d{2})\\s*USD/);
              if (m) {
                var price = parseFloat(m[1]);
                var timeMatch = (lines[i+1] || '').match(/(\\d+)/);
                matches.push({ price: price, time: timeMatch ? timeMatch[1] + ' min' : '?' });
              }
            }
            matches.sort(function(a, b) { return b.price - a.price; });
            return JSON.stringify(matches.slice(0, 10));
          })()
        `);
        L("Top surveys: " + surveys);

        // Try clicking the highest priced one
        try {
          let top = JSON.parse(surveys);
          if (top.length > 0) {
            let target = top[0].price.toFixed(2);
            L("Targeting $" + target + " instead");
            let pos = await eval_(`
              (function() {
                var target = '${target}';
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var node;
                while (node = walker.nextNode()) {
                  if (node.textContent.trim().includes(target)) {
                    var el = node.parentElement;
                    for (var i = 0; i < 8; i++) {
                      if (!el) break;
                      if ((el.className||'').includes('cursor-pointer')) {
                        el.scrollIntoView({ block: 'center' });
                        var rect = el.getBoundingClientRect();
                        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                      }
                      el = el.parentElement;
                    }
                    var textEl = node.parentElement;
                    textEl.scrollIntoView({ block: 'center' });
                    var rect = textEl.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), fallback: true });
                  }
                }
                return 'not found';
              })()
            `);
            if (pos !== 'not found') {
              let p = JSON.parse(pos);
              L("Clicking at (" + p.x + ", " + p.y + ")");
              await cdpClick(p.x, p.y);
              await sleep(5000);
            }
          }
        } catch(e) { L("Error: " + e.message); }
      } else {
        let pos = JSON.parse(scrollResult);
        L("Clicking $6.40 at (" + pos.x + ", " + pos.y + ")");
        await cdpClick(pos.x, pos.y);
        await sleep(5000);
      }

      // Check result
      let newUrl = await eval_(`window.location.href`);
      let newPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nURL: " + newUrl);
      L("Page:\n" + newPage.substring(0, 2000));

      // Handle qualification questions if present
      if (newPage.includes('Question')) {
        L("\n=== ANSWERING QUALIFICATION ===");
        for (let round = 0; round < 8; round++) {
          let qText = await eval_(`document.body.innerText.substring(0, 2000)`);
          if (!qText.includes('Question')) break;

          let qMatch = qText.match(/Question (\d+)\/(\d+)/);
          L("\n--- " + (qMatch ? qMatch[0] : "Q?") + " ---");
          let lines = qText.split('\n').filter(l => l.trim().length > 3);
          L("Q: " + lines.slice(1, 5).join(' | '));

          let text = qText.toLowerCase();
          let answerTarget = null;

          if (text.includes('industry') || text.includes('work in')) answerTarget = 'Architecture';
          else if (text.includes('gender') || text.includes('sex')) answerTarget = 'Male';
          else if (text.includes('hispanic') || text.includes('latino')) answerTarget = 'No';
          else if (text.includes('race') || text.includes('ethnic')) answerTarget = 'White';
          else if (text.includes('marital') || text.includes('married')) answerTarget = 'Single';
          else if (text.includes('employ') || text.includes('work status')) answerTarget = 'Self-employed';
          else if (text.includes('children') || text.includes('kids')) answerTarget = 'None';
          else if (text.includes('education') || text.includes('degree')) answerTarget = 'Some college';
          else if (text.includes('age') || text.includes('old') || text.includes('born') || text.includes('birth') || text.includes('year')) {
            // Get options and find matching age range
            let opts = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"]')).map(cb => { var l = cb.closest('label'); return l ? l.textContent.trim() : ''; }).filter(t => t.length > 0))`);
            L("Options: " + opts);
            try {
              let ageOpts = JSON.parse(opts);
              for (let o of ageOpts) {
                if (o.includes('1974') || o.includes('50-54') || o.includes('50 - 54') || o.includes('45-54') || o.includes('50 to 54') || o.includes('50-59')) { answerTarget = o; break; }
              }
              if (!answerTarget) for (let o of ageOpts) { if (o.includes('51') || o.includes('50')) { answerTarget = o; break; } }
            } catch(e) {}
          }
          else if (text.includes('income') || text.includes('earn') || text.includes('salary') || (text.includes('household') && text.includes('$'))) {
            let opts = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"]')).map(cb => { var l = cb.closest('label'); return l ? l.textContent.trim() : ''; }).filter(t => t.length > 0))`);
            L("Options: " + opts);
            try {
              let incOpts = JSON.parse(opts);
              for (let o of incOpts) { if (o.includes('75,000') || o.includes('$75') || o.includes('70,000')) { answerTarget = o; break; } }
              if (!answerTarget) for (let o of incOpts) { if ((o.includes('50,000') || o.includes('$50')) && (o.includes('99') || o.includes('100'))) { answerTarget = o; break; } }
            } catch(e) {}
          }
          else if (text.includes('state') || text.includes('where')) answerTarget = 'Idaho';

          if (!answerTarget) {
            let opts = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"]')).map(cb => { var l = cb.closest('label'); return l ? l.textContent.trim() : ''; }).filter(t => t.length > 0).slice(0, 20))`);
            L("UNKNOWN Q. Options: " + opts);
            break;
          }

          L("-> " + answerTarget);

          // Click option via CDP
          let safeAnswer = answerTarget.replace(/'/g, "\\'");
          let optPos = await eval_(`
            (function() {
              var target = '${safeAnswer}';
              var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
              for (var i = 0; i < cbs.length; i++) {
                var label = cbs[i].closest('label');
                if (!label) continue;
                var t = label.textContent.trim();
                if (t === target || (t.includes(target) && t.length < target.length + 20)) {
                  label.scrollIntoView({ block: 'center' });
                  var rect = label.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
                }
              }
              return 'not found';
            })()
          `);

          if (optPos !== 'not found') {
            let op = JSON.parse(optPos);
            await cdpClick(op.x, op.y);
          } else {
            L("   Option not found, trying direct checkbox click");
            await eval_(`
              (function() {
                var target = '${safeAnswer}';
                var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
                for (var i = 0; i < cbs.length; i++) {
                  var p = cbs[i];
                  for (var j = 0; j < 6; j++) {
                    p = p.parentElement;
                    if (!p) break;
                    if (p.textContent.trim().includes(target) && p.textContent.trim().length < target.length + 30) {
                      cbs[i].click();
                      return;
                    }
                  }
                }
              })()
            `);
          }
          await sleep(1500);

          // Click Continue
          let contPos = await eval_(`
            (function() {
              var btns = document.querySelectorAll('button');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim() === 'Continue') {
                  btns[i].scrollIntoView({ block: 'center' });
                  var rect = btns[i].getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              }
              return 'none';
            })()
          `);
          if (contPos !== 'none') {
            let cp = JSON.parse(contPos);
            await cdpClick(cp.x, cp.y);
            await sleep(3000);
          }
        }
      }

      // Final
      L("\n=== FINAL ===");
      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 2000));

      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nTargets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

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
