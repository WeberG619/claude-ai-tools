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
  const tab = tabs.find(t => t.type === "page" && t.url.includes('insights-today'));
  if (!tab) { L("No insights tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      let lastHash = '';
      let stuckCount = 0;

      for (let round = 0; round < 50; round++) {
        let url, pageText;
        try {
          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 3000) : 'loading'`);
        } catch(e) {
          L("R" + round + ": " + e.message);
          await sleep(3000);
          continue;
        }
        if (!pageText || pageText === 'loading') { await sleep(2000); continue; }

        let lower = pageText.toLowerCase();
        let hash = pageText.substring(0, 150);
        L("\n=== R" + round + " ===");

        // End states
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response') || lower.includes('completed') || lower.includes('you have finished')) {
          L("SURVEY COMPLETE!"); L(pageText.substring(0, 500)); break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('not eligible') || lower.includes('quota full') || lower.includes('do not qualify')) {
          L("SCREENED OUT"); L(pageText.substring(0, 300)); break;
        }
        if (!url.includes('insights-today') && !url.includes('bitlabs') && url.includes('clickworker')) {
          L("REDIRECTED: " + url.substring(0, 80)); break;
        }

        if (hash === lastHash) {
          stuckCount++;
          if (stuckCount >= 5) { L("STUCK! " + pageText.substring(0, 300)); break; }
        } else { stuckCount = 0; }
        lastHash = hash;

        // Handle ALL elements on the page (multi-question pages)
        // 1. Fill text inputs
        let textResult = await eval_(`
          (function() {
            var filled = [];
            document.querySelectorAll('input[type="text"], textarea, input[type="number"], input:not([type])').forEach(function(el) {
              if (el.offsetParent !== null && el.type !== 'hidden' && !el.value) {
                // Determine value based on context
                var context = (el.placeholder || '') + ' ' + (el.parentElement ? el.parentElement.textContent : '');
                var lower = context.toLowerCase();
                var val = '';
                if (lower.includes('zip')) val = '83864';
                else if (lower.includes('age') || lower.includes('year')) val = '51';
                else if (lower.includes('name')) val = 'Weber';
                else if (lower.includes('email')) val = '';
                else val = '83864'; // default for short inputs, likely zip

                if (val) {
                  var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                  setter.call(el, val);
                  el.dispatchEvent(new Event('input', {bubbles:true}));
                  el.dispatchEvent(new Event('change', {bubbles:true}));
                  el.dispatchEvent(new Event('blur', {bubbles:true}));
                  filled.push(val);
                }
              }
            });
            return filled.join(', ') || 'none';
          })()
        `);
        if (textResult !== 'none') L("   Filled: " + textResult);

        // 2. Handle radios - pick right answers
        let radioResult = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            if (radios.length === 0) return 'no radios';

            // Group by name
            var groups = {};
            radios.forEach(function(r) {
              if (!groups[r.name]) groups[r.name] = [];
              var lbl = document.querySelector('label[for="' + r.id + '"]');
              var text = lbl ? lbl.textContent.trim() : (r.parentElement ? r.parentElement.textContent.trim() : '');
              groups[r.name].push({ id: r.id, label: text, checked: r.checked });
            });

            var actions = [];
            for (var name in groups) {
              var opts = groups[name];
              // Skip if already answered
              if (opts.some(function(o) { return o.checked; })) continue;

              var labels = opts.map(function(o) { return o.label.toLowerCase(); });
              var allLabels = labels.join(' ');
              var targetId = null;

              // Gender
              if (allLabels.includes('male') && allLabels.includes('female')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label === 'Male' || opts[i].label.includes('Male') && !opts[i].label.includes('Female')) { targetId = opts[i].id; break; }
                }
              }
              // Yes/No
              else if (opts.length === 2 && labels.includes('yes') && labels.includes('no')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase() === 'yes') { targetId = opts[i].id; break; }
                }
              }
              // Agree/disagree
              else if (allLabels.includes('agree') && allLabels.includes('disagree')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase().includes('agree') && !opts[i].label.toLowerCase().includes('disagree') && !opts[i].label.toLowerCase().includes('strong')) { targetId = opts[i].id; break; }
                }
              }
              // Satisfaction
              else if (allLabels.includes('satisfied') || allLabels.includes('dissatisfied')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase().includes('satisfied') && !opts[i].label.toLowerCase().includes('dis')) { targetId = opts[i].id; break; }
                }
              }
              // Likely
              else if (allLabels.includes('likely') || allLabels.includes('unlikely')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase().includes('somewhat likely') || (opts[i].label.toLowerCase().includes('likely') && !opts[i].label.toLowerCase().includes('un'))) { targetId = opts[i].id; break; }
                }
              }
              // Important
              else if (allLabels.includes('important')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase().includes('somewhat important') || opts[i].label.toLowerCase().includes('important')) { targetId = opts[i].id; break; }
                }
              }
              // Frequency
              else if (allLabels.includes('never') || allLabels.includes('always')) {
                for (var i = 0; i < opts.length; i++) {
                  if (opts[i].label.toLowerCase().includes('sometimes') || opts[i].label.toLowerCase().includes('occasionally')) { targetId = opts[i].id; break; }
                }
              }

              // Fallback: pick middle
              if (!targetId) {
                var idx = Math.floor(opts.length / 2);
                targetId = opts[idx].id;
              }

              if (targetId) {
                var lbl = document.querySelector('label[for="' + targetId + '"]');
                if (lbl) lbl.click(); else document.getElementById(targetId).click();
                var chosen = opts.find(function(o) { return o.id === targetId; });
                actions.push(chosen ? chosen.label.substring(0, 30) : targetId);
              }
            }
            return actions.length > 0 ? actions.join('; ') : 'no action needed';
          })()
        `);
        L("   Radios: " + radioResult);

        // 3. Handle checkboxes
        let cbResult = await eval_(`
          (function() {
            var cbs = document.querySelectorAll('input[type="checkbox"]');
            if (cbs.length === 0) return 'none';
            var checked = false;
            cbs.forEach(function(cb) {
              if (!cb.checked && !checked) {
                var lbl = document.querySelector('label[for="' + cb.id + '"]');
                if (lbl) lbl.click(); else cb.click();
                checked = true;
              }
            });
            return checked ? 'checked first' : 'all checked';
          })()
        `);
        if (cbResult !== 'none') L("   CBs: " + cbResult);

        // 4. Handle selects
        let selResult = await eval_(`
          (function() {
            var sels = document.querySelectorAll('select');
            var actions = [];
            sels.forEach(function(s) {
              if (s.offsetParent !== null && s.selectedIndex <= 0) {
                s.selectedIndex = Math.min(2, s.options.length - 1);
                s.dispatchEvent(new Event('change', {bubbles:true}));
                actions.push(s.options[s.selectedIndex].text.substring(0, 30));
              }
            });
            return actions.length > 0 ? actions.join('; ') : 'none';
          })()
        `);
        if (selResult !== 'none') L("   Sels: " + selResult);

        L("   Q: " + pageText.substring(0, 80).replace(/\n/g, ' '));

        await sleep(500);

        // Click submit - look for arrow button, Next, Submit, Continue, or any clickable submit
        let submitResult = await eval_(`
          (function() {
            // Check for input[type=submit]
            var sub = document.querySelector('input[type="submit"]');
            if (sub && sub.offsetParent !== null) {
              sub.click();
              return 'clicked submit input: ' + (sub.value || '').substring(0, 20);
            }
            // Check for buttons
            var btns = document.querySelectorAll('button[type="submit"], button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (t === 'Next' || t === 'Submit' || t === 'Continue' || t === '➔' || t === '→' || t === '>>' || t === '»') {
                btns[i].click();
                return 'clicked button: ' + t;
              }
            }
            // Check for clickable arrows/links
            var arrows = document.querySelectorAll('a, [role="button"], [class*="next"], [class*="submit"], [class*="forward"], [class*="arrow"]');
            for (var i = 0; i < arrows.length; i++) {
              var t = arrows[i].textContent.trim();
              if (t === '➔' || t === '→' || t === '>>' || t === '»' || t.toLowerCase() === 'next' || t.toLowerCase() === 'continue') {
                arrows[i].click();
                return 'clicked arrow: ' + t;
              }
            }
            // Last resort: find any element with arrow text
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              if (all[i].children.length === 0) {
                var t = all[i].textContent.trim();
                if (t === '➔' || t === '→') {
                  var rect = all[i].getBoundingClientRect();
                  if (rect.width > 5 && rect.height > 5) {
                    all[i].click();
                    return 'clicked text arrow at ' + Math.round(rect.x) + ',' + Math.round(rect.y);
                  }
                }
              }
            }
            // Try form submit
            var form = document.querySelector('form');
            if (form) { form.submit(); return 'submitted form'; }
            return 'no submit found';
          })()
        `);
        L("   " + submitResult);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      try {
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'null'`);
        L("URL: " + fUrl.substring(0, 100));
        L("Page:\n" + fPage.substring(0, 800));
      } catch(e) { L("Final error: " + e.message); }

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
