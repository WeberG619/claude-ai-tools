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

    (async () => {
      // We're stuck on the Hispanic question. Fix: click the exact option text
      L("=== FIX HISPANIC ===");

      // First, let's see the DOM structure to understand the option elements
      let r = await eval_(`
        (function() {
          // Find all elements that look like options (specific text match)
          var all = document.querySelectorAll('*');
          var matches = [];
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            var ownText = '';
            for (var j = 0; j < all[i].childNodes.length; j++) {
              if (all[i].childNodes[j].nodeType === 3) ownText += all[i].childNodes[j].textContent;
            }
            ownText = ownText.trim();
            if (ownText === 'No, not of Hispanic, Latino, or Spanish origin' ||
                t === 'No, not of Hispanic, Latino, or Spanish origin') {
              matches.push({
                tag: all[i].tagName,
                class: (all[i].className || '').substring(0, 80),
                role: all[i].getAttribute('role') || '',
                ownText: ownText.substring(0, 80),
                fullText: t.substring(0, 80)
              });
            }
          }
          return JSON.stringify(matches);
        })()
      `);
      L("Hispanic option elements: " + r);

      // Try clicking the exact "No, not of Hispanic..." text
      r = await eval_(`
        (function() {
          var all = document.querySelectorAll('div, span, label, li, p, button');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t === 'No, not of Hispanic, Latino, or Spanish origin') {
              all[i].click();
              return 'clicked exact: ' + all[i].tagName + '.' + (all[i].className||'').substring(0,40);
            }
          }
          // Try contains "not of Hispanic"
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.includes('not of Hispanic') && t.length < 100) {
              all[i].click();
              return 'clicked partial: ' + t.substring(0, 60) + ' tag=' + all[i].tagName;
            }
          }
          return 'not found';
        })()
      `);
      L("Click No Hispanic: " + r);
      await sleep(1000);

      // Click Continue
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              btns[i].click();
              return 'clicked Continue';
            }
          }
          return 'Continue not found';
        })()
      `);
      L("Continue: " + r);
      await sleep(4000);

      // Now handle subsequent questions in a loop
      let lastQuestion = '';
      let stuckCount = 0;

      for (let step = 0; step < 20; step++) {
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        let q = pageText.substring(0, 400).replace(/\n/g, ' ').trim();
        L("\n=== STEP " + step + " ===");
        L("Q: " + q.substring(0, 250));

        // Stuck detection
        if (q.substring(0, 100) === lastQuestion.substring(0, 100)) {
          stuckCount++;
          if (stuckCount >= 2) {
            L("STUCK - breaking");
            break;
          }
        } else {
          stuckCount = 0;
        }
        lastQuestion = q;

        let ql = q.toLowerCase();

        // Survey wall / completion
        if (ql.includes('surveys') && (ql.includes('available') || ql.includes('earn') || ql.includes('complete'))) {
          L("SURVEY WALL REACHED!");
          break;
        }
        if (ql.includes('thank you') || ql.includes('profile complete') || ql.includes('all done')) {
          L("PROFILE COMPLETE!");
          break;
        }
        if (ql.includes('no surveys available') || ql.includes('come back later')) {
          L("NO SURVEYS AVAILABLE");
          break;
        }

        let answered = false;

        // Education
        if (ql.includes('education') || ql.includes('highest level') || ql.includes('degree')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t.toLowerCase().includes('some college') && t.length < 80) {
                  all[i].click();
                  return 'clicked: ' + t;
                }
              }
              return 'not found';
            })()
          `);
          L("  Education: " + r);
          answered = true;
        }
        // Employment
        else if (ql.includes('employ') || ql.includes('work') || ql.includes('job status')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim().toLowerCase();
                if ((t.includes('self') && t.includes('employ')) || t === 'self-employed') {
                  all[i].click();
                  return 'clicked: ' + all[i].textContent.trim();
                }
              }
              // Fallback: employed full-time
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim().toLowerCase();
                if (t.includes('employed full') || t === 'employed, full-time' || (t.includes('full') && t.includes('time') && t.includes('employ'))) {
                  all[i].click();
                  return 'clicked: ' + all[i].textContent.trim();
                }
              }
              return 'not found';
            })()
          `);
          L("  Employment: " + r);
          answered = true;
        }
        // Marital
        else if (ql.includes('marital') || ql.includes('married') || ql.includes('relationship')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === 'Single' || t === 'Single, never married' || t.toLowerCase() === 'single') {
                  all[i].click();
                  return 'clicked: ' + t;
                }
              }
              return 'not found';
            })()
          `);
          L("  Marital: " + r);
          answered = true;
        }
        // Children
        else if (ql.includes('children') || ql.includes('kids') || ql.includes('parent')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              // Try "No" or "None" or "0"
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === 'No' || t === 'None' || t === '0' || t === 'No children') {
                  all[i].click();
                  return 'clicked: ' + t;
                }
              }
              return 'not found';
            })()
          `);
          L("  Children: " + r);
          answered = true;
        }
        // Industry
        else if (ql.includes('industry') || ql.includes('field') || ql.includes('sector')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p, option');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim().toLowerCase();
                if (t.includes('architecture') || t.includes('construction') || t.includes('engineering')) {
                  all[i].click();
                  return 'clicked: ' + all[i].textContent.trim();
                }
              }
              return 'not found';
            })()
          `);
          L("  Industry: " + r);
          answered = true;
        }
        // State / region
        else if ((ql.includes('state') || ql.includes('region')) && !ql.includes('united states')) {
          r = await eval_(`
            (function() {
              var sel = document.querySelector('select');
              if (sel) {
                for (var i = 0; i < sel.options.length; i++) {
                  if (sel.options[i].text.includes('Idaho') || sel.options[i].value === 'ID') {
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'selected: Idaho';
                  }
                }
              }
              // Try clicking
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === 'Idaho' || t === 'ID') {
                  all[i].click();
                  return 'clicked: ' + t;
                }
              }
              return 'not found';
            })()
          `);
          L("  State: " + r);
          answered = true;
        }
        // Language
        else if (ql.includes('language')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === 'English') {
                  all[i].click();
                  return 'clicked: English';
                }
              }
              return 'not found';
            })()
          `);
          L("  Language: " + r);
          answered = true;
        }
        // Gender (in case it comes back)
        else if (ql.includes('gender') || ql.includes('sex')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if (t === 'Male') {
                  all[i].click();
                  return 'clicked: Male';
                }
              }
              return 'not found';
            })()
          `);
          L("  Gender: " + r);
          answered = true;
        }
        // Homeowner/rent
        else if (ql.includes('own') && ql.includes('rent') || ql.includes('homeowner') || ql.includes('housing')) {
          r = await eval_(`
            (function() {
              var all = document.querySelectorAll('div, span, label, li, p');
              for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim().toLowerCase();
                if (t === 'rent' || t === 'renting' || t.includes('rent')) {
                  all[i].click();
                  return 'clicked: ' + all[i].textContent.trim();
                }
              }
              return 'not found';
            })()
          `);
          L("  Housing: " + r);
          answered = true;
        }

        // Generic fallback - try to click an option
        if (!answered) {
          r = await eval_(`
            (function() {
              // Look for radio-like options (not question text, not buttons)
              var options = [];
              var all = document.querySelectorAll('[role="radio"], [role="option"], [class*="option"], [class*="answer"], [class*="choice"]');
              for (var i = 0; i < all.length; i++) {
                var rect = all[i].getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                  options.push(all[i]);
                }
              }
              if (options.length > 0) {
                var mid = Math.floor(options.length / 2);
                options[mid].click();
                return 'clicked generic[' + mid + '/' + options.length + ']: ' + options[mid].textContent.trim().substring(0, 60);
              }
              return 'no options found';
            })()
          `);
          L("  Generic: " + r);
        }

        // Click Continue
        await sleep(500);
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t === 'continue' || t === 'next' || t === 'submit' || t === 'done') {
                btns[i].click();
                return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            return 'no button found';
          })()
        `);
        L("  Submit: " + r);
        await sleep(3000);
      }

      // Final state
      let url = await eval_(`window.location.href`);
      L("\n=== FINAL STATE ===");
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page: " + pageText.substring(0, 1500));

      // Get buttons/links
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 80),
                href: (els[i].href || '').substring(0, 200),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 20));
        })()
      `);
      L("Clickable: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_final.png', Buffer.from(ss.data, 'base64'));
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
