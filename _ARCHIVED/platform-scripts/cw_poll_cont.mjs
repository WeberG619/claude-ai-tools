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
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('ayet.io'));
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
      L("=== CLICKING CONTINUE ===");

      // Click Continue button
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked: ' + btns[i].textContent.trim(); }
          }
          // Try links too
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { links[i].click(); return 'clicked link: ' + links[i].textContent.trim(); }
          }
          return 'no continue button';
        })()
      `);
      L("Continue: " + r);
      await sleep(8000);

      // Check for new tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nTabs:");
      allTabs.forEach(t => { if (t.url) L("  " + t.type + ": " + t.url.substring(0, 150)); });

      // Check current page
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 800));

      // Find survey tab
      let surveyTab = allTabs.find(t => t.type === 'page' && !t.url.includes('ayet.io') && t.url.startsWith('http'));
      if (surveyTab) {
        L("\n*** SURVEY TAB: " + surveyTab.url);

        // Connect to survey tab
        const ws2 = new WebSocket(surveyTab.webSocketDebuggerUrl);
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

        let surveyUrl = await eval2(`window.location.href`);
        let surveyText = await eval2(`document.body.innerText.substring(0, 2000)`);
        L("\nSurvey URL: " + surveyUrl);
        L("Survey page: " + surveyText.substring(0, 800));

        // Take screenshot of survey
        const ss2 = await send2("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_start.png', Buffer.from(ss2.data, 'base64'));
        L("Survey screenshot saved");

        ws2.close();
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
