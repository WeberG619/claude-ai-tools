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

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Step 1: Click the $3.20 survey
      L("=== CLICKING $3.20 SURVEY ===");
      let cardInfo = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.includes('3.20') && t.includes('USD') && t.length < 50) {
              var el = all[i];
              while (el && el !== document.body) {
                var style = window.getComputedStyle(el);
                if (style.cursor === 'pointer') {
                  var rect = el.getBoundingClientRect();
                  if (rect.width > 50) {
                    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                  }
                }
                el = el.parentElement;
              }
            }
          }
          // Fallback: find highest priced survey
          var best = { price: 0, x: 0, y: 0 };
          for (var i = 0; i < all.length; i++) {
            var match = all[i].textContent.trim().match(/^(\\d+\\.\\d+) USD$/);
            if (match && parseFloat(match[1]) > best.price) {
              var el = all[i];
              while (el && el !== document.body) {
                if (window.getComputedStyle(el).cursor === 'pointer') {
                  var rect = el.getBoundingClientRect();
                  if (rect.width > 50) {
                    best = { price: parseFloat(match[1]), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) };
                  }
                  break;
                }
                el = el.parentElement;
              }
            }
          }
          if (best.price > 0) return JSON.stringify(best);
          return 'not found';
        })()
      `);
      L("Card: " + cardInfo);

      if (cardInfo === 'not found') {
        L("No survey found!");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(1);
        return;
      }

      let ci = JSON.parse(cardInfo);
      if (ci.y > 800) {
        await eval_(`window.scrollBy(0, ${ci.y - 400})`);
        await sleep(500);
        cardInfo = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.includes('3.20') && t.includes('USD') && t.length < 50) {
                var el = all[i];
                while (el && el !== document.body) {
                  if (window.getComputedStyle(el).cursor === 'pointer') {
                    var rect = el.getBoundingClientRect();
                    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                  }
                  el = el.parentElement;
                }
              }
            }
            return 'not found';
          })()
        `);
        ci = JSON.parse(cardInfo);
      }

      L("Clicking at (" + ci.x + ", " + ci.y + ")");
      await cdpClick(ci.x, ci.y);
      await sleep(5000);

      // Step 2: Handle qualification questions
      L("\n=== QUALIFICATION ===");
      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      if (url.includes('qualification')) {
        for (let q = 0; q < 10; q++) {
          let pageText;
          try {
            pageText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'loading'`);
          } catch(e) {
            L("Page loading... waiting");
            await sleep(3000);
            try {
              pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
            } catch(e2) {
              L("Page still loading. Checking tabs...");
              break;
            }
          }
          url = await eval_(`window.location.href`);
          L("\nQ" + q + ": ");

          let lower = pageText.toLowerCase();

          // Qualified?
          if (lower.includes('your profile matches') || lower.includes('congratulations') || lower.includes('qualified')) {
            L("QUALIFIED!");
            // Click Start survey
            let startInfo = await eval_(`
              (function() {
                var btns = document.querySelectorAll('button, a, [role="button"]');
                for (var i = 0; i < btns.length; i++) {
                  var t = btns[i].textContent.trim();
                  if (t.includes('Start') || t.includes('Begin')) {
                    var rect = btns[i].getBoundingClientRect();
                    return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                  }
                }
                return 'not found';
              })()
            `);
            if (startInfo !== 'not found') {
              let si = JSON.parse(startInfo);
              L("Clicking '" + si.text + "'");
              await cdpClick(si.x, si.y);
              await sleep(5000);
            }
            break;
          }
          if (lower.includes('sorry') || lower.includes('not a match')) {
            L("NOT QUALIFIED");
            break;
          }
          if (!url.includes('bitlabs')) {
            L("LEFT BITLABS");
            break;
          }

          // Get question line
          let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
          let qIdx = lines.findIndex(l => l.startsWith('Question'));
          let question = qIdx >= 0 && qIdx + 1 < lines.length ? lines[qIdx + 1] : lines.find(l => l.includes('?') || l.includes('...')) || lines[0];
          L(question);
          let qLower = question.toLowerCase();

          let target = null;
          if (qLower.includes('employ') && qLower.includes('people')) target = '1 to 5';
          else if (qLower.includes('department')) target = 'Creative/Design';
          else if (qLower.includes('role') || qLower.includes('title') || qLower.includes('level') || qLower.includes('seniority')) target = 'Owner';
          else if (qLower.includes('revenue') || qLower.includes('budget')) target = 'Less than';
          else if (qLower.includes('decision') || qLower.includes('authority') || qLower.includes('purchase')) target = 'Final';
          else if (qLower.includes('industry') || qLower.includes('sector')) target = 'Architecture';
          else if (qLower.includes('income')) target = '$75,000';
          else if (qLower.includes('age') || qLower.includes('how old')) target = '50';
          else if (qLower.includes('gender')) target = 'Male';
          else if (qLower.includes('education')) target = 'Some college';
          else if (qLower.includes('streaming')) target = 'Netflix';
          else if (qLower.includes('travel') || qLower.includes('write') || qLower.includes('describe')) {
            // Free text
            let typed = await eval_(`
              (function() {
                var inputs = document.querySelectorAll('input[type="text"], textarea');
                for (var i = 0; i < inputs.length; i++) {
                  if (inputs[i].offsetParent !== null) {
                    var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set || Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                    setter.call(inputs[i], 'I am an architect who enjoys design and innovation.');
                    inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                    inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
                    return 'typed';
                  }
                }
                return 'no input';
              })()
            `);
            L("-> Free text: " + typed);
          }
          else {
            // Unknown - try first real option
            let firstOpt = lines.find((l, i) => i > (qIdx || 0) + 1 && l.length > 2 && l.length < 60 && !['Continue','Next','Menu','Earn'].includes(l));
            if (firstOpt) {
              target = firstOpt;
              L("-> Guessing: " + target);
            } else {
              L("-> STUCK: " + question);
              L("Page: " + pageText.substring(0, 500));
              break;
            }
          }

          if (target) {
            L("-> " + target);
            // Click option (BitLabs style)
            let clickResult = await eval_(`
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
            L("   " + clickResult);
          }

          // Click Continue
          await sleep(500);
          let contInfo = await eval_(`
            (function() {
              var btns = document.querySelectorAll('button, a, [role="button"]');
              for (var i = 0; i < btns.length; i++) {
                var t = btns[i].textContent.trim();
                if (t === 'Continue' || t === 'Next') {
                  var rect = btns[i].getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              }
              return 'not found';
            })()
          `);
          if (contInfo !== 'not found') {
            let bi = JSON.parse(contInfo);
            await cdpClick(bi.x, bi.y);
          }
          await sleep(3000);
        }
      }

      // Step 3: Check final state - look for survey tab
      L("\n=== FINAL STATE ===");
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      allTabs.filter(t => t.type === 'page' || t.type === 'iframe').forEach(t => L("Tab: " + t.type + " " + t.url.substring(0, 120)));

      try {
        url = await eval_(`window.location.href`);
        let page = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
        L("\nBitLabs URL: " + url);
        L("Page:\n" + page.substring(0, 800));
      } catch(e) {
        L("BitLabs page error: " + e.message);
      }

      // Check for samplicio survey tab
      let surveyTab = allTabs.find(t => t.type === 'page' && (t.url.includes('samplicio') || t.url.includes('survey')));
      if (surveyTab) {
        L("\nSurvey tab found: " + surveyTab.url.substring(0, 100));
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
