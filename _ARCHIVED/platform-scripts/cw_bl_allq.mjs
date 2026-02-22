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
  const blTarget = tabs.find(t => t.url.includes('bitlabs'));
  if (!blTarget) { L("No BitLabs target"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(blTarget.webSocketDebuggerUrl);
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

    // Profile answers for Weber:
    // Male, 51 (DOB 3/18/1974), White, Not Hispanic, Single, No children
    // Self-employed, Architecture, Some college, ~$75K, Idaho 83864

    // Generic answer function: finds checkbox/radio by label text, checks it, clicks Continue
    const answerByCheckbox = async (targetText) => {
      let result = await eval_(`
        (function() {
          var checkboxes = document.querySelectorAll('input[type="checkbox"][name^="answers"], input[type="radio"][name^="answers"]');
          for (var i = 0; i < checkboxes.length; i++) {
            var label = checkboxes[i].closest('label');
            var parent = checkboxes[i].parentElement;
            // Walk up looking for text
            var el = checkboxes[i];
            for (var j = 0; j < 5; j++) {
              el = el.parentElement;
              if (!el) break;
              var t = el.textContent.trim();
              if (t === '${targetText}' || (t.includes('${targetText}') && t.length < ${targetText.length + 20})) {
                checkboxes[i].click();
                return 'checked: ' + t + ' (index ' + i + ', checked=' + checkboxes[i].checked + ')';
              }
            }
          }
          // Try with all text nodes
          var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          var node;
          while (node = walker.nextNode()) {
            if (node.textContent.trim() === '${targetText}') {
              var el = node.parentElement;
              while (el) {
                var cb = el.querySelector('input[type="checkbox"], input[type="radio"]');
                if (cb) { cb.click(); return 'checked via text walk: ' + cb.checked; }
                el = el.parentElement;
              }
            }
          }
          return 'NOT_FOUND';
        })()
      `);
      return result;
    };

    const clickContinue = async () => {
      await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              btns[i].disabled = false;
              btns[i].click();
              return;
            }
          }
        })()
      `);
      await sleep(3000);
    };

    const getPageInfo = async () => {
      return await eval_(`
        (function() {
          var text = document.body.innerText;
          var qMatch = text.match(/Question (\\d+)\\/(\\d+)/);
          var question = qMatch ? qMatch[0] : 'no question marker';
          // Get the question text (usually after the Question X/Y line)
          var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
          var qText = lines.slice(0, 5).join(' | ');
          // Get options
          var options = [];
          document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function(cb) {
            var el = cb.closest('label') || cb.parentElement;
            if (el) {
              var t = el.textContent.trim();
              if (t.length > 0 && t.length < 80) options.push(t);
            }
          });
          return JSON.stringify({ question: question, text: qText, options: options.slice(0, 25) });
        })()
      `);
    };

    (async () => {
      // Loop through questions
      for (let round = 0; round < 8; round++) {
        let info = await getPageInfo();
        let parsed;
        try { parsed = JSON.parse(info); } catch(e) { L("Parse error: " + info); break; }

        L("\n=== " + parsed.question + " ===");
        L("Q: " + parsed.text.substring(0, 200));
        L("Options: " + parsed.options.slice(0, 15).join(' | '));

        // Check if we're past the questions (survey started or redirected)
        if (!parsed.question.includes('Question') && !parsed.text.includes('Question')) {
          L("No more questions - survey may have started");
          break;
        }

        let text = parsed.text.toLowerCase();
        let opts = parsed.options.map(o => o.toLowerCase());
        let answer = null;

        // Determine answer based on question content
        if (text.includes('industry') || text.includes('work in')) {
          answer = 'Architecture';
        } else if (text.includes('gender') || text.includes('sex')) {
          // Look for Male option
          if (opts.some(o => o === 'male')) answer = 'Male';
          else if (opts.some(o => o.includes('man'))) answer = 'Man';
          else answer = 'Male';
        } else if (text.includes('age') || text.includes('old are you') || text.includes('year of birth') || text.includes('born') || text.includes('birthday')) {
          // Age 51, born 1974 - look for appropriate range
          for (let opt of parsed.options) {
            if (opt.includes('1974')) { answer = opt; break; }
            if (opt.includes('50-54') || opt.includes('50 - 54')) { answer = opt; break; }
            if (opt.includes('45-54') || opt.includes('45 - 54')) { answer = opt; break; }
            if (opt.includes('50-59') || opt.includes('50 to 59')) { answer = opt; break; }
            if (opt.includes('51')) { answer = opt; break; }
          }
          if (!answer) answer = parsed.options.find(o => o.includes('50')) || parsed.options.find(o => o.includes('45'));
        } else if (text.includes('income') || text.includes('earn') || text.includes('salary') || text.includes('household')) {
          // ~$75K
          for (let opt of parsed.options) {
            if (opt.includes('75,000') || opt.includes('$75')) { answer = opt; break; }
            if (opt.includes('70,000') || opt.includes('$70')) { answer = opt; break; }
            if ((opt.includes('50,000') || opt.includes('$50')) && (opt.includes('99,999') || opt.includes('100,000') || opt.includes('74,999'))) { answer = opt; break; }
          }
          if (!answer) {
            for (let opt of parsed.options) {
              if (opt.includes('75') || opt.includes('70')) { answer = opt; break; }
            }
          }
        } else if (text.includes('education') || text.includes('degree') || text.includes('school')) {
          for (let opt of parsed.options) {
            if (opt.toLowerCase().includes('some college') || opt.toLowerCase().includes('college, no degree')) { answer = opt; break; }
          }
          if (!answer) answer = parsed.options.find(o => o.toLowerCase().includes('college')) || parsed.options.find(o => o.toLowerCase().includes('associate'));
        } else if (text.includes('hispanic') || text.includes('latino')) {
          answer = parsed.options.find(o => o === 'No' || o === 'No, not of Hispanic' || o.toLowerCase().includes('not')) || 'No';
        } else if (text.includes('race') || text.includes('ethnic')) {
          answer = parsed.options.find(o => o.includes('White') || o.includes('Caucasian')) || 'White';
        } else if (text.includes('marital') || text.includes('married') || text.includes('relationship')) {
          answer = parsed.options.find(o => o.includes('Single') || o.includes('Never married')) || 'Single';
        } else if (text.includes('employ') || text.includes('work status') || text.includes('occupation')) {
          answer = parsed.options.find(o => o.toLowerCase().includes('self-employed') || o.toLowerCase().includes('self employed')) || parsed.options.find(o => o.toLowerCase().includes('full'));
        } else if (text.includes('children') || text.includes('kids') || text.includes('parent')) {
          answer = parsed.options.find(o => o === 'None' || o === '0' || o === 'No' || o.includes('no children') || o.includes('No children')) || 'None';
        } else if (text.includes('state') || text.includes('where do you live') || text.includes('region') || text.includes('location')) {
          answer = parsed.options.find(o => o.includes('Idaho') || o.includes('ID')) || 'Idaho';
        } else if (text.includes('zip') || text.includes('postal')) {
          // This would need a text input, handle separately
          L("ZIP code question detected - needs text input");
        }

        if (answer) {
          L("-> Answering: " + answer);
          let result = await answerByCheckbox(answer);
          L("   Result: " + result);
          if (result === 'NOT_FOUND') {
            // Try partial matching
            let words = answer.split(' ');
            for (let word of words) {
              if (word.length > 3) {
                result = await answerByCheckbox(word);
                L("   Retry with '" + word + "': " + result);
                if (result !== 'NOT_FOUND') break;
              }
            }
          }
          await sleep(500);
          await clickContinue();
        } else {
          L("-> UNKNOWN QUESTION - cannot determine answer");
          L("   Full page: " + (await eval_(`document.body.innerText.substring(0, 1500)`)));
          break;
        }
      }

      // Final state
      L("\n=== FINAL STATE ===");
      let finalUrl = await eval_(`window.location.href`);
      let finalPage = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + finalUrl);
      L("Page:\n" + finalPage.substring(0, 2000));

      // Check all targets
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
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
