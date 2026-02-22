import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";

setTimeout(() => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'TIMEOUT - WS never opened');
  process.exit(1);
}, 10000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'No PS tab'); process.exit(1); }

  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Connecting to: ' + psTab.webSocketDebuggerUrl);

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
  ws.addEventListener("error", (e) => {
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'WS error: ' + JSON.stringify(e));
    process.exit(1);
  });
  ws.addEventListener("close", (e) => {
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'WS closed: code=' + e.code + ' reason=' + e.reason);
  });
  ws.addEventListener("open", () => {
    // Simple eval
    ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { expression: "document.title", returnByValue: true } }));
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id === 1) {
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'SUCCESS: title=' + JSON.stringify(m.result));
        process.exit(0);
      }
    });
  });
})().catch(e => {
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Fatal: ' + e.message);
  process.exit(1);
});
