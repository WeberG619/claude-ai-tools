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
  const blTab = tabs.find(t => t.url.includes('bitlabs') && t.url.includes('surveys'));
  if (!blTab) { L("No BitLabs tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    const blClickOption = async (target) => {
      return await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          var cbs = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
          for (var i = 0; i < cbs.length; i++) {
            var parent = cbs[i].parentElement;
            for (var d = 0; d < 5 && parent; d++) {
              var t = parent.textContent.trim();
              if ((t === target || t.indexOf(target) >= 0) && t.length < target.length + 30) {
                cbs[i].click();
                return 'checked: ' + t.substring(0, 50);
              }
              parent = parent.parentElement;
            }
          }
          return 'NOT_FOUND';
        })()
      `);
    };

    const blClickContinue = async () => {
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, a, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Continue' || t === 'Next' || t.includes('Start survey') || t.includes('Start')) {
              var rect = btns[i].getBoundingClientRect();
              if (rect.width > 30 && rect.height > 15) {
                return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
          }
          return null;
        })()
      `);
      if (!r) return 'no button';
      let bi = JSON.parse(r);
      await cdpClick(bi.x, bi.y);
      return 'clicked ' + bi.text;
    };

    const blTypeText = async (text) => {
      return await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"], textarea');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null) {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], ${JSON.stringify(text)});
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              return 'typed';
            }
          }
          return 'no input';
        })()
      `);
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Step 1: Find and click the highest priced survey
      L("=== FINDING BEST SURVEY ===");

      // First scroll down to load all surveys
      for (let s = 0; s < 3; s++) {
        await eval_(`window.scrollBy(0, 500)`);
        await sleep(300);
      }
      await eval_(`window.scrollTo(0, 0)`);
      await sleep(500);

      let bestSurvey = await eval_(`
        (function() {
          var best = null;
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            var match = t.match(/^(\\d+\\.\\d+) USD$/);
            if (match) {
              var price = parseFloat(match[1]);
              var el = all[i];
              while (el && el !== document.body) {
                if (window.getComputedStyle(el).cursor === 'pointer') {
                  var rect = el.getBoundingClientRect();
                  if (rect.width > 50 && rect.height > 30) {
                    if (!best || price > best.price) {
                      best = { price: price, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t };
                    }
                    break;
                  }
                }
                el = el.parentElement;
              }
            }
          }
          return best ? JSON.stringify(best) : 'none';
        })()
      `);
      L("Best: " + bestSurvey);

      if (bestSurvey === 'none') {
        L("No surveys found!");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(1);
        return;
      }

      let survey = JSON.parse(bestSurvey);

      // Scroll to make it visible
      if (survey.y < 0 || survey.y > 800) {
        await eval_(`window.scrollBy(0, ${survey.y - 400})`);
        await sleep(500);
        // Re-find after scroll
        bestSurvey = await eval_(`
          (function() {
            var targetPrice = ${survey.price};
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t === targetPrice.toFixed(2) + ' USD') {
                var el = all[i];
                while (el && el !== document.body) {
                  if (window.getComputedStyle(el).cursor === 'pointer') {
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 50) {
                      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                    }
                  }
                  el = el.parentElement;
                }
              }
            }
            return null;
          })()
        `);
        if (bestSurvey) survey = { ...survey, ...JSON.parse(bestSurvey) };
      }

      L("Clicking $" + survey.price + " at (" + survey.x + ", " + survey.y + ")");
      await cdpClick(survey.x, survey.y);
      await sleep(5000);

      // Step 2: Handle qualification
      L("\n=== QUALIFICATION ===");
      for (let q = 0; q < 10; q++) {
        let pageText, url;
        try {
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'loading'`);
          url = await eval_(`window.location.href`);
        } catch(e) {
          L("Page loading...");
          await sleep(3000);
          continue;
        }

        let lower = pageText.toLowerCase();
        L("\nQ" + q + ":");

        if (lower.includes('your profile matches') || lower.includes('congratulations') || lower.includes('qualified')) {
          L("QUALIFIED!");
          await sleep(1000);
          let r = await blClickContinue();
          L("Start: " + r);
          await sleep(5000);
          break;
        }
        if (lower.includes('sorry') || lower.includes('not a match') || lower.includes('unfortunately')) {
          L("NOT QUALIFIED: " + pageText.substring(0, 200));
          break;
        }
        if (!url.includes('bitlabs')) { L("LEFT BITLABS: " + url); break; }

        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let qIdx = lines.findIndex(l => l.startsWith('Question'));
        let question = qIdx >= 0 && qIdx + 1 < lines.length ? lines[qIdx + 1] : lines.find(l => l.includes('?') || l.includes('...')) || lines[0];
        L(question);
        let qLower = question.toLowerCase();

        // Answer lookup
        let target = null;
        let freeText = null;
        if (qLower.includes('employ') && qLower.includes('people')) target = '1 to 5';
        else if (qLower.includes('department')) target = 'Creative/Design';
        else if (qLower.includes('role') || qLower.includes('title') || qLower.includes('level') || qLower.includes('seniority') || qLower.includes('position')) target = 'Owner';
        else if (qLower.includes('revenue') || qLower.includes('budget')) target = 'Less than';
        else if (qLower.includes('decision') || qLower.includes('authority')) target = 'Final';
        else if (qLower.includes('industry') || qLower.includes('sector')) target = 'Architecture';
        else if (qLower.includes('income')) target = '$75,000';
        else if (qLower.includes('age') || qLower.includes('how old')) target = '50';
        else if (qLower.includes('gender')) target = 'Male';
        else if (qLower.includes('education')) target = 'Some college';
        else if (qLower.includes('streaming')) target = 'Netflix';
        else if (qLower.includes('travel') || qLower.includes('write') || qLower.includes('describe') || qLower.includes('tell us')) {
          freeText = 'I am a self-employed architect with over 20 years of experience in residential and commercial design.';
        }
        else if (qLower.includes('software') || qLower.includes('tool')) target = 'AutoCAD';
        else if (qLower.includes('marital') || qLower.includes('relationship')) target = 'Married';
        else if (qLower.includes('children') || qLower.includes('kids')) target = 'No';
        else {
          let firstOpt = lines.find((l, i) => i > (qIdx || 0) + 1 && l.length > 2 && l.length < 60 && !['Continue','Next','Menu','Earn','Reward History','Privacy Policy','Terms of Use','Language'].includes(l));
          if (firstOpt) {
            target = firstOpt;
            L("   (guessing first option)");
          }
        }

        if (freeText) {
          L("-> [text] " + freeText.substring(0, 40));
          await blTypeText(freeText);
        } else if (target) {
          L("-> " + target);
          let r = await blClickOption(target);
          L("   " + r);
        }

        await sleep(500);
        let cont = await blClickContinue();
        L("   " + cont);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      allTabs.filter(t => t.type === 'page' || t.type === 'iframe').forEach(t => L("Tab: " + t.type + " " + t.url.substring(0, 120)));

      try {
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
        L("\nURL: " + fUrl);
        L("Page:\n" + fPage.substring(0, 1000));
      } catch(e) {
        L("Page read error: " + e.message);
      }

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
