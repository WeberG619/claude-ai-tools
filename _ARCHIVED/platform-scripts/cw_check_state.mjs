import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 35000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("Tabs: " + tabs.length);
  tabs.forEach((t, i) => L(`  [${i}] ${t.type}: ${t.url.substring(0, 120)}`));

  const tab = tabs.find(t => t.type === "page");
  if (!tab) { L("No page tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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
      // Navigate to CPX Research partner page
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1072443/edit" });
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 1000));

      // Handle agreements/confirmations
      let hasAgree = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button, a.btn');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].value || btns[i].textContent || '').trim();
            if (t === 'Agree' || t.includes('Start') || t.includes('Accept') || t === 'OK') {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'none';
        })()
      `);
      L("Button clicked: " + hasAgree);
      if (hasAgree !== 'none') {
        await sleep(5000);
        url = await eval_(`window.location.href`);
        L("After click URL: " + url);
      }

      // Get iframes
      let iframes = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 300), w: f.width, h: f.height, id: f.id };
          }));
        })()
      `);
      L("Iframes: " + iframes);

      // Get page HTML structure
      let html = await eval_(`document.body.innerHTML.substring(0, 3000)`);
      L("HTML: " + html.substring(0, 1500));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_screen.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

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
