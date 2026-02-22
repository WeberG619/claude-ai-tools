import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

setTimeout(() => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'TIMEOUT');
  process.exit(1);
}, 15000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let result = "=== ALL TABS ===\n";
  for (let t of tabs) {
    if (t.type === "page" || t.type === "iframe") {
      result += t.type + ": " + t.title.substring(0, 40) + " | " + t.url.substring(0, 80) + "\n";
    }
  }

  // Check BitLabs iframe
  const blFrame = tabs.find(t => t.type === "iframe" && t.url.includes('bitlabs'));
  if (blFrame) {
    const ws = new WebSocket(blFrame.webSocketDebuggerUrl);
    ws.addEventListener("error", () => { result += "\nBL WS error"; writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', result); process.exit(1); });
    ws.addEventListener("open", () => {
      let id = 0;
      const pending = new Map();
      ws.addEventListener("message", e => {
        const m = JSON.parse(e.data);
        if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
      });
      const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
      const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result?.value; };

      (async () => {
        let url = await eval_(`window.location.href`);
        let text = await eval_(`document.body ? document.body.innerText.substring(0, 1500) : 'no body'`);
        result += "\n=== BITLABS ===\nURL: " + url + "\nText:\n" + text;
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', result);
        process.exit(0);
      })().catch(e => {
        result += "\nError: " + e.message;
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', result);
        process.exit(1);
      });
    });
  } else {
    result += "\nNo BitLabs iframe found.";
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', result);
    process.exit(0);
  }
})().catch(e => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Fatal: ' + e.message);
  process.exit(1);
});
