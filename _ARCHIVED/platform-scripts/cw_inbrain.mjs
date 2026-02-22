import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

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
      L("=== NAVIGATING TO INBRAIN ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1066135/edit'`);
      await sleep(5000);

      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 500));

      // Find the iframe
      let iframes = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('iframe')).map(f => ({ src: (f.src||'').substring(0,200), id: f.id, w: f.width, h: f.height })))`);
      L("Iframes: " + iframes);

      // Check all tabs - Inbrain might load in a new context
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
      allTabs.forEach(t => L("  " + t.type + ": " + (t.title||'').substring(0,40) + " | " + t.url.substring(0, 120)));

      // Try to find and connect to the Inbrain iframe
      let inbrainTarget = allTabs.find(t => t.url.includes('surveyb.in') || t.url.includes('inbrain'));
      if (inbrainTarget) {
        L("\nFound Inbrain target: " + inbrainTarget.url.substring(0, 150));

        // Connect to it
        const ws2 = new WebSocket(inbrainTarget.webSocketDebuggerUrl);
        await new Promise((res, rej) => {
          ws2.addEventListener("open", res);
          ws2.addEventListener("error", rej);
          setTimeout(rej, 5000);
        });

        let id2 = 0;
        const pending2 = new Map();
        ws2.addEventListener("message", e => {
          const m = JSON.parse(e.data);
          if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
        });
        const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
        const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

        let ibUrl = await eval2(`window.location.href`);
        let ibText = await eval2(`document.body.innerText.substring(0, 2000)`);
        L("\nInbrain URL: " + ibUrl);
        L("Inbrain page: " + ibText.substring(0, 800));

        // Screenshot
        const ss2 = await send2("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_inbrain.png', Buffer.from(ss2.data, 'base64'));
        L("Inbrain screenshot saved");

        ws2.close();
      } else {
        L("No Inbrain target found in CDP targets");

        // Try accessing the iframe content from parent
        let iframeContent = await eval_(`
          (function() {
            try {
              var iframe = document.querySelector('#provider-frame, iframe[src*="surveyb"]');
              if (!iframe) return 'no iframe';
              if (!iframe.contentDocument) return 'cross-origin iframe - cannot access';
              return iframe.contentDocument.body.innerText.substring(0, 500);
            } catch(e) {
              return 'error: ' + e.message;
            }
          })()
        `);
        L("Iframe content: " + iframeContent);
      }

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
