import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs.find(t => t.type === "page");
  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
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

    (async () => {
      L("=== ADDING SKILLS ===");

      // First select a skill from the dropdown
      // Skills to add: Python, JavaScript, C#, Content Writing, Professional Writing, Data Science
      const skillsToAdd = [
        'Software Engineering > Python',
        'Software Engineering > JavaScript',
        'Software Engineering > C#',
        'Writing > Content Writing',
        'Writing > Professional / Business Writing',
        'Mathematics > Data Science'
      ];

      // Check how the skill addition mechanism works
      let r = await eval_(`
        (function() {
          // Find all skill-related selects
          var selects = document.querySelectorAll('select[name*="skill_id"]');
          var addBtns = [];
          document.querySelectorAll('a, button').forEach(function(el) {
            var t = el.textContent.trim().toLowerCase();
            if (t.includes('add') && (t.includes('skill') || t.includes('new'))) {
              addBtns.push(el.textContent.trim());
            }
          });
          return JSON.stringify({ skillSelects: selects.length, addButtons: addBtns });
        })()
      `);
      L("Skill mechanism: " + r);

      // Select first skill
      for (let si = 0; si < skillsToAdd.length; si++) {
        const skill = skillsToAdd[si];
        r = await eval_(`
          (function() {
            var selects = document.querySelectorAll('select[name*="skill_id"]');
            var lastSel = selects[selects.length - 1];
            if (!lastSel) return 'no select';
            for (var i = 0; i < lastSel.options.length; i++) {
              if (lastSel.options[i].text === '${skill}') {
                lastSel.selectedIndex = i;
                lastSel.dispatchEvent(new Event('change', { bubbles: true }));
                return 'selected: ' + lastSel.options[i].text;
              }
            }
            return 'not found: ${skill}';
          })()
        `);
        L("Skill " + si + ": " + r);
        await sleep(500);

        // Click "Add new skill" if it exists
        if (si < skillsToAdd.length - 1) {
          r = await eval_(`
            (function() {
              var links = document.querySelectorAll('a, button');
              for (var i = 0; i < links.length; i++) {
                var t = links[i].textContent.trim().toLowerCase();
                if (t.includes('add') && t.includes('skill')) {
                  links[i].click();
                  return 'clicked add skill';
                }
                if (t === 'add new skill') {
                  links[i].click();
                  return 'clicked add new skill';
                }
              }
              // Try looking for + button or add link near skills section
              var addLinks = document.querySelectorAll('[class*="add"], [class*="new"]');
              for (var i = 0; i < addLinks.length; i++) {
                var t = addLinks[i].textContent.trim();
                if (t.includes('Add') || t === '+') {
                  addLinks[i].click();
                  return 'clicked: ' + t;
                }
              }
              return 'no add button';
            })()
          `);
          L("  Add: " + r);
          await sleep(500);
        }
      }

      // Now scroll down and click Update
      await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
      await sleep(500);

      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button[type="submit"]');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].value === 'Update' || btns[i].textContent.trim() === 'Update') {
              btns[i].click();
              return 'clicked Update';
            }
          }
          return 'no update button';
        })()
      `);
      L("\nSubmit: " + r);
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nAfter update URL: " + url);
      L("Page:\n" + pageText.substring(0, 1000));

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
