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

    const cdpClick = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(100);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Dump the full HTML to understand the form structure
      L("=== PAGE HTML ANALYSIS ===");
      let formInfo = await eval_(`
        (function() {
          var results = {};
          // All form elements
          var form = document.querySelector('form');
          if (form) {
            results.formAction = form.action;
            results.formMethod = form.method;
            results.formId = form.id;
          }
          // All submit-like elements
          results.submits = [];
          document.querySelectorAll('input[type="submit"], input[type="button"], input[type="image"], button, a.btn, [class*="btn"], [class*="button"], [class*="continue"], [class*="next"]').forEach(function(el) {
            results.submits.push({
              tag: el.tagName,
              type: el.type || '',
              value: (el.value || '').substring(0, 50),
              text: el.textContent.trim().substring(0, 50),
              id: el.id || '',
              name: el.name || '',
              classes: (el.className || '').substring(0, 80),
              onclick: el.onclick ? 'has' : 'no'
            });
          });
          // Check for __doPostBack
          results.hasDoPostBack = typeof __doPostBack !== 'undefined';
          // Hidden inputs
          results.hiddenInputs = [];
          document.querySelectorAll('input[type="hidden"]').forEach(function(inp) {
            results.hiddenInputs.push({ name: inp.name, valueLen: (inp.value||'').length });
          });
          return JSON.stringify(results);
        })()
      `);
      L(formInfo);

      // Get the page HTML around the submit area
      let submitArea = await eval_(`
        (function() {
          var html = document.body.innerHTML;
          // Find continue/next/submit
          var idx = html.toLowerCase().indexOf('continue');
          if (idx === -1) idx = html.toLowerCase().indexOf('submit');
          if (idx === -1) idx = html.toLowerCase().indexOf('next');
          if (idx >= 0) return html.substring(Math.max(0, idx - 200), idx + 300);
          return 'no continue/submit found in HTML';
        })()
      `);
      L("\nSubmit area HTML:\n" + submitArea.substring(0, 500));

      // Select Architecture first
      await eval_(`
        (function() {
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.trim() === 'Architecture') {
              var radio = labels[i].querySelector('input');
              if (radio) { radio.checked = true; radio.click(); }
              return;
            }
          }
        })()
      `);
      L("\nSelected Architecture");

      // Try clicking the submit button by its actual element
      let submitResult = await eval_(`
        (function() {
          // Try input[type=submit]
          var submit = document.querySelector('input[type="submit"]');
          if (submit) {
            submit.click();
            return 'clicked input[type=submit]: ' + submit.value;
          }
          // Try any button
          var btn = document.querySelector('button[type="submit"], button');
          if (btn) {
            btn.click();
            return 'clicked button: ' + btn.textContent.trim();
          }
          // Try __doPostBack
          if (typeof __doPostBack === 'function') {
            __doPostBack('', '');
            return 'called __doPostBack';
          }
          return 'no submit mechanism found';
        })()
      `);
      L("Submit: " + submitResult);
      await sleep(5000);

      // Check result
      let newUrl = await eval_(`window.location.href`);
      let newPage = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nURL: " + newUrl);
      L("Page:\n" + newPage.substring(0, 1000));

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
