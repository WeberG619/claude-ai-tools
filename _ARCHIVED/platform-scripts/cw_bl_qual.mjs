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

    // Helper: answer a question by clicking option text then Continue
    const answerQuestion = async (optionText) => {
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 500));

      // Click the option
      let clickResult = await eval_(`
        (function() {
          var options = document.querySelectorAll('div, span, label, li, button, p');
          for (var i = 0; i < options.length; i++) {
            var t = options[i].textContent.trim();
            if (t === '${optionText}' && options[i].children.length <= 2) {
              options[i].click();
              return 'clicked: ' + t;
            }
          }
          // Try partial match
          for (var i = 0; i < options.length; i++) {
            var t = options[i].textContent.trim();
            if (t.includes('${optionText}') && t.length < 60 && options[i].children.length <= 2) {
              options[i].click();
              return 'clicked partial: ' + t;
            }
          }
          return 'not found: ${optionText}';
        })()
      `);
      L("Option click: " + clickResult);
      await sleep(1000);

      // Click Continue
      let contResult = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, [role="button"], a');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Continue' || t === 'Next' || t === 'Submit') {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'no continue button';
        })()
      `);
      L("Continue: " + contResult);
      await sleep(3000);
    };

    (async () => {
      // Q1: Industry - select Architecture
      L("=== Q1: INDUSTRY ===");
      await answerQuestion('Architecture');

      // Q2: Read the question and answer
      L("\\n=== Q2 ===");
      let q2Text = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Q2 page: " + q2Text.substring(0, 800));

      // Determine answer based on question content
      // Common qualification questions: age, gender, income, education, ethnicity, etc.
      // Weber: Male, 51, $75K income, Some college, White, Not Hispanic, Single, Self-employed
      let q2Answer = await eval_(`
        (function() {
          var text = document.body.innerText;
          // Determine question type and return best answer
          if (text.includes('gender') || text.includes('Gender')) return 'Male';
          if (text.includes('age') || text.includes('Age') || text.includes('old are you') || text.includes('birth')) return '50-54';
          if (text.includes('income') || text.includes('Income') || text.includes('earn')) return '$75,000';
          if (text.includes('education') || text.includes('Education') || text.includes('degree')) return 'Some college';
          if (text.includes('Hispanic') || text.includes('Latino') || text.includes('hispanic')) return 'No';
          if (text.includes('race') || text.includes('Race') || text.includes('ethnicity') || text.includes('Ethnicity')) return 'White';
          if (text.includes('marital') || text.includes('Marital') || text.includes('married')) return 'Single';
          if (text.includes('employed') || text.includes('employment') || text.includes('Employment') || text.includes('work status')) return 'Self-employed';
          if (text.includes('children') || text.includes('Children') || text.includes('kids')) return 'None';
          if (text.includes('state') || text.includes('State') || text.includes('where do you live')) return 'Idaho';
          if (text.includes('zip') || text.includes('ZIP') || text.includes('postal')) return '83864';
          // Return the question text so we can decide
          var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
          return 'UNKNOWN_Q: ' + lines.slice(0, 10).join(' | ');
        })()
      `);
      L("Q2 detected answer: " + q2Answer);

      if (!q2Answer.startsWith('UNKNOWN_Q')) {
        // Try clicking the answer - for range answers, try flexible matching
        let clicked = await eval_(`
          (function() {
            var answer = '${q2Answer}';
            var options = document.querySelectorAll('div, span, label, li, button, p');
            // Exact match first
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t === answer && options[i].children.length <= 2) {
                options[i].click();
                return 'exact: ' + t;
              }
            }
            // Partial/contains match
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t.length < 60 && options[i].children.length <= 2) {
                // For age ranges like 50-54, 45-54, etc
                if (answer === '50-54' && (t.includes('50') || t.includes('45-54') || t.includes('50-54') || t.includes('51'))) {
                  options[i].click();
                  return 'age match: ' + t;
                }
                // For income ranges
                if (answer.includes('75,000') && (t.includes('75,000') || t.includes('70,000') || t.includes('50,000 - 99,999') || t.includes('$75') || t.includes('$70,000') || t.includes('$50,000'))) {
                  options[i].click();
                  return 'income match: ' + t;
                }
                // Generic contains
                if (t.includes(answer)) {
                  options[i].click();
                  return 'contains: ' + t;
                }
              }
            }
            // List all visible options for debugging
            var opts = [];
            document.querySelectorAll('div, span, label, li').forEach(function(el) {
              var t = el.textContent.trim();
              if (t.length > 1 && t.length < 60 && el.children.length === 0) opts.push(t);
            });
            return 'NO_MATCH. Options: ' + opts.slice(0, 20).join(' | ');
          })()
        `);
        L("Q2 click: " + clicked);

        if (!clicked.startsWith('NO_MATCH')) {
          await sleep(1000);
          // Click Continue
          await eval_(`
            (function() {
              var btns = document.querySelectorAll('button, [role="button"]');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return 'ok'; }
              }
              return 'no btn';
            })()
          `);
          await sleep(3000);
        }
      }

      // Q3
      L("\\n=== Q3 ===");
      let q3Text = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Q3 page: " + q3Text.substring(0, 800));

      let q3Answer = await eval_(`
        (function() {
          var text = document.body.innerText;
          if (text.includes('gender') || text.includes('Gender')) return 'Male';
          if (text.includes('age') || text.includes('Age') || text.includes('old are you') || text.includes('birth')) return '50-54';
          if (text.includes('income') || text.includes('Income') || text.includes('earn')) return '$75,000';
          if (text.includes('education') || text.includes('Education') || text.includes('degree')) return 'Some college';
          if (text.includes('Hispanic') || text.includes('Latino') || text.includes('hispanic')) return 'No';
          if (text.includes('race') || text.includes('Race') || text.includes('ethnicity') || text.includes('Ethnicity')) return 'White';
          if (text.includes('marital') || text.includes('Marital') || text.includes('married')) return 'Single';
          if (text.includes('employed') || text.includes('employment') || text.includes('Employment') || text.includes('work status')) return 'Self-employed';
          if (text.includes('children') || text.includes('Children') || text.includes('kids')) return 'None';
          if (text.includes('state') || text.includes('State') || text.includes('where do you live')) return 'Idaho';
          if (text.includes('zip') || text.includes('ZIP') || text.includes('postal')) return '83864';
          var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
          return 'UNKNOWN_Q: ' + lines.slice(0, 10).join(' | ');
        })()
      `);
      L("Q3 detected answer: " + q3Answer);

      if (!q3Answer.startsWith('UNKNOWN_Q')) {
        let clicked = await eval_(`
          (function() {
            var answer = '${q3Answer}';
            var options = document.querySelectorAll('div, span, label, li, button, p');
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t === answer && options[i].children.length <= 2) { options[i].click(); return 'exact: ' + t; }
            }
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t.length < 60 && options[i].children.length <= 2) {
                if (answer === '50-54' && (t.includes('50') || t.includes('45-54') || t.includes('50-54') || t.includes('51'))) { options[i].click(); return 'age: ' + t; }
                if (answer.includes('75,000') && (t.includes('75,000') || t.includes('70,000') || t.includes('50,000 - 99,999') || t.includes('$75') || t.includes('$50,000'))) { options[i].click(); return 'income: ' + t; }
                if (t.includes(answer)) { options[i].click(); return 'contains: ' + t; }
              }
            }
            var opts = [];
            document.querySelectorAll('div, span, label, li').forEach(function(el) {
              var t = el.textContent.trim();
              if (t.length > 1 && t.length < 60 && el.children.length === 0) opts.push(t);
            });
            return 'NO_MATCH. Options: ' + opts.slice(0, 20).join(' | ');
          })()
        `);
        L("Q3 click: " + clicked);
        if (!clicked.startsWith('NO_MATCH')) {
          await sleep(1000);
          await eval_(`(function() { var btns = document.querySelectorAll('button'); for (var i = 0; i < btns.length; i++) { if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return; } } })()`);
          await sleep(3000);
        }
      }

      // Q4
      L("\\n=== Q4 ===");
      let q4Text = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Q4 page: " + q4Text.substring(0, 800));

      let q4Answer = await eval_(`
        (function() {
          var text = document.body.innerText;
          if (text.includes('gender') || text.includes('Gender')) return 'Male';
          if (text.includes('age') || text.includes('Age') || text.includes('old are you') || text.includes('birth')) return '50-54';
          if (text.includes('income') || text.includes('Income') || text.includes('earn')) return '$75,000';
          if (text.includes('education') || text.includes('Education') || text.includes('degree')) return 'Some college';
          if (text.includes('Hispanic') || text.includes('Latino') || text.includes('hispanic')) return 'No';
          if (text.includes('race') || text.includes('Race') || text.includes('ethnicity') || text.includes('Ethnicity')) return 'White';
          if (text.includes('marital') || text.includes('Marital') || text.includes('married')) return 'Single';
          if (text.includes('employed') || text.includes('employment') || text.includes('Employment') || text.includes('work status')) return 'Self-employed';
          if (text.includes('children') || text.includes('Children') || text.includes('kids')) return 'None';
          if (text.includes('state') || text.includes('State') || text.includes('where do you live')) return 'Idaho';
          if (text.includes('zip') || text.includes('ZIP') || text.includes('postal')) return '83864';
          var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
          return 'UNKNOWN_Q: ' + lines.slice(0, 10).join(' | ');
        })()
      `);
      L("Q4 detected answer: " + q4Answer);

      if (!q4Answer.startsWith('UNKNOWN_Q')) {
        let clicked = await eval_(`
          (function() {
            var answer = '${q4Answer}';
            var options = document.querySelectorAll('div, span, label, li, button, p');
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t === answer && options[i].children.length <= 2) { options[i].click(); return 'exact: ' + t; }
            }
            for (var i = 0; i < options.length; i++) {
              var t = options[i].textContent.trim();
              if (t.length < 60 && options[i].children.length <= 2) {
                if (answer === '50-54' && (t.includes('50') || t.includes('45-54') || t.includes('50-54') || t.includes('51'))) { options[i].click(); return 'age: ' + t; }
                if (answer.includes('75,000') && (t.includes('75,000') || t.includes('70,000') || t.includes('50,000 - 99,999') || t.includes('$75') || t.includes('$50,000'))) { options[i].click(); return 'income: ' + t; }
                if (t.includes(answer)) { options[i].click(); return 'contains: ' + t; }
              }
            }
            var opts = [];
            document.querySelectorAll('div, span, label, li').forEach(function(el) {
              var t = el.textContent.trim();
              if (t.length > 1 && t.length < 60 && el.children.length === 0) opts.push(t);
            });
            return 'NO_MATCH. Options: ' + opts.slice(0, 20).join(' | ');
          })()
        `);
        L("Q4 click: " + clicked);
        if (!clicked.startsWith('NO_MATCH')) {
          await sleep(1000);
          await eval_(`(function() { var btns = document.querySelectorAll('button'); for (var i = 0; i < btns.length; i++) { if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return; } } })()`);
          await sleep(3000);
        }
      }

      // Final state
      L("\\n=== FINAL STATE ===");
      let finalUrl = await eval_(`window.location.href`);
      let finalText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("URL: " + finalUrl);
      L("Page:\n" + finalText.substring(0, 2000));

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
