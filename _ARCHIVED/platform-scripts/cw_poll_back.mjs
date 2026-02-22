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
      L("=== NAVIGATING BACK TO SURVEY WALL ===");

      // Navigate to the Clickworker jobs page to check balance and try other platforms
      let r = await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/'`);
      await sleep(5000);

      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 1000));

      // Get balance
      let balance = await eval_(`
        (function() {
          var text = document.body.innerText;
          var m = text.match(/Account balance \\$ ([\\d.]+)/);
          return m ? m[1] : 'not found';
        })()
      `);
      L("\n*** BALANCE: $" + balance + " ***");

      // Get available jobs
      let jobs = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href*="/jobs/"]');
          var jobs = [];
          for (var i = 0; i < links.length; i++) {
            var href = links[i].href;
            var text = links[i].textContent.trim().substring(0, 80);
            if (text.length > 3 && !jobs.some(j => j.href === href)) {
              jobs.push({ text: text, href: href.substring(href.lastIndexOf('/') - 20) });
            }
          }
          return JSON.stringify(jobs.slice(0, 20));
        })()
      `);
      L("Jobs: " + jobs);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_done.png', Buffer.from(ss.data, 'base64'));

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
