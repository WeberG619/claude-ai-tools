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

      // Step 1: Find Architecture checkbox index (it's option-6 based on previous runs)
      let archIdx = await eval_(`
        (function() {
          var labels = document.querySelectorAll('.js-question-options label');
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim() === 'Architecture') {
              return i;
            }
          }
          return -1;
        })()
      `);
      L("Architecture index: " + archIdx);

      // Step 2: Use jQuery to click the checkbox - this triggers the bound change event
      let clickResult = await eval_(`
        (function() {
          var idx = ${archIdx};
          var cb = document.getElementById('option-' + idx);
          if (!cb) return 'checkbox not found';

          // Use jQuery .click() which triggers bound events
          jQuery('#option-' + idx).click();

          return JSON.stringify({
            checked: cb.checked,
            btnDisabled: document.getElementById('ctl00_Content_btnContinue').disabled,
            btnClass: document.getElementById('ctl00_Content_btnContinue').className
          });
        })()
      `);
      L("After jQuery click: " + clickResult);

      await sleep(500);

      // Step 3: Recheck button state
      let btnState = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          return JSON.stringify({
            disabled: btn.disabled,
            className: btn.className,
            hasDisabledAttr: btn.hasAttribute('disabled')
          });
        })()
      `);
      L("Button state: " + btnState);

      let bs = JSON.parse(btnState);

      // Step 4: Scroll button into view and get position
      await eval_(`document.getElementById('ctl00_Content_btnContinue').scrollIntoView({ behavior: 'instant', block: 'center' })`);
      await sleep(300);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            disabled: btn.disabled
          });
        })()
      `);
      L("Button rect: " + btnRect);
      let br = JSON.parse(btnRect);

      if (!br.disabled) {
        // CDP click the enabled button
        L("CDP clicking Continue at (" + br.x + ", " + br.y + ")");
        await cdpClick(br.x, br.y);
      } else {
        // Try jQuery click on the button too
        L("Button still disabled - trying jQuery submit");
        await eval_(`jQuery('#ctl00_Content_btnContinue').removeAttr('disabled').removeClass('disabled').click()`);
      }

      await sleep(5000);

      // Step 5: Check result
      let newUrl = await eval_(`window.location.href`);
      let firstLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
      L("\nResult:");
      L("URL: " + newUrl);
      L("Q: " + firstLine);

      // If still same question, check what went wrong
      if (firstLine.includes('industries')) {
        L("\nStill on same page. Checking page state...");
        let pageState = await eval_(`
          (function() {
            var checked = [];
            document.querySelectorAll('input:checked').forEach(function(c) {
              checked.push(c.id + '=' + c.value);
            });
            return JSON.stringify({
              checked: checked,
              formAction: document.querySelector('form').action,
              btnDisabled: document.getElementById('ctl00_Content_btnContinue').disabled
            });
          })()
        `);
        L("Page state: " + pageState);

        // Try one more thing: form.submit() with checked checkbox
        L("Trying form.submit()...");
        await eval_(`document.querySelector('form').submit()`);
        await sleep(5000);

        let newQ = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        L("After form.submit: " + newQ);
      }

      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nFull:\n" + pageText.substring(0, 800));

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
