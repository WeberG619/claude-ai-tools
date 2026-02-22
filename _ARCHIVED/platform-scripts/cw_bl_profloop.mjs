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
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    // Select a checkbox/radio by label text, trigger jQuery change, enable & click Continue
    const selectAndContinue = async (targetText) => {
      // Select the option
      let selectResult = await eval_(`
        (function() {
          var target = ${JSON.stringify(targetText)};
          var labels = document.querySelectorAll('.js-question-options label');
          for (var i = 0; i < labels.length; i++) {
            var t = labels[i].textContent.trim();
            if (t === target || t.includes(target)) {
              var input = labels[i].querySelector('input[type="checkbox"], input[type="radio"]');
              if (input) {
                input.checked = true;
                jQuery(input).trigger('change');
                return 'checked: ' + t.substring(0, 50) + ' (' + input.type + ')';
              }
            }
          }
          // Try select dropdown
          var selects = document.querySelectorAll('select');
          for (var i = 0; i < selects.length; i++) {
            for (var j = 0; j < selects[i].options.length; j++) {
              if (selects[i].options[j].text.includes(target)) {
                selects[i].selectedIndex = j;
                jQuery(selects[i]).trigger('change');
                return 'dropdown: ' + selects[i].options[j].text.substring(0, 50);
              }
            }
          }
          // Try text input
          var textInputs = document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])');
          for (var i = 0; i < textInputs.length; i++) {
            if (textInputs[i].offsetParent !== null) { // visible
              var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              setter.call(textInputs[i], target);
              textInputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              textInputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              textInputs[i].dispatchEvent(new Event('keyup', { bubbles: true }));
              return 'text: ' + target;
            }
          }
          return 'NOT_FOUND';
        })()
      `);

      if (selectResult === 'NOT_FOUND') return selectResult;

      await sleep(300);

      // Ensure button is enabled
      let btnEnabled = await eval_(`!document.getElementById('ctl00_Content_btnContinue').disabled`);
      if (!btnEnabled) {
        // Force enable via toggleSubmission
        await eval_(`toggleSubmission(true)`);
        await sleep(200);
      }

      // Scroll to button and get position
      await eval_(`document.getElementById('ctl00_Content_btnContinue').scrollIntoView({ behavior: 'instant', block: 'center' })`);
      await sleep(300);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
        })()
      `);
      let br = JSON.parse(btnRect);

      if (br.disabled) {
        await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            btn.disabled = false;
            btn.classList.remove('disabled');
          })()
        `);
        await sleep(100);
        // Re-get position
        btnRect = await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            var rect = btn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          })()
        `);
        br = JSON.parse(btnRect);
      }

      await cdpClick(br.x, br.y);
      return selectResult;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      for (let round = 0; round < 30; round++) {
        let questionLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        let url = await eval_(`window.location.href`);
        L("\n=== Round " + round + " ===");
        L("Q: " + questionLine);

        // Check if left samplicio
        if (!url.includes('samplicio')) {
          L("REDIRECTED: " + url);
          break;
        }

        let lower = questionLine.toLowerCase();

        // End states
        if (lower.includes('thank you') || lower.includes('unfortunately') ||
            lower.includes('disqualified') || lower.includes('screened out') ||
            lower.includes('not qualify') || lower.includes('not eligible') ||
            lower.includes('sorry')) {
          L("ENDED: " + questionLine);
          break;
        }

        // Empty/loading
        if (questionLine.length < 5) {
          L("Loading...");
          await sleep(2000);
          continue;
        }

        let target = null;

        // Determine answer based on question text only
        if (lower.includes('child') && (lower.includes('age') || lower.includes('gender'))) {
          target = 'None of the above';
        } else if (lower.includes('industr') || lower.includes('household, work') || lower.includes('work in any')) {
          target = 'Architecture';
        } else if (lower.includes('education') || lower.includes('highest level') || lower.includes('degree')) {
          target = 'Completed some college';
        } else if (lower.includes('gender') || lower.includes('are you male') || lower.includes('are you a')) {
          target = 'Male';
        } else if (lower.includes('hispanic') || lower.includes('latino') || lower.includes('latina')) {
          target = 'No';
        } else if (lower.includes('race') || lower.includes('ethnic') || lower.includes('background')) {
          target = 'White';
        } else if (lower.includes('marital') || lower.includes('married') || lower.includes('relationship')) {
          target = 'Single';
        } else if (lower.includes('employ') || lower.includes('work status') || lower.includes('job status') || lower.includes('occupation')) {
          target = 'Self';
        } else if (lower.includes('how many') && (lower.includes('child') || lower.includes('kid') || lower.includes('dependent'))) {
          target = 'None';
        } else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary') || lower.includes('household') && lower.includes('$')) {
          target = '$75,000';
        } else if (lower.includes('state') && (lower.includes('where') || lower.includes('live') || lower.includes('reside') || lower.includes('which'))) {
          target = 'Idaho';
        } else if (lower.includes('old') || lower.includes('your age') || lower.includes('year') && lower.includes('born') || lower.includes('date of birth')) {
          target = '1974';
        } else if (lower.includes('zip') || lower.includes('postal')) {
          target = '83864';
        } else if (lower.includes('pet') || lower.includes('animal') || lower.includes('dog') || lower.includes('cat')) {
          target = 'None';
        } else if (lower.includes('own') && lower.includes('rent')) {
          target = 'Own';
        } else if (lower.includes('home type') || lower.includes('dwelling') || lower.includes('type of home')) {
          target = 'Single family';
        } else if (lower.includes('phone') || lower.includes('mobile') || lower.includes('device')) {
          target = 'Android';
        } else if (lower.includes('social media') || lower.includes('facebook') || lower.includes('instagram')) {
          target = 'Facebook';
        } else if (lower.includes('smoke') || lower.includes('tobacco') || lower.includes('cigarette') || lower.includes('vape')) {
          target = 'No';
        } else if (lower.includes('drink') || lower.includes('alcohol') || lower.includes('beer') || lower.includes('wine')) {
          target = 'Occasionally';
        } else if (lower.includes('vehicle') || lower.includes('car') || lower.includes('drive')) {
          target = 'Yes';
        } else if (lower.includes('health') && lower.includes('insurance')) {
          target = 'Yes';
        } else if (lower.includes('military') || lower.includes('veteran') || lower.includes('armed forces')) {
          target = 'No';
        }

        if (target) {
          L("-> " + target);
          let result = await selectAndContinue(target);
          L("   " + result);

          if (result === 'NOT_FOUND') {
            // Show available options
            let opts = await eval_(`
              (function() {
                var options = [];
                document.querySelectorAll('.js-question-options label').forEach(function(l) {
                  options.push(l.textContent.trim().substring(0, 60));
                });
                return options.join(' | ');
              })()
            `);
            L("   Available: " + opts.substring(0, 500));

            // Try "None of the above" as fallback
            L("   Trying 'None of the above'...");
            let fallback = await selectAndContinue('None of the above');
            L("   Fallback: " + fallback);
            if (fallback === 'NOT_FOUND') {
              let fb2 = await selectAndContinue('None');
              L("   Fallback2: " + fb2);
            }
          }

          await sleep(3000);
        } else {
          L("-> UNKNOWN QUESTION");
          // Get all options
          let fullPage = await eval_(`document.body.innerText.substring(0, 2000)`);
          L("Full: " + fullPage.substring(0, 500));
          break;
        }
      }

      // Final state
      L("\n=== FINAL ===");
      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 1500));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

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
