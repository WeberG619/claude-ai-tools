import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];

// Timeout the whole thing after 20 seconds
setTimeout(() => {
  out.push("TIMEOUT after 20s");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 20000);

(async () => {
  out.push("Fetching tabs...");
  const resp = await fetch(`${CDP_HTTP}/json`);
  const tabs = await resp.json();
  out.push("Tabs: " + tabs.length);

  let tab = tabs.find(t => t.type === "page" && (t.url.includes("clickworker") || t.url.includes("unipark")));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { out.push("No tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(0); }

  out.push("Tab: " + tab.url.substring(0, 100));
  out.push("WS: " + tab.webSocketDebuggerUrl);

  const ws = new WebSocket(tab.webSocketDebuggerUrl);

  ws.addEventListener("open", async () => {
    out.push("WS connected");
    let id = 1;
    const pending = new Map();

    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });

    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = id++;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });

    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    try {
      let r = await eval_(`return window.location.href`);
      out.push("Current URL: " + r);

      // Navigate to jobs
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
      await sleep(5000);

      r = await eval_(`return window.location.href`);
      out.push("Jobs URL: " + r);

      if (r.includes("two_fa")) {
        out.push("BLOCKED BY 2FA");
      } else {
        // Balance
        r = await eval_(`
          const text = document.body.innerText;
          const match = text.match(/Account balance \\$ ([\\d.]+)/);
          return match ? match[1] : 'balance-not-found';
        `);
        out.push("Balance: $" + r);

        // Page text
        r = await eval_(`return document.body.innerText.substring(0, 4000)`);
        out.push("PAGE_TEXT_START");
        out.push(r);
        out.push("PAGE_TEXT_END");
      }
    } catch (e) {
      out.push("Eval error: " + e.message);
    }

    ws.close();
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(0);
  });

  ws.addEventListener("error", (e) => {
    out.push("WS error: " + e.message);
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  });
})().catch(e => {
  out.push("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
