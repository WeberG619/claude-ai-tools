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

      // Find the $3.35 survey card and get its position
      L("=== FINDING $3.35 SURVEY ===");
      let cardPos = await eval_(`
        (function() {
          // Find all elements with "3.35" text
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim().includes('3.35')) {
              // Found the price text - go up to find the card container
              var el = node.parentElement;
              for (var i = 0; i < 8; i++) {
                if (!el) break;
                var classes = el.className || '';
                // Look for cursor-pointer which indicates clickable card
                if (classes.includes('cursor-pointer') || classes.includes('card') || classes.includes('survey')) {
                  el.scrollIntoView({ block: 'center' });
                  var rect = el.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), tag: el.tagName, classes: classes.substring(0, 80) });
                }
                el = el.parentElement;
              }
              // Fallback - just click near the text
              var textEl = node.parentElement;
              textEl.scrollIntoView({ block: 'center' });
              var rect = textEl.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), tag: textEl.tagName, classes: (textEl.className||'').substring(0, 80), fallback: true });
            }
          }
          return 'not found';
        })()
      `);
      L("Card position: " + cardPos);

      if (cardPos === 'not found') {
        L("$3.35 survey not found on page");
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("Page: " + pageText.substring(0, 1000));
      } else {
        let pos = JSON.parse(cardPos);
        L("Clicking $3.35 card at (" + pos.x + ", " + pos.y + ") size=" + pos.w + "x" + pos.h);
        await cdpClick(pos.x, pos.y);
        await sleep(5000);

        // Check what happened
        let newUrl = await eval_(`window.location.href`);
        let newPage = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("\nAfter click URL: " + newUrl);
        L("After click page:\n" + newPage.substring(0, 2000));

        // If qualification questions appeared, answer them
        let hasQuestion = newPage.includes('Question');
        if (hasQuestion) {
          L("\n=== QUALIFICATION QUESTIONS ===");

          for (let round = 0; round < 8; round++) {
            let qText = await eval_(`document.body.innerText.substring(0, 2000)`);
            if (!qText.includes('Question')) { L("No more questions"); break; }

            let qMatch = qText.match(/Question (\d+)\/(\d+)/);
            L("\n--- " + (qMatch ? qMatch[0] : "Question") + " ---");
            let lines = qText.split('\n').filter(l => l.trim().length > 3);
            L("Q: " + lines.slice(0, 4).join(' | '));

            let text = qText.toLowerCase();
            let answerTarget = null;

            if (text.includes('industry') || text.includes('work in')) answerTarget = 'Architecture';
            else if (text.includes('gender') || text.includes('sex')) answerTarget = 'Male';
            else if (text.includes('age') || text.includes('old are you') || text.includes('born') || text.includes('birth') || text.includes('year')) {
              // Find the right age range option - need to check what options exist
              let opts = await eval_(`
                (function() {
                  var results = [];
                  document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function(cb) {
                    var label = cb.closest('label');
                    if (label) results.push(label.textContent.trim());
                  });
                  return JSON.stringify(results);
                })()
              `);
              L("Age options: " + opts);
              try {
                let ageOpts = JSON.parse(opts);
                for (let o of ageOpts) {
                  if (o.includes('1974') || o.includes('50-54') || o.includes('50 - 54') || o.includes('45-54') || o.includes('50 to 54') || o.includes('50-59')) {
                    answerTarget = o;
                    break;
                  }
                }
                if (!answerTarget) {
                  for (let o of ageOpts) { if (o.includes('51') || o.includes('50')) { answerTarget = o; break; } }
                }
              } catch(e) {}
            }
            else if (text.includes('income') || text.includes('earn') || text.includes('salary') || (text.includes('household') && text.includes('$'))) {
              let opts = await eval_(`
                (function() {
                  var results = [];
                  document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function(cb) {
                    var label = cb.closest('label');
                    if (label) results.push(label.textContent.trim());
                  });
                  return JSON.stringify(results);
                })()
              `);
              L("Income options: " + opts);
              try {
                let incOpts = JSON.parse(opts);
                for (let o of incOpts) {
                  if (o.includes('75,000') || o.includes('$75') || o.includes('70,000') || o.includes('$70')) { answerTarget = o; break; }
                }
                if (!answerTarget) {
                  for (let o of incOpts) {
                    if ((o.includes('50,000') || o.includes('$50')) && (o.includes('99') || o.includes('100'))) { answerTarget = o; break; }
                  }
                }
              } catch(e) {}
            }
            else if (text.includes('education') || text.includes('degree') || text.includes('school')) answerTarget = 'Some college';
            else if (text.includes('hispanic') || text.includes('latino')) answerTarget = 'No';
            else if (text.includes('race') || text.includes('ethnic')) answerTarget = 'White';
            else if (text.includes('marital') || text.includes('married') || text.includes('relationship')) answerTarget = 'Single';
            else if (text.includes('employ') || text.includes('work status')) answerTarget = 'Self-employed';
            else if (text.includes('children') || text.includes('kids')) answerTarget = 'None';
            else if (text.includes('state') || text.includes('where do you live')) answerTarget = 'Idaho';

            if (!answerTarget) {
              L("UNKNOWN QUESTION - stopping");
              L("Full text: " + qText.substring(0, 1000));
              break;
            }

            L("-> Answer: " + answerTarget);

            // Click the option using CDP
            let optPos = await eval_(`
              (function() {
                var target = '${answerTarget.replace(/'/g, "\\'")}';
                var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
                // Exact match
                for (var i = 0; i < cbs.length; i++) {
                  var label = cbs[i].closest('label');
                  if (label && label.textContent.trim() === target) {
                    label.scrollIntoView({ block: 'center' });
                    var rect = label.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
                  }
                }
                // Partial match
                for (var i = 0; i < cbs.length; i++) {
                  var label = cbs[i].closest('label');
                  if (label && label.textContent.trim().includes(target)) {
                    label.scrollIntoView({ block: 'center' });
                    var rect = label.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
                  }
                }
                // Walk text nodes
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var node;
                while (node = walker.nextNode()) {
                  var t = node.textContent.trim();
                  if (t === target || (t.includes(target) && t.length < target.length + 20)) {
                    var el = node.parentElement;
                    el.scrollIntoView({ block: 'center' });
                    var rect = el.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
                  }
                }
                return 'not found';
              })()
            `);

            if (optPos === 'not found') {
              L("Option not found, trying checkbox click...");
              // Fallback: use direct checkbox click
              await eval_(`
                (function() {
                  var target = '${answerTarget.replace(/'/g, "\\'")}';
                  var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
                  for (var i = 0; i < cbs.length; i++) {
                    var p = cbs[i].parentElement;
                    for (var j = 0; j < 5; j++) {
                      if (!p) break;
                      if (p.textContent.trim().includes(target) && p.textContent.trim().length < target.length + 30) {
                        cbs[i].click();
                        return 'clicked';
                      }
                      p = p.parentElement;
                    }
                  }
                })()
              `);
            } else {
              let op = JSON.parse(optPos);
              L("   Clicking at (" + op.x + ", " + op.y + ")");
              await cdpClick(op.x, op.y);
            }
            await sleep(1500);

            // Click Continue with CDP
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
                return 'none';
              })()
            `);
            if (contPos !== 'none') {
              let cp = JSON.parse(contPos);
              L("   Continue at (" + cp.x + ", " + cp.y + ") disabled=" + cp.disabled);
              await cdpClick(cp.x, cp.y);
              await sleep(3000);
            } else {
              L("   No Continue button");
            }
          }
        }

        // Final state
        L("\n=== FINAL STATE ===");
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("URL: " + fUrl);
        L("Page:\n" + fPage.substring(0, 2000));
      }

      // Check all targets
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
