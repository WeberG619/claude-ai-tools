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
      // Navigate to TapResearch job page
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1079431/edit" });
      await sleep(6000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 800));

      // Handle agreements
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button');
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
      L("Button: " + r);
      if (r !== 'none') {
        await sleep(5000);
        url = await eval_(`window.location.href`);
        L("After click URL: " + url);
      }

      // Get iframes
      let iframes = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 300), id: f.id };
          }));
        })()
      `);
      L("Iframes: " + iframes);

      // Take screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_screen.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      // Also try Inbrain and PollTastic
      for (const jobId of ['1066135', '1225955']) {
        L("\n--- Job " + jobId + " ---");
        await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/" + jobId + "/edit" });
        await sleep(6000);

        url = await eval_(`window.location.href`);
        L("URL: " + url);
        pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
        L("Page: " + pageText.substring(0, 500));

        // Handle agreements
        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('input[type="submit"], button');
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
        L("Button: " + r);
        if (r !== 'none') {
          await sleep(5000);
        }

        // Get iframes
        iframes = await eval_(`
          (function() {
            var iframes = document.querySelectorAll('iframe');
            return JSON.stringify(Array.from(iframes).map(function(f) {
              return { src: (f.src || '').substring(0, 300), id: f.id };
            }));
          })()
        `);
        L("Iframes: " + iframes);
      }

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
