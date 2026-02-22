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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    // Type text character by character using CDP Input.dispatchKeyEvent
    const typeText = async (text) => {
      for (const char of text) {
        await send("Input.dispatchKeyEvent", { type: "keyDown", text: char });
        await send("Input.dispatchKeyEvent", { type: "keyUp", text: char });
        await sleep(30);
      }
    };

    // Answer a question based on text
    const answerQ = async (q) => {
      const ql = q.toLowerCase();

      // GENDER - very broad matching
      if (ql.includes('gender') || (ql.includes("i'm a") && (ql.includes('male') || ql.includes('female'))) ||
          (ql.includes('are you') && ql.includes('male')) || ql.includes('what is your sex')) {
        return await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            for (var i = 0; i < radios.length; i++) {
              var label = (radios[i].labels?.[0]?.textContent || '').trim();
              if (label === 'Male' || label === 'Man' || radios[i].value === 'Male' || radios[i].value === '1') {
                radios[i].click(); return 'radio: Male';
              }
            }
            var all = document.querySelectorAll('label, li, div, span');
            for (var i = 0; i < all.length; i++) {
              if (all[i].textContent.trim() === 'Male') { all[i].click(); return 'clicked: Male'; }
            }
            return 'Male not found';
          })()
        `);
      }

      // BIRTH / AGE - handle selects for month/year
      if (ql.includes('born in') || ql.includes('birth') || ql.includes('year') && ql.includes('month')) {
        return await eval_(`
          (function() {
            var sels = document.querySelectorAll('select');
            var result = [];
            for (var i = 0; i < sels.length; i++) {
              var opts = Array.from(sels[i].options).map(o => o.text.toLowerCase());
              // Month select
              if (opts.some(o => o.includes('january') || o.includes('jan') || o === 'march')) {
                for (var j = 0; j < sels[i].options.length; j++) {
                  if (sels[i].options[j].text.toLowerCase().includes('march') || sels[i].options[j].text === '3' || sels[i].options[j].value === '3' || sels[i].options[j].value === 'March') {
                    sels[i].selectedIndex = j;
                    sels[i].dispatchEvent(new Event('change', { bubbles: true }));
                    result.push('month=March');
                    break;
                  }
                }
              }
              // Year select
              else if (opts.some(o => /^\\d{4}$/.test(o.trim()))) {
                for (var j = 0; j < sels[i].options.length; j++) {
                  if (sels[i].options[j].text.trim() === '1974' || sels[i].options[j].value === '1974') {
                    sels[i].selectedIndex = j;
                    sels[i].dispatchEvent(new Event('change', { bubbles: true }));
                    result.push('year=1974');
                    break;
                  }
                }
              }
            }
            return result.length > 0 ? result.join(', ') : 'no DOB selects found';
          })()
        `);
      }

      if (ql.includes('what is your age') || ql.includes('how old')) {
        return await eval_(`
          (function() {
            var inp = document.querySelector('input[type="text"], input[type="number"], input[name="selected_opt"]');
            if (inp) {
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '51');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'entered 51';
            }
            return 'no age input';
          })()
        `);
      }

      // ZIP
      if (ql.includes('zip') || ql.includes('postal code')) {
        return await eval_(`
          (function() {
            var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"]');
            if (inp) {
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '83864');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'entered 83864';
            }
            return 'no zip input';
          })()
        `);
      }

      // Hispanic
      if (ql.includes('hispanic') || ql.includes('latino') || ql.includes('spanish origin')) {
        return await eval_(`
          (function() {
            var all = document.querySelectorAll('label, li, div, span, input[type="radio"]');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.includes('not of Hispanic') || t.includes('No, not') || (t === 'No' && !t.includes('origin'))) {
                all[i].click(); return 'clicked: ' + t.substring(0, 60);
              }
            }
            return 'no Hispanic answer';
          })()
        `);
      }

      // Race/ethnicity
      if (ql.includes('ethnic') || ql.includes('race') || ql.includes('racial')) {
        return await eval_(`
          (function() {
            var all = document.querySelectorAll('label, li, div, span, input[type="radio"]');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t === 'White' || t === 'Caucasian' || t.includes('White')) {
                all[i].click(); return 'clicked: ' + t;
              }
            }
            return 'no race option';
          })()
        `);
      }

      // Open text questions (describe, explain, tell us)
      if (ql.includes('describe') || ql.includes('explain') || ql.includes('tell us') || ql.includes('in your own words') || ql.includes('two sentences') || ql.includes('open-ended')) {
        // Generate a reasonable answer based on the question
        let answer = '';
        if (ql.includes('outdoor') || ql.includes('activity')) {
          answer = 'I enjoy hiking in the mountains near my home in Idaho. The trails offer beautiful views and great exercise.';
        } else if (ql.includes('product') || ql.includes('brand')) {
          answer = 'I appreciate products that are well designed and reliable. Quality and functionality matter most to me.';
        } else if (ql.includes('experience') || ql.includes('service')) {
          answer = 'I value good customer service and straightforward communication. A positive experience makes me a repeat customer.';
        } else if (ql.includes('opinion') || ql.includes('think')) {
          answer = 'I try to form balanced opinions based on available information. I think it is important to consider different perspectives.';
        } else {
          answer = 'I appreciate quality and value in everyday choices. Good design and reliability are important to me.';
        }
        // Find textarea or text input
        return await eval_(`
          (function() {
            var ta = document.querySelector('textarea');
            if (ta) {
              ta.focus();
              ta.value = '${answer}';
              ta.dispatchEvent(new Event('input', { bubbles: true }));
              ta.dispatchEvent(new Event('change', { bubbles: true }));
              return 'textarea: ' + '${answer}'.substring(0, 40);
            }
            var inp = document.querySelector('input[type="text"]');
            if (inp) {
              inp.focus();
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '${answer}');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'input: ' + '${answer}'.substring(0, 40);
            }
            return 'no text field';
          })()
        `);
      }

      return null; // No specific handler matched
    };

    (async () => {
      // 1. Accept cookies
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Accept All') {
              btns[i].click();
              return 'accepted cookies';
            }
          }
          return 'no cookie button';
        })()
      `);
      L("Cookies: " + r);
      await sleep(1000);

      // Loop through questions
      let lastQ = '';
      let stuckCount = 0;

      for (let step = 0; step < 50; step++) {
        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        // Remove cookie banner text
        pageText = pageText.replace(/We value your privacy[\s\S]*?Accept All/g, '').trim();
        let q = pageText.replace(/\n/g, ' ').trim();

        L("\n=== Q" + step + " ===");
        L("Q: " + q.substring(0, 250));

        // Stuck detection
        let qShort = q.substring(0, 120);
        if (qShort === lastQ) {
          stuckCount++;
          if (stuckCount >= 2) { L("STUCK"); break; }
        } else { stuckCount = 0; }
        lastQ = qShort;

        let ql = q.toLowerCase();

        // Completion
        if (ql.includes('thank you') && (ql.includes('complet') || ql.includes('done') || ql.includes('finished'))) {
          L("COMPLETE!"); break;
        }
        if (ql.includes('screened out') || ql.includes('not qualify') || ql.includes('sorry') || ql.includes('unfortunately') || ql.includes('not eligible')) {
          L("SCREENED OUT"); break;
        }
        if (ql.includes('redirecting') || q.length < 20) {
          L("Waiting..."); await sleep(5000); continue;
        }

        // Try profile-based answer
        let result = await answerQ(q);
        if (result) {
          L("  Answer: " + result);
        } else {
          // GENERIC survey question handler
          // Check for radio buttons, checkboxes, selects, textareas, text inputs
          r = await eval_(`
            (function() {
              // Priority 1: Radio buttons - click first non-extreme option (skip Strongly Agree/Disagree)
              var radios = document.querySelectorAll('input[type="radio"]:not(:checked)');
              if (radios.length > 0) {
                // For gender-like questions, always pick first (Male)
                var labels = Array.from(radios).map(r => (r.labels?.[0]?.textContent||r.value||'').trim().toLowerCase());
                if (labels.includes('male') || labels.includes('man')) {
                  for (var i = 0; i < radios.length; i++) {
                    var l = (radios[i].labels?.[0]?.textContent||radios[i].value||'').trim().toLowerCase();
                    if (l === 'male' || l === 'man') { radios[i].click(); return 'gender: Male'; }
                  }
                }
                // Group radios by name
                var groups = {};
                radios.forEach(function(r) { if (!groups[r.name]) groups[r.name] = []; groups[r.name].push(r); });
                for (var name in groups) {
                  var group = groups[name];
                  // Pick middle option (slightly agree / neutral)
                  var mid = Math.floor(group.length / 2);
                  group[mid].click();
                  return 'radio[' + mid + '/' + group.length + ']: ' + (group[mid].labels?.[0]?.textContent||group[mid].value||'').trim().substring(0, 60);
                }
              }
              // Priority 2: Checkbox (pick first)
              var checks = document.querySelectorAll('input[type="checkbox"]:not(:checked)');
              if (checks.length > 0 && checks.length < 20) {
                checks[0].click();
                return 'checkbox: ' + (checks[0].labels?.[0]?.textContent||checks[0].value||'').trim().substring(0, 60);
              }
              // Priority 3: Select dropdown (pick middle)
              var sels = document.querySelectorAll('select');
              for (var i = 0; i < sels.length; i++) {
                if (sels[i].offsetParent && sels[i].options.length > 2) {
                  var mid = Math.min(Math.floor(sels[i].options.length / 2), sels[i].options.length - 1);
                  sels[i].selectedIndex = mid;
                  sels[i].dispatchEvent(new Event('change', { bubbles: true }));
                  return 'select[' + mid + ']: ' + sels[i].options[mid].text;
                }
              }
              // Priority 4: Textarea
              var ta = document.querySelector('textarea');
              if (ta && !ta.value) {
                ta.value = 'I think this is an interesting topic and I have moderate opinions about it.';
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                return 'textarea filled';
              }
              // Priority 5: Text input
              var inp = document.querySelector('input[type="text"]:not([readonly])');
              if (inp && !inp.value) {
                var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                ns.call(inp, 'moderate');
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                return 'input: moderate';
              }
              return 'NO_INTERACTIVE_ELEMENTS';
            })()
          `);
          L("  Generic: " + r);
        }

        // Click Next
        await sleep(500);
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, input[type="submit"]');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t === 'next' || t === 'continue' || t === 'submit' || t.includes('next')) {
                btns[i].click(); return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            return 'no next';
          })()
        `);
        L("  Next: " + r);
        await sleep(3000);
      }

      // Final
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\n=== FINAL ===");
      L("URL: " + url.substring(0, 150));
      L("Page: " + pageText.substring(0, 800));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_81.png', Buffer.from(ss.data, 'base64'));
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
