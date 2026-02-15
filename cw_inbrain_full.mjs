import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 180000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const ibTarget = tabs.find(t => t.url.includes('surveyb.in'));
  if (!ibTarget) { L("No Inbrain target"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(ibTarget.webSocketDebuggerUrl);
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

    const clickRadio = async (text) => {
      return await eval_(`
        (function() {
          var els = document.querySelectorAll('input[type="radio"], [role="radio"], label, [class*="option"], [class*="answer"]');
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim();
            if (t.toLowerCase().includes('${text}'.toLowerCase())) {
              els[i].click();
              var radio = els[i].querySelector('input[type="radio"]');
              if (radio) radio.click();
              return 'clicked: ' + t.substring(0, 60);
            }
          }
          return 'not found: ${text}';
        })()
      `);
    };

    const clickButton = async (text) => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, [role="button"], a');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t.includes('${text}'.toLowerCase())) {
              btns[i].click();
              return 'clicked: ' + btns[i].textContent.trim();
            }
          }
          return 'no ${text} button';
        })()
      `);
    };

    const clickContinue = async () => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, [role="button"]');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next' || t === 'submit' || t === 'done') {
              btns[i].click();
              return 'clicked: ' + btns[i].textContent.trim();
            }
          }
          return 'no continue';
        })()
      `);
    };

    const setInput = async (value) => {
      return await eval_(`
        (function() {
          var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
          if (!inp) return 'no input';
          inp.focus();
          var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          ns.call(inp, '${value}');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          return 'set: ${value}';
        })()
      `);
    };

    const setSelect = async (text) => {
      return await eval_(`
        (function() {
          var sel = document.querySelector('select');
          if (!sel) return 'no select';
          for (var i = 0; i < sel.options.length; i++) {
            if (sel.options[i].text.toLowerCase().includes('${text}'.toLowerCase())) {
              sel.selectedIndex = i;
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'selected: ' + sel.options[i].text;
            }
          }
          return 'option not found: ${text}';
        })()
      `);
    };

    (async () => {
      // Click Get Started
      L("=== CLICKING GET STARTED ===");
      let r = await clickButton('get started');
      L("Start: " + r);
      await sleep(5000);

      let lastQ = '';
      let stuckCount = 0;
      let answeredCount = 0;

      for (let step = 0; step < 25; step++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        let ql = pageText.toLowerCase();

        L("\n=== Q" + step + " (answered: " + answeredCount + ") ===");
        L("Page: " + pageText.substring(0, 300));

        // Stuck detection
        let qShort = pageText.substring(0, 80);
        if (qShort === lastQ) { stuckCount++; if (stuckCount >= 3) { L("STUCK after " + answeredCount + " answers"); break; } } else { stuckCount = 0; }
        lastQ = qShort;

        // Error page
        if (ql.includes('oops') || ql.includes('went wrong') || ql.includes('bad request')) {
          L("  ERROR PAGE - clicking Refresh");
          r = await clickButton('refresh');
          L("  Refresh: " + r);
          await sleep(5000);
          continue;
        }

        // Real completion: profile is done when we see the survey list (not the "Get Started" page)
        // The survey list shows individual survey cards with reward amounts
        if (answeredCount >= 5 && (ql.includes('profile complete') || ql.includes('all done') || ql.includes('no surveys available'))) {
          L("PROFILE DONE! Answered " + answeredCount + " questions");
          break;
        }

        // If we're back at the Get Started page after answering questions, profile might be complete
        if (answeredCount >= 5 && ql.includes('get started') && ql.includes('earn rewards')) {
          L("Back at start page after " + answeredCount + " answers - profile may be complete");
          // Check for survey cards
          let cards = await eval_(`document.querySelectorAll('[class*="SurveyCard"], [class*="survey-card"], [class*="surveyCard"]').length`);
          L("Survey cards found: " + cards);
          if (cards > 0) { L("SURVEYS AVAILABLE!"); break; }
          // Click Get Started to see if there are more questions
          r = await clickButton('get started');
          L("  Re-start: " + r);
          await sleep(5000);
          continue;
        }

        // Skip "Get Started" page on first iteration
        if (ql.includes('get started') && ql.includes('earn rewards') && answeredCount === 0) {
          L("  Still on start page, waiting...");
          await sleep(3000);
          continue;
        }

        let answered = false;

        // ZIP
        if (ql.includes('zip') || ql.includes('postal')) {
          r = await setInput('83864'); L("  ZIP: " + r); answered = true;
        }
        // Gender
        else if (ql.includes('gender')) {
          r = await clickRadio('Male'); L("  Gender: " + r); answered = true;
        }
        // Age / year of birth
        else if ((ql.includes('age') && !ql.includes('language')) || ql.includes('birth year') || ql.includes('year of birth') || ql.includes('how old')) {
          r = await setInput('1974');
          if (r.includes('no input')) {
            r = await setInput('51');
            if (r.includes('no input')) r = await clickRadio('50');
          }
          L("  Age: " + r); answered = true;
        }
        // DOB
        else if (ql.includes('date of birth') || ql.includes('birthday')) {
          r = await setInput('03/18/1974'); L("  DOB: " + r); answered = true;
        }
        // Hispanic
        else if (ql.includes('hispanic') || ql.includes('latino')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('Not Hispanic');
          if (r.includes('not found')) r = await clickRadio('not of');
          L("  Hispanic: " + r); answered = true;
        }
        // Race/ethnicity
        else if (ql.includes('ethnic') || ql.includes('race') || ql.includes('racial')) {
          r = await clickRadio('White');
          if (r.includes('not found')) r = await clickRadio('Caucasian');
          L("  Race: " + r); answered = true;
        }
        // Education
        else if (ql.includes('education') || ql.includes('highest level') || (ql.includes('degree') && !ql.includes('agree'))) {
          r = await clickRadio('some college');
          if (r.includes('not found')) r = await clickRadio('college');
          if (r.includes('not found')) r = await clickRadio('Associate');
          L("  Education: " + r); answered = true;
        }
        // Employment
        else if (ql.includes('employment status') || (ql.includes('employ') && !ql.includes('how many'))) {
          r = await clickRadio('Self Employed');
          if (r.includes('not found')) r = await clickRadio('Self-employed');
          if (r.includes('not found')) r = await clickRadio('Employed');
          L("  Employment: " + r); answered = true;
        }
        // Income
        else if (ql.includes('income') || ql.includes('salary') || ql.includes('earn per year')) {
          r = await clickRadio('$75');
          if (r.includes('not found')) r = await clickRadio('75,000');
          if (r.includes('not found')) r = await clickRadio('$50');
          if (r.includes('not found')) r = await clickRadio('50,000');
          L("  Income: " + r); answered = true;
        }
        // Marital
        else if (ql.includes('marital') || ql.includes('married') || ql.includes('relationship status')) {
          r = await clickRadio('Single');
          if (r.includes('not found')) r = await clickRadio('Never married');
          if (r.includes('not found')) r = await clickRadio('Never');
          L("  Marital: " + r); answered = true;
        }
        // Children / parent
        else if (ql.includes('children') || ql.includes('kids') || (ql.includes('parent') && !ql.includes('transparent'))) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('None');
          if (r.includes('not found')) r = await clickRadio('0');
          L("  Children: " + r); answered = true;
        }
        // Country
        else if (ql.includes('country') && !ql.includes('county')) {
          r = await clickRadio('United States');
          if (r.includes('not found')) r = await clickRadio('US');
          if (r.includes('not found')) r = await setSelect('United States');
          L("  Country: " + r); answered = true;
        }
        // Industry / sector
        else if (ql.includes('industry') || ql.includes('sector') || ql.includes('field of work')) {
          r = await clickRadio('Architecture');
          if (r.includes('not found')) r = await clickRadio('Construction');
          if (r.includes('not found')) r = await clickRadio('Engineering');
          if (r.includes('not found')) r = await clickRadio('Real Estate');
          L("  Industry: " + r); answered = true;
        }
        // Language
        else if (ql.includes('language')) {
          r = await clickRadio('English');
          L("  Language: " + r); answered = true;
        }
        // State
        else if (ql.includes('state') && !ql.includes('united states') && !ql.includes('employment status') && !ql.includes('marital status')) {
          r = await clickRadio('Idaho');
          if (r.includes('not found')) r = await clickRadio('ID');
          if (r.includes('not found')) r = await setSelect('Idaho');
          L("  State: " + r); answered = true;
        }
        // Voter
        else if (ql.includes('registered to vote') || ql.includes('voter')) {
          r = await clickRadio('Yes');
          L("  Voter: " + r); answered = true;
        }
        // Purchasing decisions
        else if (ql.includes('purchasing') || ql.includes('buying decision') || ql.includes('daily purchasing')) {
          r = await clickRadio('Yes');
          L("  Purchasing: " + r); answered = true;
        }
        // Household size
        else if (ql.includes('household') && (ql.includes('how many') || ql.includes('number') || ql.includes('size'))) {
          r = await clickRadio('1');
          if (r.includes('not found')) r = await setInput('1');
          L("  Household: " + r); answered = true;
        }
        // Region
        else if (ql.includes('region')) {
          r = await clickRadio('West');
          if (r.includes('not found')) r = await clickRadio('Pacific');
          if (r.includes('not found')) r = await clickRadio('Northwest');
          L("  Region: " + r); answered = true;
        }
        // Pet/animal ownership
        else if (ql.includes('pet') || ql.includes('animal') || ql.includes('dog') || ql.includes('cat')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('None');
          L("  Pets: " + r); answered = true;
        }
        // Homeowner
        else if (ql.includes('own or rent') || ql.includes('homeowner') || ql.includes('housing')) {
          r = await clickRadio('Own');
          if (r.includes('not found')) r = await clickRadio('Homeowner');
          L("  Housing: " + r); answered = true;
        }
        // Cell phone / mobile
        else if (ql.includes('cell phone') || ql.includes('mobile phone') || ql.includes('smartphone')) {
          r = await clickRadio('Yes');
          if (r.includes('not found')) r = await clickRadio('Android');
          L("  Phone: " + r); answered = true;
        }

        // Generic fallback for unrecognized questions
        if (!answered) {
          r = await eval_(`
            (function() {
              var radios = document.querySelectorAll('input[type="radio"]');
              if (radios.length > 0) {
                var mid = Math.floor(radios.length / 2);
                radios[mid].click();
                if (radios[mid].labels && radios[mid].labels[0]) radios[mid].labels[0].click();
                var lbl = (radios[mid].labels && radios[mid].labels[0]) ? radios[mid].labels[0].textContent.trim().substring(0,40) : '';
                return 'radio ' + mid + '/' + radios.length + ': ' + lbl;
              }
              var opts = document.querySelectorAll('[class*="option"], [class*="answer"], [role="radio"]');
              if (opts.length > 0) {
                var mid = Math.floor(opts.length / 2);
                opts[mid].click();
                return 'option ' + mid + '/' + opts.length + ': ' + opts[mid].textContent.trim().substring(0, 40);
              }
              return 'no elements';
            })()
          `);
          L("  Generic: " + r);
        }

        if (answered) answeredCount++;

        await sleep(400);
        r = await clickContinue();
        L("  Continue: " + r);
        await sleep(3000);
      }

      // Final state
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      let url = await eval_(`window.location.href`);
      L("\n=== FINAL ===");
      L("URL: " + url);
      L("Page: " + pageText.substring(0, 1500));

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
