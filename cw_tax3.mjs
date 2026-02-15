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
      // Go to jobs page where we know the tax banner is
      L("=== GOING TO JOBS PAGE ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
      await sleep(5000);

      // Find and get the tax link href
      let taxLink = await eval_(`
        (function() {
          var all = document.querySelectorAll('a[href]');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim().toLowerCase();
            if (t.includes('tax') || t.includes('complete tax')) {
              return all[i].href;
            }
          }
          // Try buttons too
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().toLowerCase().includes('tax')) {
              return 'button: ' + btns[i].textContent.trim();
            }
          }
          return 'not found';
        })()
      `);
      L("Tax link: " + taxLink);

      // Click the tax link
      if (taxLink !== 'not found') {
        let r = await eval_(`
          (function() {
            var all = document.querySelectorAll('a[href]');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim().toLowerCase();
              if (t.includes('tax') || t.includes('complete tax')) {
                all[i].click();
                return 'clicked: ' + all[i].textContent.trim();
              }
            }
            return 'not clicked';
          })()
        `);
        L("Click: " + r);
        await sleep(5000);

        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("\nURL: " + url);
        L("Page:\n" + pageText.substring(0, 2500));
      }

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
