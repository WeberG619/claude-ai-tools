import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

setTimeout(() => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'TIMEOUT');
  process.exit(1);
}, 15000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'No PS tab'); process.exit(1); }

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
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      let url = await eval_(`window.location.href`);
      let text = await eval_(`document.body ? document.body.innerText.substring(0, 1000) : 'no body'`);
      let drags = await eval_(`document.querySelectorAll('.cdk-drag').length`);
      let drops = await eval_(`document.querySelectorAll('.cdk-drop-list').length`);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt',
        'URL: ' + url + '\nDrags: ' + drags + ' Drops: ' + drops + '\n\nText:\n' + text);
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
