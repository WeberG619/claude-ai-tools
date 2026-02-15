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

    // Get JUST the question heading (not radio labels)
    const getQuestionHeading = async () => {
      return await eval_(`
        (function() {
          // Try to find a heading element
          var headings = document.querySelectorAll('h1, h2, h3, h4, h5, p, [class*="question"], [class*="title"]');
          for (var i = 0; i < headings.length; i++) {
            var t = headings[i].textContent.trim();
            if (t.length > 10 && t.length < 200 && t.includes('?')) {
              return t;
            }
          }
          // Fallback: first significant text block
          var all = document.body.innerText.split('\\n');
          for (var i = 0; i < all.length; i++) {
            var line = all[i].trim();
            if (line.length > 10 && line.includes('?') && !line.includes('earn Dollars')) {
              return line;
            }
          }
          return document.body.innerText.substring(0, 200);
        })()
      `);
    };

    (async () => {
      // Fix industry question first
      L("=== FIXING INDUSTRY ===");
      let r = await clickRadio('Architecture');
      L("Architecture: " + r);
      await sleep(500);
      r = await clickContinue();
      L("Continue: " + r);
      await sleep(3000);

      // Loop through remaining questions using question heading detection
      let lastQ = '';
      let stuckCount = 0;

      for (let step = 0; step < 15; step++) {
        let heading = await getQuestionHeading();
        let ql = heading.toLowerCase();

        L("\n=== Q" + step + " ===");
        L("Heading: " + heading.substring(0, 200));

        // Get radio options for context
        let radioLabels = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            return Array.from(radios).map(function(r) {
              var l = (r.labels?.[0]?.textContent || '').trim();
              if (!l) { var p = r.closest('label') || r.parentElement; if (p) l = p.textContent.trim(); }
              return l.substring(0, 40);
            }).join(', ');
          })()
        `);
        L("Options: " + radioLabels.substring(0, 200));

        // Check for input fields
        let hasInput = await eval_(`!!document.querySelector('input[type="text"], input[type="number"], input[type="tel"]')`);

        // Stuck detection
        if (heading.substring(0, 80) === lastQ) {
          stuckCount++;
          if (stuckCount >= 2) { L("STUCK"); break; }
        } else { stuckCount = 0; }
        lastQ = heading.substring(0, 80);

        // Completion check - check full page text
        let fullText = await eval_(`document.body.innerText.substring(0, 500)`);
        if (fullText.includes('0 Questions left') || fullText.includes('profile') && fullText.includes('complete')) {
          L("DONE!"); break;
        }

        let answered = false;

        // Handlers based on question heading only (not radio options)
        if (ql.includes('industry') || ql.includes('work in')) {
          r = await clickRadio('Architecture');
          if (r.includes('not found')) r = await clickRadio('Construction');
          L("  Industry: " + r); answered = true;
        }
        else if (ql.includes('date of birth') || ql.includes('birthday')) {
          r = await setInput('18-03-1974'); L("  DOB: " + r); answered = true;
        }
        else if (ql.includes('zip') || ql.includes('postal')) {
          r = await setInput('83864'); L("  ZIP: " + r); answered = true;
        }
        else if (ql.includes('gender')) {
          r = await clickRadio('Male'); L("  Gender: " + r); answered = true;
        }
        else if (ql.includes('hispanic') || ql.includes('latino')) {
          r = await clickRadio('Not Hispanic');
          if (r.includes('not found')) r = await clickRadio('No');
          L("  Hispanic: " + r); answered = true;
        }
        else if (ql.includes('ethnic') || ql.includes('race')) {
          r = await clickRadio('White'); L("  Race: " + r); answered = true;
        }
        else if (ql.includes('education') || ql.includes('degree') || ql.includes('highest level')) {
          r = await clickRadio('Some college');
          if (r.includes('not found')) r = await clickRadio('College');
          if (r.includes('not found')) r = await clickRadio('Associate');
          if (r.includes('not found')) r = await clickRadio('High school');
          L("  Education: " + r); answered = true;
        }
        else if (ql.includes('employ') || ql.includes('work status')) {
          r = await clickRadio('Self-employed');
          if (r.includes('not found')) r = await clickRadio('Employed');
          L("  Employment: " + r); answered = true;
        }
        else if (ql.includes('income') || ql.includes('salary') || ql.includes('household')) {
          r = await clickRadio('$75');
          if (r.includes('not found')) r = await clickRadio('75,000');
          if (r.includes('not found')) r = await clickRadio('$50');
          L("  Income: " + r); answered = true;
        }
        else if (ql.includes('marital') || ql.includes('married')) {
          r = await clickRadio('Single');
          if (r.includes('not found')) r = await clickRadio('Never');
          L("  Marital: " + r); answered = true;
        }
        else if (ql.includes('children') || ql.includes('kids')) {
          r = await clickRadio('No');
          if (r.includes('not found')) r = await clickRadio('None');
          if (r.includes('not found')) r = await clickRadio('0');
          L("  Children: " + r); answered = true;
        }
        else if (ql.includes('country')) {
          r = await clickRadio('United States');
          L("  Country: " + r); answered = true;
        }
        else if (ql.includes('language')) {
          r = await clickRadio('English');
          L("  Language: " + r); answered = true;
        }
        else if (ql.includes('state') || ql.includes('region')) {
          r = await eval_(`
            (function() {
              var sels = document.querySelectorAll('select');
              for (var j = 0; j < sels.length; j++) {
                var sel = sels[j];
                if (!sel.offsetParent) continue;
                for (var i = 0; i < sel.options.length; i++) {
                  if (sel.options[i].text.includes('Idaho')) {
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'selected Idaho';
                  }
                }
              }
              return 'no select';
            })()
          `);
          if (r.includes('no select')) r = await clickRadio('Idaho');
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

      // Final state
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
