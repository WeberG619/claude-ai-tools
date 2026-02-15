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

    // Click checkbox by text (BitLabs style) using parent text walk
    const clickOption = async (targetText) => {
      let result = await eval_(`
        (function() {
          var target = ${JSON.stringify(targetText)};
          var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
          for (var i = 0; i < cbs.length; i++) {
            var parent = cbs[i].parentElement;
            for (var depth = 0; depth < 5 && parent; depth++) {
              if (parent.textContent.trim() === target || parent.textContent.trim().indexOf(target) >= 0) {
                if (parent.textContent.trim().length < target.length + 20) {
                  cbs[i].click();
                  return JSON.stringify({ checked: cbs[i].checked, text: parent.textContent.trim().substring(0, 50) });
                }
              }
              parent = parent.parentElement;
            }
          }
          // Fallback: try label click
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim().indexOf(target) >= 0 && labels[i].textContent.trim().length < target.length + 20) {
              labels[i].click();
              var inp = labels[i].querySelector('input');
              return JSON.stringify({ checked: inp ? inp.checked : 'unknown', text: labels[i].textContent.trim().substring(0, 50), method: 'label' });
            }
          }
          return 'NOT_FOUND';
        })()
      `);
      return result;
    };

    // Click Continue button via CDP
    const clickContinue = async () => {
      let btnInfo = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, a, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Continue' || t === 'Next' || t === 'Start survey' || t === 'Start') {
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled });
            }
          }
          return 'not found';
        })()
      `);

      if (btnInfo === 'not found') return 'no continue button';
      let bi = JSON.parse(btnInfo);
      if (bi.disabled) {
        await sleep(500);
        // Recheck
        btnInfo = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, a, [role="button"]');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (t === 'Continue' || t === 'Next' || t === 'Start survey' || t === 'Start') {
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btns[i].disabled });
              }
            }
            return 'not found';
          })()
        `);
        bi = JSON.parse(btnInfo);
      }
      await cdpClick(bi.x, bi.y);
      return 'clicked ' + bi.text + ' at (' + bi.x + ',' + bi.y + ')';
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      for (let round = 0; round < 10; round++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let url = await eval_(`window.location.href`);
        L("\n=== Q" + round + " ===");

        // Extract question
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let questionIdx = lines.findIndex(l => l.includes('Question'));
        let question = questionIdx >= 0 && questionIdx + 1 < lines.length ? lines[questionIdx + 1] : lines[0];
        L("Q: " + question);

        // Check for end states
        let lower = pageText.toLowerCase();
        if (lower.includes('your profile matches') || lower.includes('congratulations') || lower.includes('qualified')) {
          L("QUALIFIED!");
          // Click Start survey
          await sleep(1000);
          let startResult = await clickContinue();
          L("Start: " + startResult);
          await sleep(5000);
          break;
        }
        if (lower.includes('sorry') || lower.includes('not a match') || lower.includes('disqualified')) {
          L("NOT QUALIFIED");
          break;
        }
        if (!url.includes('bitlabs')) {
          L("REDIRECTED: " + url);
          break;
        }

        // Determine answer based on question
        let target = null;
        let qLower = question.toLowerCase();

        if (qLower.includes('employ') && qLower.includes('people')) {
          target = '1 to 5';
        } else if (qLower.includes('company') && qLower.includes('revenue')) {
          target = 'Less than';
        } else if (qLower.includes('industry') || qLower.includes('sector') || qLower.includes('business')) {
          target = 'Architecture';
        } else if (qLower.includes('role') || qLower.includes('title') || qLower.includes('job function') || qLower.includes('position')) {
          target = 'Owner';
        } else if (qLower.includes('decision') || qLower.includes('purchase') || qLower.includes('influence')) {
          target = 'Final';
        } else if (qLower.includes('software') || qLower.includes('technology')) {
          target = 'AutoCAD';
        } else if (qLower.includes('education')) {
          target = 'Some college';
        } else if (qLower.includes('household income') || qLower.includes('annual income')) {
          target = '$75,000';
        } else if (qLower.includes('age') || qLower.includes('how old') || qLower.includes('born')) {
          target = '50';
        } else if (qLower.includes('gender') || qLower.includes('sex')) {
          target = 'Male';
        } else if (qLower.includes('streaming') || qLower.includes('subscription')) {
          // Fake service detection
          target = 'Netflix';
        } else if (qLower.includes('travel')) {
          // Free text - handled differently
          target = null;
          L("Free text question, typing answer...");
          await eval_(`
            (function() {
              var inputs = document.querySelectorAll('input[type="text"], textarea');
              for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].offsetParent !== null) {
                  var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set || Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                  setter.call(inputs[i], 'I would love to visit Italy to explore the architecture and history of Rome and Florence.');
                  inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                  inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
                  return 'typed';
                }
              }
              return 'no input found';
            })()
          `);
          await sleep(500);
          let contResult = await clickContinue();
          L("Continue: " + contResult);
          await sleep(3000);
          continue;
        }

        if (target) {
          L("-> " + target);
          let clickResult = await clickOption(target);
          L("   " + clickResult);
          await sleep(500);
          let contResult = await clickContinue();
          L("   " + contResult);
          await sleep(3000);
        } else if (!qLower.includes('travel')) {
          L("-> UNKNOWN: " + question);
          L("Options: " + pageText.substring(0, 500));
          break;
        }
      }

      // Final state
      L("\n=== FINAL ===");
      // Check all tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      allTabs.filter(t => t.type === 'page').forEach(t => L("Tab: " + t.url.substring(0, 100)));

      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 2000)`);
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
