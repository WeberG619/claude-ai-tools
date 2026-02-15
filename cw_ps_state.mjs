import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";

setTimeout(() => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'TIMEOUT');
  process.exit(1);
}, 15000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'No PS tab. Tabs: ' + tabs.map(t => t.url.substring(0,40)).join(', ')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'WS error'); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    // NO awaitPromise
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result?.value; };

    (async () => {
      let url = await eval_(`window.location.href`);
      let text = await eval_(`document.body ? document.body.innerText.substring(0, 800) : 'no body'`);
      let drags = await eval_(`document.querySelectorAll('.cdk-drag').length`);
      let imgs = await eval_(`
        (function() {
          var r = [];
          document.querySelectorAll('.cdk-drag img').forEach(function(i) { r.push(i.alt); });
          return r.join(',');
        })()
      `);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt',
        'URL: ' + url + '\nDrags: ' + drags + '\nImgs: ' + imgs + '\n\nText:\n' + text);
      ws.close();
      process.exit(0);
    })().catch(e => {
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Error: ' + e.message);
      ws.close(); process.exit(1);
    });
  });
})().catch(e => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Fatal: ' + e.message);
  process.exit(1);
});
