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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // 1. Check what JS is on the radio buttons - look for onclick, onchange handlers
      let jsInfo = await eval_(`
        (function() {
          var results = {};
          // Get ALL scripts on the page
          var scripts = document.querySelectorAll('script');
          results.scriptCount = scripts.length;
          results.scriptSrcs = [];
          results.inlineScripts = [];
          for (var i = 0; i < scripts.length; i++) {
            if (scripts[i].src) results.scriptSrcs.push(scripts[i].src.substring(0, 80));
            else if (scripts[i].textContent.trim().length > 0) {
              results.inlineScripts.push(scripts[i].textContent.trim().substring(0, 200));
            }
          }
          // Check the radio button for event listeners
          var labels = document.querySelectorAll('label');
          results.radioDetails = [];
          for (var i = 0; i < Math.min(labels.length, 3); i++) {
            var radio = labels[i].querySelector('input');
            if (radio) {
              results.radioDetails.push({
                text: labels[i].textContent.trim().substring(0, 30),
                type: radio.type,
                name: radio.name,
                value: radio.value,
                id: radio.id,
                onclick: radio.getAttribute('onclick') || 'none',
                onchange: radio.getAttribute('onchange') || 'none',
                dataAttrs: Array.from(radio.attributes).filter(a => a.name.startsWith('data-')).map(a => a.name + '=' + a.value)
              });
            }
          }
          // Check button
          var btn = document.getElementById('ctl00_Content_btnContinue');
          if (btn) {
            results.btnOnclick = btn.getAttribute('onclick') || 'none';
            results.btnType = btn.type;
            results.btnName = btn.name;
          }
          return JSON.stringify(results);
        })()
      `);
      L("JS info:\n" + jsInfo);

      // 2. Look for the specific validation/enable JS function
      let validationJS = await eval_(`
        (function() {
          var html = document.documentElement.outerHTML;
          // Search for functions related to button enabling
          var patterns = ['btnContinue', 'disabled', 'submit-btn', 'enableBtn', 'validateForm', 'checkAnswer', 'option-'];
          var results = [];
          patterns.forEach(function(pat) {
            var idx = 0;
            var found = 0;
            while ((idx = html.indexOf(pat, idx)) !== -1 && found < 3) {
              var start = Math.max(0, idx - 50);
              var end = Math.min(html.length, idx + 100);
              results.push(pat + ': ...' + html.substring(start, end).replace(/\\n/g, ' ').substring(0, 150) + '...');
              idx += pat.length;
              found++;
            }
          });
          return results.join('\\n');
        })()
      `);
      L("\nValidation patterns:\n" + validationJS);

      // 3. Get the full inline JavaScript (look for what enables/disables the button)
      let fullJS = await eval_(`
        (function() {
          var scripts = document.querySelectorAll('script:not([src])');
          var all = '';
          for (var i = 0; i < scripts.length; i++) {
            var t = scripts[i].textContent.trim();
            if (t.length > 10 && (t.includes('btn') || t.includes('disabled') || t.includes('option') || t.includes('radio') || t.includes('check'))) {
              all += '--- SCRIPT ' + i + ' ---\\n' + t.substring(0, 500) + '\\n\\n';
            }
          }
          return all || 'no relevant inline scripts found';
        })()
      `);
      L("\nRelevant JS:\n" + fullJS);

      // 4. Check if there's jQuery or other event binding
      let jqInfo = await eval_(`
        (function() {
          var results = {};
          results.hasJQuery = typeof jQuery !== 'undefined';
          results.jqVersion = typeof jQuery !== 'undefined' ? jQuery.fn.jquery : 'n/a';
          // Check for click handlers bound via jQuery
          if (typeof jQuery !== 'undefined') {
            var radio = document.querySelector('#option-6');
            if (radio) {
              var events = jQuery._data(radio, 'events');
              results.radioEvents = events ? Object.keys(events) : 'none';
            }
          }
          return JSON.stringify(results);
        })()
      `);
      L("\njQuery info: " + jqInfo);

      // Screenshot
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
