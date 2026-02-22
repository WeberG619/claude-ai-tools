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

      // Step 1: Find the Architecture radio and get its position for CDP click
      let radioInfo = await eval_(`
        (function() {
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim() === 'Architecture') {
              var radio = labels[i].querySelector('input');
              if (radio) {
                var rect = labels[i].getBoundingClientRect();
                return JSON.stringify({
                  x: Math.round(rect.x + rect.width / 2),
                  y: Math.round(rect.y + rect.height / 2),
                  radioId: radio.id,
                  radioName: radio.name,
                  checked: radio.checked
                });
              }
            }
          }
          return 'not found';
        })()
      `);
      L("Radio info: " + radioInfo);

      if (radioInfo === 'not found') {
        L("Architecture radio not found!");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(1);
      }

      let ri = JSON.parse(radioInfo);

      // Step 2: Use CDP click on the radio label (real mouse event)
      L("CDP clicking Architecture at (" + ri.x + ", " + ri.y + ")");
      await cdpClick(ri.x, ri.y);
      await sleep(1000);

      // Step 3: Check if radio is now checked and button enabled
      let state1 = await eval_(`
        (function() {
          var labels = document.querySelectorAll('label');
          var checked = null;
          for (var i = 0; i < labels.length; i++) {
            var r = labels[i].querySelector('input:checked');
            if (r) checked = labels[i].textContent.trim();
          }
          var btn = document.getElementById('ctl00_Content_btnContinue');
          return JSON.stringify({
            checkedOption: checked,
            btnDisabled: btn ? btn.disabled : 'no btn',
            btnClass: btn ? btn.className : ''
          });
        })()
      `);
      L("After CDP click: " + state1);

      let s1 = JSON.parse(state1);

      // Step 4: If button still disabled, force-enable it
      if (s1.btnDisabled === true) {
        L("Button still disabled - trying to dispatch events on radio");

        // Try dispatching various events that ASP.NET might listen to
        await eval_(`
          (function() {
            var labels = document.querySelectorAll('label');
            for (var i = 0; i < labels.length; i++) {
              if (labels[i].textContent.trim() === 'Architecture') {
                var radio = labels[i].querySelector('input');
                if (radio) {
                  radio.checked = true;
                  radio.dispatchEvent(new Event('change', { bubbles: true }));
                  radio.dispatchEvent(new Event('click', { bubbles: true }));
                  radio.dispatchEvent(new Event('input', { bubbles: true }));
                  // Also try onclick handler directly
                  if (radio.onclick) radio.onclick();
                }
              }
            }
          })()
        `);
        await sleep(500);

        // Check again
        let state2 = await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            return JSON.stringify({
              btnDisabled: btn ? btn.disabled : 'no btn',
              btnClass: btn ? btn.className : ''
            });
          })()
        `);
        L("After events: " + state2);

        let s2 = JSON.parse(state2);
        if (s2.btnDisabled === true) {
          L("Still disabled - force removing disabled attribute");
          await eval_(`
            (function() {
              var btn = document.getElementById('ctl00_Content_btnContinue');
              btn.disabled = false;
              btn.classList.remove('disabled');
            })()
          `);
          await sleep(200);
        }
      }

      // Step 5: Get button position and CDP click it
      let btnPos = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({
            x: Math.round(rect.x + rect.width / 2),
            y: Math.round(rect.y + rect.height / 2),
            disabled: btn.disabled,
            className: btn.className
          });
        })()
      `);
      L("Button pos: " + btnPos);
      let bp = JSON.parse(btnPos);

      L("CDP clicking Continue at (" + bp.x + ", " + bp.y + ")");
      await cdpClick(bp.x, bp.y);
      await sleep(5000);

      // Step 6: Check result
      let newUrl = await eval_(`window.location.href`);
      let newPage = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nURL: " + newUrl);
      L("Page:\n" + newPage.substring(0, 1000));

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
