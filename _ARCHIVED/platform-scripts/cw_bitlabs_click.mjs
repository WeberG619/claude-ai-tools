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
      await sleep(30);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Get positions of "English" checkbox/label and "Continue" button
      let positions = await eval_(`
        (function() {
          var english = document.getElementById('v-0');
          var label = english ? english.parentElement || english.labels[0] : null;
          var continueBtn = null;
          document.querySelectorAll('button').forEach(function(b) {
            if (b.textContent.trim().includes('Continue')) continueBtn = b;
          });

          var result = {};
          if (english) {
            var r = english.getBoundingClientRect();
            result.checkbox = { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) };
          }
          if (label) {
            var r2 = label.getBoundingClientRect();
            result.label = { x: Math.round(r2.x + r2.width/2), y: Math.round(r2.y + r2.height/2) };
          }
          if (continueBtn) {
            var r3 = continueBtn.getBoundingClientRect();
            result.button = { x: Math.round(r3.x + r3.width/2), y: Math.round(r3.y + r3.height/2) };
          }
          return JSON.stringify(result);
        })()
      `);
      L("Positions: " + positions);
      let pos = JSON.parse(positions);

      // Click on the English label using CDP mouse events
      if (pos.label) {
        L("Clicking label at " + pos.label.x + "," + pos.label.y);
        await clickAt(pos.label.x, pos.label.y);
        await sleep(500);
      } else if (pos.checkbox) {
        L("Clicking checkbox at " + pos.checkbox.x + "," + pos.checkbox.y);
        await clickAt(pos.checkbox.x, pos.checkbox.y);
        await sleep(500);
      }

      // Check if checkbox is now checked
      let checked = await eval_(`(function() { var cb = document.getElementById('v-0'); return cb ? cb.checked : 'not found'; })()`);
      L("Checked: " + checked);

      // Click Continue button using CDP
      if (pos.button) {
        L("Clicking Continue at " + pos.button.x + "," + pos.button.y);
        await clickAt(pos.button.x, pos.button.y);
        await sleep(3000);
      }

      // Check what page we're on now
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("After click page:");
      L(pageText.substring(0, 500));

      // If still on Q1, try a different approach - use dispatchEvent with proper Vue reactive handling
      if (pageText.includes('Question 1/10')) {
        L("\nStill on Q1 - trying Vue-compatible approach");

        // Try triggering input event on the checkbox wrapper
        let r = await eval_(`
          (function() {
            var cb = document.getElementById('v-0');
            if (!cb) return 'not found';

            // Method 1: Direct property set + trigger
            var desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
            desc.set.call(cb, true);
            cb.dispatchEvent(new Event('input', { bubbles: true }));
            cb.dispatchEvent(new Event('change', { bubbles: true }));
            cb.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));

            // Check if there's a Vue instance
            if (cb.__vue__) return 'has vue: ' + cb.checked;
            if (cb._vei) return 'has vue3 events: ' + cb.checked;

            return 'checked: ' + cb.checked;
          })()
        `);
        L("Vue approach: " + r);
        await sleep(500);

        // Try clicking Continue again
        if (pos.button) {
          await clickAt(pos.button.x, pos.button.y);
          await sleep(3000);
        }

        pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("After Vue approach:");
        L(pageText.substring(0, 500));
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
