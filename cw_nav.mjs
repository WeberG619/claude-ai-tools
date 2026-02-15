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
  const tab = tabs.find(t => t.type === "page");
  if (!tab) { out.push("No tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(0); }

  out.push("Tab URL: " + tab.url);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);

  ws.addEventListener("error", e => {
    out.push("WS error");
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  });

  ws.addEventListener("open", () => {
    out.push("WS open");
    let msgId = 1;

    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      out.push("MSG: " + JSON.stringify(m).substring(0, 300));

      if (m.id === 1) {
        // Got target info, now try Page.navigate
        ws.send(JSON.stringify({
          id: 2,
          method: "Page.navigate",
          params: { url: "https://workplace.clickworker.com/en/workplace/jobs" }
        }));
      }

      if (m.id === 2) {
        out.push("Navigation started, waiting 6s...");
        setTimeout(() => {
          // Try to evaluate after navigation
          ws.send(JSON.stringify({
            id: 3,
            method: "Runtime.evaluate",
            params: { expression: "document.title + ' ||| ' + window.location.href" }
          }));
        }, 6000);
      }

      if (m.id === 3) {
        out.push("EVAL RESULT: " + JSON.stringify(m.result).substring(0, 500));

        // Get page text
        ws.send(JSON.stringify({
          id: 4,
          method: "Runtime.evaluate",
          params: { expression: "document.body.innerText.substring(0, 4000)" }
        }));
      }

      if (m.id === 4) {
        out.push("PAGE_TEXT:");
        out.push(m.result?.result?.value || 'no value');
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
      }
    });

    // First: get Target info
    ws.send(JSON.stringify({
      id: 1,
      method: "Target.getTargetInfo"
    }));
  });
})().catch(e => {
  out.push("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
