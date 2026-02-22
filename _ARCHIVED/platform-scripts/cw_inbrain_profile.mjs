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
              // Also click any radio inside
              var radio = els[i].querySelector('input[type="radio"]');
              if (radio) radio.click();
              return 'clicked: ' + t.substring(0, 60);
            }
          }
          return 'not found: ${text}';
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

    (async () => {
      // Answer ZIP first (current question)
      L("=== ZIP ===");
      let r = await setInput('83864');
      L("ZIP: " + r);
      await sleep(300);
      r = await clickContinue();
      L("Continue: " + r);
      await sleep(3000);

      // Loop through remaining profile questions
      let lastQ = '';
      let stuckCount = 0;

      for (let step = 0; step < 15; step++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        let ql = pageText.toLowerCase();

        L("\n=== Q" + step + " ===");
        L("Page: " + pageText.substring(0, 300));

        // Stuck detection
        let qShort = pageText.substring(0, 80);
        if (qShort === lastQ) { stuckCount++; if (stuckCount >= 2) { L("STUCK"); break; } } else { stuckCount = 0; }
        lastQ = qShort;

        // Completion check
        if (ql.includes('profile complete') || ql.includes('all done') || ql.includes('survey') && ql.includes('available') || ql.includes('no surveys')) {
          L("PROFILE DONE!"); break;
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
        // Age / DOB / year of birth
        else if (ql.includes('age') || ql.includes('birth year') || ql.includes('year of birth') || ql.includes('how old')) {
          r = await setInput('1974');
          if (r.includes('no input')) r = await clickRadio('50');
          L("  Age: " + r); answered = true;
        }
        else if (ql.includes('date of birth') || ql.includes('birthday')) {
          r = await setInput('03/18/1974'); L("  DOB: " + r); answered = true;
        }
        // Hispanic
        else if (ql.includes('hispanic') || ql.includes('latino')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('Not Hispanic');
          L("  Hispanic: " + r); answered = true;
        }
        // Race/ethnicity
        else if (ql.includes('ethnic') || ql.includes('race') || ql.includes('racial')) {
          r = await clickRadio('White');
          if (r.includes('not found')) r = await clickRadio('Caucasian');
          L("  Race: " + r); answered = true;
        }
        // Education
        else if (ql.includes('education') || ql.includes('degree') || ql.includes('school')) {
          r = await clickRadio('Some college');
          if (r.includes('not found')) r = await clickRadio('college');
          if (r.includes('not found')) r = await clickRadio('Associate');
          L("  Education: " + r); answered = true;
        }
        // Employment
        else if (ql.includes('employ') || ql.includes('work status') || ql.includes('occupation')) {
          r = await clickRadio('Self-employed');
          if (r.includes('not found')) r = await clickRadio('Self');
          if (r.includes('not found')) r = await clickRadio('Employed');
          L("  Employment: " + r); answered = true;
        }
        // Income
        else if (ql.includes('income') || ql.includes('salary') || ql.includes('household income')) {
          r = await clickRadio('$75');
          if (r.includes('not found')) r = await clickRadio('75,000');
          if (r.includes('not found')) r = await clickRadio('$50');
          L("  Income: " + r); answered = true;
        }
        // Marital
        else if (ql.includes('marital') || ql.includes('married') || ql.includes('relationship')) {
          r = await clickRadio('Single');
          if (r.includes('not found')) r = await clickRadio('Never');
          L("  Marital: " + r); answered = true;
        }
        // Children
        else if (ql.includes('children') || ql.includes('kids') || ql.includes('parent')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('None');
          if (r.includes('not found')) r = await clickRadio('0');
          L("  Children: " + r); answered = true;
        }
        // Country
        else if (ql.includes('country')) {
          r = await clickRadio('United States');
          if (r.includes('not found')) r = await clickRadio('US');
          L("  Country: " + r); answered = true;
        }
        // Industry
        else if (ql.includes('industry') || ql.includes('sector')) {
          r = await clickRadio('Architecture');
          if (r.includes('not found')) r = await clickRadio('Construction');
          if (r.includes('not found')) r = await clickRadio('Engineering');
          L("  Industry: " + r); answered = true;
        }
        // Language
        else if (ql.includes('language')) {
          r = await clickRadio('English');
          L("  Language: " + r); answered = true;
        }
        // State
        else if (ql.includes('state') && !ql.includes('united states')) {
          r = await clickRadio('Idaho');
          L("  State: " + r); answered = true;
        }

        // Generic fallback
        if (!answered) {
          r = await eval_(`
            (function() {
              var radios = document.querySelectorAll('input[type="radio"]');
              if (radios.length > 0) {
                var mid = Math.floor(radios.length / 2);
                radios[mid].click();
                if (radios[mid].labels && radios[mid].labels[0]) radios[mid].labels[0].click();
                return 'radio ' + mid + '/' + radios.length;
              }
              // Try clickable option elements
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

        await sleep(300);
        r = await clickContinue();
        L("  Continue: " + r);
        await sleep(3000);
      }

      // Final state
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\n=== FINAL ===");
      L("Page: " + pageText.substring(0, 1000));

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
