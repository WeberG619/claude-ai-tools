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
      // First get the actual number of radio groups on this page
      let r = await eval_(`
        (function() {
          var names = new Set();
          document.querySelectorAll('input[type="radio"]').forEach(function(r) { names.add(r.name); });
          return JSON.stringify(Array.from(names));
        })()
      `);
      L("Radio groups: " + r);
      const groups = JSON.parse(r);

      // Answers for each group (1-5 scale):
      // Group 1: AI perception (v_249-v_253): beneficial=4, satisfactory=4, important=3, rewarding=3, pleasant=4
      // Group 2: Social influence (v_254-v_257): influence=3, important=3, value=3, similar=4
      // Group 3: Control (v_258-v_261): control=5, up to me=4, confident=4, able=5
      const answers = {
        'v_249': 'x4', // beneficial - 4
        'v_250': 'x4', // satisfactory - 4
        'v_251': 'x3', // important - 3
        'v_252': 'x3', // rewarding - 3
        'v_253': 'x4', // pleasant - 4
        'v_254': 'x3', // influence advise - 3
        'v_255': 'x3', // important advise - 3
        'v_256': 'x3', // value advise - 3
        'v_257': 'x4', // similar advise - 4
        'v_258': 'x5', // within control - 5
        'v_259': 'x4', // up to me - 4
        'v_260': 'x4', // confident - 4
        'v_261': 'x5', // able - 5
      };

      r = await eval_(`
        (function() {
          var answers = ${JSON.stringify(answers)};
          var results = [];
          for (var name in answers) {
            var radioId = name + answers[name];
            var radio = document.getElementById(radioId);
            if (radio) {
              radio.checked = true;
              radio.dispatchEvent(new Event('change', { bubbles: true }));
              results.push(radioId + ': ok');
            } else {
              results.push(radioId + ': NOT FOUND');
            }
          }
          return results.join(', ');
        })()
      `);
      L("Answers: " + r);
      await sleep(500);

      // Submit
      r = await eval_(`
        (function() {
          var form = document.querySelector('form');
          if (form) { form.submit(); return 'submitted'; }
          return 'no form';
        })()
      `);
      L("Submit: " + r);
      await sleep(5000);

      // Read next page
      let pageText = await eval_(`document.body.innerText.substring(0, 6000)`);
      L("PAGE TEXT:");
      L(pageText);

      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return {
              type: i.type || '', name: i.name || '', id: i.id || '',
              value: (i.value || '').substring(0, 80),
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 120) : ''
            };
          }).slice(0, 50));
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
