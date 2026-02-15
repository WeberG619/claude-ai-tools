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
      // First get the UHRS login link href
      let uhrsLink = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href]');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t.includes('uhrs login') || t.includes('uhrs') && t.includes('login')) {
              return links[i].href;
            }
          }
          return 'not found';
        })()
      `);
      L("UHRS login link: " + uhrsLink);

      // Click the UHRS login link
      let r = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href]');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t.includes('uhrs login') || t.includes('uhrs') && t.includes('login')) {
              links[i].click();
              return 'clicked: ' + links[i].textContent.trim();
            }
          }
          return 'not found';
        })()
      `);
      L("Click: " + r);
      await sleep(10000);

      // Check all tabs - UHRS likely opens in new tab or same tab
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets after click:");
      allTabs.forEach(t => L("  " + t.type + ": " + (t.title||'').substring(0,50) + " | " + t.url.substring(0, 150)));

      // Check if we're on UHRS now or if a new tab opened
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nCurrent tab URL: " + url);
      L("Current page:\n" + pageText.substring(0, 1500));

      // Look for UHRS target in other tabs
      let uhrsTarget = allTabs.find(t => t.url.includes('uhrs') || t.url.includes('microsoft') || t.url.includes('prod.uhrs'));
      if (uhrsTarget && uhrsTarget.url !== url) {
        L("\nFound UHRS in separate tab: " + uhrsTarget.url.substring(0, 150));

        const ws2 = new WebSocket(uhrsTarget.webSocketDebuggerUrl);
        await new Promise((res, rej) => {
          ws2.addEventListener("open", res);
          ws2.addEventListener("error", rej);
          setTimeout(rej, 10000);
        });

        let id2 = 0;
        const pending2 = new Map();
        ws2.addEventListener("message", e => {
          const m = JSON.parse(e.data);
          if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
        });
        const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
        const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

        await sleep(5000);
        let uhrsUrl = await eval2(`window.location.href`);
        let uhrsText = await eval2(`document.body.innerText.substring(0, 3000)`);
        L("\nUHRS URL: " + uhrsUrl);
        L("UHRS page:\n" + uhrsText.substring(0, 2000));

        const ss2 = await send2("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_screen.png', Buffer.from(ss2.data, 'base64'));
        L("UHRS screenshot saved");

        ws2.close();
      }

      // Screenshot current tab too
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_main.png', Buffer.from(ss.data, 'base64'));

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
