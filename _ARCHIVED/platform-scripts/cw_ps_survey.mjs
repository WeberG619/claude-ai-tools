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
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
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

    const clickNext = async () => {
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Next' || t === 'Continue' || t === 'Submit') {
              var rect = btns[i].getBoundingClientRect();
              if (rect.width > 30 && rect.x > 0) {
                return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
          }
          return null;
        })()
      `);
      if (!r) return 'no Next button';
      let bi = JSON.parse(r);
      await cdpClick(bi.x, bi.y);
      return 'clicked ' + bi.text + ' at (' + bi.x + ',' + bi.y + ')';
    };

    const selectOption = async (target) => {
      return await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          // Try radio buttons
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = radios[i].closest('label') || radios[i].parentElement;
            var t = label ? label.textContent.trim() : '';
            if (t === target || t.indexOf(target) >= 0) {
              radios[i].click();
              return 'radio: ' + t.substring(0, 50);
            }
          }
          // Try checkboxes
          var cbs = document.querySelectorAll('input[type="checkbox"]');
          for (var i = 0; i < cbs.length; i++) {
            var label = cbs[i].closest('label') || cbs[i].parentElement;
            var t = label ? label.textContent.trim() : '';
            if (t === target || t.indexOf(target) >= 0) {
              cbs[i].click();
              return 'checkbox: ' + t.substring(0, 50);
            }
          }
          // Try clickable divs/spans (modern survey UIs)
          var all = document.querySelectorAll('[class*="option"], [class*="choice"], [class*="answer"], [role="option"], [role="radio"], li');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if ((t === target || t.indexOf(target) >= 0) && t.length < target.length + 30) {
              all[i].click();
              return 'div: ' + t.substring(0, 50);
            }
          }
          // Try select dropdown
          var selects = document.querySelectorAll('select');
          for (var i = 0; i < selects.length; i++) {
            for (var j = 0; j < selects[i].options.length; j++) {
              if (selects[i].options[j].text.indexOf(target) >= 0) {
                selects[i].selectedIndex = j;
                selects[i].dispatchEvent(new Event('change', { bubbles: true }));
                return 'select: ' + selects[i].options[j].text.substring(0, 50);
              }
            }
          }
          return 'NOT_FOUND';
        })()
      `);
    };

    const typeInInput = async (value) => {
      return await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"], input[type="number"], input:not([type]), textarea');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden') {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], ${JSON.stringify(value)});
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('keyup', { bubbles: true }));
              return 'typed: ' + ${JSON.stringify(value)};
            }
          }
          return 'no input';
        })()
      `);
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Accept cookies first
      let accepted = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Accept All') {
              btns[i].click();
              return 'accepted';
            }
          }
          return 'no cookie banner';
        })()
      `);
      L("Cookies: " + accepted);
      await sleep(500);

      for (let round = 0; round < 30; round++) {
        let pageText, url;
        try {
          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'loading'`);
        } catch(e) {
          L("\nRound " + round + ": Page loading...");
          await sleep(3000);
          continue;
        }

        let lower = pageText.toLowerCase();
        L("\n=== Round " + round + " ===");

        // End states
        if (lower.includes('thank you') || lower.includes('completed') || lower.includes('survey is complete')) {
          L("SURVEY COMPLETE!");
          L(pageText.substring(0, 500));
          break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('not eligible') || lower.includes('sorry')) {
          L("SCREENED OUT");
          L(pageText.substring(0, 500));
          break;
        }
        if (!url.includes('purespectrum') && !url.includes('survey')) {
          L("REDIRECTED: " + url);
          L(pageText.substring(0, 500));
          break;
        }

        // Find the question
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        // Skip progress bar and nav elements
        let question = lines.find(l => l.includes('?') || l.includes(':') || (l.length > 20 && l.length < 200)) || lines[0];
        L("Q: " + question);
        let qLower = question.toLowerCase();

        let target = null;
        let textValue = null;

        // Zip code
        if (qLower.includes('zip') || qLower.includes('postal')) {
          textValue = '83864';
        }
        // Age/year
        else if (qLower.includes('how old') || qLower.includes('your age') || qLower.includes('year') && qLower.includes('born') || qLower.includes('date of birth')) {
          textValue = '51';
        }
        // Gender
        else if (qLower.includes('gender') || qLower.includes('sex') || qLower.includes('male') && qLower.includes('female')) {
          target = 'Male';
        }
        // Hispanic
        else if (qLower.includes('hispanic') || qLower.includes('latino')) {
          target = 'No';
        }
        // Race
        else if (qLower.includes('race') || qLower.includes('ethnic')) {
          target = 'White';
        }
        // Education
        else if (qLower.includes('education') || qLower.includes('degree') || qLower.includes('school')) {
          target = 'Some college';
        }
        // Relationship/marital
        else if (qLower.includes('marital') || qLower.includes('relationship') || qLower.includes('married')) {
          target = 'Married';
        }
        // Employment
        else if (qLower.includes('employ') || qLower.includes('work') && qLower.includes('status')) {
          target = 'Self-employed';
        }
        // Income
        else if (qLower.includes('income') || qLower.includes('earn') || qLower.includes('salary')) {
          target = '$75,000';
        }
        // Industry
        else if (qLower.includes('industr') || qLower.includes('field') || qLower.includes('sector')) {
          target = 'Architecture';
        }
        // Children
        else if (qLower.includes('child') || qLower.includes('kids')) {
          target = 'No';
        }
        // State
        else if (qLower.includes('state') && (qLower.includes('live') || qLower.includes('reside') || qLower.includes('which'))) {
          target = 'Idaho';
        }
        // Household size
        else if (qLower.includes('household') && qLower.includes('size') || qLower.includes('people in your')) {
          target = '2';
        }
        // Home ownership
        else if (qLower.includes('own') && qLower.includes('rent')) {
          target = 'Own';
        }
        // Registered to vote
        else if (qLower.includes('registered') && qLower.includes('vote')) {
          target = 'Yes';
        }
        // Political
        else if (qLower.includes('political') || qLower.includes('party') || qLower.includes('democrat') || qLower.includes('republican')) {
          target = 'Independent';
        }
        // Smoke
        else if (qLower.includes('smoke') || qLower.includes('tobacco')) {
          target = 'No';
        }
        // Alcohol
        else if (qLower.includes('alcohol') || qLower.includes('drink')) {
          target = 'Occasionally';
        }
        // Vehicle
        else if (qLower.includes('vehicle') || qLower.includes('car')) {
          target = 'Yes';
        }
        // Health insurance
        else if (qLower.includes('health insurance') || qLower.includes('medical insurance')) {
          target = 'Yes';
        }
        // Military
        else if (qLower.includes('military') || qLower.includes('veteran')) {
          target = 'No';
        }
        // Phone/device
        else if (qLower.includes('smartphone') || qLower.includes('mobile device')) {
          target = 'Android';
        }

        if (textValue) {
          L("-> typing: " + textValue);
          let r = await typeInInput(textValue);
          L("   " + r);
        } else if (target) {
          L("-> " + target);
          let r = await selectOption(target);
          L("   " + r);

          if (r === 'NOT_FOUND') {
            // List all options
            let opts = await eval_(`
              (function() {
                var options = [];
                document.querySelectorAll('[class*="option"], [class*="choice"], [class*="answer"], [role="option"], [role="radio"], label, li').forEach(function(el) {
                  var t = el.textContent.trim();
                  if (t.length > 1 && t.length < 80) options.push(t);
                });
                return JSON.stringify([...new Set(options)]);
              })()
            `);
            L("   Options: " + opts);
          }
        } else {
          L("-> UNKNOWN: " + question);
          L("Full: " + pageText.substring(0, 800));
          break;
        }

        await sleep(500);
        let cont = await clickNext();
        L("   " + cont);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      try {
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
        L("URL: " + fUrl);
        L("Page:\n" + fPage.substring(0, 1200));
      } catch(e) {
        L("Read error: " + e.message);
      }

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
