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
  L("Tabs: " + tabs.length);
  tabs.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));

  // Connect to PureSpectrum survey tab
  const surveyTab = tabs.find(t => t.type === "page" && (t.url.includes('purespectrum') || t.url.includes('screener')));
  if (!surveyTab) {
    L("No survey tab found, trying first page tab that isn't tapresearch");
    const otherTab = tabs.find(t => t.type === "page" && !t.url.includes('tapresearch'));
    if (otherTab) {
      L("Using: " + otherTab.url.substring(0, 100));
    }
  }

  const targetTab = surveyTab || tabs.find(t => t.type === "page" && !t.url.includes('tapresearch'));
  if (!targetTab) {
    L("No usable tab");
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  }

  const ws = new WebSocket(targetTab.webSocketDebuggerUrl);
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

    // Generic survey question answerer
    const answerQuestion = async (pageText) => {
      const q = pageText.toLowerCase();

      // Profile-based answers
      const profileAnswers = [
        // Gender
        { match: () => q.includes('gender') || (q.includes('are you') && (q.includes('male') || q.includes('female'))), answer: 'Male', alt: ['Man', 'male'] },
        // Age
        { match: () => q.includes('age') || q.includes('how old') || q.includes('year of birth') || q.includes('born'), answer: '51', alt: ['1974', '50-54', '45-54'] },
        // ZIP
        { match: () => q.includes('zip') || q.includes('postal'), answer: '83864', type: 'input' },
        // Hispanic
        { match: () => q.includes('hispanic') || q.includes('latino'), answer: 'No', alt: ['Not Hispanic', 'No, not'] },
        // Race
        { match: () => q.includes('ethnic') || q.includes('race') || q.includes('racial'), answer: 'White', alt: ['Caucasian'] },
        // Education
        { match: () => q.includes('education') || q.includes('degree') || q.includes('school'), answer: 'Some college', alt: ['some college', 'Associate', 'College'] },
        // Employment
        { match: () => q.includes('employ') || q.includes('work status') || q.includes('occupation'), answer: 'Self-employed', alt: ['Self', 'Employed full', 'Full-time'] },
        // Income
        { match: () => q.includes('income') || q.includes('salary') || q.includes('earn'), answer: '$75,000', alt: ['75,000', '$50,000 - $74,999', '$75,000 - $99,999'] },
        // Marital
        { match: () => q.includes('marital') || q.includes('married'), answer: 'Single', alt: ['Never married'] },
        // Children
        { match: () => q.includes('children') || q.includes('kids') || q.includes('parent'), answer: 'No', alt: ['None', '0', 'No children'] },
        // Country
        { match: () => q.includes('country') && (q.includes('live') || q.includes('reside')), answer: 'United States', alt: ['US', 'USA'] },
        // State
        { match: () => q.includes('state') && (q.includes('live') || q.includes('reside') || q.includes('which')), answer: 'Idaho', alt: ['ID'] },
        // Language
        { match: () => q.includes('language'), answer: 'English' },
        // Device
        { match: () => q.includes('device') || (q.includes('desktop') && q.includes('mobile')), answer: 'Desktop', alt: ['Computer', 'PC'] },
        // Industry
        { match: () => q.includes('industry') || q.includes('field of work'), answer: 'Architecture', alt: ['Construction', 'Engineering'] },
        // Housing
        { match: () => q.includes('own') && q.includes('rent'), answer: 'Rent', alt: ['Renting'] },
        // Smoking/tobacco
        { match: () => q.includes('smoke') || q.includes('tobacco') || q.includes('cigarette'), answer: 'No', alt: ['Never', 'Non-smoker'] },
        // Alcohol
        { match: () => q.includes('alcohol') || q.includes('drink'), answer: 'Occasionally', alt: ['Sometimes', 'Social', 'Rarely'] },
        // Health insurance
        { match: () => q.includes('health insurance') || q.includes('medical insurance'), answer: 'No', alt: ['None', 'Uninsured'] },
        // Car/vehicle
        { match: () => q.includes('car') || q.includes('vehicle') || q.includes('automobile'), answer: 'Yes', alt: ['Own'] },
        // Pet
        { match: () => q.includes('pet') || q.includes('dog') || q.includes('cat'), answer: 'No', alt: ['None'] },
      ];

      for (const pa of profileAnswers) {
        if (pa.match()) {
          return { answer: pa.answer, alt: pa.alt || [], type: pa.type || 'click' };
        }
      }

      return null;
    };

    (async () => {
      let lastUrl = '';
      let stuckCount = 0;
      let screenshotCount = 0;

      for (let step = 0; step < 50; step++) {
        await sleep(1000);
        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        let q = pageText.replace(/\n/g, ' ').trim();

        L("\n=== Q" + step + " ===");
        L("URL: " + url.substring(0, 150));
        L("Q: " + q.substring(0, 300));

        // Check for redirects / page changes
        if (url !== lastUrl) {
          stuckCount = 0;
          // Check for new tabs that might be the actual survey
          let currentTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          let newSurveyTab = currentTabs.find(t =>
            t.type === "page" &&
            !t.url.includes('tapresearch') &&
            t.url !== url &&
            t.url.length > 20
          );
          // Don't switch tabs, stay on current one
        } else {
          stuckCount++;
          if (stuckCount >= 3) {
            L("STUCK on same URL");
            break;
          }
        }
        lastUrl = url;

        let ql = q.toLowerCase();

        // Completion checks
        if (ql.includes('thank you for completing') || ql.includes('survey is complete') || ql.includes('survey complete') || ql.includes('you have completed')) {
          L("SURVEY COMPLETED!");
          break;
        }
        if (ql.includes('screened out') || ql.includes('not qualify') || ql.includes('sorry, you do not') || ql.includes('unfortunately') || ql.includes('do not match') || ql.includes('not eligible')) {
          L("SCREENED OUT");
          break;
        }
        if (ql.includes('redirecting') || q.length < 10) {
          L("Waiting for redirect/load...");
          await sleep(5000);
          continue;
        }

        // Try to answer based on profile
        let profileMatch = await answerQuestion(q);
        let answered = false;

        if (profileMatch) {
          if (profileMatch.type === 'input') {
            let r = await eval_(`
              (function() {
                var inp = document.querySelector('input[type="text"], input[type="number"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
                if (!inp) return 'no input found';
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(inp, '${profileMatch.answer}');
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                return 'set: ${profileMatch.answer}';
              })()
            `);
            L("  Input: " + r);
            answered = true;
          } else {
            // Try clicking the answer
            let allAnswers = [profileMatch.answer, ...(profileMatch.alt || [])];
            for (const ans of allAnswers) {
              let r = await eval_(`
                (function() {
                  var els = document.querySelectorAll('label, li, div, span, td, option, input[type="radio"]');
                  // Exact match first
                  for (var i = 0; i < els.length; i++) {
                    var t = els[i].textContent.trim();
                    if (t === '${ans}') {
                      els[i].click();
                      return 'exact: ' + t;
                    }
                  }
                  // Partial match
                  for (var i = 0; i < els.length; i++) {
                    var t = els[i].textContent.trim();
                    if (t.length < 100 && t.toLowerCase().includes('${ans}'.toLowerCase())) {
                      els[i].click();
                      return 'partial: ' + t;
                    }
                  }
                  // Radio buttons
                  var radios = document.querySelectorAll('input[type="radio"]');
                  for (var i = 0; i < radios.length; i++) {
                    var label = radios[i].labels && radios[i].labels[0] ? radios[i].labels[0].textContent.trim() : '';
                    if (label.toLowerCase().includes('${ans}'.toLowerCase()) || radios[i].value.toLowerCase().includes('${ans}'.toLowerCase())) {
                      radios[i].click();
                      return 'radio: ' + (label || radios[i].value);
                    }
                  }
                  return 'not found';
                })()
              `);
              if (!r.includes('not found')) {
                L("  Clicked: " + r);
                answered = true;
                break;
              }
            }
          }
        }

        // Generic survey answer for non-profile questions
        if (!answered) {
          // Check for Likert scale (strongly agree/disagree), pick neutral/agree
          if (ql.includes('agree') || ql.includes('disagree') || ql.includes('strongly')) {
            let r = await eval_(`
              (function() {
                var options = ['Somewhat agree', 'Agree', 'Slightly agree', 'Neutral', 'Neither'];
                var els = document.querySelectorAll('label, li, div, span, input[type="radio"]');
                for (var o = 0; o < options.length; o++) {
                  for (var i = 0; i < els.length; i++) {
                    var t = els[i].textContent.trim();
                    if (t.toLowerCase().includes(options[o].toLowerCase())) {
                      els[i].click();
                      return 'clicked: ' + t;
                    }
                  }
                }
                // Fallback: click middle radio
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                  var mid = Math.floor(radios.length / 2);
                  radios[mid].click();
                  return 'radio mid[' + mid + ']: ' + (radios[mid].labels?.[0]?.textContent || radios[mid].value || 'unnamed');
                }
                return 'no likert option found';
              })()
            `);
            L("  Likert: " + r);
            answered = true;
          }
          // Satisfaction / rating scale
          else if (ql.includes('satisfied') || ql.includes('rating') || ql.includes('rate') || ql.includes('likely') || ql.includes('scale')) {
            let r = await eval_(`
              (function() {
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) {
                  var mid = Math.floor(radios.length / 2);
                  radios[mid].click();
                  return 'radio mid[' + mid + '/' + radios.length + ']';
                }
                // Try clicking a number in the middle
                var all = document.querySelectorAll('label, div, span');
                var nums = [];
                for (var i = 0; i < all.length; i++) {
                  var t = all[i].textContent.trim();
                  if (/^\\d+$/.test(t) && parseInt(t) >= 1 && parseInt(t) <= 10) {
                    nums.push({ el: all[i], num: parseInt(t) });
                  }
                }
                if (nums.length > 0) {
                  var mid = nums[Math.floor(nums.length / 2)];
                  mid.el.click();
                  return 'number: ' + mid.num;
                }
                return 'no rating found';
              })()
            `);
            L("  Rating: " + r);
            answered = true;
          }
          // Generic: try to pick middle option
          else {
            let r = await eval_(`
              (function() {
                // Try radio buttons first
                var radios = document.querySelectorAll('input[type="radio"]:not(:checked)');
                if (radios.length > 0) {
                  var mid = Math.floor(radios.length / 2);
                  radios[mid].click();
                  return 'radio[' + mid + '/' + radios.length + ']: ' + (radios[mid].labels?.[0]?.textContent?.trim() || radios[mid].value || '').substring(0, 60);
                }
                // Try checkboxes
                var checks = document.querySelectorAll('input[type="checkbox"]:not(:checked)');
                if (checks.length > 0) {
                  checks[0].click();
                  return 'checkbox: ' + (checks[0].labels?.[0]?.textContent?.trim() || checks[0].value || '').substring(0, 60);
                }
                // Try select dropdowns
                var sels = document.querySelectorAll('select');
                for (var i = 0; i < sels.length; i++) {
                  if (sels[i].offsetParent && sels[i].options.length > 1) {
                    var mid = Math.floor(sels[i].options.length / 2);
                    sels[i].selectedIndex = mid;
                    sels[i].dispatchEvent(new Event('change', { bubbles: true }));
                    return 'select[' + mid + ']: ' + sels[i].options[mid].text;
                  }
                }
                return 'no interactive elements found';
              })()
            `);
            L("  Generic: " + r);
            if (!r.includes('no interactive elements')) answered = true;
          }
        }

        // Click Next/Continue/Submit
        await sleep(500);
        let r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button, input[type="submit"], a.btn, [role="button"]');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t === 'next' || t === 'continue' || t === 'submit' || t === 'done' || t.includes('next') || t.includes('>>')) {
                btns[i].click();
                return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            // Try form submit
            var form = document.querySelector('form');
            if (form) {
              try {
                HTMLFormElement.prototype.submit.call(form);
                return 'form submitted';
              } catch(e) {}
            }
            return 'no next button';
          })()
        `);
        L("  Next: " + r);
        await sleep(3000);

        // Take periodic screenshots
        if (step % 10 === 0 || step === 0) {
          const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
          writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_' + screenshotCount + '.png', Buffer.from(ss.data, 'base64'));
          screenshotCount++;
        }
      }

      // Final state
      let url = await eval_(`window.location.href`);
      L("\n=== FINAL ===");
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 1000));

      // Final screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_final.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

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
