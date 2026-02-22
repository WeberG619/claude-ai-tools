import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

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
      // Navigate to external survey
      const surveyUrl = "https://ww3.unipark.de/uc/Avatar_Usage/?user=dc8f29e61e0c622da86f040074590f3be36ea8d9&user_id=25671709&task_id=209877989&job_id=467772889";
      await send("Page.navigate", { url: surveyUrl });
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      // Get full page text
      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("PAGE TEXT:");
      L(pageText);

      // Get all form elements with full detail
      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            var opts = '';
            if (i.tagName === 'SELECT') {
              opts = Array.from(i.options).map(function(o) { return o.value + ':' + o.text.substring(0, 40); }).join('|');
            }
            return {
              tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '',
              value: (i.value || '').substring(0, 80),
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 120) : '',
              placeholder: i.placeholder || '',
              options: opts
            };
          }).slice(0, 40));
        })()
      `);
      L("FORM: " + formJson);

      // Get all buttons
      let buttonsJson = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
          return JSON.stringify(Array.from(btns).filter(function(b) { return b.offsetParent !== null; }).map(function(b) {
            return { tag: b.tagName, type: b.type, id: b.id, value: (b.value || '').substring(0, 50), text: b.textContent.trim().substring(0, 50) };
          }));
        })()
      `);
      L("BUTTONS: " + buttonsJson);

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
