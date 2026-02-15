import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 60000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('uhrs'));
  if (!pageTab) {
    const anyPage = tabs.find(t => t.type === "page");
    if (!anyPage) { L("No page tabs"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
    // Use any page and navigate
    L("No UHRS tab, navigating...");
  }
  const target = pageTab || tabs.find(t => t.type === "page");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
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
      // First accept Terms of Service if needed
      let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      if (pageText.includes('Terms of Service')) {
        L("=== ACCEPTING TOS ===");
        // Check the checkbox
        let r = await eval_(`
          (function() {
            var cb = document.querySelector('input[type="checkbox"]');
            if (cb && !cb.checked) { cb.click(); return 'checked'; }
            if (cb && cb.checked) return 'already checked';
            return 'no checkbox';
          })()
        `);
        L("Checkbox: " + r);
        await sleep(500);

        // Click Accept/Submit/OK
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t.includes('accept') || t.includes('agree') || t === 'ok' || t === 'submit') {
                btns[i].click();
                return 'clicked: ' + btns[i].textContent.trim();
              }
            }
            return 'no accept button';
          })()
        `);
        L("Accept: " + r);
        await sleep(3000);
      }

      // Now scroll through the page and get all HIT apps
      L("\n=== UHRS MARKETPLACE - AVAILABLE HIT APPS ===");

      // Scroll to load all content
      await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
      await sleep(2000);
      await eval_(`window.scrollTo(0, 0)`);
      await sleep(1000);

      // Get full page text
      pageText = await eval_(`document.body.innerText.substring(0, 10000)`);
      L(pageText.substring(0, 8000));

      // Try to find task cards/rows with details
      let tasks = await eval_(`
        (function() {
          var results = [];
          // Look for task cards, rows, or list items with pay info
          var candidates = document.querySelectorAll('[class*="card"], [class*="hit"], [class*="task"], [class*="app"], tr, [class*="row"], [class*="item"]');
          for (var i = 0; i < candidates.length; i++) {
            var t = candidates[i].textContent.trim();
            if (t.length > 20 && t.length < 500 && (t.includes('$') || t.includes('cent') || t.includes('hit'))) {
              results.push(t.replace(/\\s+/g, ' ').substring(0, 200));
            }
          }
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      L("\n=== TASK DETAILS ===");
      L(tasks);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_tasks.png', Buffer.from(ss.data, 'base64'));
      L("\nScreenshot saved");

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
