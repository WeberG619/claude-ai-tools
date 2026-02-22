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

      // Check and enable button
      let btnState = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          if (!btn) return JSON.stringify({ error: 'no button' });
          if (btn.disabled) {
            // Try toggleSubmission first
            if (typeof toggleSubmission === 'function') toggleSubmission(true);
          }
          return JSON.stringify({ disabled: btn.disabled, cls: btn.className });
        })()
      `);
      L("   btn: " + btnState);

      // Force enable if still disabled
      await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          if (btn && btn.disabled) { btn.disabled = false; btn.classList.remove('disabled'); }
        })()
      `);

      // Get viewport size
      let vp = await eval_(`JSON.stringify({ w: window.innerWidth, h: window.innerHeight })`);
      let vpObj = JSON.parse(vp);

      // Scroll to button and get position
      await eval_(`document.getElementById('ctl00_Content_btnContinue').scrollIntoView({ behavior: 'instant', block: 'center' })`);
      await sleep(300);

      let btnRect = await eval_(`
        (function() {
          var btn = document.getElementById('ctl00_Content_btnContinue');
          var rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), top: rect.top, bot: rect.bottom, w: rect.width, h: rect.height });
        })()
      `);
      let br = JSON.parse(btnRect);
      L("   btnPos: (" + br.x + "," + br.y + ") viewport:" + vpObj.w + "x" + vpObj.h);

      // Check if button is in viewport
      if (br.y < 0 || br.y > vpObj.h || br.x < 0 || br.x > vpObj.w) {
        L("   Button OUT OF VIEWPORT! Trying window.scrollTo...");
        // Use a different scroll approach
        await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            var rect = btn.getBoundingClientRect();
            window.scrollBy(0, rect.top - window.innerHeight / 2);
          })()
        `);
        await sleep(300);
        btnRect = await eval_(`
          (function() {
            var btn = document.getElementById('ctl00_Content_btnContinue');
            var rect = btn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          })()
        `);
        br = JSON.parse(btnRect);
        L("   btnPos after scrollBy: (" + br.x + "," + br.y + ")");
      }

      await cdpClick(br.x, br.y);
      return selectResult;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      let lastQ = '';
      let stuckCount = 0;

      for (let round = 0; round < 30; round++) {
        let questionLine = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
        let url = await eval_(`window.location.href`);
        L("\n=== Round " + round + " ===");
        L("Q: " + questionLine);

        if (!url.includes('samplicio')) { L("REDIRECTED: " + url); break; }

        let lower = questionLine.toLowerCase();

        if (lower.includes('thank you') || lower.includes('unfortunately') ||
            lower.includes('disqualified') || lower.includes('screened out') ||
            lower.includes('not qualify') || lower.includes('not eligible') ||
            lower.includes('sorry')) {
          L("ENDED: " + questionLine);
          break;
        }

        if (questionLine.length < 5) { L("Loading..."); await sleep(2000); continue; }

        // Detect stuck loop
        if (questionLine === lastQ) {
          stuckCount++;
          if (stuckCount >= 2) {
            L("STUCK on same question! Trying different submit approach...");
            // Try keyboard Enter
            await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
            await sleep(100);
            await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
            await sleep(3000);
            let newQ = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
            if (newQ === questionLine) {
              // Try form submit
              L("Enter didn't work, trying form.submit()");
              await eval_(`document.querySelector('form').submit()`);
              await sleep(3000);
              newQ = await eval_(`document.body.innerText.split('\\n')[0].trim()`);
              if (newQ === questionLine) {
                L("Form submit didn't work either. Trying JS button click...");
                await eval_(`
                  (function() {
                    var btn = document.getElementById('ctl00_Content_btnContinue');
                    btn.disabled = false;
                    btn.classList.remove('disabled');
                    btn.click();
                  })()
                `);
                await sleep(3000);
              }
            }
            continue;
          }
        } else {
          stuckCount = 0;
        }
        lastQ = questionLine;

        let target = null;

        // ---- Question matching ----
        if (lower.includes('child') && (lower.includes('age') || lower.includes('gender'))) {
          target = 'None of the above';
        }
        else if (lower.includes('household') && (lower.includes('describe') || lower.includes('best') || lower.includes('pregnant'))) {
          target = 'I have no children';
        }
        else if (lower.includes('industr') || (lower.includes('household') && lower.includes('work in'))) {
          target = 'Architecture';
        }
        else if (lower.includes('education') || lower.includes('highest level') || lower.includes('degree') || (lower.includes('school') && !lower.includes('which'))) {
          target = 'Completed some college';
        }
        else if (lower.includes('gender') || lower.includes('are you male') || lower.includes('are you a ')) {
          target = 'Male';
        }
        else if (lower.includes('hispanic') || lower.includes('latino')) {
          target = 'No';
        }
        else if (lower.includes('race') || lower.includes('ethnic')) {
          target = 'White';
        }
        else if (lower.includes('marital') || lower.includes('relationship')) {
          target = 'Married';
        }
        else if (lower.includes('employ') || lower.includes('work status') || lower.includes('job status') || lower.includes('occupation')) {
          target = 'Self';
        }
        else if (lower.includes('how many') && (lower.includes('child') || lower.includes('kid'))) {
          target = 'None';
        }
        else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary')) {
          target = '$75,000';
        }
        else if (lower.includes('what state') || lower.includes('which state') || lower.includes('where do you') || lower.includes('your state') || lower.includes('reside')) {
          target = 'Idaho';
        }
        else if (lower.includes('how old') || lower.includes('your age') || lower.includes('year were you born') || lower.includes('date of birth') || lower.includes('year of birth')) {
          target = '1974';
        }
        else if (lower.includes('zip') || lower.includes('postal')) {
          target = '83864';
        }
        else if (lower.includes('registered to vote')) {
          target = 'Yes';
        }
        else if (lower.includes('pet') || (lower.includes('animal') && !lower.includes('spirit'))) {
          target = 'None';
        }
        else if (lower.includes('own') && lower.includes('rent')) {
          target = 'Own';
        }
        else if (lower.includes('type of home') || lower.includes('dwelling')) {
          target = 'Single family';
        }
        else if (lower.includes('phone') || (lower.includes('device') && lower.includes('mobile'))) {
          target = 'Android';
        }
        else if (lower.includes('smoke') || lower.includes('tobacco') || lower.includes('cigarette') || lower.includes('vape')) {
          target = 'No';
        }
        else if (lower.includes('drink') || lower.includes('alcohol')) {
          target = 'Occasionally';
        }
        else if (lower.includes('vehicle') || (lower.includes('car') && lower.includes('own'))) {
          target = 'Yes';
        }
        else if (lower.includes('health') && lower.includes('insurance')) {
          target = 'Yes';
        }
        else if (lower.includes('military') || lower.includes('veteran') || lower.includes('armed forces')) {
          target = 'No';
        }
        // Generic yes/no fallback
        else if (lower.includes('do you') || lower.includes('are you') || lower.includes('have you')) {
          // Check available options to determine if it's yes/no
          let opts = await eval_(`
            (function() {
              var labels = document.querySelectorAll('.js-question-options label');
              var texts = [];
              for (var i = 0; i < labels.length; i++) texts.push(labels[i].textContent.trim());
              return JSON.stringify(texts);
            })()
          `);
          let parsed = JSON.parse(opts);
          if (parsed.length <= 3 && parsed.some(o => o === 'Yes') && parsed.some(o => o === 'No')) {
            target = 'Yes';
            L("   (yes/no question, defaulting Yes)");
          }
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
            let parsed = JSON.parse(opts);
            // Smart fallback: try partial matches
            let noOpt = parsed.find(o => o.toLowerCase().includes('no child') || o.toLowerCase().includes('none') || o.toLowerCase().includes('not '));
            if (noOpt) {
              L("   Trying: " + noOpt.substring(0, 40));
              let fb = await selectAndContinue(noOpt.substring(0, 30));
              L("   " + fb);
            } else {
              let last = parsed[parsed.length - 1];
              L("   Trying last: " + last.substring(0, 40));
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
