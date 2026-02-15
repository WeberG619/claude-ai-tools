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
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
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
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    (async () => {
      // Navigate directly to BitLabs survey wall
      const bitlabsUrl = "https://web.bitlabs.ai/?token=7ce8ef68-4443-4a76-84d2-3bf78cffe955&uid=25671709&job_id=468201969&width=full_width&hash=14e990ed22c44f91fa76dba67360fa0a1959d38a";
      await send("Page.navigate", { url: bitlabsUrl });
      await sleep(6000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("PAGE TEXT:");
      L(pageText);

      // Get all clickable elements
      let clickables = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [onclick], [role="button"]');
          return JSON.stringify(Array.from(els).filter(function(e) {
            return e.offsetParent !== null;
          }).map(function(e) {
            return {
              tag: e.tagName,
              text: e.textContent.trim().substring(0, 100),
              href: (e.href || '').substring(0, 150),
              class: (e.className || '').substring(0, 80)
            };
          }).slice(0, 30));
        })()
      `);
      L("Clickables: " + clickables);

      // Get page HTML structure
      let html = await eval_(`document.body.innerHTML.substring(0, 3000)`);
      L("HTML: " + html);

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
