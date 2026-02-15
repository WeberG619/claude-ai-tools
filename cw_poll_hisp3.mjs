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
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('ayet.io'));
  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
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

    (async () => {
      L("=== CLICK HISPANIC RADIO DIRECTLY ===");

      // The radios are visible now (from previous search). Click the first one.
      let r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.includes('not of Hispanic')) {
              // Click the radio input itself
              radios[i].click();
              radios[i].checked = true;
              radios[i].dispatchEvent(new Event('change', { bubbles: true }));
              radios[i].dispatchEvent(new Event('click', { bubbles: true }));
              // Also try clicking the label
              if (radios[i].labels && radios[i].labels[0]) {
                radios[i].labels[0].click();
              }
              return 'clicked radio: ' + label + ' checked=' + radios[i].checked;
            }
          }
          // If not visible, need to search first
          return 'radio not found - need search first';
        })()
      `);
      L("Radio click: " + r);

      if (r.includes('not found')) {
        // Need to type in search first
        L("Searching...");
        await eval_(`
          (function() {
            var inp = document.querySelector('input.MuiInputBase-input, input[type="text"]');
            if (inp) { inp.focus(); inp.click(); inp.select(); }
          })()
        `);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(300);
        for (const char of "No") {
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
          await sleep(100);
        }
        await sleep(1500);

        // Now try clicking
        r = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            if (radios.length > 0) {
              radios[0].click();
              radios[0].checked = true;
              if (radios[0].labels && radios[0].labels[0]) radios[0].labels[0].click();
              var l = (radios[0].labels?.[0]?.textContent || '').trim();
              return 'clicked first radio: ' + l + ' checked=' + radios[0].checked;
            }
            return 'still no radios';
          })()
        `);
        L("After search click: " + r);
      }

      await sleep(500);

      // Use CDP mouse click on the radio position
      let pos = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          if (radios.length > 0) {
            var rect = radios[0].getBoundingClientRect();
            var labelRect = radios[0].labels && radios[0].labels[0] ? radios[0].labels[0].getBoundingClientRect() : rect;
            return JSON.stringify({
              radioX: Math.round(rect.x + rect.width/2),
              radioY: Math.round(rect.y + rect.height/2),
              labelX: Math.round(labelRect.x + labelRect.width/2),
              labelY: Math.round(labelRect.y + labelRect.height/2),
              checked: radios[0].checked,
              label: (radios[0].labels?.[0]?.textContent || '').trim().substring(0, 60)
            });
          }
          return 'no radios';
        })()
      `);
      L("Position: " + pos);

      if (pos !== 'no radios') {
        let p = JSON.parse(pos);
        // CDP mouse click on the label
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: p.labelX, y: p.labelY, button: "left", clickCount: 1 });
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.labelX, y: p.labelY, button: "left", clickCount: 1 });
        L("CDP clicked label at " + p.labelX + "," + p.labelY);
        await sleep(500);

        // Check if checked now
        let checked = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            return radios.length > 0 ? 'checked=' + radios[0].checked : 'no radios';
          })()
        `);
        L("After CDP click: " + checked);
      }

      // Click Continue
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().toLowerCase() === 'continue') { btns[i].click(); return 'clicked'; }
          }
          return 'no continue';
        })()
      `);
      L("Continue: " + r);
      await sleep(4000);

      // Check result
      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      let url = await eval_(`window.location.href`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 800));

      let cardCount = await eval_(`document.querySelectorAll('[class*="SurveyCard_container"]').length`);
      L("Survey cards: " + cardCount);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_done.png', Buffer.from(ss.data, 'base64'));

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
