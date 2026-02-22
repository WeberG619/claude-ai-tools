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

    const findAndClickContinue = async () => {
      let btnPos = await eval_(`
        (function() {
          // Find ALL buttons/links/inputs - look for Continue with arrow or any submit
          var all = document.querySelectorAll('button, input[type="submit"], input[type="button"], a, [role="button"], [class*="btn"], [class*="button"]');
          for (var i = 0; i < all.length; i++) {
            var t = (all[i].textContent || all[i].value || '').trim();
            if (t.includes('Continue') || t.includes('continue') || t.includes('Next') || t.includes('next') || t.includes('→') || t.includes('>>') || t.includes('Submit')) {
              all[i].scrollIntoView({ block: 'center' });
              var rect = all[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t.substring(0, 30), tag: all[i].tagName });
            }
          }
          // Also check for form submit
          var forms = document.querySelectorAll('form');
          if (forms.length > 0) {
            var submit = forms[0].querySelector('[type="submit"]');
            if (submit) {
              var rect = submit.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: 'form submit', tag: submit.tagName });
            }
          }
          return 'none';
        })()
      `);
      return btnPos;
    };

    const answerProfilerQ = async (pageText) => {
      let text = pageText.toLowerCase();
      let target = null;

      if (text.includes('education') || text.includes('degree') || text.includes('school')) target = 'Completed some college';
      else if (text.includes('gender') || text.includes('male') && text.includes('female')) target = 'Male';
      else if (text.includes('hispanic') || text.includes('latino')) target = 'No';
      else if (text.includes('race') || text.includes('ethnic')) target = 'White';
      else if (text.includes('marital') || text.includes('married')) target = 'Single';
      else if (text.includes('employ')) target = 'Self';
      else if (text.includes('children') || text.includes('kids')) target = 'None';
      else if (text.includes('income') || text.includes('salary')) target = '75,000';
      else if (text.includes('age') || text.includes('old') || text.includes('born')) target = '50';
      else if (text.includes('industry') || text.includes('field') || text.includes('work in')) target = 'Architect';
      else if (text.includes('state') || text.includes('where do you')) target = 'Idaho';

      return target;
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      for (let round = 0; round < 15; round++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("\n=== Round " + round + " ===");
        L("Page: " + pageText.substring(0, 300));

        // Check if done
        if (pageText.includes('Thank you') || pageText.includes('complete') || pageText.includes('disqualified') || pageText.includes('screened out') || pageText.includes('not qualify')) {
          L("SURVEY ENDED: " + pageText.substring(0, 500));
          break;
        }

        // Check if it's still a profiler question
        let target = await answerProfilerQ(pageText);

        if (target) {
          L("Answer: " + target);
          // Click the option
          let optPos = await eval_(`
            (function() {
              var target = ${JSON.stringify(target)};
              var labels = document.querySelectorAll('label');
              for (var i = 0; i < labels.length; i++) {
                var t = labels[i].textContent.trim();
                if (t.includes(target)) {
                  labels[i].scrollIntoView({ block: 'center' });
                  var rect = labels[i].getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + 15), y: Math.round(rect.y + rect.height/2), text: t.substring(0, 60) });
                }
              }
              // Try radio inputs
              var radios = document.querySelectorAll('input[type="radio"]');
              for (var i = 0; i < radios.length; i++) {
                var parent = radios[i].parentElement;
                if (parent && parent.textContent.trim().includes(target)) {
                  parent.scrollIntoView({ block: 'center' });
                  var rect = parent.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + 15), y: Math.round(rect.y + rect.height/2), text: parent.textContent.trim().substring(0, 60) });
                }
              }
              return 'not found';
            })()
          `);
          if (optPos !== 'not found') {
            let op = JSON.parse(optPos);
            L("Clicking option: " + op.text + " at (" + op.x + ", " + op.y + ")");
            await cdpClick(op.x, op.y);
            await sleep(1000);
          } else {
            L("Option not found for: " + target);
          }
        }

        // Click Continue/Next
        let btnPos = await findAndClickContinue();
        L("Continue btn: " + btnPos);
        if (btnPos !== 'none') {
          let bp = JSON.parse(btnPos);
          L("Clicking " + bp.text + " at (" + bp.x + ", " + bp.y + ")");
          await cdpClick(bp.x, bp.y);
          await sleep(4000);
        } else {
          L("No continue button found");
          // Try form submit
          await eval_(`
            (function() {
              var forms = document.querySelectorAll('form');
              if (forms.length > 0) forms[0].submit();
            })()
          `);
          await sleep(3000);
        }

        // Check URL
        let url = await eval_(`window.location.href`);
        if (!url.includes('samplicio')) {
          L("Redirected: " + url);
          break;
        }
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
