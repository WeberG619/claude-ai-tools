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
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Strategy: Use DOM.focus + keyboard space to check the checkbox
      // First, focus the checkbox
      let r = await eval_(`
        (function() {
          var cb = document.getElementById('v-0');
          if (cb) {
            cb.focus();
            return 'focused, activeElement: ' + document.activeElement.id;
          }
          return 'not found';
        })()
      `);
      L("Focus: " + r);

      // Dispatch space key
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: " ", code: "Space", text: " " });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: " ", code: "Space", text: " " });
      await sleep(500);

      // Check state
      r = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? 'checked: ' + cb.checked : 'not found'; })()`);
      L("After space: " + r);

      if (r.includes('false')) {
        // Try clicking the label element directly via the label tag
        L("Space didn't work, trying label click...");

        r = await eval_(`
          (function() {
            var label = document.querySelector('label[for="v-0"]');
            if (label) {
              // Get the clickable area rectangle
              var rect = label.getBoundingClientRect();
              return JSON.stringify({x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height)});
            }
            return 'no label';
          })()
        `);
        L("Label rect: " + r);
        let labelPos = JSON.parse(r);

        // Click on the left part of the label (where the visual checkbox is)
        await clickAt(labelPos.x, labelPos.y);
        await sleep(500);

        r = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? 'checked: ' + cb.checked : 'not found'; })()`);
        L("After label click: " + r);
      }

      if (r.includes('false')) {
        // Try yet another approach - find the visual checkbox element
        L("Still not checked, trying visual checkbox div...");

        r = await eval_(`
          (function() {
            // Look for the .checkbox div inside the label
            var label = document.querySelector('label[for="v-0"]');
            if (!label) return 'no label';
            var checkDiv = label.querySelector('.checkbox, [class*="checkbox"]');
            if (checkDiv) {
              var rect = checkDiv.getBoundingClientRect();
              return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height)});
            }
            // Fall back to the whole row div
            var row = document.querySelector('.survey-qualification-answer-multi');
            if (row) {
              var rect = row.getBoundingClientRect();
              return JSON.stringify({x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), class: 'row'});
            }
            return 'no checkbox div';
          })()
        `);
        L("Checkbox div: " + r);

        if (r !== 'no label' && r !== 'no checkbox div') {
          let pos = JSON.parse(r);
          await clickAt(pos.x, pos.y);
          await sleep(500);

          r = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? 'checked: ' + cb.checked : 'not found'; })()`);
          L("After checkbox div click: " + r);
        }
      }

      // Take another screenshot to see state
      const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs_screen2.png', Buffer.from(screenshot.data, 'base64'));
      L("Screenshot 2 saved");

      // If somehow checked, try clicking Continue
      r = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? cb.checked : false; })()`);
      if (r === true) {
        L("Checkbox IS checked! Clicking Continue...");
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim().includes('Continue')) {
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)});
              }
            }
            return 'no button';
          })()
        `);
        let btnPos = JSON.parse(r);
        await clickAt(btnPos.x, btnPos.y);
        await sleep(3000);
        let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("After Continue: " + pageText.substring(0, 500));
      }

      // If nothing worked, let me try the full answer flow using the row click approach
      if (r !== true) {
        L("\nTrying row-based approach...");
        // The answer rows are DIVs with class 'survey-qualification-answer-multi'
        r = await eval_(`
          (function() {
            var rows = document.querySelectorAll('[class*="survey-qualification-answer"]');
            return JSON.stringify(Array.from(rows).map(function(row, idx) {
              var rect = row.getBoundingClientRect();
              return {
                idx: idx,
                text: row.textContent.trim().substring(0, 30),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
              };
            }));
          })()
        `);
        L("Answer rows: " + r);
        let rows = JSON.parse(r || '[]');

        if (rows.length > 0) {
          // Click the first row (English)
          let engRow = rows[0];
          L("Clicking English row at " + engRow.x + "," + engRow.y);
          await clickAt(engRow.x, engRow.y);
          await sleep(1000);

          r = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? 'checked: ' + cb.checked : 'not found'; })()`);
          L("After row click: " + r);

          // Take screenshot
          const ss3 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
          writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs_screen3.png', Buffer.from(ss3.data, 'base64'));
          L("Screenshot 3 saved");
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
