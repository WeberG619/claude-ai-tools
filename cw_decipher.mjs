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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('decipherinc'));
  if (!surveyTab) {
    // Fall back to PureSpectrum tab
    const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
    if (!psTab) { L("No survey tab. Tabs: " + tabs.filter(t=>t.type==='page').map(t=>t.url.substring(0,40)).join(', ')); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
  }
  const tab = tabs.find(t => t.type === "page" && (t.url.includes('decipherinc') || t.url.includes('purespectrum')));

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
        let pageHash = pageText.substring(0, 100);
        L("\n=== R" + round + " ===");

        // End states
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response has been recorded') || lower.includes('completed the survey')) {
          L("SURVEY COMPLETE!");
          L(pageText.substring(0, 500));
          break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('no longer available')) {
          L("SCREENED OUT");
          L(pageText.substring(0, 300));
          break;
        }

        // Stuck detection
        if (pageHash === lastPageHash) {
          stuckCount++;
          if (stuckCount >= 5) { L("STUCK!"); L(pageText.substring(0, 500)); break; }
        } else { stuckCount = 0; }
        lastPageHash = pageHash;

        // Analyze the page structure
        let analysis = await eval_(`
          (function() {
            var r = {};
            // Find all radios
            r.radios = [];
            document.querySelectorAll('input[type="radio"]').forEach(function(el) {
              var label = el.parentElement ? el.parentElement.textContent.trim().substring(0, 80) : '';
              r.radios.push({ id: el.id, name: el.name, value: el.value, label: label, checked: el.checked });
            });
            // Find all checkboxes
            r.checkboxes = [];
            document.querySelectorAll('input[type="checkbox"]').forEach(function(el) {
              var label = el.parentElement ? el.parentElement.textContent.trim().substring(0, 80) : '';
              r.checkboxes.push({ id: el.id, name: el.name, value: el.value, label: label, checked: el.checked });
            });
            // Find text inputs
            r.textInputs = [];
            document.querySelectorAll('input[type="text"], textarea, input:not([type])').forEach(function(el) {
              if (el.offsetParent !== null && el.type !== 'hidden') {
                r.textInputs.push({ id: el.id, name: el.name, placeholder: (el.placeholder || '').substring(0, 30) });
              }
            });
            // Find buttons/links that could be submit
            r.buttons = [];
            document.querySelectorAll('button, input[type="submit"], a.button, .button, [class*="submit"], [class*="next"], [class*="continue"]').forEach(function(el) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 20) {
                r.buttons.push({ tag: el.tagName, text: el.textContent.trim().substring(0, 30), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            });
            // Check for select dropdowns
            r.selects = [];
            document.querySelectorAll('select').forEach(function(el) {
              if (el.offsetParent !== null) {
                var opts = [];
                el.querySelectorAll('option').forEach(function(o) { opts.push(o.textContent.trim().substring(0, 40)); });
                r.selects.push({ id: el.id, name: el.name, options: opts.slice(0, 10) });
              }
            });
            return JSON.stringify(r);
          })()
        `);
        let info = JSON.parse(analysis);
        let qLines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = qLines.find(l => l.includes('?') && l.length > 10)
          || qLines.find(l => l.includes(':') && l.length > 10 && !l.includes('http'))
          || qLines.find(l => l.length > 15 && l.length < 200 && !['Next', 'Submit', 'Continue', 'Back', 'Agree'].includes(l))
          || '';
        let qLower = question.toLowerCase();

        L("Q: " + question.substring(0, 120));
        L("   radios=" + info.radios.length + " cb=" + info.checkboxes.length + " txt=" + info.textInputs.length + " sel=" + info.selects.length + " btn=" + info.buttons.length);

        // Handle privacy policy / consent
        if (lower.includes('privacy policy') && lower.includes('agree')) {
          L("Privacy policy - agreeing...");
          // Find "I have read and agree" option
          let agreed = false;
          for (let r of info.radios) {
            if (r.label.toLowerCase().includes('agree') && !r.label.toLowerCase().includes('do not')) {
              await eval_(`document.getElementById('${r.id}').click()`);
              L("   Clicked: " + r.label.substring(0, 60));
              agreed = true;
              break;
            }
          }
          if (!agreed) {
            for (let cb of info.checkboxes) {
              if (cb.label.toLowerCase().includes('agree') && !cb.label.toLowerCase().includes('do not')) {
                await eval_(`document.getElementById('${cb.id}').click()`);
                L("   Checked: " + cb.label.substring(0, 60));
                agreed = true;
                break;
              }
            }
          }
          if (!agreed) {
            // Try clicking label text
            await eval_(`
              (function() {
                var all = document.querySelectorAll('label, span, div, a');
                for (var i = 0; i < all.length; i++) {
                  var t = all[i].textContent.trim().toLowerCase();
                  if (t.includes('agree') && !t.includes('do not') && t.length < 100) {
                    all[i].click();
                    return 'clicked: ' + all[i].textContent.trim().substring(0, 50);
                  }
                }
                return 'not found';
              })()
            `);
          }
          await sleep(500);
        }
        // Handle demographic/survey questions
        else if (info.radios.length > 0) {
          // Single choice question
          let target = null;

          // Smart matching based on question content
          if (qLower.includes('gender') || lower.includes('gender')) target = 'Male';
          else if (qLower.includes('age') || qLower.includes('old are you')) {
            // Find 45-54 or 50-54 range
            for (let r of info.radios) {
              if (r.label.includes('50') || r.label.includes('51') || r.label.includes('45-54') || r.label.includes('50-54')) { target = r.label; break; }
            }
          }
          else if (qLower.includes('hispanic') || qLower.includes('latino')) target = 'No';
          else if (qLower.includes('race') || qLower.includes('ethnicity')) target = 'White';
          else if (qLower.includes('income') || qLower.includes('salary') || qLower.includes('earn')) {
            for (let r of info.radios) {
              if (r.label.includes('75') || r.label.includes('70') || r.label.includes('60,000') || r.label.includes('80,000')) { target = r.label; break; }
            }
          }
          else if (qLower.includes('education') || qLower.includes('degree')) {
            for (let r of info.radios) {
              if (r.label.toLowerCase().includes('some college') || r.label.toLowerCase().includes('associate')) { target = r.label; break; }
            }
          }
          else if (qLower.includes('employ') || qLower.includes('work')) {
            for (let r of info.radios) {
              if (r.label.toLowerCase().includes('self') || r.label.toLowerCase().includes('full-time') || r.label.toLowerCase().includes('full time')) { target = r.label; break; }
            }
          }
          else if (qLower.includes('marital') || qLower.includes('married') || qLower.includes('relationship')) target = 'Married';
          else if (qLower.includes('child') || qLower.includes('kids')) target = 'No';
          else if (qLower.includes('home') && qLower.includes('own')) target = 'Own';
          else if (qLower.includes('agree') || qLower.includes('satisfaction')) target = 'Agree';
          else if (qLower.includes('likely')) target = 'Somewhat likely';
          else if (qLower.includes('often') || qLower.includes('frequent')) target = 'Sometimes';
          else if (qLower.includes('important')) target = 'Very important';

          if (target) {
            L("-> " + target.substring(0, 50));
            let clicked = false;
            for (let r of info.radios) {
              if (r.label.includes(target) || r.label.toLowerCase().includes(target.toLowerCase())) {
                await eval_(`document.getElementById('${r.id}').click()`);
                clicked = true;
                L("   Clicked radio: " + r.label.substring(0, 50));
                break;
              }
            }
            if (!clicked) {
              // Try partial match
              for (let r of info.radios) {
                if (r.label.toLowerCase().includes(target.toLowerCase().substring(0, 6))) {
                  await eval_(`document.getElementById('${r.id}').click()`);
                  L("   Partial match: " + r.label.substring(0, 50));
                  break;
                }
              }
            }
          } else {
            // Default: pick first radio
            if (info.radios.length > 0) {
              await eval_(`document.getElementById('${info.radios[0].id}').click()`);
              L("-> first radio: " + info.radios[0].label.substring(0, 50));
            }
          }
        }
        else if (info.checkboxes.length > 0) {
          // Multi-select - pick first relevant option
          if (info.checkboxes.length > 0 && !info.checkboxes[0].checked) {
            await eval_(`document.getElementById('${info.checkboxes[0].id}').click()`);
            L("-> first cb: " + info.checkboxes[0].label.substring(0, 50));
          }
        }
        else if (info.selects.length > 0) {
          // Dropdown
          for (let sel of info.selects) {
            // Pick a middle option (not first which is usually "Select...")
            let idx = Math.min(2, sel.options.length - 1);
            await eval_(`
              (function() {
                var sel = document.querySelector('select[name="${sel.name}"]') || document.getElementById('${sel.id}');
                if (sel) { sel.selectedIndex = ${idx}; sel.dispatchEvent(new Event('change', { bubbles: true })); return 'selected ' + sel.options[sel.selectedIndex].text; }
                return 'no select';
              })()
            `);
            L("-> select: " + sel.options[idx]);
          }
        }
        else if (info.textInputs.length > 0) {
          // Text inputs
          for (let inp of info.textInputs) {
            let value = "I think it's important to consider all perspectives carefully.";
            if (qLower.includes('zip') || lower.includes('zip')) value = "83864";
            else if (qLower.includes('age') || qLower.includes('old')) value = "51";
            else if (qLower.includes('name')) value = "Weber";
            await eval_(`
              (function() {
                var el = document.getElementById('${inp.id}') || document.querySelector('[name="${inp.name}"]');
                if (el) {
                  var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                  setter.call(el, ${JSON.stringify(value)});
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                  return 'typed';
                }
                return 'no el';
              })()
            `);
            L("-> text: " + value.substring(0, 40));
          }
        }
        else {
          L("   No interactive elements found");
          L("   Page: " + pageText.substring(0, 300));
        }

        await sleep(500);

        // Click Next/Submit/Continue
        let nextClicked = false;
        // Try submit button first
        let submitBtn = await eval_(`
          (function() {
            // Check for input[type=submit]
            var sub = document.querySelector('input[type="submit"]');
            if (sub) {
              var r = sub.getBoundingClientRect();
              if (r.width > 20) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: sub.value || 'Submit' });
            }
            // Check for button
            var btns = document.querySelectorAll('button, a.button, .btn, [class*="next"], [class*="submit"], [class*="continue"]');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t === 'next' || t === 'submit' || t === 'continue' || t === 'agree' || t.includes('next')) {
                var r = btns[i].getBoundingClientRect();
                if (r.width > 20) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: btns[i].textContent.trim().substring(0, 20) });
              }
            }
            return null;
          })()
        `);

        if (submitBtn) {
          let btn = JSON.parse(submitBtn);
          await cdpClick(btn.x, btn.y);
          L("   Clicked: " + btn.text);
          nextClicked = true;
        } else {
          // Try form submit
          let formResult = await eval_(`
            (function() {
              var form = document.querySelector('form');
              if (form) { form.submit(); return 'submitted form'; }
              return null;
            })()
          `);
          if (formResult) {
            L("   " + formResult);
            nextClicked = true;
          } else {
            L("   No submit button found");
          }
        }

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
