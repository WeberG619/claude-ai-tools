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

// Weber's profile data
const PROFILE = {
  birthMonth: "March",
  birthDay: "18",
  birthYear: "1974",
  gender: "Male",
  zip: "83864",
  ethnicity: "White",
  hispanic: "No",
  education: "Some college, no degree",
  employment: "Self-employed",
  income: "75000",
  marital: "Single",
  children: "0",
  industry: "Architecture"
};

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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

    // Helper: set a select dropdown value using native setter
    const setSelect = async (selectorOrId, value) => {
      return await eval_(`
        (function() {
          var sel = document.getElementById('${selectorOrId}') || document.querySelector('${selectorOrId}');
          if (!sel) return 'select not found: ${selectorOrId}';
          var options = sel.options;
          for (var i = 0; i < options.length; i++) {
            if (options[i].text === '${value}' || options[i].value === '${value}') {
              var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
              nativeInputValueSetter.call(sel, options[i].value);
              sel.dispatchEvent(new Event('input', { bubbles: true }));
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'set ' + sel.id + ' to ' + options[i].text;
            }
          }
          // Try partial match
          for (var i = 0; i < options.length; i++) {
            if (options[i].text.toLowerCase().includes('${value}'.toLowerCase())) {
              var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
              nativeInputValueSetter.call(sel, options[i].value);
              sel.dispatchEvent(new Event('input', { bubbles: true }));
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'set (partial) ' + sel.id + ' to ' + options[i].text;
            }
          }
          return 'value not found in ' + sel.id + ': ${value}. Options: ' + Array.from(options).map(o => o.text).slice(0,10).join(', ');
        })()
      `);
    };

    // Helper: click a button by text
    const clickButton = async (text) => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, input[type="submit"], a');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t.toLowerCase() === '${text}'.toLowerCase() || t.toLowerCase().includes('${text}'.toLowerCase())) {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'button not found: ${text}';
        })()
      `);
    };

    // Helper: click a radio/option by text content
    const clickOption = async (text) => {
      return await eval_(`
        (function() {
          // Try labels, divs, spans with matching text
          var all = document.querySelectorAll('label, [role="radio"], [role="option"], [role="button"], div, span, li');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.toLowerCase() === '${text}'.toLowerCase()) {
              all[i].click();
              return 'clicked option: ' + t;
            }
          }
          // Partial match
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.length < 80 && t.toLowerCase().includes('${text}'.toLowerCase())) {
              all[i].click();
              return 'clicked partial: ' + t;
            }
          }
          return 'option not found: ${text}';
        })()
      `);
    };

    // Helper: get page state
    const getState = async () => {
      const pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      const inputs = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input:not([type="hidden"]), select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return { type: i.type, id: i.id, name: i.name, placeholder: (i.placeholder||'').substring(0,40) };
          }));
        })()
      `);
      const buttons = await eval_(`
        (function() {
          var els = document.querySelectorAll('button, [role="radio"], [role="option"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({ tag: els[i].tagName, text: els[i].textContent.trim().substring(0, 80), role: els[i].getAttribute('role') || '' });
            }
          }
          return JSON.stringify(result.slice(0, 25));
        })()
      `);
      return { pageText: pageText.substring(0, 1500), inputs: JSON.parse(inputs || '[]'), buttons: JSON.parse(buttons || '[]') };
    };

    (async () => {
      // STEP 1: Set birthday dropdowns (already on this page)
      L("=== BIRTHDAY ===");
      let r;
      r = await setSelect('rx-profile-birthday-month', 'March');
      L("Month: " + r);
      await sleep(300);
      r = await setSelect('rx-profile-birthday-day', '18');
      L("Day: " + r);
      await sleep(300);
      r = await setSelect('rx-profile-birthday-year', '1974');
      L("Year: " + r);
      await sleep(500);
      r = await clickButton('Continue');
      L("Continue: " + r);
      await sleep(4000);

      // Loop through profiling questions
      let lastQuestion = '';
      let stuckCount = 0;

      for (let step = 0; step < 25; step++) {
        const state = await getState();
        const q = state.pageText.substring(0, 300).replace(/\n/g, ' ').trim();
        L("\n=== STEP " + step + " ===");
        L("Q: " + q.substring(0, 200));
        L("Inputs: " + JSON.stringify(state.inputs));
        L("Buttons: " + state.buttons.map(b => b.text.substring(0,40)).join(' | '));

        // Stuck detection
        if (q === lastQuestion) {
          stuckCount++;
          if (stuckCount >= 2) {
            L("STUCK - same question 3 times, taking screenshot and breaking");
            const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
            writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_stuck.png', Buffer.from(ss.data, 'base64'));
            break;
          }
        } else {
          stuckCount = 0;
        }
        lastQuestion = q;

        const ql = q.toLowerCase();

        // Check if we reached the survey wall / offers page
        if (ql.includes('take a survey') || ql.includes('survey wall') || ql.includes('available surveys') || ql.includes('earn rewards')) {
          L("REACHED SURVEY WALL!");
          break;
        }

        // Check for completion
        if (ql.includes('thank you') || ql.includes('profile complete') || ql.includes('all done') || ql.includes('congratulations')) {
          L("PROFILE COMPLETE!");
          r = await clickButton('Continue');
          L("Continue: " + r);
          await sleep(3000);
          break;
        }

        // Handle based on question type
        let answered = false;

        // Birthday (already handled but just in case)
        if (state.inputs.some(i => i.id && i.id.includes('birthday'))) {
          r = await setSelect('rx-profile-birthday-month', 'March');
          L("  Month: " + r);
          await sleep(200);
          r = await setSelect('rx-profile-birthday-day', '18');
          L("  Day: " + r);
          await sleep(200);
          r = await setSelect('rx-profile-birthday-year', '1974');
          L("  Year: " + r);
          answered = true;
        }
        // Gender
        else if (ql.includes('gender') || ql.includes('what is your sex') || (ql.includes('are you') && ql.includes('male'))) {
          r = await clickOption('Male');
          L("  Gender: " + r);
          answered = true;
        }
        // ZIP code
        else if (ql.includes('zip') || ql.includes('postal code') || ql.includes('zip code')) {
          r = await eval_(`
            (function() {
              var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"])');
              if (!inp) return 'no input found';
              var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              nativeInputValueSetter.call(inp, '83864');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'set zip to 83864';
            })()
          `);
          L("  ZIP: " + r);
          answered = true;
        }
        // Country
        else if (ql.includes('country') && (ql.includes('live') || ql.includes('reside') || ql.includes('located'))) {
          r = await clickOption('United States');
          if (r.includes('not found')) r = await clickOption('US');
          if (r.includes('not found')) r = await clickOption('USA');
          L("  Country: " + r);
          answered = true;
        }
        // Hispanic/Latino
        else if (ql.includes('hispanic') || ql.includes('latino') || ql.includes('spanish origin')) {
          r = await clickOption('No');
          if (r.includes('not found')) r = await clickOption('Not Hispanic');
          L("  Hispanic: " + r);
          answered = true;
        }
        // Ethnicity/Race
        else if (ql.includes('ethnicity') || ql.includes('race') || ql.includes('racial')) {
          r = await clickOption('White');
          if (r.includes('not found')) r = await clickOption('Caucasian');
          L("  Ethnicity: " + r);
          answered = true;
        }
        // Education
        else if (ql.includes('education') || ql.includes('school') || ql.includes('degree')) {
          r = await clickOption('Some college');
          if (r.includes('not found')) r = await clickOption('some college');
          if (r.includes('not found')) {
            // Try select dropdown
            for (const inp of state.inputs) {
              if (inp.type === 'select-one') {
                r = await setSelect(inp.id, 'Some college');
                if (r.includes('not found')) r = await setSelect(inp.id, 'college');
                break;
              }
            }
          }
          L("  Education: " + r);
          answered = true;
        }
        // Employment
        else if (ql.includes('employ') || ql.includes('work status') || ql.includes('occupation')) {
          r = await clickOption('Self-employed');
          if (r.includes('not found')) r = await clickOption('Self employed');
          if (r.includes('not found')) r = await clickOption('Employed full-time');
          if (r.includes('not found')) r = await clickOption('Full-time');
          L("  Employment: " + r);
          answered = true;
        }
        // Income
        else if (ql.includes('income') || ql.includes('household income') || ql.includes('annual income') || ql.includes('earn')) {
          r = await clickOption('$75,000');
          if (r.includes('not found')) r = await clickOption('75,000');
          if (r.includes('not found')) r = await clickOption('$50,000 - $74,999');
          if (r.includes('not found')) r = await clickOption('$75,000 - $99,999');
          if (r.includes('not found')) {
            // Try select dropdown
            for (const inp of state.inputs) {
              if (inp.type === 'select-one') {
                r = await setSelect(inp.id, '75');
                break;
              }
            }
          }
          L("  Income: " + r);
          answered = true;
        }
        // Marital status
        else if (ql.includes('marital') || ql.includes('married') || ql.includes('relationship status')) {
          r = await clickOption('Single');
          if (r.includes('not found')) r = await clickOption('Never married');
          L("  Marital: " + r);
          answered = true;
        }
        // Children
        else if (ql.includes('children') || ql.includes('kids') || ql.includes('dependents')) {
          r = await clickOption('No');
          if (r.includes('not found')) r = await clickOption('None');
          if (r.includes('not found')) r = await clickOption('0');
          L("  Children: " + r);
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
        // Language
        else if (ql.includes('language') || ql.includes('speak')) {
          r = await clickOption('English');
          L("  Language: " + r);
          answered = true;
        }
        // State
        else if (ql.includes('state') && (ql.includes('live') || ql.includes('reside') || ql.includes('which state'))) {
          r = await clickOption('Idaho');
          if (r.includes('not found')) r = await clickOption('ID');
          if (r.includes('not found')) {
            for (const inp of state.inputs) {
              if (inp.type === 'select-one') {
                r = await setSelect(inp.id, 'Idaho');
                break;
              }
            }
          }
          L("  State: " + r);
          answered = true;
        }
        // Device type
        else if (ql.includes('device') || ql.includes('desktop') || ql.includes('laptop') || ql.includes('computer')) {
          r = await clickOption('Desktop');
          if (r.includes('not found')) r = await clickOption('Computer');
          if (r.includes('not found')) r = await clickOption('PC');
          L("  Device: " + r);
          answered = true;
        }

        // Generic fallback: if there are radio-like options, pick first reasonable one
        if (!answered) {
          // Check for select dropdowns
          const selects = state.inputs.filter(i => i.type === 'select-one');
          if (selects.length > 0) {
            r = await eval_(`
              (function() {
                var sel = document.getElementById('${selects[0].id}') || document.querySelector('select');
                if (!sel) return 'no select found';
                // Pick second option (first is usually placeholder)
                if (sel.options.length > 1) {
                  sel.selectedIndex = 1;
                  sel.dispatchEvent(new Event('change', { bubbles: true }));
                  return 'selected: ' + sel.options[1].text;
                }
                return 'no options';
              })()
            `);
            L("  Generic select: " + r);
            answered = true;
          }

          // Check for clickable radio-like options
          if (!answered) {
            const options = state.buttons.filter(b => b.role === 'radio' || b.role === 'option');
            if (options.length > 0) {
              // Pick middle option for unknown questions
              const midIdx = Math.floor(options.length / 2);
              r = await clickOption(options[midIdx].text);
              L("  Generic option: " + r);
              answered = true;
            }
          }

          if (!answered) {
            L("  No handler matched, trying Continue anyway");
          }
        }

        // Click Continue/Next/Submit
        await sleep(500);
        r = await clickButton('Continue');
        if (r.includes('not found')) r = await clickButton('Next');
        if (r.includes('not found')) r = await clickButton('Submit');
        if (r.includes('not found')) r = await clickButton('Done');
        L("  Submit: " + r);
        await sleep(3000);
      }

      // Final state
      let url = await eval_(`window.location.href`);
      L("\n=== FINAL STATE ===");
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 1000));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_final.png', Buffer.from(ss.data, 'base64'));
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
