import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 90000);

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

    // CDP click at specific coordinates
    const cdpClick = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: x, y: y, button: "left", clickCount: 1 });
      await sleep(100);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x, y: y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Enable input events
      await send("DOM.enable");
      await send("Runtime.enable");

      // Check current page state
      let info = await eval_(`document.body.innerText.substring(0, 500)`);
      L("Current page: " + info.substring(0, 300));

      // Get Architecture option position
      let archPos = await eval_(`
        (function() {
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim() === 'Architecture') {
              var el = node.parentElement;
              var label = el.closest('label') || el;
              var rect = label.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: rect.width, h: rect.height });
            }
          }
          return 'not found';
        })()
      `);
      L("Architecture position: " + archPos);

      if (archPos !== 'not found') {
        let pos = JSON.parse(archPos);
        L("Clicking Architecture at (" + pos.x + ", " + pos.y + ")");
        await cdpClick(pos.x, pos.y);
        await sleep(1500);

        // Verify it's checked
        let checked = await eval_(`
          (function() {
            var cbs = document.querySelectorAll('input[type="checkbox"]:checked, input[type="radio"]:checked');
            var results = [];
            cbs.forEach(function(cb) {
              var label = cb.closest('label');
              results.push(label ? label.textContent.trim().substring(0, 40) : cb.value);
            });
            return JSON.stringify(results);
          })()
        `);
        L("Checked after CDP click: " + checked);

        // Get Continue button position
        let contPos = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Continue') {
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled });
              }
            }
            return 'not found';
          })()
        `);
        L("Continue position: " + contPos);

        if (contPos !== 'not found') {
          let cPos = JSON.parse(contPos);
          L("Clicking Continue at (" + cPos.x + ", " + cPos.y + ") disabled=" + cPos.disabled);
          await cdpClick(cPos.x, cPos.y);
          await sleep(4000);
        }
      }

      // Check new page
      let newPage = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nAfter Q2:\n" + newPage.substring(0, 800));

      // Continue with remaining questions using CDP clicks
      for (let round = 0; round < 6; round++) {
        let qInfo = await eval_(`
          (function() {
            var text = document.body.innerText;
            var qMatch = text.match(/Question (\\d+)\\/(\\d+)/);
            if (!qMatch) return JSON.stringify({ done: true, text: text.substring(0, 500) });
            var qNum = parseInt(qMatch[1]);
            var qTotal = parseInt(qMatch[2]);
            // Get question text
            var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
            return JSON.stringify({ done: false, qNum: qNum, qTotal: qTotal, text: lines.slice(0, 5).join(' | ') });
          })()
        `);
        let qi = JSON.parse(qInfo);
        if (qi.done) { L("\\nQuestions complete: " + qi.text.substring(0, 300)); break; }

        L("\\n=== Q" + qi.qNum + "/" + qi.qTotal + " ===");
        L("Q: " + qi.text);

        // Determine answer
        let text = qi.text.toLowerCase();
        let answerText = null;

        if (text.includes('industry') || text.includes('work in')) answerText = 'Architecture';
        else if (text.includes('gender') || text.includes('sex')) answerText = 'Male';
        else if (text.includes('age') || text.includes('old') || text.includes('born') || text.includes('birth')) answerText = '50'; // partial match
        else if (text.includes('income') || text.includes('earn') || text.includes('salary')) answerText = '75,000'; // partial
        else if (text.includes('education') || text.includes('degree')) answerText = 'Some college';
        else if (text.includes('hispanic') || text.includes('latino')) answerText = 'No';
        else if (text.includes('race') || text.includes('ethnic')) answerText = 'White';
        else if (text.includes('marital') || text.includes('married')) answerText = 'Single';
        else if (text.includes('employ') || text.includes('work status')) answerText = 'Self';
        else if (text.includes('children') || text.includes('kids')) answerText = '0';
        else if (text.includes('state') || text.includes('where')) answerText = 'Idaho';

        if (!answerText) {
          // Get all options text
          let opts = await eval_(`
            (function() {
              var results = [];
              document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function(cb) {
                var label = cb.closest('label');
                if (label) results.push(label.textContent.trim().substring(0, 60));
              });
              return JSON.stringify(results);
            })()
          `);
          L("Unknown question. Options: " + opts);
          break;
        }

        // Find option containing answerText and get its position
        let optionPos = await eval_(`
          (function() {
            var answerText = '${answerText}';
            var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
            for (var i = 0; i < cbs.length; i++) {
              var label = cbs[i].closest('label');
              if (!label) continue;
              var t = label.textContent.trim();
              // Exact match first
              if (t === answerText) {
                var rect = label.getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t });
              }
            }
            // Partial match
            for (var i = 0; i < cbs.length; i++) {
              var label = cbs[i].closest('label');
              if (!label) continue;
              var t = label.textContent.trim();
              if (t.includes(answerText) && t.length < 80) {
                var rect = label.getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t });
              }
            }
            return 'not found: ' + answerText;
          })()
        `);
        L("Option: " + optionPos);

        if (optionPos.startsWith('not found')) {
          L("Could not find answer option");
          // Try scrolling to see if options are below viewport
          await eval_(`window.scrollBy(0, 300)`);
          await sleep(500);
          // Retry
          optionPos = await eval_(`
            (function() {
              var answerText = '${answerText}';
              var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
              for (var i = 0; i < cbs.length; i++) {
                var label = cbs[i].closest('label');
                if (!label) continue;
                var t = label.textContent.trim();
                if (t.includes(answerText) && t.length < 80) {
                  label.scrollIntoView({ block: 'center' });
                  var rect = label.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t });
                }
              }
              return 'still not found';
            })()
          `);
          L("After scroll: " + optionPos);
          if (optionPos.startsWith('still')) break;
        }

        let oPos = JSON.parse(optionPos);
        L("-> Clicking '" + oPos.text + "' at (" + oPos.x + ", " + oPos.y + ")");
        await cdpClick(oPos.x, oPos.y);
        await sleep(1500);

        // Click Continue
        let contPos = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Continue') {
                btns[i].scrollIntoView({ block: 'center' });
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled });
              }
            }
            return 'no btn';
          })()
        `);
        if (contPos !== 'no btn') {
          let cp = JSON.parse(contPos);
          L("-> Continue at (" + cp.x + ", " + cp.y + ") disabled=" + cp.disabled);
          await cdpClick(cp.x, cp.y);
          await sleep(3000);
        }
      }

      // Final state
      L("\n=== FINAL STATE ===");
      let finalUrl = await eval_(`window.location.href`);
      let finalPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + finalUrl);
      L("Page:\n" + finalPage.substring(0, 2000));

      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
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
