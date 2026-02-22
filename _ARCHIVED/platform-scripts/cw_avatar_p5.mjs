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
      // Reasons to ACCEPT AI avatar (x1=Not influential, x2=Influential, x3=Very influential)
      // v_229=Usefulness, v_230=Decision support, v_231=Efficiency, v_232=Time saving,
      // v_233=Availability, v_234=Ease of asking questions, v_235=Clarity,
      // v_236=Control, v_237=Comfort, v_238=Reliability
      const acceptAnswers = {
        'v_229': 'x3', // Usefulness - Very influential
        'v_230': 'x2', // Decision support - Influential
        'v_231': 'x3', // Efficiency - Very influential
        'v_232': 'x3', // Time saving - Very influential
        'v_233': 'x2', // Availability - Influential
        'v_234': 'x2', // Ease of asking questions - Influential
        'v_235': 'x2', // Clarity - Influential
        'v_236': 'x1', // Control - Not influential
        'v_237': 'x2', // Comfort - Influential
        'v_238': 'x2', // Reliability - Influential
      };

      // Reasons to REJECT (even though accepted)
      // v_239=Personal decision, v_240=Lack of usefulness, v_241=Lack of trust,
      // v_242=Lack of comfort, v_243=Fear misunderstanding, v_244=Lack transparency,
      // v_245=Privacy, v_246=Human interaction, v_247=Situational, v_248=Reluctance
      const rejectAnswers = {
        'v_239': 'x1', // Personal decision - Not influential
        'v_240': 'x1', // Lack of usefulness - Not influential
        'v_241': 'x2', // Lack of trust - Influential (realistic concern)
        'v_242': 'x1', // Lack of comfort - Not influential
        'v_243': 'x1', // Fear misunderstanding - Not influential
        'v_244': 'x2', // Lack transparency - Influential (realistic)
        'v_245': 'x2', // Privacy - Influential (realistic)
        'v_246': 'x1', // Human interaction - Not influential
        'v_247': 'x2', // Situational - Influential
        'v_248': 'x1', // Reluctance - Not influential
      };

      const allAnswers = { ...acceptAnswers, ...rejectAnswers };

      let r = await eval_(`
        (function() {
          var answers = ${JSON.stringify(allAnswers)};
          var results = [];
          for (var name in answers) {
            var radioId = name + answers[name];
            var radio = document.getElementById(radioId);
            if (radio) {
              radio.checked = true;
              radio.dispatchEvent(new Event('change', { bubbles: true }));
              results.push(radioId + ': checked');
            } else {
              results.push(radioId + ': NOT FOUND');
            }
          }
          return results.join(', ');
        })()
      `);
      L("Answers: " + r);
      await sleep(500);

      // Submit form directly (button might have timer)
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
