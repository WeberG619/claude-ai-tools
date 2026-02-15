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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    const typeText = async (text) => {
      for (const char of text) {
        await send("Input.dispatchKeyEvent", { type: "keyDown", text: char, key: char });
        await sleep(30);
        await send("Input.dispatchKeyEvent", { type: "keyUp", text: char, key: char });
        await sleep(30);
      }
    };

    const pressKey = async (key, code) => {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key, code: code || key });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyUp", key, code: code || key });
    };

    const clickContinue = async () => {
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().includes('Continue')) {
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)});
            }
          }
          return null;
        })()
      `);
      if (r) {
        let pos = JSON.parse(r);
        await clickAt(pos.x, pos.y);
      }
    };

    (async () => {
      // Process up to 12 profiling pages
      for (let page = 0; page < 12; page++) {
        await sleep(1000);
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);

        // Check if profiling is done
        if (!pageText.includes('Complete your profile') && !pageText.includes('Question')) {
          L("\n=== PROFILING DONE ===");
          L(pageText.substring(0, 500));
          break;
        }

        let questionMatch = pageText.match(/Question (\d+)\/(\d+)/);
        let qNum = questionMatch ? questionMatch[1] : '?';
        L("\n--- Q" + qNum + " ---");
        L(pageText.substring(0, 300));

        // Get form elements
        let formJson = await eval_(`
          (function() {
            var inputs = document.querySelectorAll('input, select');
            return JSON.stringify(Array.from(inputs).filter(function(i) {
              return i.type !== 'hidden';
            }).map(function(i) {
              return {
                tag: i.tagName, type: i.type, id: i.id, name: i.name,
                value: (i.value || '').substring(0, 40),
                label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 80) : ''
              };
            }));
          })()
        `);
        let fields = JSON.parse(formJson || '[]');
        let questionLC = pageText.toLowerCase();

        // Handle date input (birthday)
        if (questionLC.includes('birthday') || questionLC.includes('date of birth') || questionLC.includes('born')) {
          let dateField = fields.find(f => f.type === 'date');
          if (dateField) {
            // Set date value to 1974-03-18
            await eval_(`
              (function() {
                var input = document.getElementById('${dateField.id}');
                if (input) {
                  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                  setter.call(input, '1974-03-18');
                  input.dispatchEvent(new Event('input', {bubbles: true}));
                  input.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
            L("Set birthday: 1974-03-18");
          } else {
            // Try typing the date
            let textField = fields.find(f => f.type === 'text' || f.type === 'number');
            if (textField) {
              await eval_(`(function() { var i = document.getElementById('${textField.id}'); if (i) i.focus(); })()`);
              await typeText("03181974");
              L("Typed birthday");
            }
          }
        }
        // Handle gender (radio buttons)
        else if (questionLC.includes('gender') || questionLC.includes('sex')) {
          let male = fields.find(f => f.label.toLowerCase().includes('male') && !f.label.toLowerCase().includes('female'));
          if (male) {
            await eval_(`(function() { var r = document.getElementById('${male.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected: Male");
          }
        }
        // Handle employment
        else if (questionLC.includes('employ') || questionLC.includes('occupation') || questionLC.includes('work')) {
          let selfEmp = fields.find(f => f.label.toLowerCase().includes('self') || f.label.toLowerCase().includes('freelance'));
          let fullTime = fields.find(f => f.label.toLowerCase().includes('full'));
          let pick = selfEmp || fullTime || fields.find(f => f.type === 'radio' || f.type === 'checkbox');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected work: " + pick.label);
          }
        }
        // Handle education
        else if (questionLC.includes('education') || questionLC.includes('degree') || questionLC.includes('school')) {
          let college = fields.find(f => f.label.toLowerCase().includes('bachelor') || f.label.toLowerCase().includes('college') || f.label.toLowerCase().includes('some college'));
          let pick = college || fields.find(f => f.type === 'radio');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected education: " + pick.label);
          }
        }
        // Handle income
        else if (questionLC.includes('income') || questionLC.includes('salary') || questionLC.includes('household') || questionLC.includes('earn')) {
          let radios = fields.filter(f => f.type === 'radio');
          let midIdx = Math.floor(radios.length / 2);
          let pick = radios[midIdx] || radios[0];
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected income: " + pick.label);
          }
        }
        // Handle ethnicity/race
        else if (questionLC.includes('ethnic') || questionLC.includes('race') || questionLC.includes('hispanic')) {
          let white = fields.find(f => f.label.toLowerCase().includes('white') || f.label.toLowerCase().includes('caucasian'));
          let noHisp = fields.find(f => f.label.toLowerCase().includes('not') || f.label.toLowerCase().includes('no,'));
          let pick = white || noHisp || fields.find(f => f.type === 'radio');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected ethnicity: " + pick.label);
          }
        }
        // Handle marital/relationship
        else if (questionLC.includes('marital') || questionLC.includes('relationship') || questionLC.includes('married')) {
          let single = fields.find(f => f.label.toLowerCase().includes('single') || f.label.toLowerCase().includes('never'));
          let pick = single || fields.find(f => f.type === 'radio');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected: " + pick.label);
          }
        }
        // Handle ZIP/postal code
        else if (questionLC.includes('zip') || questionLC.includes('postal')) {
          let textField = fields.find(f => f.type === 'text' || f.type === 'number');
          if (textField) {
            await eval_(`
              (function() {
                var i = document.getElementById('${textField.id}');
                if (i) {
                  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                  setter.call(i, '83864');
                  i.dispatchEvent(new Event('input', {bubbles: true}));
                  i.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
            L("Entered ZIP: 83864");
          }
        }
        // Handle children/kids
        else if (questionLC.includes('children') || questionLC.includes('kids')) {
          let no = fields.find(f => f.label.toLowerCase().includes('no') || f.label.toLowerCase() === 'none' || f.label.toLowerCase().includes('0'));
          let pick = no || fields.find(f => f.type === 'radio');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected children: " + pick.label);
          }
        }
        // Generic - pick first radio/checkbox option
        else {
          let pick = fields.find(f => f.type === 'radio' || f.type === 'checkbox');
          if (pick) {
            await eval_(`(function() { var r = document.getElementById('${pick.id}'); if (r) r.focus(); })()`);
            await pressKey(" ", "Space");
            L("Selected first option: " + pick.label);
          } else {
            L("No matching handler for this question");
            L("Fields: " + JSON.stringify(fields.slice(0, 5)));
          }
        }

        await sleep(500);
        await clickContinue();
        await sleep(2000);
      }

      // After profiling - check what page we're on
      let url = await eval_(`window.location.href`);
      L("\nFINAL URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("FINAL PAGE:");
      L(pageText.substring(0, 1000));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs_final.png', Buffer.from(ss.data, 'base64'));
      L("Final screenshot saved");

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
