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

      // Step 1: CDP click Architecture radio
      let radioInfo = await eval_(`
        (function() {
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim() === 'Architecture') {
              var radio = labels[i].querySelector('input');
              var rect = labels[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          }
          return 'not found';
        })()
      `);
      L("Radio: " + radioInfo);

      if (radioInfo !== 'not found') {
        let ri = JSON.parse(radioInfo);
        await cdpClick(ri.x, ri.y);
        await sleep(1000);
      }

      // Step 2: Check button state
      let btnState = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          return JSON.stringify({
            disabled: btn.disabled,
            className: btn.className,
            visible: btn.offsetParent !== null
          });
        })()
      `);
      L("Button state: " + btnState);

      // Step 3: Scroll button into view, then get its NEW viewport position
      let btnNewPos = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          btn.scrollIntoView({ behavior: 'instant', block: 'center' });
          // Need a moment for scroll to settle
          return 'scrolled';
        })()
      `);
      await sleep(500);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            top: Math.round(rect.top),
            bottom: Math.round(rect.bottom),
            disabled: btn.disabled
          });
        })()
      `);
      L("Button rect after scroll: " + btnRect);

      let br = JSON.parse(btnRect);

      if (br.disabled) {
        L("Button still disabled - force enabling");
        await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            btn.disabled = false;
            btn.classList.remove('disabled');
          })()
        `);
        await sleep(200);
      }

      // Step 4: CDP click the button at its viewport position
      L("CDP clicking Continue at (" + br.x + ", " + br.y + ")");
      await cdpClick(br.x, br.y);
      await sleep(5000);

      // Step 5: Check result
      let newUrl = await eval_(`window.location.href`);
      let questionLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
      L("\nAfter click:");
      L("URL: " + newUrl);
      L("Q: " + questionLine);

      // If still on same question, try JS click as fallback
      if (questionLine.includes('industries')) {
        L("Still same page - trying JS click on enabled button");
        await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            btn.disabled = false;
            btn.classList.remove('disabled');
            btn.click();
          })()
        `);
        await sleep(5000);

        newUrl = await eval_(`window.location.href`);
        questionLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        L("After JS click:");
        L("URL: " + newUrl);
        L("Q: " + questionLine);
      }

      // If STILL same page, try form submit with proper postback
      if (questionLine.includes('industries')) {
        L("Still same page - trying __doPostBack style submit");
        await eval_(`
          (function() {
            // Set the radio properly
            var labels = document.querySelectorAll('label');
            for (var i = 0; i < labels.length; i++) {
              if (labels[i].textContent.trim() === 'Architecture') {
                var radio = labels[i].querySelector('input');
                if (radio) radio.checked = true;
              }
            }
            // Try clicking the submit with a real mouse event
            var btn = document.getElementById('ctl00_Content_btnContinue');
            btn.disabled = false;
            var evt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
            btn.dispatchEvent(evt);
          })()
        `);
        await sleep(5000);

        newUrl = await eval_(`window.location.href`);
        questionLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        L("After MouseEvent:");
        L("URL: " + newUrl);
        L("Q: " + questionLine);
      }

      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nFull page:\n" + pageText.substring(0, 1000));

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
