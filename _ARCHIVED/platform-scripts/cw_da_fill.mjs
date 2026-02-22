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
      L("=== FILLING DATAANNOTATION PROFILE ===");

      // 1. Set English to Native
      let r = await eval_(`
        (function() {
          // Find the language select
          var langSel = document.querySelector('select[name*="language_id"]');
          if (!langSel) return 'no language select';
          // Find English option
          for (var i = 0; i < langSel.options.length; i++) {
            if (langSel.options[i].text.includes('English')) {
              langSel.selectedIndex = i;
              langSel.dispatchEvent(new Event('change', { bubbles: true }));
              break;
            }
          }
          // Set fluency to Native
          var flSel = document.querySelector('select[name*="fluency"]');
          if (flSel) {
            for (var i = 0; i < flSel.options.length; i++) {
              if (flSel.options[i].text.toLowerCase().includes('native') || flSel.options[i].value === 'native') {
                flSel.selectedIndex = i;
                flSel.dispatchEvent(new Event('change', { bubbles: true }));
                return 'English set to ' + flSel.options[i].text;
              }
            }
          }
          return 'language set but fluency unclear';
        })()
      `);
      L("Language: " + r);

      // 2. Get all available skills to find relevant ones
      r = await eval_(`
        (function() {
          var skillSel = document.querySelector('select[name*="skill_id"]');
          if (!skillSel) return 'no skill select';
          var opts = [];
          for (var i = 0; i < skillSel.options.length; i++) {
            var t = skillSel.options[i].text;
            if (t.toLowerCase().includes('architect') || t.toLowerCase().includes('engineer') ||
                t.toLowerCase().includes('construction') || t.toLowerCase().includes('technology') ||
                t.toLowerCase().includes('software') || t.toLowerCase().includes('writing') ||
                t.toLowerCase().includes('data') || t.toLowerCase().includes('ai') ||
                t.toLowerCase().includes('design') || t.toLowerCase().includes('cad') ||
                t.toLowerCase().includes('3d') || t.toLowerCase().includes('math')) {
              opts.push(i + ': ' + t);
            }
          }
          return JSON.stringify(opts);
        })()
      `);
      L("Relevant skills: " + r);

      // 3. Get full skill list for reference
      let allSkills = await eval_(`
        (function() {
          var skillSel = document.querySelector('select[name*="skill_id"]');
          if (!skillSel) return '[]';
          var opts = [];
          for (var i = 0; i < skillSel.options.length; i++) {
            opts.push(i + ': ' + skillSel.options[i].text);
          }
          return JSON.stringify(opts);
        })()
      `);
      L("\nAll skills:\n" + allSkills);

      // 4. Fill background text
      r = await eval_(`
        (function() {
          var ta = document.querySelector('textarea[name*="skills_and_background"]');
          if (!ta) return 'no textarea';
          ta.value = 'Experienced BIM (Building Information Modeling) professional specializing in Autodesk Revit for architectural design and construction documentation. Strong technical writing skills with deep knowledge of architecture, engineering, and construction (AEC) industry. Proficient in 3D modeling, parametric design, and construction technology. Experience with Python scripting, automation, and AI-assisted workflows. Detail-oriented with strong analytical and critical thinking skills.';
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          ta.dispatchEvent(new Event('change', { bubbles: true }));
          return 'background filled';
        })()
      `);
      L("\nBackground: " + r);

      // Screenshot before submit
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_da_fill.png', Buffer.from(ss.data, 'base64'));

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
