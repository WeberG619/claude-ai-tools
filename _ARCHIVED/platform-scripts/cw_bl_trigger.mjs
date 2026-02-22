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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
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

      // Step 1: Set checkbox checked=true and trigger jQuery change
      let result = await eval_(`
        (function() {
          // Find Architecture checkbox
          var labels = document.querySelectorAll('.js-question-options label');
          var archCb = null;
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim() === 'Architecture') {
              archCb = labels[i].querySelector('input[type="checkbox"]');
              break;
            }
          }
          if (!archCb) return 'Architecture checkbox not found';

          // Set checked directly (don't toggle)
          archCb.checked = true;

          // Trigger jQuery change event - this fires the screener.min.js handler
          jQuery(archCb).trigger('change');

          var btn = document.getElementById('ctl00_Content_btnContinue');
          return JSON.stringify({
            checked: archCb.checked,
            id: archCb.id,
            btnDisabled: btn.disabled,
            btnClass: btn.className
          });
        })()
      `);
      L("After set+trigger: " + result);

      let r = JSON.parse(result);

      if (r.btnDisabled) {
        L("Button STILL disabled after trigger. Trying direct toggleSubmission...");
        // Call the toggleSubmission function directly
        await eval_(`toggleSubmission(true)`);
        await sleep(200);
        let btnState = await eval_(`
          JSON.stringify({
            disabled: document.getElementById('ctl00_Content_btnContinue').disabled,
            className: document.getElementById('ctl00_Content_btnContinue').className
          })
        `);
        L("After toggleSubmission(true): " + btnState);
      }

      await sleep(500);

      // Step 2: Check final button state
      let btnFinal = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          return JSON.stringify({
            disabled: btn.disabled,
            className: btn.className
          });
        })()
      `);
      L("Final button: " + btnFinal);

      let bf = JSON.parse(btnFinal);

      // Step 3: Scroll to button and CDP click it
      await eval_(`document.getElementById('ctl00_Content_btnContinue').scrollIntoView({ behavior: 'instant', block: 'center' })`);
      await sleep(300);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        })()
      `);
      let br = JSON.parse(btnRect);
      L("CDP clicking at (" + br.x + ", " + br.y + ")");
      await cdpClick(br.x, br.y);
      await sleep(5000);

      // Step 4: Check result
      let newUrl = await eval_(`window.location.href`);
      let firstLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
      L("\nResult:");
      L("URL: " + newUrl);
      L("Q: " + firstLine);

      // If still same, try JS click
      if (firstLine.includes('industries')) {
        L("Still same - trying JS button click");
        await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            btn.disabled = false;
            btn.classList.remove('disabled');
            btn.click();
          })()
        `);
        await sleep(5000);
        firstLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        L("After JS click Q: " + firstLine);
      }

      // If STILL same, try Enter key
      if (firstLine.includes('industries')) {
        L("Still same - trying Enter keypress via CDP");
        // First make sure checkbox is checked
        await eval_(`
          (function() {
            var cb = document.getElementById('option-6');
            cb.checked = true;
            jQuery(cb).trigger('change');
          })()
        `);
        await sleep(300);
        // Send Enter key via CDP
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
        await sleep(100);
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
        await sleep(5000);

        firstLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        L("After Enter Q: " + firstLine);
      }

      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nPage:\n" + pageText.substring(0, 800));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

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
