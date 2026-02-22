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
      L("=== ANSWERING STATE QUESTION ===");

      // Click IDAHO radio
      let r = await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.toUpperCase() === 'IDAHO' || label.toLowerCase() === 'idaho') {
              radios[i].click();
              if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
              return 'clicked: ' + label;
            }
          }
          return 'Idaho not found in radios';
        })()
      `);
      L("State: " + r);
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

      // Check if more profiler questions or survey wall
      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      let url = await eval_(`window.location.href`);
      L("\nURL: " + url);

      // Loop to handle any remaining profiler questions
      for (let q = 0; q < 5; q++) {
        pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
        let ql = pageText.toLowerCase();

        if (ql.includes('question') && ql.includes('left')) {
          L("\n--- More profiler Q" + q + " ---");
          L("Page: " + pageText.substring(0, 300));

          // Answer based on content
          if (ql.includes('dma')) {
            await eval_(`
              (function() {
                var inp = document.querySelector('input[type="text"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
                if (inp) { inp.focus(); var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; ns.call(inp, '881'); inp.dispatchEvent(new Event('input', { bubbles: true })); inp.dispatchEvent(new Event('change', { bubbles: true })); }
              })()
            `);
            L("  Set DMA: 881");
          } else {
            // Try to find and click a matching radio
            let heading = pageText.split('\\n').find(l => l.includes('?')) || '';
            let hl2 = heading.toLowerCase();

            if (hl2.includes('city') || hl2.includes('metro')) {
              r = await eval_(`
                (function() {
                  var inp = document.querySelector('input[type="text"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
                  if (inp) { inp.focus(); var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; ns.call(inp, 'Sandpoint'); inp.dispatchEvent(new Event('input', { bubbles: true })); inp.dispatchEvent(new Event('change', { bubbles: true })); return 'set Sandpoint'; }
                  return 'no input';
                })()
              `);
              L("  City: " + r);
            } else {
              // Generic: pick middle radio or set generic input
              r = await eval_(`
                (function() {
                  var radios = document.querySelectorAll('input[type="radio"]');
                  if (radios.length > 0) {
                    var mid = Math.floor(radios.length / 2);
                    radios[mid].click();
                    if (radios[mid].labels && radios[mid].labels[0]) radios[mid].labels[0].click();
                    return 'radio ' + mid + '/' + radios.length + ': ' + (radios[mid].labels?.[0]?.textContent || '').trim().substring(0,40);
                  }
                  var inp = document.querySelector('input[type="text"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
                  if (inp) { inp.focus(); var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; ns.call(inp, 'N/A'); inp.dispatchEvent(new Event('input', { bubbles: true })); inp.dispatchEvent(new Event('change', { bubbles: true })); return 'input N/A'; }
                  return 'no elements';
                })()
              `);
              L("  Generic: " + r);
            }
          }

          await sleep(500);
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
          L("  Continue: " + r);
          await sleep(3000);
        } else {
          L("No more profiler questions");
          break;
        }
      }

      // Now check survey wall
      pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      url = await eval_(`window.location.href`);
      L("\n=== FINAL STATE ===");
      L("URL: " + url);
      L("Page: " + pageText.substring(0, 800));

      // Count available surveys
      let cardCount = await eval_(`document.querySelectorAll('[class*="SurveyCard_container"]').length`);
      L("Survey cards: " + cardCount);

      // Check tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs: " + JSON.stringify(allTabs.map(t => ({ type: t.type, url: t.url.substring(0, 100) }))));

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
