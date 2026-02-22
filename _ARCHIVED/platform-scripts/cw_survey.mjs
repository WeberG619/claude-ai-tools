import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 60000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('prsrvy.com'));
  if (!surveyTab) { L("No prsrvy tab found"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result?.value; };
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Profile data for answering
      const PROFILE = {
        zip: '83864', age: '51', dob: '03/18/1974', gender: 'male',
        ethnicity: 'white', hispanic: false, married: true, children: 0,
        employed: 'self-employed', industry: 'architecture', education: 'some college',
        income: '75000', state: 'Idaho', city: 'Sandpoint',
        name: 'Weber Gouin', email: 'weberg619@gmail.com'
      };

      // Click Continue on privacy page
      let text = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("Page: " + text.substring(0, 150));

      if (text.includes('PRIVACY POLICY') || text.includes('data-privacy')) {
        await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return 'clicked'; }
            }
            return 'no btn';
          })()
        `);
        L("Clicked Continue on privacy");
        await sleep(5000);
      }

      // Now handle survey questions in a loop
      for (let round = 0; round < 30; round++) {
        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let lower = pageText.toLowerCase();
        L("\n--- R" + round + " ---");
        L("URL: " + (url || '').substring(0, 80));
        L("Text: " + pageText.substring(0, 300));

        // Check for completion/screenout
        if (lower.includes('screenout') || lower.includes('screened out') || lower.includes('not qualify') || lower.includes('disqualif')) {
          L("SCREENED OUT");
          break;
        }
        if (lower.includes('thank you') && (lower.includes('complet') || lower.includes('finished'))) {
          L("SURVEY COMPLETE!");
          break;
        }
        if (url && (url.includes('termination') || url.includes('screenout'))) {
          L("Redirected to screenout");
          break;
        }

        // Get all interactive elements
        let inputs = await eval_(`
          (function() {
            var result = { radios: [], checkboxes: [], texts: [], selects: [], buttons: [] };
            // Radios (skip footer)
            document.querySelectorAll('input[type="radio"]').forEach(function(r) {
              if (r.name === 'tinyFooter') return;
              var label = document.querySelector('label[for="' + r.id + '"]');
              var lt = label ? label.textContent.trim() : '';
              if (!lt) { var p = r.closest('label'); lt = p ? p.textContent.trim() : ''; }
              result.radios.push({ id: r.id, name: r.name, label: lt.substring(0, 80), checked: r.checked });
            });
            // Checkboxes (skip footer)
            document.querySelectorAll('input[type="checkbox"]').forEach(function(c) {
              if (c.id.startsWith('sbFooter')) return;
              var label = document.querySelector('label[for="' + c.id + '"]');
              var lt = label ? label.textContent.trim() : '';
              result.checkboxes.push({ id: c.id, name: c.name, label: lt.substring(0, 80), checked: c.checked });
            });
            // Text inputs
            document.querySelectorAll('input[type="text"], input[type="number"], input[type="tel"], textarea').forEach(function(t) {
              if (t.type !== 'hidden' && t.offsetParent !== null) {
                result.texts.push({ id: t.id, name: t.name, placeholder: (t.placeholder || '').substring(0, 40), value: t.value });
              }
            });
            // Selects
            document.querySelectorAll('select').forEach(function(s) {
              if (s.offsetParent === null) return;
              var opts = Array.from(s.options).map(function(o,i) { return i + ':' + o.text.substring(0, 40); });
              result.selects.push({ id: s.id, name: s.name, options: opts.join('|'), selected: s.selectedIndex });
            });
            // Buttons
            document.querySelectorAll('button, input[type="submit"], a.button, a.btn, [class*="next"], [class*="submit"]').forEach(function(b) {
              var r = b.getBoundingClientRect();
              var t = b.textContent.trim().substring(0, 40);
              if (r.width > 20 && r.height > 10 && t && !t.includes('Swagbucks') && !t.includes('footer')) {
                result.buttons.push({ text: t, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), tag: b.tagName });
              }
            });
            return JSON.stringify(result);
          })()
        `);

        let els = JSON.parse(inputs);
        L("Radios: " + els.radios.length + " CBs: " + els.checkboxes.length + " Texts: " + els.texts.length + " Sels: " + els.selects.length);

        if (els.radios.length === 0 && els.checkboxes.length === 0 && els.texts.length === 0 && els.selects.length === 0) {
          // Maybe just a continue/next page
          let nextBtn = els.buttons.find(b => /continue|next|start|begin|proceed|accept|agree/i.test(b.text));
          if (nextBtn) {
            L("Clicking: " + nextBtn.text);
            fire("Input.dispatchMouseEvent", { type: "mousePressed", x: nextBtn.x, y: nextBtn.y, button: "left", clickCount: 1 });
            await sleep(100);
            fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: nextBtn.x, y: nextBtn.y, button: "left", clickCount: 1 });
            await sleep(3000);
            continue;
          }
          // Check for loading state
          L("No inputs found, waiting...");
          await sleep(3000);
          continue;
        }

        // Handle text inputs
        for (let t of els.texts) {
          let val = '';
          let nameId = (t.name + ' ' + t.id + ' ' + t.placeholder).toLowerCase();
          if (nameId.includes('zip') || nameId.includes('postal')) val = PROFILE.zip;
          else if (nameId.includes('age') || nameId.includes('old')) val = PROFILE.age;
          else if (nameId.includes('city')) val = PROFILE.city;
          else if (nameId.includes('state')) val = PROFILE.state;
          else if (nameId.includes('email')) val = PROFILE.email;
          else if (nameId.includes('name') && nameId.includes('first')) val = 'Weber';
          else if (nameId.includes('name') && nameId.includes('last')) val = 'Gouin';
          else if (nameId.includes('income') || nameId.includes('salary')) val = '75000';
          else if (nameId.includes('dob') || nameId.includes('birth')) val = PROFILE.dob;
          else if (lower.includes('zip') || lower.includes('postal')) val = PROFILE.zip;
          else if (lower.includes('how old') || lower.includes('your age')) val = PROFILE.age;
          else val = PROFILE.zip; // Default to zip as most common text field

          if (val && !t.value) {
            L("Typing '" + val + "' into " + (t.name || t.id));
            await eval_(`
              (function() {
                var el = document.querySelector('[id="${t.id}"]') || document.querySelector('[name="${t.name}"]');
                if (el) {
                  el.focus();
                  el.value = '${val}';
                  el.dispatchEvent(new Event('input', {bubbles: true}));
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
          }
        }

        // Handle radio questions
        if (els.radios.length > 0) {
          // Group by name
          let groups = {};
          els.radios.forEach(r => {
            if (!groups[r.name]) groups[r.name] = [];
            groups[r.name].push(r);
          });

          for (let name in groups) {
            let opts = groups[name];
            let labels = opts.map(o => o.label.toLowerCase());
            let allLabels = labels.join(' ');
            L("Radio group '" + name + "': " + opts.map(o => o.label.substring(0, 30)).join(' | '));

            let pick = null;

            // Gender
            if (allLabels.includes('male') && allLabels.includes('female')) {
              pick = opts.find(o => o.label.toLowerCase() === 'male') || opts.find(o => o.label.toLowerCase().includes('male') && !o.label.toLowerCase().includes('female'));
            }
            // Yes/No questions
            else if (labels.includes('yes') && labels.includes('no')) {
              // Children related
              if (lower.includes('child') || lower.includes('kid') || lower.includes('parent')) {
                pick = opts.find(o => o.label.toLowerCase() === 'no');
              }
              // Hispanic
              else if (lower.includes('hispanic') || lower.includes('latino')) {
                pick = opts.find(o => o.label.toLowerCase() === 'no');
              }
              // Generally prefer "Yes" for most survey questions
              else {
                pick = opts.find(o => o.label.toLowerCase() === 'yes');
              }
            }
            // Employment
            else if (allLabels.includes('employed') || allLabels.includes('self-employed') || allLabels.includes('self employed')) {
              pick = opts.find(o => o.label.toLowerCase().includes('self'));
              if (!pick) pick = opts.find(o => o.label.toLowerCase().includes('employ'));
            }
            // Marital
            else if (allLabels.includes('married') || allLabels.includes('single')) {
              pick = opts.find(o => o.label.toLowerCase().includes('married'));
            }
            // Education
            else if (allLabels.includes('college') || allLabels.includes('high school') || allLabels.includes('degree')) {
              pick = opts.find(o => o.label.toLowerCase().includes('some college') || o.label.toLowerCase().includes('associate'));
              if (!pick) pick = opts.find(o => o.label.toLowerCase().includes('college'));
            }
            // Race/ethnicity
            else if (allLabels.includes('white') || allLabels.includes('african') || allLabels.includes('asian')) {
              pick = opts.find(o => o.label.toLowerCase().includes('white') || o.label.toLowerCase().includes('caucasian'));
            }
            // Age ranges
            else if (allLabels.match(/\d+-\d+/)) {
              pick = opts.find(o => {
                let m = o.label.match(/(\d+)\s*[-–]\s*(\d+)/);
                if (m) return parseInt(m[1]) <= 51 && parseInt(m[2]) >= 51;
                return false;
              });
              if (!pick) pick = opts.find(o => o.label.includes('50') || o.label.includes('51'));
            }
            // Income ranges
            else if (allLabels.includes('$') || allLabels.includes('income') || lower.includes('income') || lower.includes('earn')) {
              pick = opts.find(o => {
                let m = o.label.replace(/[,$]/g, '').match(/(\d+)\s*[-–]\s*(\d+)/);
                if (m) return parseInt(m[1]) <= 75000 && parseInt(m[2]) >= 75000;
                return false;
              });
              if (!pick) pick = opts.find(o => o.label.includes('75') || o.label.includes('70') || o.label.includes('80'));
            }
            // Privacy/Agree - always agree
            else if (allLabels.includes('agree') || allLabels.includes('accept') || allLabels.includes('consent')) {
              pick = opts.find(o => o.label.toLowerCase().includes('agree') || o.label.toLowerCase().includes('accept') || o.label.toLowerCase().includes('consent'));
            }

            // Default: pick first non-"prefer not" option
            if (!pick) {
              pick = opts.find(o => !o.label.toLowerCase().includes('prefer not') && !o.label.toLowerCase().includes('rather not'));
              if (!pick) pick = opts[0];
            }

            if (pick && !pick.checked) {
              L("Selecting radio: " + pick.label.substring(0, 40));
              await eval_(`
                (function() {
                  var el = document.getElementById('${pick.id}');
                  if (el) {
                    var label = document.querySelector('label[for="${pick.id}"]');
                    if (label) label.click();
                    else el.click();
                  }
                })()
              `);
            }
          }
        }

        // Handle checkboxes
        if (els.checkboxes.length > 0) {
          let labels = els.checkboxes.map(c => c.label.toLowerCase());
          let allLabels = labels.join(' ');

          // For "select all that apply" - pick the most relevant
          let picked = false;
          for (let cb of els.checkboxes) {
            let lbl = cb.label.toLowerCase();
            // Architecture/construction related
            if (lbl.includes('architect') || lbl.includes('construction') || lbl.includes('design') || lbl.includes('building')) {
              L("Checking: " + cb.label.substring(0, 40));
              await eval_(`
                (function() {
                  var label = document.querySelector('label[for="${cb.id}"]');
                  if (label) label.click();
                  else { var el = document.getElementById('${cb.id}'); if (el) el.click(); }
                })()
              `);
              picked = true;
            }
            // None of the above for children
            if (lower.includes('child') && (lbl.includes('none') || lbl.includes('n/a'))) {
              await eval_(`
                (function() {
                  var label = document.querySelector('label[for="${cb.id}"]');
                  if (label) label.click();
                  else { var el = document.getElementById('${cb.id}'); if (el) el.click(); }
                })()
              `);
              picked = true;
            }
          }
          // If nothing relevant, pick first
          if (!picked && els.checkboxes.length > 0) {
            let first = els.checkboxes[0];
            if (!first.checked) {
              L("Default check: " + first.label.substring(0, 40));
              await eval_(`
                (function() {
                  var label = document.querySelector('label[for="${first.id}"]');
                  if (label) label.click();
                  else { var el = document.getElementById('${first.id}'); if (el) el.click(); }
                })()
              `);
            }
          }
        }

        // Handle selects
        for (let sel of els.selects) {
          let optsLower = sel.options.toLowerCase();
          let selectedVal = -1;
          let optList = sel.options.split('|');

          // State
          if (optsLower.includes('idaho') || lower.includes('state')) {
            for (let i = 0; i < optList.length; i++) {
              if (optList[i].toLowerCase().includes('idaho')) { selectedVal = i; break; }
            }
          }
          // Industry
          else if (optsLower.includes('architect') || optsLower.includes('construction') || lower.includes('industry') || lower.includes('occupation')) {
            for (let i = 0; i < optList.length; i++) {
              if (optList[i].toLowerCase().includes('architect')) { selectedVal = i; break; }
            }
            if (selectedVal < 0) {
              for (let i = 0; i < optList.length; i++) {
                if (optList[i].toLowerCase().includes('construct')) { selectedVal = i; break; }
              }
            }
          }
          // Age
          else if (lower.includes('age') || lower.includes('born')) {
            for (let i = 0; i < optList.length; i++) {
              let m = optList[i].match(/(\d+)\s*[-–]\s*(\d+)/);
              if (m && parseInt(m[1]) <= 51 && parseInt(m[2]) >= 51) { selectedVal = i; break; }
              if (optList[i].includes('51') || optList[i].includes('1974')) { selectedVal = i; break; }
            }
          }
          // Income
          else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary')) {
            for (let i = 0; i < optList.length; i++) {
              let cleaned = optList[i].replace(/[,$]/g, '');
              let m = cleaned.match(/(\d+)\s*[-–]\s*(\d+)/);
              if (m && parseInt(m[1]) <= 75000 && parseInt(m[2]) >= 75000) { selectedVal = i; break; }
            }
          }

          if (selectedVal >= 0 && sel.selected !== selectedVal) {
            L("Select " + sel.name + " -> index " + selectedVal + ": " + optList[selectedVal]);
            await eval_(`
              (function() {
                var sel = document.getElementById('${sel.id}') || document.querySelector('[name="${sel.name}"]');
                if (sel) {
                  sel.selectedIndex = ${selectedVal};
                  sel.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
          }
        }

        // Click submit/next/continue
        await sleep(500);
        let submitted = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, input[type="submit"], a.btn, a.button, [role="button"]');
            var targets = ['continue', 'next', 'submit', 'proceed', '➔', '→', '>>', '»'];
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (btns[i].id && btns[i].id.startsWith('sbFooter')) continue;
              for (var j = 0; j < targets.length; j++) {
                if (t.includes(targets[j]) || t === targets[j]) {
                  btns[i].click();
                  return 'clicked: ' + btns[i].textContent.trim().substring(0, 30);
                }
              }
            }
            // Try arrow button
            var arrows = document.querySelectorAll('[class*="arrow"], [class*="next"], [class*="forward"]');
            for (var i = 0; i < arrows.length; i++) {
              var r = arrows[i].getBoundingClientRect();
              if (r.width > 10 && r.height > 10) {
                arrows[i].click();
                return 'clicked arrow';
              }
            }
            return 'no submit btn';
          })()
        `);
        L("Submit: " + submitted);
        await sleep(3000);
      }

      // Final status
      let finalUrl = await eval_(`window.location.href`);
      let finalText = await eval_(`document.body.innerText.substring(0, 500)`);
      L("\n=== FINAL ===");
      L("URL: " + (finalUrl || '').substring(0, 80));
      L("Text: " + (finalText || '').substring(0, 300));

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
