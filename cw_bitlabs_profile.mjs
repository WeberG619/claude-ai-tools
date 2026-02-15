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
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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

    (async () => {
      // Process profiling questions iteratively
      for (let q = 0; q < 15; q++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("\n--- Q" + (q+1) + " ---");
        L(pageText.substring(0, 500));

        // Check if profiling is done
        if (!pageText.includes('Question') && !pageText.includes('Complete your profile')) {
          L("PROFILING DONE - on actual survey now");
          break;
        }

        let formJson = await eval_(`
          (function() {
            var inputs = document.querySelectorAll('input, select');
            return JSON.stringify(Array.from(inputs).filter(function(i) {
              return i.offsetParent !== null && i.type !== 'hidden';
            }).map(function(i) {
              var opts = '';
              if (i.tagName === 'SELECT') {
                opts = Array.from(i.options).slice(0, 20).map(function(o) { return o.value + ':' + o.text.substring(0, 30); }).join('|');
              }
              return {
                tag: i.tagName, type: i.type, name: i.name, id: i.id,
                value: (i.value || '').substring(0, 40),
                label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 80) : '',
                options: opts
              };
            }));
          })()
        `);
        let fields = JSON.parse(formJson || '[]');

        // Determine question type and answer
        let questionText = pageText.toLowerCase();
        let answered = false;

        // Language question
        if (questionText.includes('language')) {
          await eval_(`(function() { var cb = document.getElementById('v-0'); if (cb) { cb.checked = true; cb.click(); } })()`);
          L("Selected: English");
          answered = true;
        }
        // Gender question
        else if (questionText.includes('gender') || questionText.includes('sex')) {
          let maleField = fields.find(f => f.label.toLowerCase().includes('male') && !f.label.toLowerCase().includes('female'));
          if (maleField) {
            await eval_(`(function() { var r = document.getElementById('${maleField.id}'); if (r) { r.checked = true; r.click(); } })()`);
            L("Selected: Male");
            answered = true;
          }
        }
        // Age/birth year question
        else if (questionText.includes('age') || questionText.includes('birth') || questionText.includes('born')) {
          let textField = fields.find(f => f.type === 'text' || f.type === 'number');
          let selectField = fields.find(f => f.tag === 'SELECT');
          if (textField) {
            await eval_(`(function() { var i = document.getElementById('${textField.id}'); if (i) { var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(i, '1974'); i.dispatchEvent(new Event('input', {bubbles:true})); i.dispatchEvent(new Event('change', {bubbles:true})); } })()`);
            L("Entered: 1974");
            answered = true;
          } else if (selectField) {
            // Find option for 1974 or 50-54 age range
            await eval_(`(function() {
              var sel = document.getElementById('${selectField.id}');
              if (sel) {
                for (var i = 0; i < sel.options.length; i++) {
                  if (sel.options[i].text.includes('1974') || sel.options[i].value.includes('1974') ||
                      sel.options[i].text.includes('50') || sel.options[i].text.includes('51')) {
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', {bubbles:true}));
                    break;
                  }
                }
              }
            })()`);
            L("Selected age range");
            answered = true;
          }
        }
        // Employment/work question
        else if (questionText.includes('employ') || questionText.includes('occupation') || questionText.includes('work status')) {
          let selfEmp = fields.find(f => f.label.toLowerCase().includes('self') || f.label.toLowerCase().includes('freelance') || f.label.toLowerCase().includes('business owner'));
          let fullTime = fields.find(f => f.label.toLowerCase().includes('full') && f.label.toLowerCase().includes('time'));
          let pick = selfEmp || fullTime || fields[0];
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            L("Selected: " + pick.label);
            answered = true;
          }
        }
        // Education question
        else if (questionText.includes('education') || questionText.includes('degree') || questionText.includes('school')) {
          let bach = fields.find(f => f.label.toLowerCase().includes('bachelor') || f.label.toLowerCase().includes('college'));
          let pick = bach || fields[Math.min(2, fields.length-1)];
          if (pick) {
            if (pick.tag === 'SELECT') {
              await eval_(`(function() { var s = document.getElementById('${pick.id}'); if (s) { s.selectedIndex = Math.min(3, s.options.length-1); s.dispatchEvent(new Event('change',{bubbles:true})); } })()`);
            } else {
              await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            }
            L("Selected education: " + (pick.label || 'option'));
            answered = true;
          }
        }
        // Income question
        else if (questionText.includes('income') || questionText.includes('salary') || questionText.includes('household')) {
          // Pick a middle-range income
          let midIdx = Math.floor(fields.length / 2);
          let pick = fields[midIdx] || fields[0];
          if (pick) {
            if (pick.tag === 'SELECT') {
              await eval_(`(function() { var s = document.getElementById('${pick.id}'); if (s) { s.selectedIndex = Math.floor(s.options.length/2); s.dispatchEvent(new Event('change',{bubbles:true})); } })()`);
            } else {
              await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            }
            L("Selected income: " + (pick.label || 'middle option'));
            answered = true;
          }
        }
        // Ethnicity question
        else if (questionText.includes('ethnic') || questionText.includes('race') || questionText.includes('hispanic')) {
          let white = fields.find(f => f.label.toLowerCase().includes('white') || f.label.toLowerCase().includes('caucasian'));
          let noHisp = fields.find(f => f.label.toLowerCase().includes('no') || f.label.toLowerCase().includes('not'));
          let pick = white || noHisp || fields[0];
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            L("Selected ethnicity: " + pick.label);
            answered = true;
          }
        }
        // Marital status
        else if (questionText.includes('marital') || questionText.includes('relationship')) {
          let single = fields.find(f => f.label.toLowerCase().includes('single'));
          let pick = single || fields[0];
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            L("Selected: " + pick.label);
            answered = true;
          }
        }
        // Generic - pick first option for radio, first valid for select
        else if (!answered && fields.length > 0) {
          let pick = fields[0];
          if (pick.type === 'radio' || pick.type === 'checkbox') {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) { r.checked = true; r.click(); } })()`);
            L("Selected first option: " + pick.label);
            answered = true;
          } else if (pick.tag === 'SELECT') {
            await eval_(`(function() { var s = document.getElementById('${pick.id}'); if (s && s.options.length > 1) { s.selectedIndex = 1; s.dispatchEvent(new Event('change',{bubbles:true})); } })()`);
            L("Selected first select option");
            answered = true;
          } else if (pick.type === 'text' || pick.type === 'number') {
            await eval_(`(function() { var i = document.getElementById('${pick.id}'); if (i) { var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(i, '83864'); i.dispatchEvent(new Event('input',{bubbles:true})); } })()`);
            L("Entered text value");
            answered = true;
          }
        }

        await sleep(500);

        // Click Continue
        let r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim().includes('Continue') || btns[i].textContent.trim().includes('Next')) {
                btns[i].click();
                return 'clicked Continue';
              }
            }
            return 'no Continue button';
          })()
        `);
        L("Nav: " + r);
        await sleep(3000);
      }

      // After profiling, check what we're on
      let url = await eval_(`window.location.href`);
      L("\nFINAL URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("FINAL PAGE:");
      L(pageText);

      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null && i.type !== 'hidden';
          }).map(function(i) {
            return {
              type: i.type || '', name: i.name || '', id: i.id || '',
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 80) : ''
            };
          }).slice(0, 30));
        })()
      `);
      L("FORM: " + formJson);

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
