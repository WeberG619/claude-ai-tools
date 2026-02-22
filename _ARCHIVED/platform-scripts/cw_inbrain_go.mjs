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
  // Find Inbrain iframe target
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

    (async () => {
      L("=== INBRAIN - GETTING STARTED ===");

      // Click "Get Started"
      let r = await eval_(`
        (function() {
          var els = document.querySelectorAll('button, a, [class*="button"], [role="button"]');
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim().toLowerCase();
            if (t.includes('get started') || t.includes('start') || t.includes('begin')) {
              els[i].click();
              return 'clicked: ' + els[i].textContent.trim();
            }
          }
          return 'no start button';
        })()
      `);
      L("Start: " + r);
      await sleep(5000);

      // Check what's on screen now
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      let url = await eval_(`window.location.href`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 800));

      // Check for survey elements
      let elements = await eval_(`
        (function() {
          var radios = [];
          document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            var l = (r.labels?.[0]?.textContent || '').trim();
            if (!l) { var p = r.closest('label') || r.parentElement; if (p) l = p.textContent.trim(); }
            radios.push(l.substring(0, 60));
          });
          var inputs = [];
          document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])').forEach(function(i) {
            if (i.offsetParent !== null) inputs.push({ type: i.type, placeholder: (i.placeholder||'').substring(0,30) });
          });
          var buttons = [];
          document.querySelectorAll('button').forEach(function(b) {
            buttons.push(b.textContent.trim().substring(0, 40));
          });
          var selects = [];
          document.querySelectorAll('select').forEach(function(s) {
            if (s.offsetParent !== null) selects.push({ options: s.options.length, first3: Array.from(s.options).slice(0,3).map(o=>o.text) });
          });
          return JSON.stringify({ radios: radios.slice(0,15), inputs: inputs, buttons: buttons, selects: selects });
        })()
      `);
      L("Elements: " + elements);

      // If there are profile questions, start answering
      let ql = pageText.toLowerCase();
      let answered = false;

      // Gender
      if (ql.includes('gender') || (ql.includes('male') && ql.includes('female'))) {
        r = await eval_(`
          (function() {
            var els = document.querySelectorAll('input[type="radio"], button, [role="radio"], [class*="option"], li, label');
            for (var i = 0; i < els.length; i++) {
              var t = els[i].textContent.trim().toLowerCase();
              if (t === 'male' || t === 'm' || t.includes('male') && !t.includes('female')) {
                els[i].click();
                return 'clicked: ' + els[i].textContent.trim();
              }
            }
            return 'male not found';
          })()
        `);
        L("Gender: " + r); answered = true;
      }
      // Age / DOB
      else if (ql.includes('age') || ql.includes('birth') || ql.includes('old')) {
        // Check for select or input
        r = await eval_(`
          (function() {
            var sel = document.querySelector('select');
            if (sel) {
              for (var i = 0; i < sel.options.length; i++) {
                if (sel.options[i].text.includes('1974') || sel.options[i].value === '1974') {
                  sel.selectedIndex = i;
                  sel.dispatchEvent(new Event('change', { bubbles: true }));
                  return 'selected 1974';
                }
                if (sel.options[i].text.includes('51') || sel.options[i].text.includes('50-')) {
                  sel.selectedIndex = i;
                  sel.dispatchEvent(new Event('change', { bubbles: true }));
                  return 'selected: ' + sel.options[i].text;
                }
              }
            }
            var inp = document.querySelector('input[type="text"], input[type="number"]');
            if (inp) {
              inp.focus();
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '51');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'input: 51';
            }
            return 'no age element';
          })()
        `);
        L("Age/DOB: " + r); answered = true;
      }
      // ZIP
      else if (ql.includes('zip') || ql.includes('postal')) {
        r = await eval_(`
          (function() {
            var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"]');
            if (inp) {
              inp.focus();
              var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              ns.call(inp, '83864');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'set: 83864';
            }
            return 'no input';
          })()
        `);
        L("ZIP: " + r); answered = true;
      }

      if (answered) {
        await sleep(500);
        // Click Next/Continue/Submit
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, [role="button"]');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t === 'next' || t === 'continue' || t === 'submit' || t === 'done') {
                btns[i].click();
                return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            return 'no next button';
          })()
        `);
        L("Next: " + r);
        await sleep(3000);
      }

      // Get final state
      pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nFinal page: " + pageText.substring(0, 800));

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
