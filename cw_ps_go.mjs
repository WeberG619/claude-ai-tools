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

    // Click a checkbox/radio by label text (PureSpectrum uses multi-select-input checkboxes)
    const psSelectOption = async (target) => {
      return await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          // Find checkbox by its label text
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            var t = labels[i].textContent.trim();
            if (t === target || t.indexOf(target) >= 0) {
              var forId = labels[i].getAttribute('for');
              if (forId && forId.startsWith('selection-item')) {
                var cb = document.getElementById(forId);
                if (cb) {
                  cb.click();
                  return 'checked ' + forId + ': ' + t.substring(0, 50) + ' checked=' + cb.checked;
                }
              }
              // Also try clicking the label directly
              labels[i].click();
              return 'clicked label: ' + t.substring(0, 50);
            }
          }
          // Fallback: try the parent div click
          var divs = document.querySelectorAll('.multi-selection-container-item, [class*="option"], [class*="choice"]');
          for (var i = 0; i < divs.length; i++) {
            var t = divs[i].textContent.trim();
            if (t === target || t.indexOf(target) >= 0) {
              divs[i].click();
              return 'clicked div: ' + t.substring(0, 50);
            }
          }
          return 'NOT_FOUND';
        })()
      `);
    };

    const psClickNext = async () => {
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

    const psTypeText = async (value) => {
      return await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"], input[type="number"], input:not([type]), textarea, input[type="search"]');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden' && !inputs[i].id.startsWith('cky') && inputs[i].id !== 'search-input') {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], ${JSON.stringify(value)});
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('keyup', { bubbles: true }));
              return 'typed';
            }
          }
          // Try textarea specifically
          var tas = document.querySelectorAll('textarea');
          for (var i = 0; i < tas.length; i++) {
            if (tas[i].offsetParent !== null) {
              var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
              setter.call(tas[i], ${JSON.stringify(value)});
              tas[i].dispatchEvent(new Event('input', { bubbles: true }));
              return 'textarea typed';
            }
          }
          return 'no input';
        })()
      `);
    };

    // Fill ALL visible text inputs/textareas on the page
    const psFillTexts = async (answers) => {
      return await eval_(`
        (function() {
          var answers = ${JSON.stringify(answers)};
          var inputs = document.querySelectorAll('input[type="text"], textarea');
          var filled = 0;
          var aIdx = 0;
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden' && !inputs[i].id.startsWith('cky') && inputs[i].id !== 'search-input') {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], answers[aIdx % answers.length]);
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
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      const govTextAnswers = [
        "They should invest more in road maintenance and infrastructure throughout the community.",
        "More affordable housing options would help working families in our area.",
        "Better public transportation access would reduce congestion and improve mobility.",
        "Expanding parks and recreational facilities would benefit all residents.",
        "Investing in local school improvements would strengthen our community.",
        "More support for small business development through streamlined permits.",
        "Improving broadband internet access especially in rural neighborhoods.",
        "Creating walkable downtown areas with better sidewalks and lighting.",
        "Investing in renewable energy and sustainability initiatives.",
        "Better emergency response times and public safety resources needed."
      ];
      let textIdx = 0;

      let lastQ = '';
      let stuckCount = 0;

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
        let progress = pageText.match(/(\d+)%/);
        if (progress) L("Progress: " + progress[1] + "%");

        // End states
        if (lower.includes('thank you for completing') || lower.includes('survey is complete') || lower.includes('your response has been recorded')) {
          L("SURVEY COMPLETE!");
          L(pageText.substring(0, 500));
          break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('not eligible')) {
          L("SCREENED OUT");
          L(pageText.substring(0, 300));
          break;
        }
        if (!url.includes('purespectrum')) { L("REDIRECTED: " + url); break; }

        // Get question
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = lines.find(l => l.includes('?') && l.length > 15) || lines.find(l => l.length > 20 && l.length < 200 && !l.match(/^\d+%$/) && l !== 'Next' && l !== 'A') || '';
        L("Q: " + question.substring(0, 100));

        // Stuck detection
        if (question === lastQ) {
          stuckCount++;
          if (stuckCount >= 3) {
            L("STUCK! Taking screenshot and breaking.");
            break;
          }
        } else {
          stuckCount = 0;
        }
        lastQ = question;

        let qLower = question.toLowerCase();

        // Count visible text inputs (excluding search/cookie)
        let textInputCount = await eval_(`
          (function() {
            var count = 0;
            document.querySelectorAll('input[type="text"], textarea').forEach(function(i) {
              if (i.offsetParent !== null && !i.id.startsWith('cky') && i.id !== 'search-input') count++;
            });
            return count;
          })()
        `);

        // Count checkbox options (excluding cookie toggles)
        let cbCount = await eval_(`
          (function() {
            return document.querySelectorAll('input[type="checkbox"][id^="selection-item"]').length;
          })()
        `);

        // Count radio options
        let radioCount = await eval_(`document.querySelectorAll('input[type="radio"]').length`);

        L("   inputs=" + textInputCount + " cb=" + cbCount + " radio=" + radioCount);

        if (textInputCount > 0) {
          // Open-ended text question
          let answers = govTextAnswers.slice(textIdx, textIdx + textInputCount);
          if (answers.length < textInputCount) answers = govTextAnswers.slice(0, textInputCount);
          let filled = await psFillTexts(answers);
          L("   Filled " + filled + " text inputs");
          textIdx += filled;
        } else if (cbCount > 0) {
          // Checkbox/multi-select question
          let target = null;
          if (qLower.includes('sport')) target = 'National Football League';
          else if (qLower.includes('news') || qLower.includes('media')) target = 'Local TV news';
          else if (qLower.includes('social media')) target = 'Facebook';
          else if (qLower.includes('streaming')) target = 'Netflix';
          else if (qLower.includes('brand')) target = null; // pick first
          else if (qLower.includes('store') || qLower.includes('shop')) target = 'Amazon';
          else if (qLower.includes('issue') || qLower.includes('concern') || qLower.includes('important')) target = 'Economy';
          else if (qLower.includes('candidate') || qLower.includes('party')) target = 'Independent';

          if (target) {
            L("-> " + target);
            let r = await psSelectOption(target);
            L("   " + r);
          }

          if (!target || target === null) {
            // Just pick the first real option
            L("-> selecting first checkbox");
            let r = await eval_(`
              (function() {
                var cbs = document.querySelectorAll('input[type="checkbox"][id^="selection-item"]');
                if (cbs.length > 0) {
                  cbs[0].click();
                  var label = document.querySelector('label[for="' + cbs[0].id + '"]');
                  return 'checked: ' + (label ? label.textContent.trim().substring(0, 50) : cbs[0].id);
                }
                return 'no checkboxes';
              })()
            `);
            L("   " + r);
          }
        } else if (radioCount > 0) {
          // Radio/single-select question
          let target = null;
          if (qLower.includes('gender')) target = 'Male';
          else if (qLower.includes('agree') || qLower.includes('satisfaction')) target = 'Agree';
          else if (qLower.includes('likely')) target = 'Somewhat likely';
          else if (qLower.includes('important') || qLower.includes('priority')) target = 'Very important';
          else if (qLower.includes('often') || qLower.includes('frequently')) target = 'Sometimes';
          else if (qLower.includes('rate') || qLower.includes('scale')) target = '7'; // middle-high on 1-10

          if (target) {
            L("-> " + target);
            let r = await psSelectOption(target);
            L("   " + r);
          } else {
            // Pick first radio
            L("-> first radio");
            let r = await eval_(`
              (function() {
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                  radios[0].click();
                  var label = document.querySelector('label[for="' + radios[0].id + '"]');
                  return 'checked: ' + (label ? label.textContent.trim().substring(0, 50) : radios[0].id);
                }
                return 'no radios';
              })()
            `);
            L("   " + r);
          }
        } else {
          L("   No inputs found. Page: " + pageText.substring(0, 300));
        }

        await sleep(500);
        let cont = await psClickNext();
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
