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
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

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
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked'; }
          }
          return 'no continue';
        })()
      `);
    };

    const getHeading = async () => {
      return await eval_(`
        (function() {
          var headings = document.querySelectorAll('h1, h2, h3, h4, h5, p, [class*="question"], [class*="title"]');
          for (var i = 0; i < headings.length; i++) {
            var t = headings[i].textContent.trim();
            if (t.length > 10 && t.length < 300 && t.includes('?')) return t;
          }
          var lines = document.body.innerText.split('\\n');
          for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (line.length > 10 && line.includes('?') && !line.includes('earn Dollars')) return line;
          }
          return document.body.innerText.substring(0, 300);
        })()
      `);
    };

    const getQuestionsLeft = async () => {
      return await eval_(`
        (function() {
          var m = document.body.innerText.match(/(\\d+) Questions? left/);
          return m ? parseInt(m[1]) : -1;
        })()
      `);
    };

    (async () => {
      // Fix first name question
      L("=== FIXING FIRST NAME ===");
      let r = await setInput('Weber');
      L("First name: " + r);
      await sleep(500);
      r = await clickContinue();
      L("Continue: " + r);
      await sleep(3000);

      let left = await getQuestionsLeft();
      L("Questions left: " + left);

      // Loop remaining
      let lastH = '';
      let stuckCount = 0;

      for (let step = 0; step < 8; step++) {
        let heading = await getHeading();
        let hl = heading.toLowerCase();

        L("\n=== Q" + step + " ===");
        L("Heading: " + heading.substring(0, 250));

        let radioLabels = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            return Array.from(radios).map(function(r) {
              var l = (r.labels?.[0]?.textContent || '').trim();
              if (!l) { var p = r.closest('label') || r.parentElement; if (p) l = p.textContent.trim(); }
              return l.substring(0, 50);
            }).join(', ');
          })()
        `);
        L("Options: " + radioLabels.substring(0, 300));

        left = await getQuestionsLeft();
        L("Left: " + left);

        // Stuck
        if (heading.substring(0, 80) === lastH) {
          stuckCount++;
          if (stuckCount >= 2) { L("STUCK"); break; }
        } else { stuckCount = 0; }
        lastH = heading.substring(0, 80);

        if (left === 0) { L("DONE!"); break; }

        let answered = false;

        // Name fields
        if (hl.includes('first name')) {
          r = await setInput('Weber'); L("  First name: " + r); answered = true;
        }
        else if (hl.includes('last name') || hl.includes('surname')) {
          r = await setInput('Gouin'); L("  Last name: " + r); answered = true;
        }
        // Email
        else if (hl.includes('email')) {
          r = await setInput('weberg619@gmail.com'); L("  Email: " + r); answered = true;
        }
        // Phone
        else if (hl.includes('phone') || hl.includes('mobile')) {
          r = await setInput('2085551234'); L("  Phone: " + r); answered = true;
        }
        // DOB
        else if (hl.includes('date of birth') || hl.includes('birthday')) {
          r = await setInput('18-03-1974'); L("  DOB: " + r); answered = true;
        }
        // ZIP
        else if (hl.includes('zip') || hl.includes('postal')) {
          r = await setInput('83864'); L("  ZIP: " + r); answered = true;
        }
        // Gender
        else if (hl.includes('gender')) {
          r = await clickRadio('Male'); L("  Gender: " + r); answered = true;
        }
        // Education
        else if (hl.includes('education') || hl.includes('degree')) {
          r = await clickRadio('Some college');
          if (r.includes('not found')) r = await clickRadio('College');
          if (r.includes('not found')) r = await clickRadio('Associate');
          L("  Education: " + r); answered = true;
        }
        // Income
        else if (hl.includes('income') || hl.includes('salary') || hl.includes('household')) {
          r = await clickRadio('$75');
          if (r.includes('not found')) r = await clickRadio('75,000');
          L("  Income: " + r); answered = true;
        }
        // Marital
        else if (hl.includes('marital') || hl.includes('married')) {
          r = await clickRadio('Single');
          L("  Marital: " + r); answered = true;
        }
        // Children
        else if (hl.includes('children') || hl.includes('kids')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('None');
          L("  Children: " + r); answered = true;
        }
        // Hispanic
        else if (hl.includes('hispanic') || hl.includes('latino')) {
          r = await clickRadio('Not Hispanic');
          if (r.includes('not found')) r = await clickRadio('No');
          L("  Hispanic: " + r); answered = true;
        }
        // Race
        else if (hl.includes('ethnic') || hl.includes('race')) {
          r = await clickRadio('White'); L("  Race: " + r); answered = true;
        }
        // Country
        else if (hl.includes('country')) {
          r = await clickRadio('United States'); L("  Country: " + r); answered = true;
        }
        // Language
        else if (hl.includes('language')) {
          r = await clickRadio('English'); L("  Language: " + r); answered = true;
        }
        // Employee count
        else if (hl.includes('employee')) {
          r = await eval_(`
            (function() {
              var radios = document.querySelectorAll('input[type="radio"]');
              for (var i = 0; i < radios.length; i++) {
                var label = (radios[i].labels?.[0]?.textContent || '').trim();
                if (label === '1') { radios[i].click(); if (radios[i].labels[0]) radios[i].labels[0].click(); return 'clicked: 1'; }
              }
              return 'not found';
            })()
          `);
          L("  Employees: " + r); answered = true;
        }
        // Industry
        else if (hl.includes('industry') || hl.includes('sector')) {
          r = await clickRadio('Architecture');
          if (r.includes('not found')) r = await clickRadio('Construction');
          L("  Industry: " + r); answered = true;
        }
        // Role
        else if (hl.includes('role') || hl.includes('job function') || hl.includes('position')) {
          r = await clickRadio('Design');
          if (r.includes('not found')) r = await clickRadio('Engineer');
          if (r.includes('not found')) r = await clickRadio('Other');
          L("  Role: " + r); answered = true;
        }
        // State
        else if (hl.includes('state') || hl.includes('region')) {
          r = await clickRadio('Idaho'); L("  State: " + r); answered = true;
        }

        // Generic fallback
        if (!answered) {
          // Check if there's a text input
          let hasInput = await eval_(`!!document.querySelector('input[type="text"], input[type="number"], input[type="tel"]')`);
          if (hasInput) {
            r = await setInput('N/A');
            L("  Generic input: " + r);
          } else {
            r = await eval_(`
              (function() {
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                  var mid = Math.floor(radios.length / 2);
                  radios[mid].click();
                  if (radios[mid].labels && radios[mid].labels[0]) radios[mid].labels[0].click();
                  var lbl = (radios[mid].labels?.[0]?.textContent || '').trim();
                  return 'radio[' + mid + '/' + radios.length + ']: ' + lbl.substring(0, 60);
                }
                return 'no elements';
              })()
            `);
            L("  Generic radio: " + r);
          }
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
