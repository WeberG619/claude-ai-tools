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
  if (!tab) { L("No insights-today tab. Tabs: " + tabs.filter(t=>t.type==='page').map(t=>t.url.substring(0,40)).join(', ')); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    const clickOption = async (optId) => {
      return await eval_(`
        (function() {
          var label = document.querySelector('label[for="' + ${JSON.stringify(optId)} + '"]');
          if (label) { label.click(); return 'clicked label'; }
          var el = document.getElementById(${JSON.stringify(optId)});
          if (el) { el.click(); return 'clicked el'; }
          return 'not found';
        })()
      `);
    };

    const clickSubmit = async () => {
      let btn = await eval_(`
        (function() {
          var subs = document.querySelectorAll('input[type="submit"], button[type="submit"], button, a');
          for (var i = 0; i < subs.length; i++) {
            var t = (subs[i].value || subs[i].textContent || '').trim().toLowerCase();
            if (t === 'next' || t === 'submit' || t === 'continue' || t.includes('next') || t.includes('>>') || t === '→') {
              var r = subs[i].getBoundingClientRect();
              if (r.width > 15) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: (subs[i].value || subs[i].textContent || '').trim().substring(0, 20) });
            }
          }
          // Also check for arrow/next buttons
          var arrows = document.querySelectorAll('[class*="next"], [class*="submit"], [class*="forward"], [aria-label*="next"], [aria-label*="Next"]');
          for (var i = 0; i < arrows.length; i++) {
            var r = arrows[i].getBoundingClientRect();
            if (r.width > 10 && r.height > 10) return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), text: 'arrow' });
          }
          return null;
        })()
      `);
      if (!btn) return 'no submit';
      let b = JSON.parse(btn);
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
      await sleep(100);
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
      return 'clicked ' + b.text;
    };

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
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response') || lower.includes('completed')) {
          L("SURVEY COMPLETE!"); L(pageText.substring(0, 500)); break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('not eligible') || lower.includes('quota full')) {
          L("SCREENED OUT"); L(pageText.substring(0, 300)); break;
        }

        // Stuck detection
        if (hash === lastHash) {
          stuckCount++;
          if (stuckCount >= 5) { L("STUCK! " + pageText.substring(0, 300)); break; }
        } else { stuckCount = 0; }
        lastHash = hash;

        // Analyze page
        let analysis = await eval_(`
          (function() {
            var r = {};
            r.radios = [];
            document.querySelectorAll('input[type="radio"]').forEach(function(el) {
              var lbl = document.querySelector('label[for="' + el.id + '"]');
              var text = lbl ? lbl.textContent.trim() : (el.parentElement ? el.parentElement.textContent.trim() : '');
              r.radios.push({ id: el.id, name: el.name, value: el.value, label: text.substring(0, 80), checked: el.checked });
            });
            r.cbs = [];
            document.querySelectorAll('input[type="checkbox"]').forEach(function(el) {
              var lbl = document.querySelector('label[for="' + el.id + '"]');
              var text = lbl ? lbl.textContent.trim() : (el.parentElement ? el.parentElement.textContent.trim() : '');
              r.cbs.push({ id: el.id, name: el.name, value: el.value, label: text.substring(0, 80), checked: el.checked });
            });
            r.texts = [];
            document.querySelectorAll('input[type="text"], textarea, input[type="number"], input:not([type])').forEach(function(el) {
              if (el.offsetParent !== null && el.type !== 'hidden') r.texts.push({ id: el.id, name: el.name, ph: (el.placeholder || '').substring(0, 30) });
            });
            r.selects = [];
            document.querySelectorAll('select').forEach(function(s) {
              if (s.offsetParent !== null) {
                var opts = []; s.querySelectorAll('option').forEach(function(o) { opts.push(o.textContent.trim().substring(0, 40)); });
                r.selects.push({ id: s.id, name: s.name, opts: opts.slice(0, 15) });
              }
            });
            return JSON.stringify(r);
          })()
        `);
        let info = JSON.parse(analysis);

        // Get question
        let qLines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = qLines.find(l => l.includes('?') && l.length > 10)
          || qLines.find(l => l.length > 15 && l.length < 300 && !['Next', 'Submit', 'Continue', 'Back', '«', '»', '→', '>'].includes(l))
          || '';
        let qLower = question.toLowerCase();

        L("Q: " + question.substring(0, 120));
        L("   r=" + info.radios.length + " cb=" + info.cbs.length + " txt=" + info.texts.length + " sel=" + info.selects.length);

        // Answer based on question content
        if (info.radios.length > 0) {
          let targetId = null;

          // Age
          if (qLower.includes('age') || qLower.includes('old')) {
            for (let r of info.radios) { if (r.label.includes('50') || r.label.includes('51') || r.label.includes('45-54') || r.label.includes('50-54') || r.label.includes('1974')) { targetId = r.id; break; } }
          }
          // Gender
          else if (qLower.includes('gender') || qLower.includes('sex')) {
            for (let r of info.radios) { if (r.label.includes('Male') || r.label.includes('Man')) { targetId = r.id; break; } }
          }
          // Hispanic
          else if (qLower.includes('hispanic') || qLower.includes('latino')) {
            for (let r of info.radios) { if (r.label === 'No' || r.label.startsWith('No,') || r.label.includes('Not Hispanic')) { targetId = r.id; break; } }
          }
          // Race
          else if (qLower.includes('race') || qLower.includes('ethnic')) {
            for (let r of info.radios) { if (r.label.includes('White') || r.label.includes('Caucasian')) { targetId = r.id; break; } }
          }
          // Income
          else if (qLower.includes('income') || qLower.includes('salary') || qLower.includes('earn')) {
            for (let r of info.radios) { if (r.label.includes('75') || r.label.includes('70') || r.label.includes('60')) { targetId = r.id; break; } }
          }
          // Education
          else if (qLower.includes('education') || qLower.includes('degree')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('some college') || r.label.toLowerCase().includes('associate')) { targetId = r.id; break; } }
          }
          // Employment
          else if (qLower.includes('employ') || qLower.includes('work') || qLower.includes('occupation')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('self') || r.label.toLowerCase().includes('full-time')) { targetId = r.id; break; } }
          }
          // Marital
          else if (qLower.includes('marital') || qLower.includes('married')) {
            for (let r of info.radios) { if (r.label.includes('Married')) { targetId = r.id; break; } }
          }
          // Children
          else if (qLower.includes('child') || qLower.includes('kids')) {
            for (let r of info.radios) { if (r.label.includes('No') || r.label.includes('None') || r.label === '0') { targetId = r.id; break; } }
          }
          // Consent/agree
          else if (lower.includes('privacy') || lower.includes('consent') || lower.includes('agree')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('agree') && !r.label.toLowerCase().includes('disagree') && !r.label.toLowerCase().includes('do not')) { targetId = r.id; break; } }
          }
          // Company size
          else if (qLower.includes('employee') || qLower.includes('company size')) {
            for (let r of info.radios) { if (r.label === '1' || r.label.includes('1-4') || r.label.includes('Self')) { targetId = r.id; break; } }
          }
          // Yes/No default
          else if (info.radios.length === 2 && info.radios.some(r => r.label === 'Yes')) {
            for (let r of info.radios) { if (r.label === 'Yes') { targetId = r.id; break; } }
          }
          // Agree/disagree
          else if (qLower.includes('agree') || qLower.includes('disagree')) {
            for (let r of info.radios) { if (r.label.includes('Agree') && !r.label.includes('Disagree') && !r.label.includes('Strongly')) { targetId = r.id; break; } }
          }
          // Likely
          else if (qLower.includes('likely')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('somewhat likely') || r.label.toLowerCase().includes('likely')) { targetId = r.id; break; } }
          }
          // Satisfaction
          else if (qLower.includes('satisf')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('satisfied') && !r.label.toLowerCase().includes('dis')) { targetId = r.id; break; } }
          }
          // Frequency
          else if (qLower.includes('often') || qLower.includes('frequent')) {
            for (let r of info.radios) { if (r.label.toLowerCase().includes('sometimes') || r.label.toLowerCase().includes('occasionally')) { targetId = r.id; break; } }
          }

          // Fallback: pick middle option (not first, not last)
          if (!targetId) {
            let idx = Math.floor(info.radios.length / 2);
            targetId = info.radios[idx].id;
            L("   [fallback -> middle: " + info.radios[idx].label.substring(0, 40) + "]");
          }

          let r = await clickOption(targetId);
          L("   " + r + " -> " + (info.radios.find(x => x.id === targetId) || {}).label);
        }
        else if (info.cbs.length > 0) {
          // Check first unchecked
          for (let cb of info.cbs) {
            if (!cb.checked) {
              await clickOption(cb.id);
              L("   cb: " + cb.label.substring(0, 40));
              break;
            }
          }
        }
        else if (info.selects.length > 0) {
          for (let sel of info.selects) {
            let idx = Math.min(2, sel.opts.length - 1);
            await eval_(`
              (function() {
                var s = document.getElementById('${sel.id}') || document.querySelector('[name="${sel.name}"]');
                if (s) { s.selectedIndex = ${idx}; s.dispatchEvent(new Event('change', {bubbles:true})); }
              })()
            `);
            L("   sel: " + (sel.opts[idx] || 'idx ' + idx));
          }
        }
        else if (info.texts.length > 0) {
          for (let t of info.texts) {
            let val = "I believe investing in quality infrastructure and community services makes the biggest positive impact.";
            if (qLower.includes('zip') || lower.includes('zip')) val = "83864";
            else if (qLower.includes('age') || qLower.includes('old')) val = "51";
            await eval_(`
              (function() {
                var el = document.getElementById('${t.id}') || document.querySelector('[name="${t.name}"]');
                if (el) {
                  var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                  setter.call(el, ${JSON.stringify(val)});
                  el.dispatchEvent(new Event('input', {bubbles:true}));
                  el.dispatchEvent(new Event('change', {bubbles:true}));
                }
              })()
            `);
            L("   txt: " + val.substring(0, 40));
          }
        }
        else {
          L("   No inputs. " + pageText.substring(0, 150));
        }

        await sleep(500);
        let sub = await clickSubmit();
        L("   " + sub);
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
