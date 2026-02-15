import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 300000);

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
      // CPX Research uses: radio.click() for selection, #submitquestion1.click() for submit
      // HTMLFormElement.prototype.submit.call(form) if needed (button[name=submit] shadows form.submit)

      const selectRadio = async (searchText) => {
        return await eval_(`
          (function() {
            var labels = document.querySelectorAll('label');
            for (var i = 0; i < labels.length; i++) {
              if (labels[i].textContent.trim().includes('${searchText.replace(/'/g, "\\'")}')) {
                var input = labels[i].querySelector('input') || document.getElementById(labels[i].getAttribute('for'));
                if (input) { input.click(); return 'selected: ' + labels[i].textContent.trim().substring(0, 60); }
                labels[i].click();
                return 'label-clicked: ' + labels[i].textContent.trim().substring(0, 60);
              }
            }
            return null;
          })()
        `);
      };

      const selectRadioById = async (id) => {
        return await eval_(`
          (function() {
            var r = document.getElementById('${id}');
            if (r) { r.click(); return 'clicked #${id}'; }
            return null;
          })()
        `);
      };

      const setInputValue = async (name, value) => {
        return await eval_(`
          (function() {
            var input = document.querySelector('input[name="${name}"]') || document.querySelector('input[type="text"], input[type="number"]');
            if (!input) return null;
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, '${value}');
            input.dispatchEvent(new Event('input', {bubbles: true}));
            input.dispatchEvent(new Event('change', {bubbles: true}));
            return 'set ' + input.name + '=' + input.value;
          })()
        `);
      };

      const submitForm = async () => {
        return await eval_(`
          (function() {
            var btn = document.getElementById('submitquestion1');
            if (btn) { btn.click(); return 'clicked #submitquestion1'; }
            // Fallback: HTMLFormElement.prototype.submit
            var form = document.getElementById('submitquestion');
            if (form) { HTMLFormElement.prototype.submit.call(form); return 'submitted form'; }
            // Fallback: any submit button
            var submit = document.querySelector('button[type="submit"], input[type="submit"]');
            if (submit) { submit.click(); return 'clicked submit: ' + (submit.className || '').substring(0, 30); }
            // Fallback: Next/Continue/Submit button
            var btns = document.querySelectorAll('button, a.btn');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (t.includes('Next') || t.includes('Continue') || t.includes('Submit') || t.includes('Start')) {
                btns[i].click();
                return 'clicked: ' + t.substring(0, 30);
              }
            }
            return 'no submit found';
          })()
        `);
      };

      // First navigate to the offer wall and pick a survey
      await send("Page.navigate", { url: "https://offers.cpx-research.com/index.php?app_id=15613&ext_user_id=25671709&secure_hash=e37e9602d522dcee740e36b6907c2c18&subid_1=468201977" });
      await sleep(5000);

      // Click on the second survey ($1.05, row 2, col 2 = position ~1356, 385)
      // Actually let's find and click a survey via JS
      let surveyClicked = await eval_(`
        (function() {
          var cards = document.querySelectorAll('[class*="survey-card"], [class*="cpx-card"], a[href*="#"]');
          var arrows = [];
          for (var i = 0; i < cards.length; i++) {
            var rect = cards[i].getBoundingClientRect();
            if (rect.width > 20 && rect.width < 80 && rect.height > 20 && rect.height < 80 && rect.y > 100 && rect.y < 600) {
              arrows.push({el: cards[i], y: rect.y, x: rect.x});
            }
          }
          // Click the 4th arrow (different survey than the one we tried)
          if (arrows.length > 3) { arrows[3].el.click(); return 'clicked arrow #4 at ' + arrows[3].x + ',' + arrows[3].y; }
          if (arrows.length > 0) { arrows[0].el.click(); return 'clicked arrow #1'; }
          return 'no arrows found';
        })()
      `);
      L("Survey click: " + surveyClicked);
      await sleep(5000);

      let lastQuestion = '';
      let stuckCount = 0;

      // Process up to 40 question pages
      for (let page = 0; page < 40; page++) {
        await sleep(3000);

        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        let q = pageText.toLowerCase();
        L("\n--- Q" + (page+1) + " ---");
        L("Q: " + pageText.substring(0, 300));

        // Stuck detection
        let questionTitle = pageText.substring(0, 100);
        if (questionTitle === lastQuestion) {
          stuckCount++;
          if (stuckCount >= 2) {
            L("=== STUCK ON SAME QUESTION ===");
            break;
          }
        } else {
          stuckCount = 0;
        }
        lastQuestion = questionTitle;

        // End conditions
        if (q.includes('thank you') && (q.includes('completed') || q.includes('finished') || q.includes('reward'))) {
          L("=== SURVEY COMPLETE ===");
          break;
        }
        if (q.includes('screenout') || q.includes('did not qualify') || q.includes('not eligible') || q.includes('unfortunately') || q.includes('do not match')) {
          L("=== SCREENED OUT ===");
          break;
        }
        if (q.includes('choose a survey') && q.includes('usd') && q.includes('minutes')) {
          L("=== BACK TO OFFER WALL ===");
          break;
        }
        // Check if redirected to external survey
        if (!url.includes('cpx-research.com')) {
          L("=== REDIRECTED TO EXTERNAL SURVEY ===");
          L("External URL: " + url);
          // Take screenshot and bail - we'll handle external surveys separately
          const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
          writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_external.png', Buffer.from(ss.data, 'base64'));
          L("External survey screenshot saved");
          break;
        }

        // Get form inputs
        let inputsJson = await eval_(`
          (function() {
            var inputs = document.querySelectorAll('#submitquestion input:not([type="hidden"]), #submitquestion select, #submitquestion textarea');
            return JSON.stringify(Array.from(inputs).filter(function(i) {
              return i.offsetParent !== null;
            }).map(function(i) {
              return {
                type: i.type, id: i.id, name: i.name,
                value: (i.value||'').substring(0,40),
                label: (i.labels&&i.labels[0])?i.labels[0].textContent.trim().substring(0,80):'',
                checked: i.checked||false
              };
            }));
          })()
        `);
        let fields = JSON.parse(inputsJson || '[]');
        let radios = fields.filter(f => f.type === 'radio');
        let textInputs = fields.filter(f => f.type === 'text' || f.type === 'number');
        let selects = fields.filter(f => f.type === 'select-one');
        let checkboxes = fields.filter(f => f.type === 'checkbox');

        let answered = false;

        // --- Screening Questions ---
        // NOTE: Order matters! Hispanic/ethnicity MUST be before country (options contain "Country" word)

        // "Start the survey" transition page - click green button
        if (q.includes('start the survey') && q.includes('congratulations')) {
          let r = await eval_(`
            (function() {
              var btns = document.querySelectorAll('a, button');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim().includes('Start the survey')) {
                  btns[i].click();
                  return 'clicked: Start the survey';
                }
              }
              return null;
            })()
          `);
          L("  Start survey: " + r);
          answered = true;
          await sleep(5000); // Extra wait for redirect
          continue; // Skip submit - this page doesn't have the standard form
        }
        // Privacy/Agree
        else if (q.includes('ready to start') || q.includes('agreed') || (q.includes('privacy') && q.includes('survey'))) {
          let r = await selectRadio('Agreed') || await selectRadioById('1');
          L("  Agree: " + r); answered = !!r;
        }
        // Hispanic/Latino (MUST be before country check)
        else if (q.includes('hispanic') || q.includes('latino') || q.includes('spanish origin')) {
          let r = await selectRadio('No, not of Hispanic');
          if (!r) r = await selectRadio('Not Hispanic') || await selectRadio('Prefer not to answer');
          L("  Hispanic: " + r); answered = !!r;
        }
        // Ethnicity/Race
        else if (q.includes('ethnic') || q.includes('race') || q.includes('racial')) {
          let r = await selectRadio('White') || await selectRadio('Caucasian');
          L("  Race: " + r); answered = !!r;
        }
        // Country (more specific check)
        else if ((q.includes('currently living') && q.includes('united states')) || (q.includes('country') && q.includes('select') && !q.includes('hispanic'))) {
          let r = await selectRadio('Yes, I am') || await selectRadio('United States');
          L("  Country: " + r); answered = !!r;
        }
        // Birth year
        else if (q.includes('year') && q.includes('born')) {
          let r = await setInputValue('birthday_year', '1974');
          L("  Birth year: " + r); answered = !!r;
        }
        // Birth month
        else if (q.includes('month') && q.includes('born')) {
          let r = await selectRadio('March');
          L("  Birth month: " + r); answered = !!r;
        }
        // Birth day
        else if (q.includes('day') && q.includes('born')) {
          let r = await selectRadio('18 March') || await selectRadio('18');
          L("  Birth day: " + r); answered = !!r;
        }
        // Gender
        else if (q.includes('gender') || q.includes('what is your sex') || q.includes('are you male') || q.includes('i am a') || (q.includes('man') && q.includes('woman') && !q.includes('spider'))) {
          let r = await selectRadio('Male') || await selectRadio('Man');
          L("  Gender: " + r); answered = !!r;
        }
        // Device type
        else if (q.includes('are you on a') || q.includes('device') || (q.includes('desktop') && q.includes('laptop'))) {
          let r = await selectRadio('Desktop') || await selectRadio('Laptop') || await selectRadio('PC');
          L("  Device: " + r); answered = !!r;
        }
        // Language
        else if (q.includes('language') && (q.includes('speak') || q.includes('fluent'))) {
          let r = await selectRadio('English');
          if (!r) {
            r = await eval_(`
              (function() {
                var labels = document.querySelectorAll('label');
                for (var i = 0; i < labels.length; i++) {
                  if (labels[i].textContent.trim() === 'English') {
                    var input = labels[i].querySelector('input') || document.getElementById(labels[i].getAttribute('for'));
                    if (input) { input.click(); return 'checked English'; }
                    labels[i].click();
                    return 'clicked English label';
                  }
                }
                return null;
              })()
            `);
          }
          L("  Language: " + r); answered = !!r;
        }
        // Email consent
        else if (q.includes('email') && (q.includes('consent') || q.includes('optional') || q.includes('advertising'))) {
          let r = await selectRadio('I am fine not') || await selectRadio('No') || await selectRadio('decline');
          L("  Email consent: " + r); answered = !!r;
        }
        // ZIP/Postal
        else if (q.includes('zip') || q.includes('postal')) {
          let r = await setInputValue('zip_code', '83864') || await setInputValue('zipcode', '83864');
          if (!r) r = await setInputValue('', '83864');
          L("  ZIP: " + r); answered = !!r;
        }
        // State
        else if (q.includes('state') && (q.includes('which') || q.includes('what') || q.includes('live') || q.includes('reside'))) {
          let r = await selectRadio('Idaho');
          if (!r) {
            r = await eval_(`
              (function() {
                var sel = document.querySelector('#submitquestion select');
                if (sel) {
                  for (var i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].text.includes('Idaho')) {
                      sel.selectedIndex = i;
                      sel.dispatchEvent(new Event('change', {bubbles: true}));
                      return 'selected: Idaho';
                    }
                  }
                }
                return null;
              })()
            `);
          }
          L("  State: " + r); answered = !!r;
        }
        // Ethnicity
        else if (q.includes('ethnic') || q.includes('hispanic') || q.includes('latino')) {
          if (q.includes('hispanic') || q.includes('latino')) {
            let r = await selectRadio('No,') || await selectRadio('Not Hispanic') || await selectRadio('No');
            L("  Hispanic: " + r); answered = !!r;
          } else {
            let r = await selectRadio('White') || await selectRadio('Caucasian');
            L("  Race: " + r); answered = !!r;
          }
        }
        // Race
        else if (q.includes('race')) {
          let r = await selectRadio('White') || await selectRadio('Caucasian');
          L("  Race: " + r); answered = !!r;
        }
        // Education
        else if (q.includes('education') || q.includes('degree') || q.includes('school level')) {
          let r = await selectRadio('Some college') || await selectRadio('some college') || await selectRadio('Completed some college');
          if (!r) r = await selectRadio("Bachelor");
          L("  Education: " + r); answered = !!r;
        }
        // Employment
        else if (q.includes('employ') || q.includes('work status') || q.includes('job status') || q.includes('occupation')) {
          let r = await selectRadio('Self-employed') || await selectRadio('Self employed');
          if (!r) r = await selectRadio('Employed full') || await selectRadio('Full-time');
          L("  Employment: " + r); answered = !!r;
        }
        // Income
        else if (q.includes('income') || q.includes('salary') || q.includes('household') || q.includes('earn') || q.includes('annual')) {
          let r = await selectRadio('$75,000') || await selectRadio('75,000') || await selectRadio('$70,000') || await selectRadio('$80,000');
          if (!r && radios.length > 0) {
            let mid = radios[Math.floor(radios.length / 2)];
            r = await selectRadioById(mid.id);
          }
          L("  Income: " + r); answered = !!r;
        }
        // Marital
        else if (q.includes('marital') || q.includes('married') || q.includes('relationship status')) {
          let r = await selectRadio('Single') || await selectRadio('Never married') || await selectRadio('Divorced');
          L("  Marital: " + r); answered = !!r;
        }
        // Children
        else if (q.includes('children') || q.includes('kids') || q.includes('child')) {
          let r = await selectRadio('None') || await selectRadio('No children') || await selectRadio('0');
          if (!r) r = await selectRadio('No');
          L("  Children: " + r); answered = !!r;
        }
        // Industry/Work
        else if (q.includes('industry') || q.includes('sector') || q.includes('field of work')) {
          let r = await selectRadio('Architecture') || await selectRadio('Construction') || await selectRadio('Engineering');
          if (!r) r = await selectRadio('Other');
          L("  Industry: " + r); answered = !!r;
        }
        // --- Generic/Survey Questions ---
        else {
          // Group radio buttons by name
          let radioGroups = {};
          radios.forEach(r => { if (!radioGroups[r.name]) radioGroups[r.name] = []; radioGroups[r.name].push(r); });
          let groupNames = Object.keys(radioGroups);

          if (groupNames.length > 0) {
            for (let name of groupNames) {
              let group = radioGroups[name];
              // For Likert scales/agreement: pick middle
              let midIdx = Math.floor(group.length / 2);
              // If labels suggest scale (strongly agree...disagree), pick "Neutral" or "Agree"
              let neutral = group.find(g => g.label.toLowerCase().includes('neutral') || g.label.toLowerCase().includes('neither'));
              let agree = group.find(g => g.label.toLowerCase().includes('agree') && !g.label.toLowerCase().includes('disagree') && !g.label.toLowerCase().includes('strongly'));
              let pick = neutral || agree || group[midIdx];
              await selectRadioById(pick.id);
              L("  Radio[" + name + "]: " + pick.label.substring(0, 40));
            }
            answered = true;
          } else if (checkboxes.length > 0) {
            // Check first checkbox
            await selectRadioById(checkboxes[0].id);
            L("  Checkbox: " + checkboxes[0].label.substring(0, 40));
            answered = true;
          } else if (selects.length > 0) {
            for (let sel of selects) {
              await eval_(`
                (function() {
                  var s = document.getElementById('${sel.id}');
                  if (s && s.options.length > 1) {
                    s.selectedIndex = Math.min(2, s.options.length - 1);
                    s.dispatchEvent(new Event('change', {bubbles: true}));
                  }
                })()
              `);
            }
            L("  Select: picked option");
            answered = true;
          } else if (textInputs.length > 0) {
            for (let tf of textInputs) {
              await setInputValue(tf.name || '', '5');
            }
            L("  Text input: entered 5");
            answered = true;
          } else {
            L("  NO HANDLER for: " + pageText.substring(0, 100));
          }
        }

        // Submit
        await sleep(500);
        let submitR = await submitForm();
        L("  Submit: " + submitR);
        await sleep(2000);
      }

      // Final state
      let finalUrl = await eval_(`window.location.href`);
      L("\nFINAL URL: " + finalUrl);
      let finalText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("FINAL PAGE: " + finalText.substring(0, 1000));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_final.png', Buffer.from(ss.data, 'base64'));
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
