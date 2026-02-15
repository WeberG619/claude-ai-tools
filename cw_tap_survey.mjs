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
  // Find all tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("Tabs: " + tabs.length);
  tabs.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));

  // Connect to the survey tab (opnion.io)
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('opnion.io'));
  if (!surveyTab) {
    L("No survey tab found");
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  }

  L("Connecting to survey tab: " + surveyTab.url.substring(0, 150));
  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    // Profile data for answering questions
    const answers = {
      age: '50', // born 1974, now 2026 => ~51 actually, but the survey asks about age range
      birthYear: '1974',
      gender: 'male',
      zip: '83864',
      state: 'idaho',
      ethnicity: 'white',
      hispanic: 'no',
      education: 'some college',
      employment: 'self-employed',
      income: '75000',
      marital: 'single',
      children: '0'
    };

    (async () => {
      // Get initial page state
      let url = await eval_(`window.location.href`);
      L("Survey URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Get all inputs and buttons
      let r = await eval_(`
        (function() {
          var result = { inputs: [], buttons: [], radios: [], selects: [] };
          // Inputs
          var inputs = document.querySelectorAll('input:not([type="hidden"]), textarea');
          inputs.forEach(function(i) {
            if (i.offsetParent !== null) {
              var rect = i.getBoundingClientRect();
              result.inputs.push({ type: i.type, id: i.id, name: i.name, placeholder: (i.placeholder||'').substring(0,60), x: Math.round(rect.x+rect.width/2), y: Math.round(rect.y+rect.height/2) });
            }
          });
          // Buttons
          var btns = document.querySelectorAll('button, input[type="submit"], a.btn, [role="button"]');
          btns.forEach(function(b) {
            var rect = b.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.buttons.push({ tag: b.tagName, text: b.textContent.trim().substring(0,60), x: Math.round(rect.x+rect.width/2), y: Math.round(rect.y+rect.height/2) });
            }
          });
          // Radio buttons / checkboxes
          var radios = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
          radios.forEach(function(r) {
            var label = r.labels && r.labels[0] ? r.labels[0].textContent.trim() : '';
            result.radios.push({ type: r.type, id: r.id, name: r.name, value: r.value, label: label.substring(0,60), checked: r.checked });
          });
          // Selects
          var sels = document.querySelectorAll('select');
          sels.forEach(function(s) {
            if (s.offsetParent !== null) {
              result.selects.push({ id: s.id, name: s.name, options: Array.from(s.options).slice(0,10).map(o => o.text) });
            }
          });
          return JSON.stringify(result);
        })()
      `);
      L("Elements: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_survey.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      // Try to answer the first question based on URL (it says /screenersurvey/age)
      // This looks like a screener - let's see what's on the page
      // The URL has "age" in it, might ask about age

      // Try interacting with what's there
      if (url.includes('/age')) {
        // Likely asking about age - need to find the input or select
        r = await eval_(`
          (function() {
            // Look for any interactive elements that might represent age selection
            var labels = document.querySelectorAll('label, [class*="option"], [class*="answer"], div[class*="choice"]');
            var result = [];
            labels.forEach(function(l) {
              var rect = l.getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0) {
                result.push({ text: l.textContent.trim().substring(0, 80), tag: l.tagName, class: (l.className||'').substring(0,40), x: Math.round(rect.x+rect.width/2), y: Math.round(rect.y+rect.height/2) });
              }
            });
            return JSON.stringify(result.slice(0, 20));
          })()
        `);
        L("Labels/Options: " + r);

        // Try to find age ranges and click the right one (born 1974 = ~51-52 years old)
        r = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              // Look for age ranges containing 50-54 or 45-54 etc
              if ((t.includes('50') || t.includes('51') || t.includes('45-54') || t.includes('50-54') || t.includes('45 - 54') || t.includes('50 - 54')) && t.length < 30) {
                all[i].click();
                return 'clicked age: ' + t;
              }
            }
            // Look for year of birth input/select
            var sel = document.querySelector('select');
            if (sel) {
              for (var i = 0; i < sel.options.length; i++) {
                if (sel.options[i].text === '1974' || sel.options[i].value === '1974') {
                  sel.selectedIndex = i;
                  sel.dispatchEvent(new Event('change', { bubbles: true }));
                  return 'selected year 1974';
                }
              }
            }
            // Check for text input for age
            var inp = document.querySelector('input[type="text"], input[type="number"]');
            if (inp) {
              var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              nativeInputValueSetter.call(inp, '51');
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              return 'entered age 51';
            }
            return 'no age input found';
          })()
        `);
        L("Age answer: " + r);
        await sleep(1000);

        // Click Next/Continue/Submit
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, input[type="submit"], a.btn');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t.includes('next') || t.includes('continue') || t.includes('submit') || t === 'ok' || t.includes('start')) {
                btns[i].click();
                return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            return 'no submit button';
          })()
        `);
        L("Submit: " + r);
        await sleep(5000);

        // Check new state
        url = await eval_(`window.location.href`);
        L("New URL: " + url);
        pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("New page: " + pageText.substring(0, 1000));

        // Screenshot
        const ss2 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_survey2.png', Buffer.from(ss2.data, 'base64'));
        L("Screenshot 2 saved");
      }

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
