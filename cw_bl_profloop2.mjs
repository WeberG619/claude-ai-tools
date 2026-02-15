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

    // Select option by partial label match, trigger jQuery change, click Continue
    const selectAndContinue = async (targetText) => {
      let selectResult = await eval_(`
        (function() {
          var target = ${JSON.stringify(targetText)};
          var labels = document.querySelectorAll('.js-question-options label');
          for (var i = 0; i < labels.length; i++) {
            var t = labels[i].textContent.trim();
            if (t === target || t.indexOf(target) >= 0) {
              var input = labels[i].querySelector('input[type="checkbox"], input[type="radio"]');
              if (input) {
                input.checked = true;
                jQuery(input).trigger('change');
                return 'checked: ' + t.substring(0, 60) + ' (' + input.type + ')';
              }
            }
          }
          // Select dropdown
          var selects = document.querySelectorAll('select');
          for (var i = 0; i < selects.length; i++) {
            for (var j = 0; j < selects[i].options.length; j++) {
              if (selects[i].options[j].text.indexOf(target) >= 0) {
                selects[i].selectedIndex = j;
                jQuery(selects[i]).trigger('change');
                return 'dropdown: ' + selects[i].options[j].text.substring(0, 60);
              }
            }
          }
          // Text input
          var textInputs = document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])');
          for (var i = 0; i < textInputs.length; i++) {
            if (textInputs[i].offsetParent !== null) {
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

      // Ensure button enabled
      let btnEnabled = await eval_(`!document.getElementById('ctl00_Content_btnContinue').disabled`);
      if (!btnEnabled) {
        await eval_(`toggleSubmission(true)`);
        await sleep(200);
      }

      // Scroll to button
      await eval_(`document.getElementById('ctl00_Content_btnContinue').scrollIntoView({ behavior: 'instant', block: 'center' })`);
      await sleep(300);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          if (btn.disabled) { btn.disabled = false; btn.classList.remove('disabled'); }
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        })()
      `);
      let br = JSON.parse(btnRect);
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

        if (!url.includes('samplicio')) { L("REDIRECTED: " + url); break; }

        let lower = questionLine.toLowerCase();

        // End states
        if (lower.includes('thank you') || lower.includes('unfortunately') ||
            lower.includes('disqualified') || lower.includes('screened out') ||
            lower.includes('not qualify') || lower.includes('not eligible') ||
            lower.includes('sorry')) {
          L("ENDED: " + questionLine);
          break;
        }

        if (questionLine.length < 5) { L("Loading..."); await sleep(2000); continue; }

        let target = null;

        // ---- Question matching (ORDER MATTERS - most specific first) ----

        // Children age/gender
        if (lower.includes('child') && (lower.includes('age') || lower.includes('gender'))) {
          target = 'None of the above';
        }
        // Household children/pregnancy description
        else if (lower.includes('household') && (lower.includes('describe') || lower.includes('best'))) {
          target = 'I have no children';
        }
        // Industry
        else if (lower.includes('industr') || (lower.includes('household') && lower.includes('work in'))) {
          target = 'Architecture';
        }
        // Education
        else if (lower.includes('education') || lower.includes('highest level') || lower.includes('degree') || lower.includes('school')) {
          target = 'Completed some college';
        }
        // Gender
        else if (lower.includes('gender') || lower.includes('are you male') || lower.includes('are you a ')) {
          target = 'Male';
        }
        // Hispanic
        else if (lower.includes('hispanic') || lower.includes('latino')) {
          target = 'No';
        }
        // Race
        else if (lower.includes('race') || lower.includes('ethnic')) {
          target = 'White';
        }
        // Marital
        else if (lower.includes('marital') || lower.includes('married') || lower.includes('relationship status')) {
          target = 'Single';
        }
        // Employment
        else if (lower.includes('employ') || lower.includes('work status') || lower.includes('job status') || lower.includes('occupation')) {
          target = 'Self';
        }
        // Number of children
        else if (lower.includes('how many') && (lower.includes('child') || lower.includes('kid'))) {
          target = 'None';
        }
        // Income
        else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary')) {
          target = '$75,000';
        }
        // State (must check for "state" but not "describe your state")
        else if ((lower.includes('what state') || lower.includes('which state') || lower.includes('where do you') || lower.includes('your state') || lower.includes('reside'))) {
          target = 'Idaho';
        }
        // Age/birth year (use word boundary - "how old" not "household")
        else if (lower.includes('how old') || lower.includes('your age') || lower.includes('year were you born') || lower.includes('date of birth') || lower.includes('year of birth')) {
          target = '1974';
        }
        // ZIP
        else if (lower.includes('zip') || lower.includes('postal')) {
          target = '83864';
        }
        // Pets
        else if (lower.includes('pet') || (lower.includes('animal') && !lower.includes('spirit'))) {
          target = 'None';
        }
        // Own/rent
        else if (lower.includes('own') && lower.includes('rent')) {
          target = 'Own';
        }
        // Home type
        else if (lower.includes('type of home') || lower.includes('dwelling') || lower.includes('type of house')) {
          target = 'Single family';
        }
        // Phone/device
        else if (lower.includes('phone') || (lower.includes('device') && lower.includes('mobile'))) {
          target = 'Android';
        }
        // Smoking
        else if (lower.includes('smoke') || lower.includes('tobacco') || lower.includes('cigarette') || lower.includes('vape')) {
          target = 'No';
        }
        // Alcohol
        else if (lower.includes('drink') || lower.includes('alcohol')) {
          target = 'Occasionally';
        }
        // Vehicle
        else if (lower.includes('vehicle') || (lower.includes('car') && lower.includes('own'))) {
          target = 'Yes';
        }
        // Health insurance
        else if (lower.includes('health') && lower.includes('insurance')) {
          target = 'Yes';
        }
        // Military
        else if (lower.includes('military') || lower.includes('veteran') || lower.includes('armed forces')) {
          target = 'No';
        }

        if (target) {
          L("-> " + target);
          let result = await selectAndContinue(target);
          L("   " + result);

          if (result === 'NOT_FOUND') {
            let opts = await eval_(`
              (function() {
                var options = [];
                document.querySelectorAll('.js-question-options label').forEach(function(l) {
                  options.push(l.textContent.trim());
                });
                return JSON.stringify(options);
              })()
            `);
            L("   Options: " + opts);

            // Try partial match on "no children" or similar
            let parsed = JSON.parse(opts);
            let noOption = parsed.find(o => o.toLowerCase().includes('no child') || o.toLowerCase().includes('none') || o.toLowerCase().includes('not'));
            if (noOption) {
              L("   Trying partial: " + noOption.substring(0, 40));
              let fb = await selectAndContinue(noOption.substring(0, 30));
              L("   " + fb);
            } else {
              // Pick last option as "none of above" fallback
              let last = parsed[parsed.length - 1];
              L("   Trying last option: " + last.substring(0, 40));
              let fb = await selectAndContinue(last.substring(0, 30));
              L("   " + fb);
            }
          }

          await sleep(3000);
        } else {
          L("-> UNKNOWN QUESTION");
          let fullPage = await eval_(`document.body.innerText.substring(0, 2000)`);
          L("Full: " + fullPage.substring(0, 800));
          break;
        }
      }

      // Final
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
