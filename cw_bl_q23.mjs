import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 90000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const blTab = tabs.find(t => t.url.includes('bitlabs') && t.url.includes('qualification'));
  if (!blTab) { L("No BitLabs qualification tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blTab.webSocketDebuggerUrl);
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

    const clickOptionByText = async (target) => {
      return await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
          for (var i = 0; i < cbs.length; i++) {
            var parent = cbs[i].parentElement;
            for (var depth = 0; depth < 5 && parent; depth++) {
              var t = parent.textContent.trim();
              if ((t === target || t.indexOf(target) >= 0) && t.length < target.length + 20) {
                cbs[i].click();
                return 'checked: ' + t.substring(0, 50) + ' checked=' + cbs[i].checked;
              }
              parent = parent.parentElement;
            }
          }
          return 'NOT_FOUND';
        })()
      `);
    };

    const clickContinue = async () => {
      let btnInfo = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, a, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Continue' || t === 'Next' || t === 'Start survey' || t === 'Start') {
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled || btns[i].getAttribute('disabled') !== null });
            }
          }
          return 'not found';
        })()
      `);
      if (btnInfo === 'not found') return 'no button';
      let bi = JSON.parse(btnInfo);
      await cdpClick(bi.x, bi.y);
      return 'clicked ' + bi.text + ' at (' + bi.x + ',' + bi.y + ') disabled=' + bi.disabled;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      for (let round = 0; round < 8; round++) {
        await sleep(1000);
        let pageText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'loading'`);
        let url = await eval_(`window.location.href`);
        L("\n=== Round " + round + " ===");

        let lower = pageText.toLowerCase();

        // End states
        if (lower.includes('your profile matches') || lower.includes('congratulations') || lower.includes('qualified')) {
          L("QUALIFIED! " + pageText.substring(0, 200));
          await sleep(1000);
          let r = await clickContinue();
          L("Start: " + r);
          await sleep(5000);
          break;
        }
        if (lower.includes('sorry') || lower.includes('not a match') || lower.includes('unfortunately')) {
          L("NOT QUALIFIED: " + pageText.substring(0, 200));
          break;
        }
        if (!url.includes('bitlabs')) {
          L("LEFT BITLABS: " + url);
          break;
        }

        // Get question
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let qIdx = lines.findIndex(l => l.startsWith('Question'));
        let question = qIdx >= 0 && qIdx + 1 < lines.length ? lines[qIdx + 1] : lines.find(l => l.includes('?') || l.includes('...')) || lines[0];
        L("Q: " + question);
        let qLower = question.toLowerCase();

        let target = null;
        if (qLower.includes('department')) {
          target = 'Creative/Design';
        } else if (qLower.includes('employ') && qLower.includes('people')) {
          target = '1 to 5';
        } else if (qLower.includes('role') || qLower.includes('title') || qLower.includes('level') || qLower.includes('seniority') || qLower.includes('position')) {
          target = 'Owner';
        } else if (qLower.includes('revenue') || qLower.includes('budget')) {
          target = 'Less than';
        } else if (qLower.includes('decision') || qLower.includes('purchase') || qLower.includes('influence') || qLower.includes('authority')) {
          target = 'Final';
        } else if (qLower.includes('industry') || qLower.includes('sector')) {
          target = 'Architecture';
        } else if (qLower.includes('income')) {
          target = '$75,000';
        } else if (qLower.includes('age') || qLower.includes('how old')) {
          target = '50';
        } else if (qLower.includes('gender')) {
          target = 'Male';
        } else if (qLower.includes('education')) {
          target = 'Some college';
        } else {
          L("UNKNOWN Q: " + question);
          L("Page: " + pageText.substring(0, 500));
          // Try first option as default
          target = lines.find((l, i) => i > (qIdx || 0) + 1 && l.length > 2 && l.length < 60 && l !== 'Continue');
          if (target) L("Guessing first option: " + target);
        }

        if (target) {
          L("-> " + target);
          let result = await clickOptionByText(target);
          L("   " + result);

          if (result === 'NOT_FOUND') {
            // Try searching with a search box
            let searched = await eval_(`
              (function() {
                var search = document.querySelector('input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]');
                if (search) {
                  search.value = ${JSON.stringify(target)};
                  search.dispatchEvent(new Event('input', { bubbles: true }));
                  return 'searched: ' + ${JSON.stringify(target)};
                }
                return 'no search box';
              })()
            `);
            L("   " + searched);
            await sleep(500);

            // Try clicking the filtered option
            result = await clickOptionByText(target);
            L("   After search: " + result);
          }

          await sleep(500);
          let cont = await clickContinue();
          L("   " + cont);
          await sleep(3000);
        }
      }

      // Final
      L("\n=== FINAL ===");
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      allTabs.filter(t => t.type === 'page' || t.type === 'iframe').forEach(t => L("Tab: " + t.type + " " + t.url.substring(0, 100)));

      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 1500));

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
