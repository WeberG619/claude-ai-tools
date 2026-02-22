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

      for (let round = 0; round < 20; round++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let url = await eval_(`window.location.href`);
        L("\n=== Round " + round + " ===");

        if (!url.includes('samplicio')) { L("REDIRECTED: " + url); break; }

        // Get the QUESTION text (first line only, before the options)
        let questionLine = pageText.split('\n')[0].trim();
        L("Q: " + questionLine);

        let lower = questionLine.toLowerCase();

        // Check done states
        if (lower.includes('thank you') || lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out') || lower.includes('not qualify') || lower.includes('not eligible')) {
          L("ENDED: " + questionLine);
          break;
        }

        let target = null;

        // Match on QUESTION text only (not options)
        if (lower.includes('industr') || lower.includes('household, work') || lower.includes('work in')) {
          target = 'Architecture';
        } else if (lower.includes('education') || lower.includes('highest level')) {
          target = 'Completed some college';
        } else if (lower.includes('gender') || lower.includes('are you male')) {
          target = 'Male';
        } else if (lower.includes('hispanic') || lower.includes('latino')) {
          target = 'No';
        } else if (lower.includes('race') || lower.includes('ethnic')) {
          target = 'White';
        } else if (lower.includes('marital') || lower.includes('married') || lower.includes('relationship')) {
          target = 'Single';
        } else if (lower.includes('employ') || lower.includes('work status') || lower.includes('job status')) {
          target = 'Self';
        } else if (lower.includes('children') || lower.includes('kids') || lower.includes('dependents')) {
          target = 'None';
        } else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary')) {
          target = '75,000';
        } else if (lower.includes('state') || lower.includes('where do you')) {
          target = 'Idaho';
        } else if (lower.includes('old') || lower.includes('age') || lower.includes('born') || lower.includes('birth') || lower.includes('year')) {
          target = '1974';
        } else if (lower.includes('zip') || lower.includes('postal')) {
          target = '83864';
        }

        if (target) {
          L("-> " + target);
          let result = await eval_(`
            (function() {
              var target = ${JSON.stringify(target)};
              // Try radio/checkbox via label
              var labels = document.querySelectorAll('label');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim();
                if (t === target || t.includes(target)) {
                  var input = labels[i].querySelector('input');
                  if (input) { input.checked = true; input.click(); return 'radio: ' + t.substring(0, 50); }
                  labels[i].click();
                  return 'label: ' + t.substring(0, 50);
                }
              }
              // Try select dropdown
              var selects = document.querySelectorAll('select');
              for (var i = 0; i < selects.length; i++) {
                for (var j = 0; j < selects[i].options.length; j++) {
                  if (selects[i].options[j].text.includes(target)) {
                    selects[i].selectedIndex = j;
                    selects[i].dispatchEvent(new Event('change', { bubbles: true }));
                    return 'select: ' + selects[i].options[j].text.substring(0, 50);
                  }
                }
              }
              // Try text input
              var textInputs = document.querySelectorAll('input[type="text"], input:not([type])');
              if (textInputs.length > 0) {
                var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(textInputs[0], target);
                textInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                return 'text: ' + target;
              }
              return 'NOT_FOUND';
            })()
          `);
          L("   " + result);

          if (result === 'NOT_FOUND') {
            L("   Options: " + pageText.substring(questionLine.length, questionLine.length + 500));
          }
        } else {
          L("-> UNKNOWN: " + questionLine);
          L("   Full: " + pageText.substring(0, 800));
          break;
        }

        // Submit form
        await sleep(500);
        await eval_(`(function(){ var f = document.querySelector('form'); if(f) f.submit(); })()`);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 2000));

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
