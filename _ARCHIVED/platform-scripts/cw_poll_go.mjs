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
  if (!pageTab) { L("No ayet.io tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
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
      L("=== RAPID SURVEY ATTEMPTS ===");

      // First dismiss any "not available" message if present
      await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, [class*="close"], [class*="dismiss"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t.includes('try another') || t.includes('close') || t.includes('ok')) {
              btns[i].click();
              return 'dismissed';
            }
          }
          return 'nothing to dismiss';
        })()
      `);
      await sleep(1000);

      // Try each survey card sequentially
      let tried = new Set();
      for (let attempt = 0; attempt < 12; attempt++) {
        // Get card list and click untried one
        let r = await eval_(`
          (function() {
            var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
            var tried = ${JSON.stringify([...tried])};
            for (var i = 0; i < cards.length; i++) {
              if (tried.includes(i)) continue;
              var text = cards[i].textContent;
              var priceM = text.match(/\\+(\\d+\\.\\d+)/);
              var timeM = text.match(/(\\d+) Minutes/);
              if (priceM && timeM) {
                cards[i].click();
                return JSON.stringify({ idx: i, price: priceM[1], time: timeM[1], text: text.substring(0,80) });
              }
            }
            return 'none';
          })()
        `);

        if (r === 'none') { L("No more untried cards"); break; }

        let info;
        try { info = JSON.parse(r); } catch(e) { L("Parse error: " + r); break; }
        tried.add(info.idx);

        L("\n--- #" + attempt + " Card " + info.idx + ": $" + info.price + "/" + info.time + "min ---");
        await sleep(3000);

        // Check result
        let pageText = await eval_(`document.body.innerText.substring(0, 800)`);
        let url = await eval_(`window.location.href`);

        // Handle profiler questions
        if (pageText.includes('Question') && pageText.includes('left')) {
          L("Profiler Q - auto-answering");
          let ql = pageText.toLowerCase();
          if (ql.includes('dma') || ql.includes('metro') || ql.includes('market area')) {
            await eval_(`(function() { var inp = document.querySelector('input[type="text"]'); if (inp) { inp.focus(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, '881'); inp.dispatchEvent(new Event('input', {bubbles:true})); inp.dispatchEvent(new Event('change', {bubbles:true})); } })()`);
          } else {
            // Click middle radio or set generic
            await eval_(`(function() { var r = document.querySelectorAll('input[type="radio"]'); if (r.length > 0) { var m = Math.floor(r.length/2); r[m].click(); if(r[m].labels&&r[m].labels[0]) r[m].labels[0].click(); } })()`);
          }
          await sleep(500);
          await eval_(`(function() { var b = document.querySelectorAll('button'); for(var i=0;i<b.length;i++) if(b[i].textContent.trim().toLowerCase()==='continue') b[i].click(); })()`);
          await sleep(3000);
          pageText = await eval_(`document.body.innerText.substring(0, 800)`);
        }

        if (pageText.includes('not available') || pageText.includes('Unfortunately')) {
          L("NOT AVAILABLE");
          continue;
        }

        // Check for new tab (survey opened externally)
        let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
        let newTab = allTabs.find(t => t.type === 'page' && !t.url.includes('ayet.io') && t.url.startsWith('http'));
        if (newTab) {
          L("*** SURVEY OPENED IN NEW TAB: " + newTab.url.substring(0, 120));
          break;
        }

        // Check if URL changed (survey loaded in same page)
        if (!url.includes('ayet.io/surveys') && !url.includes('ayet.io/profiler')) {
          L("*** URL CHANGED: " + url);
          L("Page: " + pageText.substring(0, 400));
          break;
        }

        // Check if page content changed (survey loaded inline)
        if (!pageText.includes('Choose a survey') && !pageText.includes('not available')) {
          L("*** PAGE CHANGED");
          L("Page: " + pageText.substring(0, 400));
          break;
        }

        L("Still on wall");
      }

      // Final state
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\n=== FINAL ===");
      allTabs.forEach(t => { if (t.url) L(t.type + ": " + t.url.substring(0, 120)); });

      let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("Page: " + pageText.substring(0, 500));

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
