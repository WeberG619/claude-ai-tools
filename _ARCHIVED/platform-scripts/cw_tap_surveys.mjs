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
      // Click "Let's go!" button
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().includes("Let's go")) {
              btns[i].click();
              return 'clicked Let\\'s go!';
            }
          }
          return 'not found';
        })()
      `);
      L("Let's go: " + r);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("Page text:");
      L(pageText.substring(0, 3000));

      // Get clickable elements
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 80),
                href: (els[i].href || '').substring(0, 250),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 30));
        })()
      `);
      L("Clickable: " + r);

      // Get iframes
      r = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 300), id: f.id, name: f.name };
          }));
        })()
      `);
      L("Iframes: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_surveys.png', Buffer.from(ss.data, 'base64'));
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
