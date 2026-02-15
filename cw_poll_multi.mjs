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
      L("=== TRYING MULTIPLE SURVEYS ===");

      for (let attempt = 0; attempt < 8; attempt++) {
        // Get all cards and pick the one at index = attempt
        let r = await eval_(`
          (function() {
            var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
            var list = [];
            for (var i = 0; i < cards.length; i++) {
              var text = cards[i].textContent;
              var priceM = text.match(/\\+(\\d+\\.\\d+)/);
              var timeM = text.match(/(\\d+) Minutes/);
              var qualM = text.match(/(\\d+) Qualification/);
              if (priceM && timeM) {
                list.push({ idx: i, price: parseFloat(priceM[1]), time: parseInt(timeM[1]), quals: qualM ? parseInt(qualM[1]) : 99 });
              }
            }
            // Sort by fewest qualifications, then best $/min
            list.sort(function(a,b) {
              if (a.quals !== b.quals) return a.quals - b.quals;
              return (b.price/b.time) - (a.price/a.time);
            });
            var pick = list[${attempt}];
            if (!pick) return 'no card at index ${attempt}';
            cards[pick.idx].click();
            return '$' + pick.price + '/' + pick.time + 'min/' + pick.quals + 'q';
          })()
        `);
        L("\n--- Attempt " + attempt + ": " + r + " ---");
        await sleep(4000);

        // Check if we got a survey or "not available" or profiler question
        let pageText = await eval_(`document.body.innerText.substring(0, 800)`);
        let url = await eval_(`window.location.href`);
        L("URL: " + url.substring(0, 100));

        // Check if profiler question popped up (DMA etc)
        if (pageText.includes('Question') && pageText.includes('left')) {
          L("Profiler question appeared - answering...");
          let hl = pageText.toLowerCase();
          if (hl.includes('dma')) {
            await eval_(`
              (function() {
                var inp = document.querySelector('input[type="text"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
                if (!inp) return;
                inp.focus();
                var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                ns.call(inp, '881');
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
              })()
            `);
            await sleep(500);
            await eval_(`
              (function() {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                  if (btns[i].textContent.trim().toLowerCase() === 'continue') { btns[i].click(); return; }
                }
              })()
            `);
            L("Answered DMA: 881");
            await sleep(4000);
            pageText = await eval_(`document.body.innerText.substring(0, 800)`);
            url = await eval_(`window.location.href`);
          }
        }

        if (pageText.includes('not available')) {
          L("NOT AVAILABLE - trying next");
          continue;
        }

        // Check if survey opened in a new tab
        let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
        let newTab = allTabs.find(t => t.type === 'page' && !t.url.includes('ayet.io') && t.url.startsWith('http'));
        if (newTab) {
          L("NEW TAB OPENED: " + newTab.url.substring(0, 120));
          L("SURVEY FOUND!");
          break;
        }

        // Check if page changed from survey wall
        if (!pageText.includes('Choose a survey to earn Dollars') && !pageText.includes('not available')) {
          L("PAGE CHANGED - possible survey start");
          L("Page: " + pageText.substring(0, 400));
          break;
        }

        L("Page: " + pageText.substring(0, 200));
      }

      // Final state
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\n=== FINAL TABS ===");
      allTabs.forEach(t => L(t.type + ": " + t.url.substring(0, 120)));

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("\nFinal URL: " + url);
      L("Final page: " + pageText.substring(0, 500));

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
