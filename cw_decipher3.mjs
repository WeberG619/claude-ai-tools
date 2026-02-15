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
  const tab = tabs.find(t => t.type === "page" && t.url.includes('decipherinc'));
  if (!tab) { L("No decipher tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    const cdpClick = async (x, y) => {
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(100);
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    // Decipher-specific helpers
    // Find radios with their proper labels (via label[for] or parent traversal)
    const getRadioOptions = async () => {
      return await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            var labelEl = document.querySelector('label[for="' + r.id + '"]');
            var labelText = labelEl ? labelEl.textContent.trim() : '';
            if (!labelText) {
              // Walk up to find text
              var el = r.parentElement;
              for (var d = 0; d < 5 && el; d++) {
                var t = el.textContent.trim();
                if (t.length > 3 && t.length < 200 && t !== 'radio') { labelText = t; break; }
                el = el.parentElement;
              }
            }
            results.push({ id: r.id, name: r.name, value: r.value, checked: r.checked, label: labelText.substring(0, 100) });
          });
          return JSON.stringify(results);
        })()
      `);
    };

    const getCheckboxOptions = async () => {
      return await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('input[type="checkbox"]').forEach(function(c) {
            var labelEl = document.querySelector('label[for="' + c.id + '"]');
            var labelText = labelEl ? labelEl.textContent.trim() : '';
            if (!labelText) {
              var el = c.parentElement;
              for (var d = 0; d < 5 && el; d++) {
                var t = el.textContent.trim();
                if (t.length > 3 && t.length < 200) { labelText = t; break; }
                el = el.parentElement;
              }
            }
            results.push({ id: c.id, name: c.name, value: c.value, checked: c.checked, label: labelText.substring(0, 100) });
          });
          return JSON.stringify(results);
        })()
      `);
    };

    // Click a radio/checkbox by clicking its label (for Decipher's fir-hidden radios)
    const clickOption = async (optId) => {
      return await eval_(`
        (function() {
          var label = document.querySelector('label[for="' + ${JSON.stringify(optId)} + '"]');
          if (label) { label.click(); return 'clicked label for ' + ${JSON.stringify(optId)}; }
          var el = document.getElementById(${JSON.stringify(optId)});
          if (el) { el.click(); return 'clicked element ' + ${JSON.stringify(optId)}; }
          return 'not found';
        })()
      `);
    };

    const clickSubmit = async () => {
      let btn = await eval_(`
        (function() {
          var sub = document.querySelector('input[type="submit"]');
          if (sub) {
            var r = sub.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: sub.value });
          }
          var btns = document.querySelectorAll('button, a.button, .btn');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t.includes('next') || t.includes('submit') || t.includes('continue')) {
              var r = btns[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: btns[i].textContent.trim() });
            }
          }
          return null;
        })()
      `);
      if (!btn) return 'no submit btn';
      let b = JSON.parse(btn);
      await cdpClick(b.x, b.y);
      return 'clicked ' + b.text;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      let lastPageHash = '';
      let stuckCount = 0;

      for (let round = 0; round < 50; round++) {
        let url, pageText;
        try {
          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 3000) : 'loading'`);
        } catch(e) {
          L("R" + round + ": Error - " + e.message);
          await sleep(3000);
          continue;
        }
        if (!pageText || pageText === 'loading') { await sleep(2000); continue; }

        let lower = pageText.toLowerCase();
        let pageHash = pageText.substring(0, 200);
        L("\n=== R" + round + " ===");

        // End states
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response has been recorded') || lower.includes('completed the survey')) {
          L("SURVEY COMPLETE!"); L(pageText.substring(0, 500)); break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('no longer available')) {
          L("SCREENED OUT"); L(pageText.substring(0, 300)); break;
        }
        if (!url.includes('decipherinc') && !url.includes('nrg.')) {
          L("REDIRECTED: " + url.substring(0, 80));
          break;
        }

        // Stuck detection
        if (pageHash === lastPageHash) {
          stuckCount++;
          if (stuckCount >= 5) { L("STUCK!"); L(pageText.substring(0, 500)); break; }
        } else { stuckCount = 0; }
        lastPageHash = pageHash;

        // Question text
        let qLines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = qLines.find(l => l.includes('?') && l.length > 10)
          || qLines.find(l => l.length > 15 && l.length < 300 && !['Next', 'Submit', 'Continue', 'Continue »', 'Back', '«'].includes(l) && !l.startsWith('Please select'))
          || '';
        L("Q: " + question.substring(0, 120));

        // Get options
        let radioStr = await getRadioOptions();
        let radios = JSON.parse(radioStr);
        let cbStr = await getCheckboxOptions();
        let cbs = JSON.parse(cbStr);

        // Text inputs
        let textInputs = await eval_(`
          (function() {
            var r = [];
            document.querySelectorAll('input[type="text"], textarea, input:not([type])').forEach(function(el) {
              if (el.offsetParent !== null && el.type !== 'hidden' && !el.classList.contains('fir-hidden')) {
                r.push({ id: el.id, name: el.name });
              }
            });
            return JSON.stringify(r);
          })()
        `);
        let txts = JSON.parse(textInputs);

        // Selects
        let selectStr = await eval_(`
          (function() {
            var r = [];
            document.querySelectorAll('select').forEach(function(s) {
              if (s.offsetParent !== null) {
                var opts = [];
                s.querySelectorAll('option').forEach(function(o) { opts.push({ v: o.value, t: o.textContent.trim().substring(0, 50) }); });
                r.push({ id: s.id, name: s.name, options: opts });
              }
            });
            return JSON.stringify(r);
          })()
        `);
        let selects = JSON.parse(selectStr);

        L("   radio=" + radios.length + " cb=" + cbs.length + " txt=" + txts.length + " sel=" + selects.length);
        if (radios.length > 0 && radios.length <= 6) L("   Options: " + radios.map(r => r.label.substring(0, 40)).join(' | '));

        let qLower = question.toLowerCase() + ' ' + lower;

        // Answer logic
        if (radios.length > 0) {
          let targetId = null;

          // Privacy/consent
          if (lower.includes('privacy') && lower.includes('agree')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('agree') && !r.label.toLowerCase().includes('do not') && !r.label.toLowerCase().includes('disagree')) {
                targetId = r.id; break;
              }
            }
          }
          // Gender
          else if (qLower.includes('gender') || qLower.includes('sex')) {
            for (let r of radios) { if (r.label.includes('Male') || r.label.includes('Man')) { targetId = r.id; break; } }
          }
          // Age
          else if (qLower.includes('age') || qLower.includes('how old') || qLower.includes('year of birth') || qLower.includes('born')) {
            for (let r of radios) {
              if (r.label.includes('50') || r.label.includes('51') || r.label.includes('45-54') || r.label.includes('50-54') || r.label.includes('1974')) {
                targetId = r.id; break;
              }
            }
          }
          // Hispanic
          else if (qLower.includes('hispanic') || qLower.includes('latino')) {
            for (let r of radios) { if (r.label === 'No' || r.label.startsWith('No,') || r.label.includes('Not Hispanic')) { targetId = r.id; break; } }
          }
          // Race
          else if (qLower.includes('race') || qLower.includes('ethnic')) {
            for (let r of radios) { if (r.label.includes('White') || r.label.includes('Caucasian')) { targetId = r.id; break; } }
          }
          // Income
          else if (qLower.includes('income') || qLower.includes('salary') || qLower.includes('earn') || qLower.includes('household income')) {
            for (let r of radios) {
              if (r.label.includes('75,0') || r.label.includes('$75') || r.label.includes('70,0') || r.label.includes('60,0')) {
                targetId = r.id; break;
              }
            }
          }
          // Education
          else if (qLower.includes('education') || qLower.includes('degree') || qLower.includes('school')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('some college') || r.label.toLowerCase().includes('associate') || r.label.toLowerCase().includes('technical')) {
                targetId = r.id; break;
              }
            }
          }
          // Employment
          else if (qLower.includes('employ') || qLower.includes('occupation') || qLower.includes('work status')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('self-employ') || r.label.toLowerCase().includes('self employ') || r.label.toLowerCase().includes('full-time') || r.label.toLowerCase().includes('full time')) {
                targetId = r.id; break;
              }
            }
          }
          // Marital
          else if (qLower.includes('marital') || qLower.includes('married') || qLower.includes('relationship status')) {
            for (let r of radios) { if (r.label.includes('Married')) { targetId = r.id; break; } }
          }
          // Children
          else if (qLower.includes('children') || qLower.includes('kids') || qLower.includes('child')) {
            for (let r of radios) {
              if (r.label.includes('No') || r.label.includes('None') || r.label === '0') { targetId = r.id; break; }
            }
          }
          // Yes/No - default Yes
          else if (radios.length === 2 && radios.some(r => r.label === 'Yes') && radios.some(r => r.label === 'No')) {
            for (let r of radios) { if (r.label === 'Yes') { targetId = r.id; break; } }
          }
          // Agree/disagree scale
          else if (qLower.includes('agree') || qLower.includes('disagree')) {
            for (let r of radios) {
              if (r.label.includes('Agree') && !r.label.includes('Disagree') && !r.label.includes('Strongly')) {
                targetId = r.id; break;
              }
            }
          }
          // Likely scale
          else if (qLower.includes('likely') || qLower.includes('likelihood')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('somewhat likely') || r.label.toLowerCase().includes('likely')) {
                targetId = r.id; break;
              }
            }
          }
          // Satisfaction
          else if (qLower.includes('satisf')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('satisfied') && !r.label.toLowerCase().includes('dissatisfied') && !r.label.toLowerCase().includes('very')) {
                targetId = r.id; break;
              }
            }
          }
          // Frequency
          else if (qLower.includes('often') || qLower.includes('frequent') || qLower.includes('how many times')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('sometimes') || r.label.toLowerCase().includes('occasionally') || r.label.includes('2-3')) {
                targetId = r.id; break;
              }
            }
          }
          // Important
          else if (qLower.includes('important')) {
            for (let r of radios) {
              if (r.label.toLowerCase().includes('somewhat important') || r.label.toLowerCase().includes('important')) {
                targetId = r.id; break;
              }
            }
          }

          // Fallback: pick first or middle option
          if (!targetId && radios.length > 0) {
            let idx = Math.min(1, radios.length - 1); // second option usually safer than first
            targetId = radios[idx].id;
            L("   [fallback -> " + radios[idx].label.substring(0, 40) + "]");
          }

          if (targetId) {
            let r = await clickOption(targetId);
            L("   " + r);
          }
        }
        else if (cbs.length > 0) {
          // Check first unchecked option
          for (let cb of cbs) {
            if (!cb.checked) {
              let r = await clickOption(cb.id);
              L("   cb: " + r + " - " + cb.label.substring(0, 40));
              break;
            }
          }
        }
        else if (selects.length > 0) {
          for (let sel of selects) {
            let idx = Math.min(2, sel.options.length - 1);
            await eval_(`
              (function() {
                var s = document.getElementById('${sel.id}') || document.querySelector('[name="${sel.name}"]');
                if (s) { s.selectedIndex = ${idx}; s.dispatchEvent(new Event('change', { bubbles: true })); }
              })()
            `);
            L("   selected: " + (sel.options[idx] ? sel.options[idx].t : 'idx ' + idx));
          }
        }
        else if (txts.length > 0) {
          for (let t of txts) {
            let val = "I think investing in community infrastructure and supporting local businesses are the most important priorities.";
            await eval_(`
              (function() {
                var el = document.getElementById('${t.id}') || document.querySelector('[name="${t.name}"]');
                if (el) {
                  var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                  setter.call(el, ${JSON.stringify(val)});
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                }
              })()
            `);
            L("   text: " + val.substring(0, 40));
          }
        }
        else {
          L("   No inputs. Page: " + pageText.substring(0, 200));
        }

        await sleep(500);
        let submitResult = await clickSubmit();
        L("   " + submitResult);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      try {
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
        L("URL: " + fUrl.substring(0, 100));
        L("Page:\n" + fPage.substring(0, 1000));
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
