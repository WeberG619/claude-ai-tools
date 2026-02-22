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
      L("=== CHECKING UHRS ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/51749/edit'`);
      await sleep(5000);

      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L(pageText.substring(0, 2500));

      // Check for UHRS links or iframes
      let links = await eval_(`
        (function() {
          var links = [];
          document.querySelectorAll('a[href]').forEach(function(a) {
            var t = a.textContent.trim();
            var h = a.href;
            if (h.includes('uhrs') || h.includes('microsoft') || h.includes('prod.uhrs') || t.toLowerCase().includes('uhrs') || t.toLowerCase().includes('start')) {
              links.push({ text: t.substring(0, 60), href: h.substring(0, 150) });
            }
          });
          return JSON.stringify(links);
        })()
      `);
      L("\nUHRS links: " + links);

      let iframes = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('iframe')).map(f => ({ src: (f.src||'').substring(0,150), id: f.id })))`);
      L("Iframes: " + iframes);

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
