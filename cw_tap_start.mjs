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
  L("Tabs: " + tabs.length);
  tabs.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));
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
      // First, find and click "LET'S GO!" - it might be in a shadow DOM or specific div
      let r = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          var matches = [];
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t === "LET'S GO!" || t === "LET\\'S GO!" || t.toUpperCase() === "LET'S GO!") {
              var rect = all[i].getBoundingClientRect();
              matches.push({
                tag: all[i].tagName,
                class: (all[i].className || '').substring(0, 80),
                text: t,
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                clickable: !!all[i].onclick || all[i].tagName === 'BUTTON' || all[i].tagName === 'A'
              });
            }
          }
          return JSON.stringify(matches);
        })()
      `);
      L("LET'S GO elements: " + r);

      let elements = [];
      try { elements = JSON.parse(r); } catch(e) {}

      if (elements.length > 0) {
        // Click the smallest (most specific) element
        elements.sort((a, b) => (a.w * a.h) - (b.w * b.h));
        let el = elements[0];
        L("Clicking at (" + el.x + ", " + el.y + ")");
        await clickAt(el.x, el.y);
      } else {
        // Try JS click
        r = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.includes("LET") && t.includes("GO")) {
                all[i].click();
                return 'clicked: ' + all[i].tagName + ' ' + t.substring(0, 30);
              }
            }
            return 'not found';
          })()
        `);
        L("JS click: " + r);
      }

      await sleep(10000);

      // Check if new tab opened
      const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs after click: " + tabs2.length);
      tabs2.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 200)));

      // If there's a new page tab, connect to it
      let surveyTab = tabs2.find(t => t.type === "page" && !t.url.includes('tapresearch.com'));
      if (!surveyTab) surveyTab = tabs2.find(t => t.type === "page");

      // Check current page state
      let url = await eval_(`window.location.href`);
      L("Current URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Check for iframes (survey might be embedded)
      r = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 400), id: f.id, name: f.name,
                     w: f.offsetWidth, h: f.offsetHeight };
          }));
        })()
      `);
      L("Iframes: " + r);

      // Get all visible elements for debugging
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"], input[type="submit"], input[type="radio"], input[type="checkbox"], label');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                type: els[i].type || '',
                text: els[i].textContent.trim().substring(0, 80),
                id: els[i].id,
                name: els[i].name || '',
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 30));
        })()
      `);
      L("Elements: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_start.png', Buffer.from(ss.data, 'base64'));
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
