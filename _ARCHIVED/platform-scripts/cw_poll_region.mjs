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

    const clickRadio = async (text) => {
      return await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.toLowerCase().includes('${text}'.toLowerCase())) {
              radios[i].click();
              if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
              return 'clicked: ' + label;
            }
          }
          return 'not found: ${text}';
        })()
      `);
    };

    const clickContinue = async () => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked'; }
          }
          return 'no continue';
        })()
      `);
    };

    const setInput = async (value) => {
      return await eval_(`
        (function() {
          var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
          if (!inp) return 'no input';
          inp.focus();
          var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          ns.call(inp, '${value}');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          return 'set: ${value}';
        })()
      `);
    };

    (async () => {
      // Answer remaining profiler questions in a loop
      for (let q = 0; q < 10; q++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
        let ql = pageText.toLowerCase();

        // Check if on survey wall (no more questions)
        if (!ql.includes('question') || !ql.includes('left')) {
          if (ql.includes('choose a survey') || ql.includes('earn dollars')) {
            L("ON SURVEY WALL - profile complete!");
            break;
          }
        }

        let leftMatch = pageText.match(/(\d+) Questions? left/);
        let left = leftMatch ? leftMatch[1] : '?';

        L("\n=== Profiler Q" + q + " (" + left + " left) ===");
        L("Page: " + pageText.substring(0, 300));

        let answered = false;
        let r;

        // Region
        if (ql.includes('region')) {
          r = await clickRadio('West');
          L("Region: " + r); answered = true;
        }
        // DMA
        else if (ql.includes('dma')) {
          r = await setInput('881');
          L("DMA: " + r); answered = true;
        }
        // City
        else if (ql.includes('city') || ql.includes('metro')) {
          r = await setInput('Sandpoint');
          L("City: " + r); answered = true;
        }
        // State
        else if (ql.includes('state')) {
          r = await clickRadio('IDAHO');
          if (r.includes('not found')) r = await clickRadio('Idaho');
          L("State: " + r); answered = true;
        }
        // Division
        else if (ql.includes('division') || ql.includes('census')) {
          r = await clickRadio('Mountain');
          if (r.includes('not found')) r = await clickRadio('Pacific');
          if (r.includes('not found')) r = await clickRadio('West');
          L("Division: " + r); answered = true;
        }
        // Age range
        else if (ql.includes('age') && (ql.includes('range') || ql.includes('group') || ql.includes('bracket'))) {
          r = await clickRadio('50');
          if (r.includes('not found')) r = await clickRadio('45');
          L("Age range: " + r); answered = true;
        }
        // Standard of living / household size
        else if (ql.includes('household') && ql.includes('size')) {
          r = await clickRadio('1');
          if (r.includes('not found')) r = await clickRadio('Single');
          L("Household: " + r); answered = true;
        }
        // Any other question
        else {
          // Check for input field
          let hasInput = await eval_(`!!document.querySelector('input[type="text"], input[type="number"], input[type="tel"]')`);
          if (hasInput) {
            r = await setInput('N/A');
            L("Generic input: " + r);
          } else {
            r = await eval_(`
              (function() {
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                  var mid = Math.floor(radios.length / 2);
                  radios[mid].click();
                  if (radios[mid].labels && radios[mid].labels[0]) radios[mid].labels[0].click();
                  return 'radio ' + mid + '/' + radios.length + ': ' + (radios[mid].labels?.[0]?.textContent || '').trim().substring(0,50);
                }
                return 'no elements';
              })()
            `);
            L("Generic radio: " + r);
          }
          answered = true;
        }

        await sleep(500);
        r = await clickContinue();
        L("Continue: " + r);
        await sleep(3000);
      }

      // Now try to click surveys
      L("\n=== TRYING SURVEYS ===");
      let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      L("Current page: " + pageText.substring(0, 200));

      let cardCount = await eval_(`document.querySelectorAll('[class*="SurveyCard_container"]').length`);
      L("Cards found: " + cardCount);

      if (cardCount > 0) {
        for (let attempt = 0; attempt < Math.min(cardCount, 8); attempt++) {
          let r = await eval_(`
            (function() {
              var cards = document.querySelectorAll('[class*="SurveyCard_container"]');
              if (cards.length <= ${attempt}) return 'no card';
              var text = cards[${attempt}].textContent;
              var priceM = text.match(/\\+(\\d+\\.\\d+)/);
              var timeM = text.match(/(\\d+) Minutes/);
              cards[${attempt}].click();
              return '$' + (priceM?priceM[1]:'?') + '/' + (timeM?timeM[1]:'?') + 'min';
            })()
          `);
          L("\n--- Survey #" + attempt + ": " + r + " ---");
          await sleep(4000);

          pageText = await eval_(`document.body.innerText.substring(0, 800)`);

          // Handle profiler again if needed
          if (pageText.includes('Question') && pageText.includes('left')) {
            let ql2 = pageText.toLowerCase();
            L("Another profiler Q: " + pageText.substring(0, 100));
            if (ql2.includes('region')) await clickRadio('West');
            else if (ql2.includes('dma')) await setInput('881');
            else if (ql2.includes('state')) await clickRadio('IDAHO');
            else if (ql2.includes('division')) { let x = await clickRadio('Mountain'); if (x.includes('not found')) await clickRadio('Pacific'); }
            else {
              await eval_(`(function() { var r = document.querySelectorAll('input[type="radio"]'); if (r.length > 0) { var m = Math.floor(r.length/2); r[m].click(); if(r[m].labels&&r[m].labels[0]) r[m].labels[0].click(); } })()`);
            }
            await sleep(500);
            await clickContinue();
            await sleep(3000);
            pageText = await eval_(`document.body.innerText.substring(0, 800)`);
          }

          if (pageText.includes('not available') || pageText.includes('Unfortunately')) {
            L("NOT AVAILABLE");
            continue;
          }

          // Check for new tabs
          let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          let newTab = allTabs.find(t => t.type === 'page' && !t.url.includes('ayet.io') && t.url.startsWith('http'));
          if (newTab) {
            L("*** SURVEY OPENED: " + newTab.url);
            break;
          }

          if (!pageText.includes('Choose a survey') && !pageText.includes('not available')) {
            L("*** PAGE CHANGED: " + pageText.substring(0, 300));
            break;
          }
        }
      }

      // Final
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\n=== FINAL ===");
      allTabs.forEach(t => { if (t.url) L(t.type + ": " + t.url.substring(0, 120)); });
      pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      L("Page: " + pageText.substring(0, 300));

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
