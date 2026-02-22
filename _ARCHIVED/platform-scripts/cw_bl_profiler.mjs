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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (!surveyTab) { L("No survey tab"); tabs.forEach(t => L("  " + t.url.substring(0,100))); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
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

    // Weber's profile for survey answers:
    // Education: Some college, no degree
    // Gender: Male, Age: 51, DOB: 3/18/1974
    // Race: White, Hispanic: No
    // Income: ~$75K
    // Employment: Self-employed, Architecture
    // Marital: Single, Children: None
    // State: Idaho, ZIP: 83864

    const answerMap = {
      'education': 'Completed some college, but no degree',
      'gender': 'Male',
      'hispanic': 'No, not of Hispanic',
      'race': 'White',
      'marital': 'Single',
      'employ': 'Self-employed',
      'children': '0',
      'income': '75',
      'state': 'Idaho',
      'age': '50',
      'industry': 'Architecture'
    };

    const answerQuestion = async () => {
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      let text = pageText.toLowerCase();
      L("Page: " + pageText.substring(0, 300));

      // Determine what to answer
      let answerTarget = null;
      if (text.includes('education') || text.includes('degree') || text.includes('school')) {
        answerTarget = 'Completed some college';
      } else if (text.includes('gender') || text.includes('sex') || text.includes('are you')) {
        if (text.includes('male') && text.includes('female')) answerTarget = 'Male';
      } else if (text.includes('hispanic') || text.includes('latino')) {
        answerTarget = 'No';
      } else if (text.includes('race') || text.includes('ethnic')) {
        answerTarget = 'White';
      } else if (text.includes('marital') || text.includes('married')) {
        answerTarget = 'Single';
      } else if (text.includes('employ') || text.includes('work') || text.includes('occupation')) {
        if (text.includes('self')) answerTarget = 'Self';
        else answerTarget = 'Self-employed';
      } else if (text.includes('children') || text.includes('kids') || text.includes('dependents')) {
        answerTarget = '0';
        if (!text.includes('0')) answerTarget = 'None';
      } else if (text.includes('income') || text.includes('earn') || text.includes('salary')) {
        answerTarget = '75,000';
        if (!text.includes('75,000')) answerTarget = '$70';
      } else if (text.includes('state') || text.includes('where do you')) {
        answerTarget = 'Idaho';
      } else if (text.includes('age') || text.includes('year') || text.includes('born') || text.includes('old')) {
        answerTarget = '51';
        if (!text.includes('51')) answerTarget = '50';
      } else if (text.includes('industry') || text.includes('field')) {
        answerTarget = 'Architecture';
      }

      return { pageText, answerTarget };
    };

    const clickOption = async (target) => {
      // Try radio buttons first
      let clicked = await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
          for (var i = 0; i < inputs.length; i++) {
            var label = inputs[i].closest('label') || inputs[i].parentElement;
            var text = label ? label.textContent.trim() : '';
            if (text.includes(target) || (target.length > 3 && text.toLowerCase().includes(target.toLowerCase()))) {
              label.scrollIntoView({ block: 'center' });
              var rect = label.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + 15), y: Math.round(rect.y + rect.height/2), text: text.substring(0, 60) });
            }
          }
          // Try finding by text
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            var t = node.textContent.trim();
            if (t.includes(target) && t.length < 100) {
              var el = node.parentElement;
              el.scrollIntoView({ block: 'center' });
              var rect = el.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + 15), y: Math.round(rect.y + rect.height/2), text: t.substring(0, 60) });
            }
          }
          return 'not found';
        })()
      `);
      return clicked;
    };

    const clickNext = async () => {
      let btnPos = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button, input[type="button"], a.btn, .button, [class*="next"], [class*="submit"]');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || btns[i].value || '').trim();
            if (t === 'Next' || t === 'Continue' || t === 'Submit' || t === 'NEXT' || t === 'CONTINUE' || t.includes('>>') || t.includes('Next')) {
              btns[i].scrollIntoView({ block: 'center' });
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          }
          return 'none';
        })()
      `);
      if (btnPos !== 'none') {
        let bp = JSON.parse(btnPos);
        await cdpClick(bp.x, bp.y);
        return true;
      }
      return false;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // First dismiss cookie notice if present
      await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, a, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'OK') {
              btns[i].click();
              return;
            }
          }
        })()
      `);
      await sleep(1000);

      // Answer profiler questions in a loop
      for (let round = 0; round < 15; round++) {
        let { pageText, answerTarget } = await answerQuestion();

        if (!answerTarget) {
          L("\n=== UNKNOWN QUESTION (round " + round + ") ===");
          L("Full text:\n" + pageText.substring(0, 1500));

          // Check if this is the actual survey (not profiler)
          if (pageText.includes('Thank you') || pageText.includes('survey is complete') || pageText.includes('disqualified') || pageText.includes('screened out')) {
            L("Survey ended or disqualified");
            break;
          }
          // Might be the actual survey - stop and report
          L("This may be the actual survey content - stopping automation");
          break;
        }

        L("\n--- Round " + round + " ---");
        L("Answer: " + answerTarget);

        let optResult = await clickOption(answerTarget);
        L("Click result: " + optResult);

        if (optResult !== 'not found') {
          let op = JSON.parse(optResult);
          await cdpClick(op.x, op.y);
          await sleep(1000);
        }

        // Click Next/Continue/Submit
        let nextClicked = await clickNext();
        L("Next: " + nextClicked);
        await sleep(3000);

        // Check if page changed
        let newUrl = await eval_(`window.location.href`);
        if (!newUrl.includes('samplicio')) {
          L("Redirected to: " + newUrl);
          break;
        }
      }

      // Final state
      L("\n=== CURRENT STATE ===");
      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 2000));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));
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
