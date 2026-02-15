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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('opnion.io'));
  if (!surveyTab) {
    L("No survey tab found. Tabs:");
    tabs.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 100)));
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    // Helper: set text input
    const setInput = async (value) => {
      return await eval_(`
        (function() {
          var inp = document.querySelector('input[type="text"], input[type="number"], input[name="selected_opt"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
          if (!inp) return 'no input found';
          inp.focus();
          var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          nativeInputValueSetter.call(inp, '${value}');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          return 'set to: ${value}';
        })()
      `);
    };

    // Helper: click option by exact or partial text
    const clickOption = async (text) => {
      return await eval_(`
        (function() {
          // First try exact match on clickable-looking elements
          var els = document.querySelectorAll('label, li, div[class*="opt"], div[class*="answer"], div[class*="choice"], span, p, button');
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim();
            if (t === '${text}') {
              els[i].click();
              return 'exact: ' + t;
            }
          }
          // Partial match (case insensitive)
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim();
            if (t.length < 100 && t.toLowerCase().includes('${text}'.toLowerCase())) {
              els[i].click();
              return 'partial: ' + t;
            }
          }
          // Try radio buttons
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = radios[i].labels && radios[i].labels[0] ? radios[i].labels[0].textContent.trim() : '';
            if (label.toLowerCase().includes('${text}'.toLowerCase()) || radios[i].value.toLowerCase().includes('${text}'.toLowerCase())) {
              radios[i].click();
              return 'radio: ' + label;
            }
          }
          return 'not found: ${text}';
        })()
      `);
    };

    // Helper: click Next/Continue/Submit button
    const clickNext = async () => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, input[type="submit"], a.btn, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'next' || t === 'continue' || t === 'submit' || t === 'ok' || t === 'done' || t.includes('next')) {
              btns[i].click();
              return 'clicked: ' + btns[i].textContent.trim();
            }
          }
          return 'no next button';
        })()
      `);
    };

    (async () => {
      let lastUrl = '';
      let stuckCount = 0;

      for (let step = 0; step < 40; step++) {
        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let q = pageText.replace(/\n/g, ' ').trim();

        L("\n=== Q" + step + " ===");
        L("URL: " + url.substring(url.indexOf('#') >= 0 ? url.indexOf('#') : 0));
        L("Q: " + q.substring(0, 200));

        // Stuck detection
        if (url === lastUrl) {
          stuckCount++;
          if (stuckCount >= 3) {
            L("STUCK on same URL 3 times");
            break;
          }
        } else {
          stuckCount = 0;
        }
        lastUrl = url;

        let ql = q.toLowerCase();
        let urlL = url.toLowerCase();

        // Check for completion/screenout
        if (ql.includes('thank you') || ql.includes('completed') || ql.includes('all done') || ql.includes('survey is complete')) {
          L("SURVEY COMPLETE!");
          break;
        }
        if (ql.includes('screened out') || ql.includes('not qualify') || ql.includes('sorry') || ql.includes('do not match') || ql.includes('unfortunately')) {
          L("SCREENED OUT");
          break;
        }
        if (ql.includes('redirecting') || ql.includes('please wait')) {
          L("Redirecting, waiting...");
          await sleep(5000);
          continue;
        }

        let answered = false;
        let r;

        // Gender question
        if (urlL.includes('/gender') || (ql.includes('are you') && (ql.includes('male') || ql.includes('female')))) {
          r = await clickOption('Male');
          L("  Gender: " + r);
          answered = true;
        }
        // Age question (text input)
        else if (urlL.includes('/age') || ql.includes('what is your age')) {
          r = await setInput('51');
          L("  Age: " + r);
          answered = true;
        }
        // ZIP code
        else if (urlL.includes('/zip') || ql.includes('zip') || ql.includes('postal code')) {
          r = await setInput('83864');
          L("  ZIP: " + r);
          answered = true;
        }
        // State
        else if (urlL.includes('/state') || (ql.includes('state') && ql.includes('live'))) {
          r = await clickOption('Idaho');
          if (r.includes('not found')) r = await setInput('Idaho');
          L("  State: " + r);
          answered = true;
        }
        // Hispanic
        else if (ql.includes('hispanic') || ql.includes('latino')) {
          r = await clickOption('No');
          if (r.includes('not found')) r = await clickOption('Not Hispanic');
          L("  Hispanic: " + r);
          answered = true;
        }
        // Ethnicity/race
        else if (ql.includes('ethnic') || ql.includes('race') || ql.includes('racial')) {
          r = await clickOption('White');
          if (r.includes('not found')) r = await clickOption('Caucasian');
          L("  Race: " + r);
          answered = true;
        }
        // Education
        else if (ql.includes('education') || ql.includes('degree') || ql.includes('school')) {
          r = await clickOption('Some college');
          if (r.includes('not found')) r = await clickOption('college');
          L("  Education: " + r);
          answered = true;
        }
        // Employment
        else if (ql.includes('employ') || ql.includes('work') || ql.includes('occupation')) {
          r = await clickOption('Self-employed');
          if (r.includes('not found')) r = await clickOption('Self');
          if (r.includes('not found')) r = await clickOption('Employed');
          L("  Employment: " + r);
          answered = true;
        }
        // Income
        else if (ql.includes('income') || ql.includes('salary') || ql.includes('earn')) {
          r = await clickOption('$75,000');
          if (r.includes('not found')) r = await clickOption('75,000');
          if (r.includes('not found')) r = await clickOption('$50,000');
          if (r.includes('not found')) r = await setInput('75000');
          L("  Income: " + r);
          answered = true;
        }
        // Marital
        else if (ql.includes('marital') || ql.includes('married') || ql.includes('relationship')) {
          r = await clickOption('Single');
          if (r.includes('not found')) r = await clickOption('Never married');
          L("  Marital: " + r);
          answered = true;
        }
        // Children
        else if (ql.includes('children') || ql.includes('kids') || ql.includes('parent')) {
          r = await clickOption('No');
          if (r.includes('not found')) r = await clickOption('None');
          if (r.includes('not found')) r = await clickOption('0');
          L("  Children: " + r);
          answered = true;
        }
        // Country
        else if (ql.includes('country') && (ql.includes('live') || ql.includes('reside'))) {
          r = await clickOption('United States');
          if (r.includes('not found')) r = await clickOption('US');
          L("  Country: " + r);
          answered = true;
        }
        // Language
        else if (ql.includes('language')) {
          r = await clickOption('English');
          L("  Language: " + r);
          answered = true;
        }
        // Device
        else if (ql.includes('device') || ql.includes('desktop') || ql.includes('computer')) {
          r = await clickOption('Desktop');
          if (r.includes('not found')) r = await clickOption('Computer');
          L("  Device: " + r);
          answered = true;
        }
        // Industry
        else if (ql.includes('industry') || ql.includes('field of work') || ql.includes('sector')) {
          r = await clickOption('Architecture');
          if (r.includes('not found')) r = await clickOption('Construction');
          if (r.includes('not found')) r = await clickOption('Engineering');
          L("  Industry: " + r);
          answered = true;
        }
        // Homeownership
        else if (ql.includes('own') && ql.includes('rent') || ql.includes('homeowner')) {
          r = await clickOption('Rent');
          if (r.includes('not found')) r = await clickOption('Renting');
          L("  Housing: " + r);
          answered = true;
        }
        // Yes/No questions (generic)
        else if (ql.includes('?') && (ql.includes(' yes ') || ql.includes(' no ')) && q.length < 200) {
          // For generic yes/no, default to "No" for safety
          r = await clickOption('No');
          L("  Generic Y/N: " + r);
          answered = true;
        }

        // Generic fallback for survey questions with options
        if (!answered) {
          r = await eval_(`
            (function() {
              // Get all visible option-like elements
              var options = [];
              var all = document.querySelectorAll('label, li, div, span');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                var rect = all[i].getBoundingClientRect();
                if (rect.width > 20 && rect.height > 10 && rect.height < 100 && t.length > 0 && t.length < 100) {
                  // Exclude question text (usually longer) and buttons
                  if (!t.toLowerCase().includes('next') && !t.toLowerCase().includes('submit') && all[i].tagName !== 'BUTTON') {
                    var isChild = false;
                    // Check if this has child elements with text (i.e., it's a container)
                    var childText = '';
                    for (var j = 0; j < all[i].children.length; j++) {
                      childText += all[i].children[j].textContent;
                    }
                    options.push({ text: t, tag: all[i].tagName, y: rect.y });
                  }
                }
              }
              // Sort by y position, get unique-ish ones
              options.sort(function(a, b) { return a.y - b.y; });
              // Pick the middle option for neutral answers
              if (options.length > 2) {
                var mid = Math.floor(options.length / 2);
                return JSON.stringify(options.slice(0, Math.min(10, options.length)));
              }
              return JSON.stringify(options);
            })()
          `);
          L("  Generic options: " + r);

          // Try clicking the first reasonable option
          let options = [];
          try { options = JSON.parse(r); } catch(e) {}
          if (options.length > 1) {
            // Pick middle option
            let midIdx = Math.floor(options.length / 2);
            r = await clickOption(options[midIdx].text);
            L("  Clicked middle[" + midIdx + "]: " + r);
            answered = true;
          }
        }

        // Click Next
        await sleep(500);
        r = await clickNext();
        L("  Next: " + r);
        await sleep(3000);
      }

      // Final state
      let url = await eval_(`window.location.href`);
      L("\n=== FINAL ===");
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 1000));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_loop.png', Buffer.from(ss.data, 'base64'));
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
