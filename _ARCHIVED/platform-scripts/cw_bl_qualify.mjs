import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 40000);

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

      // Answer qualification questions in a loop
      for (let round = 0; round < 10; round++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("\n=== R" + round + " ===");
        L(pageText.substring(0, 200));

        if (!pageText || pageText.includes('Offerwall') && !pageText.includes('Question')) {
          L("Back to offerwall - survey rejected or complete");
          break;
        }

        // If "Start survey" is visible
        if (pageText.includes('Start survey') || pageText.includes('Start Survey')) {
          let btn = await eval_(`
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
          if (btn) {
            let b = JSON.parse(btn);
            L("Clicking Start Survey...");
            fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
            await sleep(100);
            fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
            await sleep(5000);
            // Check for new tab
            let newTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
            for (let t of newTabs) {
              if (t.type === "page" && !t.url.includes('clickworker') && !t.url.includes('reddit') && !t.url.includes('upwork') && t.url.startsWith('http')) {
                L("Survey opened: " + t.url.substring(0, 80));
              }
            }
            break;
          }
        }

        // Find and click the right answer based on question
        let lower = pageText.toLowerCase();

        // Look for clickable options (BitLabs uses tailwind checkboxes)
        let qLower = lower;

        // Company size - self-employed = 1
        if (qLower.includes('employees') || qLower.includes('company size') || qLower.includes('how many people')) {
          L("Company size -> 1");
          let clicked = await eval_(`
            (function() {
              var labels = document.querySelectorAll('label');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim();
                if (t === '1' || t === 'Just me' || t === 'Self-employed') {
                  labels[i].click();
                  return 'clicked: ' + t;
                }
              }
              // Try finding by text content
              var all = document.querySelectorAll('*');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === '1' && all[i].children.length === 0) {
                  var rect = all[i].getBoundingClientRect();
                  if (rect.width > 5 && rect.height > 5) {
                    all[i].click();
                    return 'clicked text: 1 at ' + Math.round(rect.x) + ',' + Math.round(rect.y);
                  }
                }
              }
              return 'not found';
            })()
          `);
          L("   " + clicked);
        }
        // Industry
        else if (qLower.includes('industry') || qLower.includes('sector')) {
          L("Industry -> Architecture");
          let clicked = await eval_(`
            (function() {
              var labels = document.querySelectorAll('label, span, div');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim().toLowerCase();
                if (t.includes('architecture') || t.includes('construction') || t.includes('engineering')) {
                  labels[i].click();
                  return 'clicked: ' + labels[i].textContent.trim().substring(0, 40);
                }
              }
              return 'not found';
            })()
          `);
          L("   " + clicked);
        }
        // Job role
        else if (qLower.includes('role') || qLower.includes('job title') || qLower.includes('position')) {
          L("Role -> Owner/Principal");
          let clicked = await eval_(`
            (function() {
              var els = document.querySelectorAll('label, span, div');
              for (var i = 0; i < els.length; i++) {
                var t = els[i].textContent.trim().toLowerCase();
                if (t.includes('owner') || t.includes('principal') || t.includes('executive') || t.includes('c-level') || t.includes('senior')) {
                  els[i].click();
                  return 'clicked: ' + els[i].textContent.trim().substring(0, 40);
                }
              }
              return 'not found';
            })()
          `);
          L("   " + clicked);
        }
        // Decision maker
        else if (qLower.includes('decision') || qLower.includes('purchase') || qLower.includes('buying')) {
          L("Decision maker -> Yes / Final");
          let clicked = await eval_(`
            (function() {
              var els = document.querySelectorAll('label, span, div');
              for (var i = 0; i < els.length; i++) {
                var t = els[i].textContent.trim().toLowerCase();
                if (t.includes('final') || t === 'yes' || t.includes('sole decision')) {
                  els[i].click();
                  return 'clicked: ' + els[i].textContent.trim().substring(0, 40);
                }
              }
              return 'not found';
            })()
          `);
          L("   " + clicked);
        }
        // Default - click first option
        else {
          L("Unknown Q -> first option");
          let clicked = await eval_(`
            (function() {
              // Look for hidden checkboxes with labels (BitLabs pattern)
              var inputs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
              for (var i = 0; i < inputs.length; i++) {
                var label = document.querySelector('label[for="' + inputs[i].id + '"]');
                if (label) { label.click(); return 'clicked label: ' + label.textContent.trim().substring(0, 40); }
              }
              // Fall back to clickable text items
              var items = document.querySelectorAll('label, [class*="option"], [class*="choice"]');
              if (items.length > 0) { items[0].click(); return 'clicked first item: ' + items[0].textContent.trim().substring(0, 40); }
              return 'no options found';
            })()
          `);
          L("   " + clicked);
        }

        await sleep(500);

        // Click Continue
        let contBtn = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (t === 'Continue' || t === 'Next' || t === 'Submit') {
                var r = btns[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: t });
              }
            }
            return null;
          })()
        `);
        if (contBtn) {
          let cb = JSON.parse(contBtn);
          L("Clicking " + cb.text);
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: cb.x, y: cb.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: cb.x, y: cb.y, button: "left", clickCount: 1 });
        }
        await sleep(3000);
      }

      // Final state
      let finalText = await eval_(`document.body.innerText.substring(0, 800)`);
      L("\nFINAL: " + finalText.substring(0, 400));

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
