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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Navigate to TapResearch
      const tapUrl = "https://www.tapresearch.com/router/offers/d6ed80f2feca2bbe1fec6f8c2c29ff8d?tid=919ee19884b43cc25c838eb54cc450ed57eadcd4&uid=25671709&pass_through_values=eyJqb2JfaWQiOjQ2ODIwMTk4NX0=&app_id=2316&timestamp=1770633403&sech=bea16f4f70dbca883eeaa1eb1efb21ac6053666f";
      await send("Page.navigate", { url: tapUrl });
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      // Click Begin button
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().toLowerCase().includes('begin')) {
              btns[i].click();
              return 'clicked Begin';
            }
          }
          // Also try links
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.trim().toLowerCase().includes('begin')) {
              links[i].click();
              return 'clicked Begin link';
            }
          }
          return 'Begin not found';
        })()
      `);
      L("Begin: " + r);
      await sleep(6000);

      url = await eval_(`window.location.href`);
      L("After Begin URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Get all clickable elements
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"], input[type="submit"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 80),
                type: els[i].type || '',
                href: (els[i].href || '').substring(0, 200),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 30));
        })()
      `);
      L("Clickable: " + r);

      // Get all inputs
      r = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            var rect = i.getBoundingClientRect();
            return {
              type: i.type, id: i.id, name: i.name,
              value: (i.value||'').substring(0,40),
              placeholder: (i.placeholder||'').substring(0,40),
              label: (i.labels&&i.labels[0])?i.labels[0].textContent.trim().substring(0,80):'',
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2)
            };
          }));
        })()
      `);
      L("Inputs: " + r);

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
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_profile.png', Buffer.from(ss.data, 'base64'));
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
