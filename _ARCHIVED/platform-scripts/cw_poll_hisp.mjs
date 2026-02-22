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
      L("=== FIXING HISPANIC QUESTION ===");

      // First, check the page structure for the search input
      let structure = await eval_(`
        (function() {
          var allInputs = document.querySelectorAll('input');
          var results = [];
          for (var i = 0; i < allInputs.length; i++) {
            results.push({
              type: allInputs[i].type,
              id: allInputs[i].id,
              name: allInputs[i].name,
              placeholder: allInputs[i].placeholder,
              value: allInputs[i].value,
              class: allInputs[i].className.substring(0, 60),
              visible: allInputs[i].offsetParent !== null
            });
          }
          // Also check for radio buttons
          var radios = document.querySelectorAll('input[type="radio"]');
          var radioLabels = [];
          for (var i = 0; i < Math.min(radios.length, 10); i++) {
            var l = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!l) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) l = p.textContent.trim(); }
            radioLabels.push(l.substring(0, 60));
          }
          return JSON.stringify({ inputs: results, radios: radioLabels });
        })()
      `);
      L("Structure: " + structure);

      // Clear the search input and type "not of hispanic" to filter
      let r = await eval_(`
        (function() {
          // Find the search input (has "Search" placeholder or similar)
          var inputs = document.querySelectorAll('input[type="text"], input[type="search"]');
          for (var i = 0; i < inputs.length; i++) {
            var inp = inputs[i];
            if (inp.placeholder && inp.placeholder.toLowerCase().includes('search')) {
              inp.focus();
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              ns.call(inp, 'not of');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'typed "not of" in search: ' + inp.id;
            }
          }
          // Fallback: try any visible text input
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null) {
              inputs[i].focus();
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inputs[i], '');
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              ns.call(inputs[i], 'not of');
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              return 'typed in fallback input: ' + inputs[i].id;
            }
          }
          return 'no search input found';
        })()
      `);
      L("Search: " + r);
      await sleep(2000);

      // Now check what radio options appeared after search
      r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          var results = [];
          for (var i = 0; i < radios.length; i++) {
            var l = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!l) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) l = p.textContent.trim(); }
            results.push(l.substring(0, 80));
          }
          return JSON.stringify(results);
        })()
      `);
      L("Filtered radios: " + r);

      // Click "No, not of Hispanic" option
      r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.toLowerCase().includes('not of hispanic') || label.toLowerCase().includes('no , not') || label.toLowerCase().includes('no, not')) {
              radios[i].click();
              if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
              return 'clicked: ' + label;
            }
          }
          // Try just "No"
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.toLowerCase().startsWith('no')) {
              radios[i].click();
              if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
              return 'clicked: ' + label;
            }
          }
          return 'No option not found';
        })()
      `);
      L("Click: " + r);
      await sleep(500);

      // Click Continue
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked'; }
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
      L("Screenshot saved");

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
