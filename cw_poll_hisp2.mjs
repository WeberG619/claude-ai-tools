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
      L("=== FIXING HISPANIC SEARCH ===");

      // First clear the old N/A value and try keyboard-based input
      // Use CDP Input.dispatchKeyEvent to type character by character
      // This better simulates real user input for React/MUI components

      // First, focus the input
      let r = await eval_(`
        (function() {
          var inp = document.querySelector('input.MuiInputBase-input, input[type="text"]');
          if (!inp) return 'no input';
          inp.focus();
          inp.click();
          // Clear it
          inp.select();
          return 'focused: ' + inp.id + ' value: ' + inp.value;
        })()
      `);
      L("Focus: " + r);

      // Use keyboard to clear and type
      // First select all and delete
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
      await sleep(500);

      // Type "No" character by character
      const typeText = async (text) => {
        for (const char of text) {
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
          await sleep(100);
        }
      };
      await typeText("No");
      await sleep(2000);

      // Check what appeared
      r = await eval_(`
        (function() {
          var inp = document.querySelector('input.MuiInputBase-input, input[type="text"]');
          var val = inp ? inp.value : 'no input';
          var radios = document.querySelectorAll('input[type="radio"]');
          var labels = [];
          for (var i = 0; i < radios.length; i++) {
            var l = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!l) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) l = p.textContent.trim(); }
            labels.push(l.substring(0, 80));
          }
          // Also check for any list items or options
          var listItems = [];
          document.querySelectorAll('li, [role="option"], [class*="option"], [class*="answer"]').forEach(function(el) {
            var t = el.textContent.trim();
            if (t.length > 2 && t.length < 100 && !t.includes('Search')) listItems.push(t.substring(0, 80));
          });
          return JSON.stringify({ inputValue: val, radios: labels, listItems: listItems.slice(0, 10) });
        })()
      `);
      L("After typing: " + r);

      // Check page text
      let pageText = await eval_(`document.body.innerText.substring(0, 800)`);
      L("Page: " + pageText.substring(0, 400));

      // Try clicking on the "No , not of Hispanic" text if visible
      r = await eval_(`
        (function() {
          // Find any element that contains "not of Hispanic"
          var allEls = document.querySelectorAll('label, span, div, p, li');
          for (var i = 0; i < allEls.length; i++) {
            var ownText = '';
            for (var j = 0; j < allEls[i].childNodes.length; j++) {
              if (allEls[i].childNodes[j].nodeType === 3) ownText += allEls[i].childNodes[j].textContent;
            }
            ownText = ownText.trim();
            var fullText = allEls[i].textContent.trim();
            if ((fullText.includes('not of Hispanic') || fullText.includes('No , not of') || fullText.includes('No, not of')) && fullText.length < 100) {
              allEls[i].click();
              return 'clicked element: ' + allEls[i].tagName + ' - ' + fullText.substring(0, 80);
            }
          }
          return 'No matching element found';
        })()
      `);
      L("Direct click: " + r);
      await sleep(1000);

      // Check radios again
      r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          var checked = [];
          for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) {
              var l = (radios[i].labels?.[0]?.textContent || '').trim();
              checked.push(l);
            }
          }
          return 'checked: ' + JSON.stringify(checked);
        })()
      `);
      L("Checked: " + r);

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
      pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
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
