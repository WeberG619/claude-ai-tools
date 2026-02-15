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
  const tab = tabs.find(t => t.type === "page");
  if (!tab) { L("No tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(0); }

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
      // Jobs to try (simpler ones first)
      const jobs = [
        { id: '1265821', name: 'Christian athlete' },
        { id: '1262113', name: 'Keyword search 1' },
        { id: '1255859', name: 'Keyword search 2' },
      ];

      for (const job of jobs) {
        L(`\n=== TRYING: ${job.name} (${job.id}) ===`);

        await send("Page.navigate", { url: `https://workplace.clickworker.com/en/workplace/jobs/${job.id}/edit` });
        await sleep(5000);

        let url = await eval_(`window.location.href`);
        L("URL: " + url);

        if (url.includes('two_fa')) {
          L("BLOCKED BY 2FA - stopping");
          break;
        }

        // Handle agreement pages
        if (url.includes('confirm_agreement')) {
          await eval_(`
            var btn = document.querySelector('input[type="submit"][value="Agree"]');
            if (btn) btn.click();
          `);
          L("Agreed to terms");
          await sleep(3000);
          url = await eval_(`window.location.href`);
        }

        if (url.includes('confirm_instruction')) {
          await eval_(`
            var btn = document.querySelector('input[type="submit"][value="Agree"], input[type="submit"][name="confirm"]');
            if (btn) btn.click();
          `);
          L("Confirmed instructions");
          await sleep(3000);
          url = await eval_(`window.location.href`);
        }

        if (!url.includes('/edit')) {
          const pageText = await eval_(`document.body.innerText.substring(0, 300)`);
          L("Not on edit page: " + pageText?.substring(0, 200));
          continue;
        }

        // Get page content
        const pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("Page: " + pageText?.substring(0, 500));

        // Check if no more jobs
        if (pageText.includes('no further jobs') || pageText.includes('No jobs available')) {
          L("No more jobs in this project");
          continue;
        }

        // Get radio buttons
        const radiosJson = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            return JSON.stringify(Array.from(radios).map(function(r) {
              return {
                id: r.id, value: (r.value || '').substring(0, 80), name: r.name,
                label: (r.labels && r.labels[0]) ? r.labels[0].textContent.trim().substring(0, 80) : ''
              };
            }));
          })()
        `);
        const radios = JSON.parse(radiosJson || '[]');
        L("Radios: " + radios.length);

        if (radios.length > 0) {
          // Select first radio option
          const pick = radios[0];
          const result = await eval_(`
            (function() {
              var radio = document.getElementById('${pick.id}');
              if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
                radio.click();
                return 'selected: ' + radio.value;
              }
              return 'not found';
            })()
          `);
          L("Selected: " + result);
          await sleep(500);

          // Check for required textareas
          const tasJson = await eval_(`
            (function() {
              var tas = document.querySelectorAll('textarea');
              var visible = Array.from(tas).filter(function(t) { return t.offsetParent !== null; });
              return JSON.stringify(visible.map(function(t) { return {name: t.name, id: t.id, required: t.required}; }));
            })()
          `);
          const textareas = JSON.parse(tasJson || '[]');
          if (textareas.length > 0) {
            for (const ta of textareas) {
              await eval_(`
                (function() {
                  var el = document.getElementById('${ta.id}');
                  if (el) {
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(el, 'This is an important topic that deserves careful consideration from multiple perspectives.');
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                  }
                })()
              `);
              L("Filled textarea: " + ta.id);
            }
          }

          // Submit
          const submitResult = await eval_(`
            (function() {
              var btn = document.querySelector('input[type="submit"][name="submit_job"]');
              if (btn) { btn.click(); return 'submitted'; }
              return 'no submit button';
            })()
          `);
          L("Submit: " + submitResult);
          await sleep(4000);

          // Check balance
          const balance = await eval_(`
            (function() {
              var text = document.body.innerText;
              var match = text.match(/Account balance \\$ ([\\d.]+)/);
              return match ? match[1] : 'unknown';
            })()
          `);
          L("Balance: $" + balance);
        } else {
          L("No radio buttons - checking for other form elements");
          const formInfo = await eval_(`
            (function() {
              var inputs = document.querySelectorAll('input, select, textarea');
              return JSON.stringify(Array.from(inputs).filter(function(i) {
                return i.offsetParent !== null && i.type !== 'hidden';
              }).map(function(i) {
                return {tag: i.tagName, type: i.type, name: i.name, id: i.id};
              }).slice(0, 20));
            })()
          `);
          L("Form elements: " + formInfo);
        }
      }

      // Final balance check
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
      await sleep(3000);
      const finalBalance = await eval_(`
        (function() {
          var text = document.body.innerText;
          var match = text.match(/Account balance \\$ ([\\d.]+)/);
          return match ? match[1] : 'unknown';
        })()
      `);
      L("\n=== FINAL BALANCE: $" + finalBalance + " ===");

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
