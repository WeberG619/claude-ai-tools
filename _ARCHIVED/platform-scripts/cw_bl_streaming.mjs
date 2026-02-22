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

      // Check the DOM structure for these options
      L("=== ANALYZING STREAMING OPTIONS ===");
      let structure = await eval_(`
        (function() {
          var results = [];
          // Check all interactive elements
          var all = document.querySelectorAll('input, [role], label, button, [class*="answer"], [class*="option"], [class*="choice"]');
          all.forEach(function(el) {
            var t = el.textContent.trim();
            if (t.length > 2 && t.length < 50) {
              results.push({
                tag: el.tagName,
                type: el.type || '',
                role: el.getAttribute('role') || '',
                text: t,
                classes: (el.className || '').substring(0, 80),
                checked: el.checked || false
              });
            }
          });
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      L("Interactive elements:\n" + structure);

      // Check for all checkboxes/radios
      let allInputs = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input').forEach(function(inp) {
            var label = inp.closest('label');
            var parentText = '';
            var el = inp;
            for (var i = 0; i < 5; i++) {
              el = el.parentElement;
              if (!el) break;
              parentText = el.textContent.trim();
              if (parentText.length > 2 && parentText.length < 50) break;
            }
            results.push({
              type: inp.type,
              name: inp.name || '',
              value: (inp.value || '').substring(0, 30),
              checked: inp.checked,
              labelText: label ? label.textContent.trim().substring(0, 50) : '',
              parentText: parentText.substring(0, 50),
              classes: (inp.className || '').substring(0, 60)
            });
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nAll inputs:\n" + allInputs);

      // Select real services: Netflix, Disney Plus, Apple TV+ (NOT CineWave, StreamPlay)
      let realServices = ['Netflix', 'Disney Plus', 'Apple TV+'];

      for (let service of realServices) {
        L("\nSelecting: " + service);

        // Find and click the option
        let safeService = service.replace(/\+/g, '\\+').replace(/'/g, "\\'");
        let optPos = await eval_(`
          (function() {
            var target = '${service}';
            // Try finding text node and walking up to clickable
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while (node = walker.nextNode()) {
              var t = node.textContent.trim();
              if (t === target) {
                var el = node.parentElement;
                el.scrollIntoView({ block: 'center' });
                var rect = el.getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t });
              }
            }
            return 'not found';
          })()
        `);
        L("Position: " + optPos);

        if (optPos !== 'not found') {
          let op = JSON.parse(optPos);
          await cdpClick(op.x, op.y);
          await sleep(800);
        } else {
          // Try direct checkbox click
          let clicked = await eval_(`
            (function() {
              var target = '${service}';
              var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
              for (var i = 0; i < cbs.length; i++) {
                var el = cbs[i];
                for (var j = 0; j < 5; j++) {
                  el = el.parentElement;
                  if (!el) break;
                  if (el.textContent.trim() === target || el.textContent.trim().includes(target)) {
                    cbs[i].click();
                    return 'clicked checkbox ' + i;
                  }
                }
              }
              return 'not found';
            })()
          `);
          L("Checkbox: " + clicked);
        }
      }

      await sleep(1000);

      // Verify what's checked
      let checked = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input:checked').forEach(function(cb) {
            var el = cb;
            for (var i = 0; i < 5; i++) {
              el = el.parentElement;
              if (!el) break;
              var t = el.textContent.trim();
              if (t.length > 2 && t.length < 50) { results.push(t); break; }
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nChecked: " + checked);

      // Click Continue
      L("\n=== CLICKING CONTINUE ===");
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
      L("Continue: " + contPos);
      if (contPos !== 'none') {
        let cp = JSON.parse(contPos);
        await cdpClick(cp.x, cp.y);
        await sleep(4000);
      }

      // Check next question or redirect
      let nextPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      let nextUrl = await eval_(`window.location.href`);
      L("\nAfter Q1 URL: " + nextUrl);
      L("After Q1:\n" + nextPage.substring(0, 1500));

      // If Q2, handle it
      if (nextPage.includes('Question 2')) {
        L("\n=== Q2 ===");
        // Read Q2 and answer similarly
        let text = nextPage.toLowerCase();
        let qLines = nextPage.split('\n').filter(l => l.trim().length > 3);
        L("Q2: " + qLines.slice(1, 5).join(' | '));

        // Get options
        let opts = await eval_(`
          (function() {
            var results = [];
            document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function(cb) {
              var el = cb;
              for (var i = 0; i < 5; i++) {
                el = el.parentElement;
                if (!el) break;
                var t = el.textContent.trim();
                if (t.length > 2 && t.length < 80) { results.push(t); break; }
              }
            });
            // Also get text-only options
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while (node = walker.nextNode()) {
              var t = node.textContent.trim();
              if (t.length > 2 && t.length < 50 && !['Complete your profile', 'Question', 'Continue', 'Menu', 'Offerwall', 'Earn', 'Reward History', 'Privacy Policy', 'Terms of Use', 'Language'].includes(t)) {
                if (!results.includes(t)) results.push(t);
              }
            }
            return JSON.stringify(results);
          })()
        `);
        L("Q2 options: " + opts);

        // Determine answer based on question
        let answerTarget = null;
        if (text.includes('industry') || text.includes('work in')) answerTarget = 'Architecture';
        else if (text.includes('gender') || text.includes('sex')) answerTarget = 'Male';
        else if (text.includes('hispanic') || text.includes('latino')) answerTarget = 'No';
        else if (text.includes('race') || text.includes('ethnic')) answerTarget = 'White';
        else if (text.includes('marital') || text.includes('married')) answerTarget = 'Single';
        else if (text.includes('employ') || text.includes('work status')) answerTarget = 'Self-employed';
        else if (text.includes('children') || text.includes('kids')) answerTarget = 'None';
        else if (text.includes('education') || text.includes('degree')) answerTarget = 'Some college';
        else if (text.includes('age') || text.includes('old') || text.includes('born')) {
          try {
            let ageOpts = JSON.parse(opts);
            for (let o of ageOpts) {
              if (o.includes('1974') || o.includes('50-54') || o.includes('45-54') || o.includes('50 to 54')) { answerTarget = o; break; }
            }
            if (!answerTarget) for (let o of ageOpts) { if (o.includes('50') || o.includes('51')) { answerTarget = o; break; } }
          } catch(e) {}
        }
        else if (text.includes('income') || text.includes('earn') || text.includes('salary')) {
          try {
            let incOpts = JSON.parse(opts);
            for (let o of incOpts) { if (o.includes('75,000') || o.includes('$75')) { answerTarget = o; break; } }
            if (!answerTarget) for (let o of incOpts) { if (o.includes('50,000') && o.includes('99')) { answerTarget = o; break; } }
          } catch(e) {}
        }

        if (answerTarget) {
          L("-> " + answerTarget);
          let opPos = await eval_(`
            (function() {
              var target = '${answerTarget.replace(/'/g, "\\'")}';
              var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
              var node;
              while (node = walker.nextNode()) {
                if (node.textContent.trim() === target || node.textContent.trim().includes(target)) {
                  var el = node.parentElement;
                  el.scrollIntoView({ block: 'center' });
                  var rect = el.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              }
              return 'not found';
            })()
          `);
          if (opPos !== 'not found') {
            let op = JSON.parse(opPos);
            await cdpClick(op.x, op.y);
            await sleep(1500);
          }
          // Continue
          let cp2 = await eval_(`
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
          if (cp2 !== 'none') { let c = JSON.parse(cp2); await cdpClick(c.x, c.y); await sleep(4000); }
        } else {
          L("Unknown Q2 - full text:\n" + nextPage.substring(0, 1000));
        }
      }

      // Final state
      L("\n=== FINAL STATE ===");
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
