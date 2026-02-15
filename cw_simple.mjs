import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const out = [];

setTimeout(() => {
  out.push("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 15000);

(async () => {
  const resp = await fetch(`${CDP_HTTP}/json`);
  const tabs = await resp.json();
  out.push("Tabs: " + JSON.stringify(tabs.map(t => ({url: t.url?.substring(0, 80), type: t.type, id: t.id}))));

  let tab = tabs.find(t => t.type === "page");
  if (!tab) { out.push("No page tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(0); }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);

  const result = await new Promise((resolve, reject) => {
    ws.addEventListener("error", e => reject(new Error("WS error")));

    ws.addEventListener("open", () => {
      out.push("WS open");

      // Simple evaluate without async wrapper
      const msg = JSON.stringify({
        id: 1,
        method: "Runtime.evaluate",
        params: { expression: "document.title + ' | ' + window.location.href" }
      });
      out.push("Sending: " + msg.substring(0, 100));
      ws.send(msg);
    });

    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      out.push("Got msg id=" + m.id + " method=" + (m.method || 'none'));
      if (m.id === 1) {
        resolve(m);
      }
    });
  });

  out.push("Result: " + JSON.stringify(result).substring(0, 500));
  ws.close();
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(0);
})().catch(e => {
  out.push("Error: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
