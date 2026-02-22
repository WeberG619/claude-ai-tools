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
  const pageTab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
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

    const clickRadio = async (labelText) => {
      return await eval_(`
        (function() {
          var radios = document.querySelectorAll('input[type="radio"]');
          for (var i = 0; i < radios.length; i++) {
            var label = (radios[i].labels?.[0]?.textContent || '').trim();
            if (!label) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) label = p.textContent.trim(); }
            if (label.toLowerCase().includes('${labelText}'.toLowerCase())) {
              radios[i].click();
              if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
              return 'clicked: ' + label;
            }
          }
          return 'not found: ${labelText}';
        })()
      `);
    };

    const clickContinue = async () => {
      return await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next' || t === 'submit') {
              btns[i].click(); return 'clicked ' + btns[i].textContent.trim();
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

    const setSelect = async (value) => {
      return await eval_(`
        (function() {
          var sels = document.querySelectorAll('select');
          for (var j = 0; j < sels.length; j++) {
            var sel = sels[j];
            if (!sel.offsetParent) continue;
            for (var i = 0; i < sel.options.length; i++) {
              if (sel.options[i].text.toLowerCase().includes('${value}'.toLowerCase()) || sel.options[i].value === '${value}') {
                var ns = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
                ns.call(sel, sel.options[i].value);
                sel.dispatchEvent(new Event('input', { bubbles: true }));
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                return 'selected: ' + sel.options[i].text;
              }
            }
          }
          return 'no select or not found: ${value}';
        })()
      `);
    };

    // Extract just the question text (between header and "N Questions left")
    const getQuestion = async () => {
      return await eval_(`
        (function() {
          var text = document.body.innerText;
          // Remove header
          text = text.replace(/Choose a survey to earn Dollars/g, '');
          // Remove footer
          text = text.replace(/\\d+ Questions? left/g, '');
          text = text.replace(/Continue/g, '');
          return text.trim().substring(0, 300);
        })()
      `);
    };

    (async () => {
      // Fix ZIP first (currently stuck)
      L("=== FIXING ZIP ===");
      let r = await setInput('83864');
      L("ZIP: " + r);
      await sleep(500);
      r = await clickContinue();
      L("Continue: " + r);
      await sleep(3000);

      // Loop through remaining questions
      let lastQ = '';
      let stuckCount = 0;

      for (let step = 0; step < 15; step++) {
        let q = await getQuestion();
        let ql = q.toLowerCase();

        L("\n=== Q" + step + " ===");
        L("Q: " + q.substring(0, 200));

        // Get elements
        let els = await eval_(`
          (function() {
            var radios = [];
            document.querySelectorAll('input[type="radio"]').forEach(function(r) {
              var label = (r.labels?.[0]?.textContent || '').trim();
              if (!label) { var p = r.closest('label') || r.parentElement; if (p) label = p.textContent.trim(); }
              radios.push(label.substring(0, 60));
            });
            return JSON.stringify({ radios: radios });
          })()
        `);
        L("Radios: " + els);

        // Stuck detection
        let qShort = q.substring(0, 80);
        if (qShort === lastQ) {
          stuckCount++;
          if (stuckCount >= 2) { L("STUCK"); break; }
        } else { stuckCount = 0; }
        lastQ = qShort;

        let answered = false;

        // Handlers ordered by specificity - most specific first
        // DOB
        if (ql.includes('date of birth') || ql.includes('birthday') || ql.includes('when were you born')) {
          r = await setInput('18-03-1974'); L("  DOB: " + r); answered = true;
        }
        // ZIP
        else if (ql.includes('zip') || ql.includes('postal')) {
          r = await setInput('83864'); L("  ZIP: " + r); answered = true;
        }
        // Gender
        else if (ql.includes('gender') || (ql.includes('male') && ql.includes('female'))) {
          r = await clickRadio('Male'); L("  Gender: " + r); answered = true;
        }
        // Hispanic (before ethnicity)
        else if (ql.includes('hispanic') || ql.includes('latino')) {
          r = await clickRadio('Not Hispanic');
          if (r.includes('not found')) r = await clickRadio('No');
          L("  Hispanic: " + r); answered = true;
        }
        // Race/ethnicity
        else if (ql.includes('ethnic') || ql.includes('race') || ql.includes('racial')) {
          r = await clickRadio('White');
          if (r.includes('not found')) r = await clickRadio('Caucasian');
          L("  Ethnicity: " + r); answered = true;
        }
        // Education
        else if (ql.includes('education') || ql.includes('degree') || ql.includes('highest level')) {
          r = await clickRadio('Some college');
          if (r.includes('not found')) r = await clickRadio('College');
          if (r.includes('not found')) r = await clickRadio('Associate');
          if (r.includes('not found')) r = await clickRadio('High school');
          L("  Education: " + r); answered = true;
        }
        // Employment (check BEFORE income because "earn" is ambiguous)
        else if (ql.includes('employ') || ql.includes('work status') || ql.includes('occupat')) {
          r = await clickRadio('Self-employed');
          if (r.includes('not found')) r = await clickRadio('Self');
          if (r.includes('not found')) r = await clickRadio('Employed');
          L("  Employment: " + r); answered = true;
        }
        // Income (specific: must say "income" or "salary" or "household" but NOT just "earn")
        else if (ql.includes('income') || ql.includes('salary') || ql.includes('household')) {
          r = await clickRadio('$75');
          if (r.includes('not found')) r = await clickRadio('75,000');
          if (r.includes('not found')) r = await clickRadio('$50,000');
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
          if (r.includes('not found')) r = await setSelect('United States');
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
        else if (ql.includes('state') || ql.includes('region')) {
          r = await setSelect('Idaho');
          if (r.includes('not found')) r = await clickRadio('Idaho');
          L("  State: " + r); answered = true;
        }
        // Housing
        else if (ql.includes('own') && ql.includes('rent') || ql.includes('homeowner')) {
          r = await clickRadio('Rent');
          L("  Housing: " + r); answered = true;
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
                return 'radio[' + mid + '/' + radios.length + ']';
              }
              return 'no elements';
            })()
          `);
          L("  Generic: " + r);
        }

        await sleep(500);
        r = await clickContinue();
        L("  Continue: " + r);
        await sleep(3000);
      }

      // Final
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\n=== FINAL ===");
      L("URL: " + url);
      L("Page: " + pageText.substring(0, 1000));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_done.png', Buffer.from(ss.data, 'base64'));
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
