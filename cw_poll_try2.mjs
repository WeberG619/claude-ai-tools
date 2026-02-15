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
  if (!pageTab) { L("No ayet.io tab found"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
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
      // Click the $1.15/10min survey (94 completes, 1 qual)
      L("=== TRYING $1.15/10min SURVEY ===");
      let r = await eval_(`
        (function() {
          var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
          // Sort by best value: prefer 1 qualification, short time
          var best = [];
          for (var i = 0; i < cards.length; i++) {
            var text = cards[i].textContent;
            var priceM = text.match(/\\+(\\d+\\.\\d+)/);
            var timeM = text.match(/(\\d+) Minutes/);
            var qualM = text.match(/(\\d+) Qualification/);
            if (priceM && timeM) {
              best.push({ idx: i, price: parseFloat(priceM[1]), time: parseInt(timeM[1]), quals: qualM ? parseInt(qualM[1]) : 99, text: text.substring(0, 80) });
            }
          }
          // Sort: prefer 1 qual, then best $/min
          best.sort(function(a,b) {
            if (a.quals !== b.quals) return a.quals - b.quals;
            return (b.price/b.time) - (a.price/a.time);
          });
          if (best.length > 0) {
            var pick = best[0];
            cards[pick.idx].click();
            return 'clicked: $' + pick.price + '/' + pick.time + 'min/' + pick.quals + 'q - ' + pick.text.substring(0,60);
          }
          return 'no cards found';
        })()
      `);
      L("Click: " + r);
      await sleep(5000);

      // Check what happened
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("URL: " + url);
      L("Page: " + pageText.substring(0, 600));

      // If survey not available, try next
      if (pageText.includes('not available')) {
        L("Survey not available, trying next...");
        await sleep(2000);

        // Try next best
        r = await eval_(`
          (function() {
            var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
            var best = [];
            for (var i = 0; i < cards.length; i++) {
              var text = cards[i].textContent;
              var priceM = text.match(/\\+(\\d+\\.\\d+)/);
              var timeM = text.match(/(\\d+) Minutes/);
              var qualM = text.match(/(\\d+) Qualification/);
              if (priceM && timeM) {
                best.push({ idx: i, price: parseFloat(priceM[1]), time: parseInt(timeM[1]), quals: qualM ? parseInt(qualM[1]) : 99, text: text.substring(0, 80) });
              }
            }
            best.sort(function(a,b) {
              if (a.quals !== b.quals) return a.quals - b.quals;
              return (b.price/b.time) - (a.price/a.time);
            });
            // Skip first (already tried), pick second
            if (best.length > 1) {
              var pick = best[1];
              cards[pick.idx].click();
              return 'clicked: $' + pick.price + '/' + pick.time + 'min/' + pick.quals + 'q';
            }
            return 'no more cards';
          })()
        `);
        L("Click2: " + r);
        await sleep(5000);

        url = await eval_(`window.location.href`);
        pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
        L("URL2: " + url);
        L("Page2: " + pageText.substring(0, 600));
      }

      // If still not available, try third
      if (pageText.includes('not available')) {
        L("Second survey not available, trying third...");
        await sleep(2000);

        r = await eval_(`
          (function() {
            var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
            var best = [];
            for (var i = 0; i < cards.length; i++) {
              var text = cards[i].textContent;
              var priceM = text.match(/\\+(\\d+\\.\\d+)/);
              var timeM = text.match(/(\\d+) Minutes/);
              var qualM = text.match(/(\\d+) Qualification/);
              if (priceM && timeM) {
                best.push({ idx: i, price: parseFloat(priceM[1]), time: parseInt(timeM[1]), quals: qualM ? parseInt(qualM[1]) : 99, text: text.substring(0, 80) });
              }
            }
            best.sort(function(a,b) {
              if (a.quals !== b.quals) return a.quals - b.quals;
              return (b.price/b.time) - (a.price/a.time);
            });
            if (best.length > 2) {
              var pick = best[2];
              cards[pick.idx].click();
              return 'clicked: $' + pick.price + '/' + pick.time + 'min/' + pick.quals + 'q';
            }
            return 'no more cards';
          })()
        `);
        L("Click3: " + r);
        await sleep(5000);

        url = await eval_(`window.location.href`);
        pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
        L("URL3: " + url);
        L("Page3: " + pageText.substring(0, 600));
      }

      // Check for new tabs (survey might open in new tab)
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      let tabInfo = allTabs.map(t => ({ type: t.type, url: t.url.substring(0, 120) }));
      L("\nAll tabs: " + JSON.stringify(tabInfo));

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
