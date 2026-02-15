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
      if (!r) return 'no button';
      let bi = JSON.parse(r);
      await cdpClick(bi.x, bi.y);
      return 'clicked ' + bi.text;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Answers for open-ended government improvement questions
      const govAnswers = [
        "They should invest more in road maintenance and infrastructure improvements throughout the city.",
        "Building more affordable housing options for working families would help the community grow.",
        "Better public transportation access would reduce traffic congestion and help people get around.",
        "Expanding parks and recreational facilities would improve quality of life for residents.",
        "More investment in local school facilities and educational programs for students.",
        "Improving broadband internet access in rural areas would help bridge the digital divide.",
        "Creating more walkable downtown areas with better sidewalks and pedestrian safety measures.",
        "Supporting small business development through reduced fees and streamlined permitting processes.",
        "Investing in renewable energy infrastructure and sustainability programs for the community.",
        "Improving emergency services response times and public safety resources in the area."
      ];
      let ansIdx = 0;

      for (let round = 0; round < 30; round++) {
        let pageText, url;
        try {
          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 3000) : 'loading'`);
        } catch(e) {
          L("\nR" + round + ": Loading...");
          await sleep(3000);
          continue;
        }

        let lower = pageText.toLowerCase();
        L("\n=== R" + round + " ===");

        // Get progress %
        let progress = pageText.match(/(\d+)%/);
        if (progress) L("Progress: " + progress[1] + "%");

        // End states
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response has been')) {
          L("SURVEY COMPLETE!");
          L(pageText.substring(0, 500));
          break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('quota') || lower.includes('sorry')) {
          L("SCREENED OUT");
          L(pageText.substring(0, 500));
          break;
        }
        if (!url.includes('purespectrum') && !url.includes('survey')) {
          L("REDIRECTED: " + url);
          break;
        }

        // Find question
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = lines.find(l => l.includes('?') && l.length > 15) || lines.find(l => l.length > 20 && l.length < 200 && !l.includes('%') && l !== 'Next') || '';
        L("Q: " + question.substring(0, 100));
        let qLower = question.toLowerCase();

        // Check for text inputs (open-ended questions)
        let inputCount = await eval_(`
          (function() {
            var inputs = document.querySelectorAll('input[type="text"], textarea');
            var visible = 0;
            inputs.forEach(function(i) { if (i.offsetParent !== null && i.type !== 'hidden') visible++; });
            return visible;
          })()
        `);

        if (inputCount > 0) {
          L("   " + inputCount + " text input(s)");
          // Fill all visible text inputs
          let filled = await eval_(`
            (function() {
              var answers = ${JSON.stringify(govAnswers.slice(ansIdx, ansIdx + 5))};
              var inputs = document.querySelectorAll('input[type="text"], textarea');
              var filled = 0;
              var aIdx = 0;
              for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden') {
                  var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                  setter.call(inputs[i], answers[aIdx] || answers[0]);
                  inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                  inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
                  inputs[i].dispatchEvent(new Event('keyup', { bubbles: true }));
                  filled++;
                  aIdx++;
                }
              }
              return filled;
            })()
          `);
          L("   Filled " + filled + " inputs");
          ansIdx += filled;
        } else {
          // Check for radio/checkbox options
          let optionCount = await eval_(`
            (function() {
              return document.querySelectorAll('input[type="radio"], input[type="checkbox"]').length;
            })()
          `);

          if (optionCount > 0) {
            L("   " + optionCount + " options");

            // Try to answer based on question
            let target = null;
            if (qLower.includes('gender') || qLower.includes('sex')) target = 'Male';
            else if (qLower.includes('hispanic') || qLower.includes('latino')) target = 'No';
            else if (qLower.includes('race') || qLower.includes('ethnic')) target = 'White';
            else if (qLower.includes('education') || qLower.includes('degree')) target = 'Some college';
            else if (qLower.includes('marital') || qLower.includes('relationship')) target = 'Married';
            else if (qLower.includes('employ')) target = 'Self';
            else if (qLower.includes('income')) target = '75,000';
            else if (qLower.includes('industr')) target = 'Architecture';
            else if (qLower.includes('child')) target = 'No';
            else if (qLower.includes('state') && qLower.includes('live')) target = 'Idaho';
            else if (qLower.includes('register') && qLower.includes('vote')) target = 'Yes';
            else if (qLower.includes('agree') || qLower.includes('disagree') || qLower.includes('satisfied') || qLower.includes('likely') || qLower.includes('rate') || qLower.includes('scale')) {
              // Likert scale - pick middle or slightly positive
              target = 'Agree';
              if (qLower.includes('satisfied')) target = 'Satisfied';
              if (qLower.includes('likely')) target = 'Somewhat likely';
            }
            else if (qLower.includes('important') || qLower.includes('priority')) {
              target = 'Very important';
            }
            else if (qLower.includes('often') || qLower.includes('frequently')) {
              target = 'Sometimes';
            }
            else if (qLower.includes('yes') || qLower.includes('no')) {
              target = 'Yes';
            }

            if (target) {
              L("-> " + target);
              let r = await eval_(`
                (function() {
                  var target = ${JSON.stringify(target)};
                  var els = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                  for (var i = 0; i < els.length; i++) {
                    var label = els[i].closest('label') || els[i].parentElement;
                    var t = label ? label.textContent.trim() : '';
                    if (t.indexOf(target) >= 0 || t.toLowerCase().indexOf(target.toLowerCase()) >= 0) {
                      els[i].click();
                      return 'selected: ' + t.substring(0, 50);
                    }
                  }
                  // Try any clickable div/span
                  var all = document.querySelectorAll('[class*="option"], [class*="choice"], [class*="answer"], [role="option"], li, span');
                  for (var i = 0; i < all.length; i++) {
                    var t = all[i].textContent.trim();
                    if (t.indexOf(target) >= 0 && t.length < target.length + 30) {
                      all[i].click();
                      return 'clicked: ' + t.substring(0, 50);
                    }
                  }
                  return 'NOT_FOUND';
                })()
              `);
              L("   " + r);
            } else {
              // Default: select first option
              L("-> selecting first option");
              let r = await eval_(`
                (function() {
                  var radios = document.querySelectorAll('input[type="radio"]');
                  if (radios.length > 0) {
                    radios[0].click();
                    var label = radios[0].closest('label') || radios[0].parentElement;
                    return 'first radio: ' + (label ? label.textContent.trim().substring(0, 50) : 'unknown');
                  }
                  return 'no radios';
                })()
              `);
              L("   " + r);
            }
          } else {
            L("   No inputs or options. Page: " + pageText.substring(0, 300));
          }
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
      } catch(e) { L("Error: " + e.message); }

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
