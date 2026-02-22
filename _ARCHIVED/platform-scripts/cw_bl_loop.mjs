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

      for (let round = 0; round < 20; round++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let url = await eval_(`window.location.href`);
        L("\n=== Round " + round + " ===");
        L("URL: " + url.substring(0, 80));
        L("Page: " + pageText.substring(0, 300));

        // Check if redirected away from samplicio (actual survey started)
        if (!url.includes('samplicio')) {
          L("REDIRECTED to actual survey: " + url);
          break;
        }

        // Check if screened out or done (but NOT matching "Completed some college")
        let lower = pageText.toLowerCase();
        if ((lower.includes('thank you') && !lower.includes('education')) ||
            lower.includes('unfortunately') ||
            lower.includes('disqualified') ||
            lower.includes('screened out') ||
            lower.includes('do not qualify') ||
            lower.includes('not eligible')) {
          L("SURVEY ENDED");
          break;
        }

        // Determine answer
        let target = null;
        if (lower.includes('education') || (lower.includes('degree') && lower.includes('school'))) {
          target = 'Completed some college';
        } else if (lower.includes('industry') || lower.includes('household, work')) {
          target = 'Architecture';
        } else if (lower.includes('gender') || (lower.includes('male') && lower.includes('female') && !lower.includes('income'))) {
          target = 'Male';
        } else if (lower.includes('hispanic') || lower.includes('latino')) {
          target = 'No';
        } else if (lower.includes('race') || lower.includes('ethnic')) {
          target = 'White';
        } else if (lower.includes('marital') || lower.includes('married') || lower.includes('relationship status')) {
          target = 'Single';
        } else if (lower.includes('employment') || lower.includes('employed') || lower.includes('work status')) {
          target = 'Self';
        } else if (lower.includes('children') || lower.includes('kids') || lower.includes('dependents')) {
          target = 'None';
          if (pageText.includes('0') && !pageText.includes('None')) target = '0';
        } else if (lower.includes('income') || lower.includes('earn') || lower.includes('salary') || lower.includes('household') && lower.includes('$')) {
          target = '75,000';
        } else if (lower.includes('what state') || lower.includes('which state') || lower.includes('where do you live') || lower.includes('your state')) {
          target = 'Idaho';
        } else if (lower.includes('how old') || lower.includes('your age') || lower.includes('year of birth') || lower.includes('date of birth') || lower.includes('what year were you born')) {
          target = '1974';
          if (!pageText.includes('1974')) target = '50';
        } else if (lower.includes('zip') || lower.includes('postal')) {
          // Text input needed
          target = '83864';
        }

        if (target) {
          L("-> Answer: " + target);

          // Click the matching radio/checkbox option
          let clicked = await eval_(`
            (function() {
              var target = ${JSON.stringify(target)};
              // Try labels
              var labels = document.querySelectorAll('label');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim();
                if (t.includes(target) && t.length < 100) {
                  var radio = labels[i].querySelector('input[type="radio"], input[type="checkbox"]');
                  if (radio) {
                    radio.checked = true;
                    radio.click();
                    return 'checked label: ' + t.substring(0, 50);
                  }
                  labels[i].click();
                  return 'clicked label: ' + t.substring(0, 50);
                }
              }
              // Try select/dropdown
              var selects = document.querySelectorAll('select');
              for (var i = 0; i < selects.length; i++) {
                var options = selects[i].querySelectorAll('option');
                for (var j = 0; j < options.length; j++) {
                  if (options[j].textContent.includes(target)) {
                    selects[i].value = options[j].value;
                    selects[i].dispatchEvent(new Event('change', { bubbles: true }));
                    return 'selected dropdown: ' + options[j].textContent.substring(0, 50);
                  }
                }
              }
              // Try text input (for ZIP, year)
              var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
              for (var i = 0; i < inputs.length; i++) {
                if (!inputs[i].type || inputs[i].type === 'text') {
                  var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                  setter.call(inputs[i], target);
                  inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                  inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
                  return 'set input: ' + target;
                }
              }
              return 'not found';
            })()
          `);
          L("   Click: " + clicked);
        } else {
          L("-> UNKNOWN QUESTION - stopping");
          L("Full: " + pageText.substring(0, 1000));
          break;
        }

        // Submit form
        await sleep(500);
        await eval_(`
          (function() {
            var forms = document.querySelectorAll('form');
            if (forms.length > 0) forms[0].submit();
          })()
        `);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL STATE ===");
      let fUrl = await eval_(`window.location.href`);
      let fPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + fUrl);
      L("Page:\n" + fPage.substring(0, 2000));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nTargets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

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
