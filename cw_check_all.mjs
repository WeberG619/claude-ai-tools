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
  // List all browser tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("=== ALL BROWSER TABS ===");
  tabs.forEach(t => L("  " + t.type + ": " + (t.title||'').substring(0,50) + " | " + t.url.substring(0, 120)));

  // Connect to main clickworker page
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (!pageTab) {
    // Try any page tab
    const anyPage = tabs.find(t => t.type === "page");
    if (anyPage) {
      L("\nNo clickworker tab, using: " + anyPage.url.substring(0, 100));
      const ws = new WebSocket(anyPage.webSocketDebuggerUrl);
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
          // Navigate to clickworker jobs
          L("\n=== NAVIGATING TO CLICKWORKER JOBS ===");
          await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
          await sleep(5000);

          let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
          L("\nJobs page:\n" + pageText.substring(0, 3000));

          // Get balance
          let balance = await eval_(`
            (function() {
              var el = document.querySelector('[class*="balance"], [class*="earning"]');
              if (el) return el.textContent.trim();
              // Try header area
              var all = document.body.innerText;
              var m = all.match(/\\$[\\d.]+/);
              return m ? m[0] : 'not found';
            })()
          `);
          L("\nBalance: " + balance);

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
    } else {
      L("No page tabs found at all");
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    }
    return;
  }

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
      // Go to jobs page
      L("\n=== NAVIGATING TO JOBS PAGE ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
      await sleep(5000);

      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("\nJobs page:\n" + pageText.substring(0, 3000));

      // Get balance
      let balance = await eval_(`
        (function() {
          var all = document.body.innerText;
          var m = all.match(/\\$[\\d.]+/);
          return m ? m[0] : 'balance not found';
        })()
      `);
      L("\nBalance: " + balance);

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
