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

    const pressKey = async (key, code) => {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key, code: code || key });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyUp", key, code: code || key });
    };

    (async () => {
      // Helper: click a radio/option containing specific text
      const clickOption = async (text) => {
        let r = await eval_(`
          (function() {
            var els = document.querySelectorAll('label, div, span, li, option, input');
            for (var i = 0; i < els.length; i++) {
              var t = els[i].textContent.trim();
              if (t === '${text}' || t.includes('${text}')) {
                var rect = els[i].getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                  return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)});
                }
              }
            }
            return null;
          })()
        `);
        if (r) {
          let pos = JSON.parse(r);
          await clickAt(pos.x, pos.y);
          return true;
        }
        return false;
      };

      // Helper: click the next/continue/arrow button
      const clickNext = async () => {
        let r = await eval_(`
          (function() {
            // Look for blue arrow, Next, Continue, Submit buttons
            var btns = document.querySelectorAll('button, a.btn, [class*="next"], [class*="arrow"], [class*="submit"]');
            for (var i = 0; i < btns.length; i++) {
              var rect = btns[i].getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0 && rect.y > 300) {
                var text = btns[i].textContent.trim();
                if (text.includes('Next') || text.includes('Continue') || text.includes('Submit') || text.includes('→') || text === '' || btns[i].querySelector('svg, i, [class*="arrow"]')) {
                  return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: text.substring(0, 20)});
                }
              }
            }
            // Fallback: look for any button/link at bottom of page
            var allBtns = document.querySelectorAll('button, a');
            for (var j = allBtns.length - 1; j >= 0; j--) {
              var rect = allBtns[j].getBoundingClientRect();
              if (rect.width > 20 && rect.width < 100 && rect.height > 20 && rect.height < 100 && rect.y > 400) {
                return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: 'fallback'});
              }
            }
            return null;
          })()
        `);
        if (r) {
          let pos = JSON.parse(r);
          L("  Clicking next at " + pos.x + "," + pos.y + " (" + pos.text + ")");
          await clickAt(pos.x, pos.y);
          return true;
        }
        return false;
      };

      // Weber's profile for answering screening questions
      const profile = {
        country: 'United States',
        state: 'Idaho',
        zip: '83864',
        age: 51,
        gender: 'Male',
        ethnicity: 'White',
        hispanic: 'No',
        education: 'Some college',
        employment: 'Self-employed',
        income: '$75,000',
        marital: 'Single',
        children: 'No',
        industry: 'Architecture',
      };

      // Process up to 30 pages of screening/survey
      for (let page = 0; page < 30; page++) {
        await sleep(2000);
        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        let questionLC = pageText.toLowerCase();
        L("\n--- Page " + (page+1) + " ---");
        L("URL: " + url.substring(0, 100));
        L("Q: " + pageText.substring(0, 300));

        // Check if survey is done/screened out
        if (questionLC.includes('thank you') || questionLC.includes('completed') || questionLC.includes('screenout') || questionLC.includes('did not qualify') || questionLC.includes('survey is closed')) {
          L("=== SURVEY ENDED ===");
          L(pageText.substring(0, 500));
          break;
        }

        // Check if redirected back to CPX offer wall
        if (questionLC.includes('choose a survey') && questionLC.includes('usd')) {
          L("=== BACK TO OFFER WALL ===");
          break;
        }

        // Get form elements
        let formJson = await eval_(`
          (function() {
            var inputs = document.querySelectorAll('input, select, textarea');
            return JSON.stringify(Array.from(inputs).filter(function(i) {
              return i.type !== 'hidden' && i.offsetParent !== null;
            }).map(function(i) {
              var rect = i.getBoundingClientRect();
              return {
                tag: i.tagName, type: i.type, id: i.id, name: i.name,
                value: (i.value || '').substring(0, 40),
                label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 80) : '',
                x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2),
                checked: i.checked || false
              };
            }));
          })()
        `);
        let fields = JSON.parse(formJson || '[]');
        L("  Fields: " + fields.length);

        // Get clickable answer options (many surveys use div-based options, not form inputs)
        let options = await eval_(`
          (function() {
            var opts = document.querySelectorAll('[class*="answer"], [class*="option"], [class*="choice"], [role="radio"], [role="checkbox"], [role="option"], li');
            var result = [];
            for (var i = 0; i < opts.length; i++) {
              var rect = opts[i].getBoundingClientRect();
              if (rect.width > 50 && rect.height > 10) {
                result.push({
                  text: opts[i].textContent.trim().substring(0, 80),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2)
                });
              }
            }
            return JSON.stringify(result);
          })()
        `);
        let optList = JSON.parse(options || '[]');

        let answered = false;

        // Handle country question
        if (questionLC.includes('country') || questionLC.includes('united states') || questionLC.includes('living in')) {
          answered = await clickOption('Yes, I am from the United States');
          if (!answered) answered = await clickOption('United States');
          if (!answered) answered = await clickOption('Yes');
          L("  Country: " + answered);
        }
        // Handle gender
        else if (questionLC.includes('gender') || questionLC.includes('sex') || questionLC.includes('are you male')) {
          answered = await clickOption('Male');
          if (!answered) answered = await clickOption('Man');
          L("  Gender: " + answered);
        }
        // Handle age/birthday/DOB
        else if (questionLC.includes('age') || questionLC.includes('birthday') || questionLC.includes('born') || questionLC.includes('date of birth') || questionLC.includes('how old')) {
          // Try text input for age
          let ageField = fields.find(f => f.type === 'text' || f.type === 'number');
          if (ageField) {
            await eval_(`
              (function() {
                var i = document.querySelector('input[type="text"], input[type="number"]');
                if (i) {
                  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                  setter.call(i, '51');
                  i.dispatchEvent(new Event('input', {bubbles: true}));
                  i.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
            answered = true;
            L("  Entered age: 51");
          } else {
            // Click age range that includes 51
            answered = await clickOption('50-54') || await clickOption('45-54') || await clickOption('50-59') || await clickOption('45-55');
            L("  Age range: " + answered);
          }
        }
        // Handle zip code
        else if (questionLC.includes('zip') || questionLC.includes('postal')) {
          let tf = fields.find(f => f.type === 'text' || f.type === 'number');
          if (tf) {
            await eval_(`
              (function() {
                var i = document.querySelector('input[type="text"], input[type="number"]');
                if (i) {
                  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                  setter.call(i, '83864');
                  i.dispatchEvent(new Event('input', {bubbles: true}));
                  i.dispatchEvent(new Event('change', {bubbles: true}));
                }
              })()
            `);
            answered = true;
            L("  Entered ZIP: 83864");
          }
        }
        // Handle state
        else if (questionLC.includes('state') && (questionLC.includes('which') || questionLC.includes('what') || questionLC.includes('select') || questionLC.includes('live'))) {
          answered = await clickOption('Idaho');
          if (!answered) {
            // Try select dropdown
            await eval_(`
              (function() {
                var sel = document.querySelector('select');
                if (sel) {
                  for (var i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].text.includes('Idaho')) {
                      sel.selectedIndex = i;
                      sel.dispatchEvent(new Event('change', {bubbles: true}));
                      break;
                    }
                  }
                }
              })()
            `);
            answered = true;
          }
          L("  State: " + answered);
        }
        // Handle ethnicity/race
        else if (questionLC.includes('ethnic') || questionLC.includes('race') || questionLC.includes('hispanic')) {
          if (questionLC.includes('hispanic') || questionLC.includes('latino')) {
            answered = await clickOption('No') || await clickOption('Not Hispanic');
          } else {
            answered = await clickOption('White') || await clickOption('Caucasian');
          }
          L("  Ethnicity: " + answered);
        }
        // Handle education
        else if (questionLC.includes('education') || questionLC.includes('degree') || questionLC.includes('school')) {
          answered = await clickOption('Some college') || await clickOption('some college') || await clickOption('Completed some college');
          if (!answered) answered = await clickOption('Bachelor');
          L("  Education: " + answered);
        }
        // Handle employment
        else if (questionLC.includes('employ') || questionLC.includes('occupation') || questionLC.includes('work status')) {
          answered = await clickOption('Self-employed') || await clickOption('Self employed');
          if (!answered) answered = await clickOption('Employed') || await clickOption('Full-time');
          L("  Employment: " + answered);
        }
        // Handle income
        else if (questionLC.includes('income') || questionLC.includes('salary') || questionLC.includes('household') || questionLC.includes('earn')) {
          answered = await clickOption('$75,000') || await clickOption('75,000') || await clickOption('$70,000');
          if (!answered) {
            // Pick middle option
            let radios = fields.filter(f => f.type === 'radio');
            if (radios.length > 0) {
              let mid = radios[Math.floor(radios.length / 2)];
              await clickAt(mid.x, mid.y);
              answered = true;
            } else if (optList.length > 0) {
              let mid = optList[Math.floor(optList.length / 2)];
              await clickAt(mid.x, mid.y);
              answered = true;
            }
          }
          L("  Income: " + answered);
        }
        // Handle marital status
        else if (questionLC.includes('marital') || questionLC.includes('married') || questionLC.includes('relationship')) {
          answered = await clickOption('Single') || await clickOption('Never married');
          L("  Marital: " + answered);
        }
        // Handle children
        else if (questionLC.includes('children') || questionLC.includes('kids') || questionLC.includes('child')) {
          answered = await clickOption('No') || await clickOption('None') || await clickOption('0');
          L("  Children: " + answered);
        }
        // Handle industry
        else if (questionLC.includes('industry') || questionLC.includes('sector') || questionLC.includes('field of work')) {
          answered = await clickOption('Architecture') || await clickOption('Construction') || await clickOption('Engineering');
          if (!answered) answered = await clickOption('Other');
          L("  Industry: " + answered);
        }
        // Generic: if there are radio buttons, pick first or middle
        else {
          if (fields.length > 0) {
            let radios = fields.filter(f => f.type === 'radio');
            if (radios.length > 0) {
              // For "how often" / agreement scales, pick middle
              let pick = radios[Math.floor(radios.length / 2)];
              await clickAt(pick.x, pick.y);
              answered = true;
              L("  Generic radio: " + pick.label);
            } else {
              let checkboxes = fields.filter(f => f.type === 'checkbox');
              if (checkboxes.length > 0) {
                await clickAt(checkboxes[0].x, checkboxes[0].y);
                answered = true;
                L("  Generic checkbox: " + checkboxes[0].label);
              }
            }
          }
          if (!answered && optList.length > 0) {
            // Click first visible option
            await clickAt(optList[0].x, optList[0].y);
            answered = true;
            L("  Generic option: " + optList[0].text.substring(0, 50));
          }
          if (!answered) {
            L("  NO HANDLER - fields: " + JSON.stringify(fields.slice(0, 3)));
            L("  Options: " + JSON.stringify(optList.slice(0, 3)));
          }
        }

        await sleep(1000);
        await clickNext();
        await sleep(2000);
      }

      // Final state
      let finalUrl = await eval_(`window.location.href`);
      L("\nFINAL URL: " + finalUrl);
      let finalText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("FINAL PAGE: " + finalText.substring(0, 800));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_survey_screen.png', Buffer.from(ss.data, 'base64'));
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
